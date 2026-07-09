"""LLM 에이전트 (OpenAI function calling).

사용자 자연어 → LLM 이 control_device / read_data 도구를 호출 → 온실별 IoT 어댑터 실행 →
자연어 응답. 의존성(온실별 IoT 어댑터, 온실 이름, 실시간 상태 조회 함수, OpenAI 클라이언트,
모델명)은 생성자로 주입받는다.

온실 지정: 도구 인자 greenhouse_id 로 대상 온실을 고른다. "딸기 온실"처럼 작물 이름으로
말해도 시스템 프롬프트의 농장 구성 정보를 보고 모델이 번호로 매핑한다.

- control_device 는 greenhouse_id 가 **필수**다 — 장비를 조작하는 명령인데 온실을
  특정하지 않으면(예: "차광막 닫아줘") 함부로 아무 온실에나 적용하지 않고, 모델이
  먼저 사용자에게 되묻게 한다 (프롬프트 지시 + 실제 상태를 근거로 확인 질문 생성).
  이때 경고/위험 중인 온실이 있으면 그 온실을 근거로 확인하도록 상태를 프롬프트에 넣는다.
- read_data 는 조회일 뿐 장비를 바꾸지 않아 위험이 낮으므로, 미지정 시 기존처럼
  1번 온실을 기본값으로 조회한다.

handle() 반환 스키마 (smartfarm_api_spec.md 1.1 대응):
  {"reply": str,
   "actions_taken": [{"device": str, "greenhouse_id": int|None, "action": str, "success": bool}, ...]}
"""

import json
import logging
from typing import Callable

from openai import OpenAI

from ..iot.base import IoTAdapter

logger = logging.getLogger(__name__)

_STATUS_LABEL = {"normal": "정상", "warning": "경고", "critical": "위험"}


