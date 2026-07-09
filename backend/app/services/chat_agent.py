"""LLM 에이전트 (OpenAI function calling).

사용자 자연어 → LLM 이 control_device / read_data 도구를 호출 → 온실별 IoT 어댑터 실행 →
자연어 응답. 의존성(온실별 IoT 어댑터, 온실 이름, OpenAI 클라이언트, 모델명)은 생성자로 주입받는다.

온실 지정: 도구 인자 greenhouse_id 로 대상 온실을 고른다. 사용자가 온실을 말하지
않으면 1번 온실이 기본값이고, "딸기 온실"처럼 작물 이름으로 말해도 시스템 프롬프트의
농장 구성 정보를 보고 모델이 번호로 매핑한다.

handle() 반환 스키마 (smartfarm_api_spec.md 1.1 대응):
  {"reply": str,
   "actions_taken": [{"device": str, "greenhouse_id": int, "action": str, "success": bool}, ...]}
"""

import json
import logging

from openai import OpenAI

from ..iot.base import IoTAdapter

logger = logging.getLogger(__name__)


class ChatAgent:
    MODEL = "gpt-5.4-mini"  # function calling 지원, 저비용/저지연
    DEFAULT_GREENHOUSE_ID = 1  # 온실을 지정하지 않은 명령의 기본 대상
    MAX_TOOL_ITERATIONS = 5  # tool 왕복 상한 (무한 루프 방지)

    SYSTEM_PROMPT_BASE = (
        "당신은 스마트팜 농가를 돕는 친근한 AI 대화 도우미입니다. "
        "기본은 '일반 챗봇'입니다. 인사·잡담·날씨·컨디션 같은 일상 대화나 일반적인 질문에는 "
        "도구를 쓰지 말고 자연스럽고 따뜻하게 대화로 응답하세요. "
        "고령 농가 사용자를 대상으로 하니 항상 짧고 쉬운 말로 답합니다.\n"
        "단, 사용자가 온실 장비(차광막/창문/관수)를 조작하려 하거나 "
        "센서/생산 데이터(온도/습도/생산량)를 물으면, 그때만 제공된 도구(control_device/read_data)를 "
        "호출해 실제로 처리하세요. "
        "장비를 조작한 뒤에는 몇 번 온실에 무엇을 했는지 확인해주는 문장으로 답하고, "
        "요청이 애매하면 되묻고, 지원하지 않는 장비/동작이면 무엇이 안 되는지 안내하세요.\n"
    )

    def __init__(
        self,
        iot_by_greenhouse: dict[int, IoTAdapter],
        greenhouse_names: dict[int, str],
        client: OpenAI | None = None,
        model: str | None = None,
    ):
        self._iot_by_greenhouse = iot_by_greenhouse
        self._client = client  # None 이면 최초 호출 때 lazy 생성 (import 시 API 키 불필요)
        self._model = model or self.MODEL
        self._system_prompt = self.SYSTEM_PROMPT_BASE + self._farm_layout_prompt(greenhouse_names)
        self._tools = self._build_tools(greenhouse_names)

    @staticmethod
    def _farm_layout_prompt(greenhouse_names: dict[int, str]) -> str:
        names = ", ".join(greenhouse_names[gid] for gid in sorted(greenhouse_names))
        return (
            f"농장 구성: {names}. "
            "사용자가 작물 이름(예: '딸기 온실')으로 말하면 해당 온실 번호(greenhouse_id)로 처리하세요. "
            f"온실을 지정하지 않으면 {ChatAgent.DEFAULT_GREENHOUSE_ID}번 온실이 대상입니다."
        )

    @staticmethod
    def _build_tools(greenhouse_names: dict[int, str]) -> list[dict]:
        greenhouse_id_schema = {
            "type": "integer",
            "enum": sorted(greenhouse_names),
            "description": (
                "대상 온실 번호. 사용자가 온실을 지정하지 않으면 생략 "
                f"(기본 {ChatAgent.DEFAULT_GREENHOUSE_ID}번)."
            ),
        }
        return [
            {
                "type": "function",
                "function": {
                    "name": "control_device",
                    "description": "온실 장비(차광막/창문/관수)를 제어한다.",
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
                            "greenhouse_id": greenhouse_id_schema,
                        },
                        "required": ["device", "action"],
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
                            "greenhouse_id": greenhouse_id_schema,
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
            {"role": "system", "content": self._system_prompt},
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

        greenhouse_id = args.get("greenhouse_id", self.DEFAULT_GREENHOUSE_ID)
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

    def _dispatch(self, name: str, args: dict, greenhouse_id: int) -> dict:
        iot = self._iot_by_greenhouse.get(greenhouse_id)
        if iot is None:
            return {"ok": False, "reason": "unknown_greenhouse", "greenhouse_id": greenhouse_id}
        if name == "control_device":
            return {**iot.control(args["device"], args["action"]), "greenhouse_id": greenhouse_id}
        if name == "read_data":
            return {**iot.read(args["target"]), "greenhouse_id": greenhouse_id}
        return {"ok": False, "reason": "unknown_tool"}
