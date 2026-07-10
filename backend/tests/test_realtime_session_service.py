"""RealtimeSessionService 테스트 — 실제 OpenAI 네트워크 호출 없이 httpx.MockTransport로 검증."""

import httpx
import pytest

from app.services.realtime_session import REALTIME_SESSIONS_URL, RealtimeSessionService


def _client_with(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_create_session_returns_client_secret_and_expiry(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    def handler(request):
        assert str(request.url) == REALTIME_SESSIONS_URL
        assert request.headers["authorization"] == "Bearer sk-test-key"
        # 실제 OpenAI 응답은 value/expires_at 이 최상위에 온다(중첩된 client_secret 객체 아님).
        return httpx.Response(
            200,
            json={
                "value": "ek_abc123",
                "expires_at": 1234567890,
                "session": {"type": "realtime", "model": RealtimeSessionService.MODEL},
            },
        )

    service = RealtimeSessionService(http_client=_client_with(handler))

    result = service.create_session()

    assert result == {"client_secret": "ek_abc123", "expires_at": 1234567890}


def test_create_session_sends_configured_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    sent_bodies = []

    def handler(request):
        sent_bodies.append(request.read())
        return httpx.Response(200, json={"value": "ek_x", "expires_at": 1, "session": {}})

    service = RealtimeSessionService(http_client=_client_with(handler))
    service.create_session()

    assert RealtimeSessionService.MODEL.encode() in sent_bodies[0]


def test_create_session_raises_on_openai_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    def handler(request):
        return httpx.Response(500, json={"error": "boom"})

    service = RealtimeSessionService(http_client=_client_with(handler))

    with pytest.raises(httpx.HTTPStatusError):
        service.create_session()