class ChatAgent:
    MODEL = "gpt-5.4-mini"  # function calling 지원, 저비용/저지연
    DEFAULT_GREENHOUSE_ID = 1  # read_data 미지정 시에만 쓰는 기본 대상
    MAX_TOOL_ITERATIONS = 5  # tool 왕복 상한 (무한 루프 방지)

    SYSTEM_PROMPT_INTRO = (
        "당신은 스마트팜 농가를 돕는 친근한 AI 대화 도우미입니다. "
        "기본은 '일반 챗봇'입니다. 인사·잡담·날씨·컨디션 같은 일상 대화나 일반적인 질문에는 "
        "도구를 쓰지 말고 자연스럽고 따뜻하게 대화로 응답하세요. "
        "고령 농가 사용자를 대상으로 하니 항상 짧고 쉬운 말로 답합니다.\n"
        "단, 사용자가 온실 장비(차광막/창문/관수)를 조작하려 하거나 "
        "센서/생산 데이터(온도/습도/생산량)를 물으면, 그때만 제공된 도구(control_device/read_data)를 "
        "호출해 실제로 처리하세요. "
        "장비를 조작한 뒤에는 몇 번 온실에 무엇을 했는지 확인해주는 문장으로 답하고, "
        "지원하지 않는 장비/동작이면 무엇이 안 되는지 안내하세요. "
        "도구 결과에 note 필드가 있으면 그 내용을 반드시 답변에 반영하세요.\n"
    )

    # 온실을 지정하지 않은 장비 조작 요청일 때 쓸 규칙. {target_hint} 는 코드가
    # 현재 상태를 보고 미리 계산해서 채운다 — 모델이 상태 목록에서 직접 찾게
    # 맡기면 지시를 놓치는 경우가 있어(실측 확인), 결정론적으로 지목해준다.
    ASK_BACK_RULE_TEMPLATE = (
        "**중요**: 장비 조작(control_device) 요청인데 사용자가 몇 번 온실인지 말하지 "
        "않았다면, 절대로 임의로 아무 온실에나 적용하지 말고 반드시 먼저 되물어 확인하세요.\n"
        "{target_hint}"
    )

    def __init__(
        self,
        iot_by_greenhouse: dict[int, IoTAdapter],
        greenhouse_names: dict[int, str],
        status_provider: Callable[[], list[dict]],
        client: OpenAI | None = None,
        model: str | None = None,
    ):
        self._iot_by_greenhouse = iot_by_greenhouse
        self._status_provider = status_provider
        self._client = client  # None 이면 최초 호출 때 lazy 생성 (import 시 API 키 불필요)
        self._model = model or self.MODEL
        self._farm_layout_prompt = self._build_farm_layout_prompt(greenhouse_names)
        self._tools = self._build_tools(greenhouse_names)

    def _current_system_prompt(self) -> str:
        status = self._status_provider()
        return (
            self.SYSTEM_PROMPT_INTRO
            + self._farm_layout_prompt
            + self._live_status_block(status)
            + self.ASK_BACK_RULE_TEMPLATE.format(target_hint=self._ask_back_target_hint(status))
        )

    @staticmethod
    def _live_status_block(status: list[dict]) -> str:
        lines = [
            f"- {s['name']}: {_STATUS_LABEL.get(s['status'], s['status'])} "
            f"(습도 {s['humidity']}%, 온도 {s['temperature']}℃)"
            for s in status
        ]
        return "현재 온실 상태:\n" + "\n".join(lines) + "\n"

    @staticmethod
    def _ask_back_target_hint(status: list[dict]) -> str:
        """온실 미지정 시 되묻는 방법을 결정론적으로 지정.

        경고/위험인 온실이 정확히 하나면 그 온실을 직접 지목해 확인하게 하고,
        그 외(0개 또는 여러 개)에는 목록을 나열해 물어보게 한다. 모델이 상태
        목록에서 알아서 찾아내는 것에만 맡기면 지시를 놓치는 경우가 있어서
        (실측 확인됨), 어떤 문장을 만들지 코드가 미리 정해준다.
        """
        abnormal = [s for s in status if s["status"] != "normal"]
        if len(abnormal) == 1:
            gh = abnormal[0]
            question = (
                f"{gh['name']}이 습도 {gh['humidity']}%로 {_STATUS_LABEL[gh['status']]} 상태인데, "
                "그 온실 말씀이신가요, 다른 온실인가요?"
            )
            return (
                f"지금 {gh['name']}이 {_STATUS_LABEL[gh['status']]} 상태입니다 (습도 {gh['humidity']}%). "
                "사용자가 다른 온실을 언급하지 않았다면 온실 목록을 나열하지 말고, "
                f"반드시 다음 문장을 그대로 사용해 되물으세요(다른 표현으로 바꾸지 마세요): "
                f'"{question}"'
            )
        names = ", ".join(s["name"] for s in status)
        return f"경고 중인 온실이 없거나 여럿이니, 몇 번 온실인지 목록으로 물어보세요: {names}"

    @staticmethod
    def _build_farm_layout_prompt(greenhouse_names: dict[int, str]) -> str:
        names = ", ".join(greenhouse_names[gid] for gid in sorted(greenhouse_names))
        return f"농장 구성: {names}. 사용자가 작물 이름으로 말하면 해당 온실 번호로 처리하세요.\n"

    @staticmethod
    def _build_tools(greenhouse_names: dict[int, str]) -> list[dict]:
        ids = sorted(greenhouse_names)
        return [
            {
                "type": "function",
                "function": {
                    "name": "control_device",
                    "description": (
                        "온실 장비(차광막/창문/관수)를 제어한다. 어떤 온실인지 확실할 때만 호출하고, "
                        "확실하지 않으면 호출하지 말고 먼저 사용자에게 되물어라."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "device": {
                                "type": "string",
                                "enum": ["shade", "window", "irrigation"],
                                "description": "shade=차광막, window=창문, irrigation=관수",
                            },
                            "action": {
                                "type": "string",
                                "enum": ["open", "close", "on", "off"],
                                "description": "shade/window는 open|close, irrigation은 on|off",
                            },
                            "greenhouse_id": {
                                "type": "integer",
                                "enum": ids,
                                "description": "대상 온실 번호. 반드시 명시해야 한다 (생략 금지).",
                            },
                        },
                        "required": ["device", "action", "greenhouse_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_data",
                    "description": "센서/생산 데이터를 조회한다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target": {
                                "type": "string",
                                "enum": ["temperature", "humidity", "production"],
                                "description": "temperature=온도, humidity=습도, production=생산량",
                            },
                            "greenhouse_id": {
                                "type": "integer",
                                "enum": ids,
                                "description": (
                                    "대상 온실 번호. 사용자가 온실을 지정하지 않으면 생략 "
                                    f"(기본 {ChatAgent.DEFAULT_GREENHOUSE_ID}번)."
                                ),
                            },
                        },
                        "required": ["target"],
                    },
                },
            },
        ]

    def _client_or_default(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI()
        return self._client

    def handle(self, message: str, history: list[dict] | None = None) -> dict:
        """사용자 한 마디를 받아 {"reply", "actions_taken"} 를 돌려준다."""
        client = self._client_or_default()
        messages = [
            {"role": "system", "content": self._current_system_prompt()},
            *(history or []),
            {"role": "user", "content": message},
        ]
        actions_taken: list[dict] = []

        for _ in range(self.MAX_TOOL_ITERATIONS):
            response = client.chat.completions.create(
                model=self._model, messages=messages, tools=self._tools
            )
            reply_message = response.choices[0].message

            if not reply_message.tool_calls:
                reply = reply_message.content or "네, 알겠습니다."
                return {"reply": reply, "actions_taken": actions_taken}

            messages.append(self._assistant_message(reply_message))
            for tool_call in reply_message.tool_calls:
                result = self._run_tool(tool_call, actions_taken)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )

        logger.warning("tool 루프 %d회 초과 — message=%r", self.MAX_TOOL_ITERATIONS, message)
        return {
            "reply": "죄송해요, 요청을 처리하지 못했어요. 다시 한 번 말씀해 주시겠어요?",
            "actions_taken": actions_taken,
        }

    @staticmethod
    def _assistant_message(reply_message) -> dict:
        return {
            "role": "assistant",
            "content": reply_message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in reply_message.tool_calls
            ],
        }

    def _run_tool(self, tool_call, actions_taken: list[dict]) -> dict:
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except (json.JSONDecodeError, TypeError):
            logger.warning("tool 인자 JSON 파싱 실패: %r", tool_call.function.arguments)
            return {"ok": False, "reason": "invalid_arguments"}

        greenhouse_id = args.get("greenhouse_id")
        if greenhouse_id is None and name == "read_data":
            # read_data 는 위험이 낮으므로 미지정 시 기본 온실로 조회 (하위 호환)
            greenhouse_id = self.DEFAULT_GREENHOUSE_ID
        result = self._dispatch(name, args, greenhouse_id)

        if name == "control_device":
            actions_taken.append(
                {
                    "device": args.get("device"),
                    "greenhouse_id": greenhouse_id,
                    "action": args.get("action"),
                    "success": result.get("ok", False),
                }
            )
        return result

    def _dispatch(self, name: str, args: dict, greenhouse_id: int | None) -> dict:
        if greenhouse_id is None:
            # control_device 는 온실 미지정 시 실행하지 않는다 — 모델이 되물어야 한다.
            return {"ok": False, "reason": "missing_greenhouse_id"}
        iot = self._iot_by_greenhouse.get(greenhouse_id)
        if iot is None:
            return {"ok": False, "reason": "unknown_greenhouse", "greenhouse_id": greenhouse_id}
        if name == "control_device":
            was_alerting = self._is_alerting(greenhouse_id)
            result = {**iot.control(args["device"], args["action"]), "greenhouse_id": greenhouse_id}
            if result.get("ok") and was_alerting:
                # 챗으로 경고 중인 온실을 조치하면 대시보드 알림/조치버튼이 습도가
                # 내려가는 대로 조용히 사라진다 — 사용자가 왜 사라졌는지 모를 수
                # 있어(실측 확인) 답변에서 미리 설명하도록 안내를 실어준다.
                result["note"] = (
                    "이 온실은 방금까지 경고/위험 상태였습니다. 이 조치로 습도가 내려가면 "
                    "대시보드의 알림과 조치 버튼이 자동으로 사라집니다(=해결됐다는 뜻). "
                    "답변에 이 사실을 한 문장으로 짧게 안내하세요."
                )
            return result
        if name == "read_data":
            return {**iot.read(args["target"]), "greenhouse_id": greenhouse_id}
        return {"ok": False, "reason": "unknown_tool"}

    def _is_alerting(self, greenhouse_id: int) -> bool:
        return any(
            s["id"] == greenhouse_id and s["status"] != "normal" for s in self._status_provider()
        )
