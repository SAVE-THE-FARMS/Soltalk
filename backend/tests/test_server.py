"""server.py 엔드포인트 테스트.

container.chat_agent.handle 은 monkeypatch 로 대체해 실제 OpenAI 호출 없이 검증한다.
server 모듈은 import 시 AppContainer 인스턴스(container) 하나를 만들어 공유한다.
"""

from fastapi.testclient import TestClient

from app import server


def _reset_all():
    server.container.reset_all()


def test_health_ok():
    client = TestClient(server.app)

    resp = client.get("/health")

    assert resp.json() == {"status": "ok"}


def test_chat_returns_reply_actions_and_state(monkeypatch):
    _reset_all()
    monkeypatch.setattr(
        server.container.chat_agent,
        "handle",
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
    _reset_all()

    def boom(message, history=None):
        raise RuntimeError("openai down")

    monkeypatch.setattr(server.container.chat_agent, "handle", boom)
    client = TestClient(server.app)

    resp = client.post("/api/chat", json={"message": "차광막 닫아줘"})

    assert resp.status_code == 200
    assert "죄송" in resp.json()["reply"]


def test_transcribe_returns_text(monkeypatch):
    _reset_all()
    monkeypatch.setattr(
        server.container.transcription,
        "transcribe",
        lambda audio, filename="audio.webm": "차광막 닫아줘",
    )
    client = TestClient(server.app)

    resp = client.post("/api/transcribe", files={"audio": ("cmd.webm", b"fake-bytes", "audio/webm")})

    assert resp.status_code == 200
    assert resp.json() == {"text": "차광막 닫아줘"}


def test_transcribe_rejects_empty_audio():
    _reset_all()
    client = TestClient(server.app)

    resp = client.post("/api/transcribe", files={"audio": ("empty.webm", b"", "audio/webm")})

    assert resp.status_code == 400


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


def test_get_state_includes_auto_flag_defaulting_false():
    _reset_all()
    client = TestClient(server.app)

    resp = client.get("/api/state")

    assert all(g["auto"] is False for g in resp.json()["greenhouses"])


def test_set_auto_mode_enables_and_reflects_in_state():
    _reset_all()
    client = TestClient(server.app)

    resp = client.post("/api/greenhouses/2/auto-mode", json={"enabled": True})

    assert resp.status_code == 200
    assert resp.json() == {"greenhouse_id": 2, "auto": True}
    states = {g["id"]: g for g in client.get("/api/state").json()["greenhouses"]}
    assert states[2]["auto"] is True
    assert states[1]["auto"] is False
    assert client.get("/api/state/2").json()["auto"] is True


def test_set_auto_mode_on_unknown_greenhouse_is_404():
    _reset_all()
    client = TestClient(server.app)

    resp = client.post("/api/greenhouses/999/auto-mode", json={"enabled": True})

    assert resp.status_code == 404


def test_auto_mode_resets_on_demo_reset():
    client = TestClient(server.app)
    client.post("/api/greenhouses/2/auto-mode", json={"enabled": True})

    client.post("/api/reset")

    assert client.get("/api/state/2").json()["auto"] is False


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
    server.container.chat_iot.control("shade", "close")
    client = TestClient(server.app)
    assert client.get("/api/state").json()["greenhouses"][0]["devices"]["shade"] == "closed"

    resp = client.post("/api/reset")

    assert resp.status_code == 200
    assert client.get("/api/state").json()["greenhouses"][0]["devices"]["shade"] == "open"


def test_realtime_session_returns_client_secret(monkeypatch):
    monkeypatch.setattr(
        server.container.realtime_sessions,
        "create_session",
        lambda: {"client_secret": "ek_test", "expires_at": 1234567890},
    )
    client = TestClient(server.app)

    resp = client.post("/api/realtime/session")

    assert resp.status_code == 200
    assert resp.json() == {"client_secret": "ek_test", "expires_at": 1234567890}


def test_realtime_session_returns_502_when_openai_call_fails(monkeypatch):
    def boom():
        raise RuntimeError("openai down")

    monkeypatch.setattr(server.container.realtime_sessions, "create_session", boom)
    client = TestClient(server.app)

    resp = client.post("/api/realtime/session")

    assert resp.status_code == 502


def test_tools_execute_runs_control_device():
    _reset_all()
    client = TestClient(server.app)

    resp = client.post(
        "/api/tools/execute",
        json={
            "tool_name": "control_device",
            "arguments": {"device": "shade", "action": "close", "greenhouse_id": 1},
        },
    )

    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["ok"] is True
    assert result["device"] == "shade"
    assert result["state"] == "closed"
    assert result["greenhouse_id"] == 1


def test_tools_execute_read_data_defaults_to_greenhouse_1():
    _reset_all()
    client = TestClient(server.app)

    resp = client.post(
        "/api/tools/execute",
        json={"tool_name": "read_data", "arguments": {"target": "temperature"}},
    )

    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["ok"] is True
    assert result["greenhouse_id"] == 1


def test_tools_execute_control_device_without_greenhouse_id_is_not_applied():
    _reset_all()
    client = TestClient(server.app)

    resp = client.post(
        "/api/tools/execute",
        json={"tool_name": "control_device", "arguments": {"device": "shade", "action": "close"}},
    )

    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result == {"ok": False, "reason": "missing_greenhouse_id"}
