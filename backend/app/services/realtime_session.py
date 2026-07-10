"""OpenAI Realtime API 임시(ephemeral) 키 발급 + 음성 세션 설정.

서버가 보유한 OPENAI_API_KEY로 OpenAI에 세션 생성을 요청하고, 브라우저에 전달할
짧은 유효시간의 client_secret 만 돌려준다 — 원본 API 키는 절대 클라이언트에 노출하지 않는다.
프론트는 이 client_secret 으로 OpenAI와 직접 WebRTC 연결한다(오디오는 우리 서버를 거치지 않음).

지침(instructions)과 도구(tools)는 **여기서 키 발급 시점에 세션에 바인딩**한다.
프론트가 연결 후 session.update 로 보내는 방식은 payload 가 API 계약과 조금만 어긋나도
조용히 거부되어 "도구 없는 일반 챗봇"이 되는 사고가 실측으로 확인됐다(session.type 누락).
서버에 두면 그 실패 지점 자체가 없고, 도구 스키마의 단일 진실 공급원도 백엔드가 된다.

주의: Realtime 의 tools 형식은 Chat Completions(chat_agent.py)와 다르다 — flat
{type, name, description, parameters} 이고 "function" 으로 한 번 더 감싸지 않는다.
도구 이름/인자는 ToolExecutor(tool_executor.py)가 아는 것과 일치해야 한다
(control_device / query_data — 프론트가 /api/tools/execute 로 그대로 중계).
"""

import logging
from datetime import datetime
from typing import Callable

from openai import OpenAI

from .persona import SMART_JUDGMENT_RULES

logger = logging.getLogger(__name__)

_STATUS_LABEL = {"normal": "정상", "warning": "경고", "critical": "위험"}


def _build_instructions(
    greenhouse_names: dict[int, str],
    status: list[dict] | None = None,
    now: datetime | None = None,
) -> str:
    names = ", ".join(greenhouse_names[gid] for gid in sorted(greenhouse_names))
    parts = [
        "당신은 스마트팜 농가를 돕는 친근한 AI 음성 도우미입니다. 고령 농가 사용자를 "
        "대상으로 하니 항상 짧고 쉬운 말로, 친절한 말투로 답하세요. 한국어로만 응답하세요.\n"
        f"농장 구성: {names}. 사용자가 작물 이름으로 말하면 해당 온실 번호로 처리하세요.\n"
        "장비(차광막/창문/관수)를 조작하려 하거나 센서/생산/알림 데이터를 물으면 반드시 "
        "제공된 도구를 호출해 실제로 처리하고, 도구 없이 임의로 답하지 마세요. 지원하지 "
        "않는 장비/동작이면 무엇이 안 되는지 안내하세요. 어떤 온실인지, 어떤 동작인지 "
        "불명확하면 실행하지 말고 먼저 되물으세요."
    ]
    if now is not None:
        parts.append(f"현재 시각: {now.strftime('%H시 %M분')} (시각을 판단 근거로 활용하세요).")
    if status:
        lines = [
            f"- {s['name']}: {_STATUS_LABEL.get(s['status'], s['status'])} "
            f"(습도 {s['humidity']}%, 온도 {s['temperature']}℃)"
            for s in status
        ]
        parts.append(
            "통화 시작 시점의 온실 상태:\n" + "\n".join(lines) + "\n"
            "이 값은 통화 중 바뀔 수 있으니, 판단/실행 직전에는 query_data 로 최신 값을 "
            "확인하세요."
        )
    parts.append(SMART_JUDGMENT_RULES)
    return "\n".join(parts)


def _build_tools(greenhouse_names: dict[int, str]) -> list[dict]:
    ids = sorted(greenhouse_names)
    return [
        {
            "type": "function",
            "name": "control_device",
            "description": (
                "온실 장비(차광막/창문/관수)를 제어한다. 어떤 온실인지 확실할 때만 호출하고, "
                "확실하지 않으면 호출하지 말고 먼저 사용자에게 되물어라."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "greenhouse_id": {
                        "type": "integer",
                        "enum": ids,
                        "description": "대상 온실 번호. 반드시 명시해야 한다 (생략 금지).",
                    },
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
                "required": ["greenhouse_id", "device", "action"],
            },
        },
        {
            "type": "function",
            "name": "query_data",
            "description": "센서/생산/알림/온실 상태 데이터를 조회한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "greenhouse_id": {
                        "type": "integer",
                        "enum": ids,
                        "description": "대상 온실 번호. 미지정 시 기본 온실.",
                    },
                    "target": {
                        "type": "string",
                        "enum": ["temperature", "humidity", "state", "alerts", "production"],
                        "description": (
                            "temperature=온도, humidity=습도, state=온실 종합 상태, "
                            "alerts=알림 목록, production=생산량"
                        ),
                    },
                },
                "required": ["target"],
            },
        },
    ]


class RealtimeSessionService:
    MODEL = "gpt-realtime-mini"  # 저비용/저지연 realtime 모델 (챗봇의 mini 선택과 같은 이유)
    TRANSCRIPTION_MODEL = "gpt-4o-transcribe"  # 사용자 발화 자막용 (transcription.py 와 동일)

    def __init__(
        self,
        greenhouse_names: dict[int, str],
        status_provider: Callable[[], list[dict]] | None = None,
        client: OpenAI | None = None,
        model: str | None = None,
    ):
        self._greenhouse_names = greenhouse_names
        self._status_provider = status_provider  # 연결 시점 온실 상태를 지침에 싣는 용도
        self._client = client  # None 이면 최초 호출 때 lazy 생성 (import 시 API 키 불필요)
        self._model = model or self.MODEL
        self._tools = _build_tools(greenhouse_names)

    def _client_or_default(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI()
        return self._client

    def _current_instructions(self) -> str:
        status = None
        if self._status_provider is not None:
            try:
                status = self._status_provider()
            except Exception:
                # 상태 조회가 실패해도 키 발급(=음성 연결)은 막지 않는다 —
                # 모델이 query_data 로 직접 조회하면 되기 때문.
                logger.exception("음성 지침용 온실 상태 조회 실패 — 상태 없이 발급")
        return _build_instructions(self._greenhouse_names, status=status, now=datetime.now())

    def create_session(self) -> dict:
        """{"client_secret": str, "expires_at": int} 를 돌려준다."""
        client = self._client_or_default()
        secret = client.realtime.client_secrets.create(
            session={
                "type": "realtime",
                "model": self._model,
                "instructions": self._current_instructions(),
                "tools": self._tools,
                "tool_choice": "auto",
                # 입력 음성 자막 — 세션 설정에 켜야만 프론트로
                # conversation.item.input_audio_transcription.completed 가 온다
                # (사용자 발화가 채팅 이력에 남는 기능).
                "audio": {
                    "input": {
                        "transcription": {"model": self.TRANSCRIPTION_MODEL, "language": "ko"}
                    }
                },
            }
        )
        return {"client_secret": secret.value, "expires_at": secret.expires_at}
