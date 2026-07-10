"""execute_tool() 단위 테스트 — ChatAgent와 Realtime tool 브릿지가 공유하는 실행 로직."""

from app.iot.mock import MockIoTAdapter
from app.services.tool_execution import execute_tool


def _always_normal(greenhouse_id):
    return False


def _always_alerting(greenhouse_id):
    return True


def test_control_device_without_greenhouse_id_is_not_executed():
    result = execute_tool(
        "control_device",
        {"device": "shade", "action": "close"},
        None,
        {1: MockIoTAdapter()},
        _always_normal,
    )
    assert result == {"ok": False, "reason": "missing_greenhouse_id"}


def test_control_device_unknown_greenhouse_fails_gracefully():
    result = execute_tool(
        "control_device",
        {"device": "shade", "action": "close"},
        99,
        {1: MockIoTAdapter()},
        _always_normal,
    )
    assert result == {"ok": False, "reason": "unknown_greenhouse", "greenhouse_id": 99}


def test_control_device_success_on_normal_greenhouse_has_no_note():
    adapter = MockIoTAdapter()

    result = execute_tool(
        "control_device", {"device": "shade", "action": "close"}, 1, {1: adapter}, _always_normal
    )

    assert result["ok"] is True
    assert result["device"] == "shade"
    assert result["state"] == "closed"
    assert result["greenhouse_id"] == 1
    assert "note" not in result


def test_control_device_success_on_alerting_greenhouse_adds_note():
    adapter = MockIoTAdapter()

    result = execute_tool(
        "control_device", {"device": "shade", "action": "close"}, 1, {1: adapter}, _always_alerting
    )

    assert result["ok"] is True
    assert "note" in result
    assert "사라집니다" in result["note"]


def test_read_data_returns_target_value():
    adapter = MockIoTAdapter()

    result = execute_tool("read_data", {"target": "temperature"}, 1, {1: adapter}, _always_normal)

    assert result["ok"] is True
    assert result["target"] == "temperature"
    assert result["greenhouse_id"] == 1


def test_query_data_is_an_alias_for_read_data():
    """Realtime(음성) 프론트는 조회 도구를 "query_data"라는 이름으로 호출한다."""
    adapter = MockIoTAdapter()

    result = execute_tool("query_data", {"target": "temperature"}, 1, {1: adapter}, _always_normal)

    assert result["ok"] is True
    assert result["target"] == "temperature"
    assert result["greenhouse_id"] == 1


def test_unknown_tool_name_fails_gracefully():
    result = execute_tool("delete_everything", {}, 1, {1: MockIoTAdapter()}, _always_normal)

    assert result == {"ok": False, "reason": "unknown_tool"}
