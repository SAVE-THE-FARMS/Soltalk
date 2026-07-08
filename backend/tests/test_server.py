"""server.py 엔드포인트 테스트.

agent.handle_message 는 monkeypatch 로 대체해 실제 OpenAI 호출 없이 검증한다.
"""

from fastapi.testclient import TestClient

from app import alerts_service, server, session_service, state


def _reset_all():
    session_service.reset()
    alerts_service.reset()
    state.reset_all()


def test_health_ok():
    client = TestClient(server.app)

    resp = client.get("/health")

    assert resp.json() == {"status": "ok"}


def test_chat_returns_reply_actions_and_state(monkeypatch):
    session_service.reset()
    monkeypatch.setattr(
        server.agent,
        "handle_message",
        lambda message, history=None: {
            "reply": "차광막을 닫았어요.",
            "actions_taken": [{"device": "shade", "greenhouse_id": 1, "action": "close", "success": True}],
        },
    )
    client = TestClient(server.app)

    resp = client.post("/api/chat", json={"message": "차광막 닫아줘"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "차광막을 닫았어요."
    assert body["actions_taken"] == [{"device": "shade", "greenhouse_id": 1, "action": "close", "success": True}]
    assert "updated_state" in body


def test_chat_returns_friendly_message_when_agent_fails(monkeypatch):
    session_service.reset()

    def boom(message, history=None):
        raise RuntimeError("openai down")

    monkeypatch.setattr(server.agent, "handle_message", boom)
    client = TestClient(server.app)

    resp = client.post("/api/chat", json={"message": "차광막 닫아줘"})

    assert resp.status_code == 200
    assert "죄송" in resp.json()["reply"]


def test_get_state_returns_all_greenhouses():
    _reset_all()
    client = TestClient(server.app)

    resp = client.get("/api/state")

    assert resp.status_code == 200
    assert [g["id"] for g in resp.json()["greenhouses"]] == [1, 2, 3]


def test_get_state_detail_for_known_greenhouse():
    _reset_all()
    client = TestClient(server.app)

    resp = client.get("/api/state/2")

    assert resp.status_code == 200
    assert resp.json()["status"] == "warning"


def test_get_state_detail_for_unknown_greenhouse_is_404():
    _reset_all()
    client = TestClient(server.app)

    resp = client.get("/api/state/999")

    assert resp.status_code == 404


def test_get_alerts_lists_active_alerts():
    _reset_all()
    client = TestClient(server.app)

    resp = client.get("/api/alerts")

    assert resp.status_code == 200
    assert [a["greenhouse_id"] for a in resp.json()["alerts"]] == [2]


def test_alert_action_executes_and_removes_from_active_list():
    _reset_all()
    client = TestClient(server.app)

    resp = client.post("/api/alerts/gh2-humidity/action")

    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert client.get("/api/alerts").json()["alerts"] == []


def test_alert_action_on_unknown_alert_is_404():
    _reset_all()
    client = TestClient(server.app)

    resp = client.post("/api/alerts/gh999-humidity/action")

    assert resp.status_code == 404


def test_alert_dismiss_removes_from_active_list():
    _reset_all()
    client = TestClient(server.app)

    resp = client.post("/api/alerts/gh2-humidity/dismiss")

    assert resp.status_code == 200
    assert client.get("/api/alerts").json()["alerts"] == []


def test_alert_dismiss_on_unknown_alert_is_404():
    _reset_all()
    client = TestClient(server.app)

    resp = client.post("/api/alerts/gh999-humidity/dismiss")

    assert resp.status_code == 404


def test_reset_restores_device_state():
    _reset_all()
    state.iot.control("shade", "close")
    client = TestClient(server.app)
    assert client.get("/api/state").json()["greenhouses"][0]["devices"]["shade"] == "closed"

    resp = client.post("/api/reset")

    assert resp.status_code == 200
    assert client.get("/api/state").json()["greenhouses"][0]["devices"]["shade"] == "open"
