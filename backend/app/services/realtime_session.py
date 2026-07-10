"""OpenAI Realtime API용 ephemeral 세션 발급.

브라우저(프론트)가 OpenAI에 직접 WebRTC로 연결하려면 짧은 시간만 유효한
"ephemeral key"가 필요하다. 이 키는 서버가 보유한 OPENAI_API_KEY로만 발급받을
수 있고, 프론트에는 절대 OPENAI_API_KEY 자체를 넘기지 않는다.

SDK의 특정 헬퍼 메서드 이름에 의존하지 않고 REST 엔드포인트를 직접 호출한다
(SDK 버전마다 메서드 경로가 바뀔 수 있어 REST 스펙이 더 안정적인 기준).
"""

import os

import httpx

REALTIME_SESSIONS_URL = "https://api.openai.com/v1/realtime/client_secrets"


class RealtimeSessionService:
    # 실제 OpenAI 계정에서 쓸 수 있는 Realtime 모델명이 다르면 이 상수만 바꾸면 된다.
    # 2026-07-10 실제 키로 라이브 호출해 확인된 값 — /v1/realtime/sessions 는 404 (구
    # 엔드포인트), 현재는 /v1/realtime/client_secrets + {"session": {"type": "realtime", ...}}
    # 바디, 응답도 {"value", "expires_at", "session": {...}} 형태로 최상위에 온다(중첩 아님).
    MODEL = "gpt-4o-realtime-preview"

    def __init__(self, http_client: httpx.Client | None = None):
        self._http_client = http_client  # None 이면 최초 호출 때 lazy 생성 (import 시 API 키 불필요)

    def _client_or_default(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=10.0)
        return self._http_client

    def create_session(self) -> dict:
        """OpenAI에 Realtime ephemeral 키를 만들고 프론트에 넘길 {"client_secret", "expires_at"}만 추출해 돌려준다."""
        client = self._client_or_default()
        response = client.post(
            REALTIME_SESSIONS_URL,
            json={"session": {"type": "realtime", "model": self.MODEL}},
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        )
        response.raise_for_status()
        data = response.json()
        return {"client_secret": data["value"], "expires_at": data["expires_at"]}
