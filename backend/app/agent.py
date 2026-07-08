"""LLM 에이전트.

역할: 사용자 자연어 → LLM(OpenAI function calling)으로 의도 파악 → MockIoTAdapter 호출 → 자연어 응답.
모델에게 control_device / read_data 를 도구로 주고, 모델이 알아서 호출하게 한다.

handle_message() 반환 스키마 (Docs/smartfarm_api_spec.md 1.1 대응):
  {"reply": str, "actions_taken": [{"device": str, "greenhouse_id": 1, "action": str, "success": bool}, ...]}
"""

import json

from openai import OpenAI

from .iot.mock import MockIoTAdapter
from .state import iot as _default_iot

MODEL = "gpt-5.4-mini"  # function calling 지원, 저비용/저지연 (BACKEND.md 지정)

# 챗봇으로 직접 제어 가능한 건 1번 온실뿐 (CLAUDE.md 의 NLU 계약: {intent, device, action} — 온실 구분 없음)
CHAT_GREENHOUSE_ID = 1

SYSTEM_PROMPT = (
    "당신은 스마트팜 온실 장비를 관리하는 AI 도우미입니다. "
    "고령 농가 사용자를 대상으로 하니 짧고 친절한 말투로 답하고, "
    "장비를 조작했으면 무엇을 했는지 확인해주는 문장으로 답하세요. "
    "요청이 애매하면 되묻고, 지원하지 않는 장비/동작이면 무엇이 안 되는지 안내하세요."
)

TOOLS = [
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
                },
                "required": ["target"],
            },
        },
    },
]

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def _dispatch_tool(name: str, args: dict, iot: MockIoTAdapter) -> dict:
    if name == "control_device":
        return iot.control(args["device"], args["action"])
    if name == "read_data":
        return iot.read(args["target"])
    return {"ok": False, "reason": "unknown_tool"}


def handle_message(
    message: str,
    client=None,
    iot: MockIoTAdapter | None = None,
    history: list[dict] | None = None,
) -> dict:
    """사용자 한 마디를 받아 {"reply", "actions_taken"} 를 돌려준다.

    history: session_service 가 관리하는 이전 대화(사용자/응답 쌍). 재질문 흐름 대응용.
    """
    client = client or _get_client()
    iot = iot or _default_iot

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *(history or []),
        {"role": "user", "content": message},
    ]
    actions_taken = []

    for _ in range(5):  # 무한 루프 방지
        response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        reply_message = response.choices[0].message

        if not reply_message.tool_calls:
            reply = reply_message.content or "네, 알겠습니다."
            return {"reply": reply, "actions_taken": actions_taken}

        messages.append(
            {
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
        )

        for tc in reply_message.tool_calls:
            args = json.loads(tc.function.arguments)
            result = _dispatch_tool(tc.function.name, args, iot)

            if tc.function.name == "control_device":
                actions_taken.append(
                    {
                        "device": args.get("device"),
                        "greenhouse_id": CHAT_GREENHOUSE_ID,
                        "action": args.get("action"),
                        "success": result.get("ok", False),
                    }
                )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    return {
        "reply": "죄송해요, 요청을 처리하지 못했어요. 다시 한 번 말씀해 주시겠어요?",
        "actions_taken": actions_taken,
    }
