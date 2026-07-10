"""ToolExecutor 테스트 — control_device/read_data(query_data) 실행 로직.

ChatAgent가 이미 이 실행기를 통해 검증되는 케이스(control_device 기본 동작, note 부착 등)는
test_agent.py 에서 다루므로 여기서는 ToolExecutor 단위 동작과, ChatAgent 스키마에는 없는
실시간 음성 전용 target(state/alerts), 그리고 알 수 없는 tool_name 처리를 다룬다.
"""

from app.iot.mock import MockIoTAdapter
from app.services.alerts import AlertService
from app.services.greenhouse import GreenhouseService
from app.services.tool_executor import ToolExecutor


def _all_normal_status():
    return [{"id": 1, "name": "1번 온실", "status": "normal", "temperature": 24.0, "humidity": 60}]


def test_execute_routes_control_device():
    iot = MockIoTAdapter()
    executor = ToolExecutor({1: iot}, _all_normal_status)

    result = executor.execute("control_device", {"device": "shade", "action": "close", "greenhouse_id": 1})

    assert result["ok"] is True
    assert iot.state["shade"] == "closed"


def test_execute_routes_query_data_same_as_read_data():
    executor = ToolExecutor({1: MockIoTAdapter()}, _all_normal_status)

    read_data_result = executor.execute("read_data", {"target": "temperature", "greenhouse_id": 1})
    query_data_result = executor.execute("query_data", {"target": "temperature", "greenhouse_id": 1})

    assert read_data_result == query_data_result


def test_execute_unknown_tool_fails_gracefully():
    executor = ToolExecutor({1: MockIoTAdapter()}, _all_normal_status)

    result = executor.execute("delete_everything", {})

    assert result == {"ok": False, "reason": "unknown_tool"}


def test_control_device_missing_device_or_action_fails_without_crash():
    """/api/tools/execute 는 외부에서 임의 JSON이 들어오는 경로 — 필수 키가 빠져도
    KeyError(500)가 아니라 구조화된 실패로 응답해야 한다."""
    iot = MockIoTAdapter()
    executor = ToolExecutor({1: iot}, _all_normal_status)

    missing_action = executor.control_device({"device": "shade", "greenhouse_id": 1})
    missing_device = executor.control_device({"action": "close", "greenhouse_id": 1})

    assert missing_action == {"ok": False, "reason": "invalid_arguments"}
    assert missing_device == {"ok": False, "reason": "invalid_arguments"}
    assert iot.state["shade"] == "open"  # 아무것도 실행되지 않아야 함


def test_read_data_missing_target_fails_without_crash():
    executor = ToolExecutor({1: MockIoTAdapter()}, _all_normal_status)

    result = executor.read_data({"greenhouse_id": 1})

    assert result == {"ok": False, "reason": "invalid_arguments"}


def test_read_data_target_temperature_defaults_to_greenhouse_1():
    executor = ToolExecutor({1: MockIoTAdapter(), 2: MockIoTAdapter()}, _all_normal_status)

    result = executor.read_data({"target": "temperature"})

    assert result["greenhouse_id"] == 1


def test_read_data_unknown_target_delegates_to_adapter():
    """유효 target 판정은 어댑터가 단일 진실 공급원 — 여기 하드코딩 목록을 두지 않는다.
    (어댑터에 새 센서를 추가하면 실행기 수정 없이 바로 조회 가능해야 함)"""
    executor = ToolExecutor({1: MockIoTAdapter()}, _all_normal_status)

    result = executor.read_data({"target": "weather_forecast"})

    assert result["ok"] is False
    assert result["reason"] == "unknown_target"
    assert result["greenhouse_id"] == 1  # 에러에도 어느 온실 조회였는지 남긴다


def test_read_data_adapter_only_target_works_without_executor_change():
    """어댑터가 아는 target 이면 실행기 쪽 목록 수정 없이 그대로 조회된다."""

    class ExtendedAdapter(MockIoTAdapter):
        def read(self, target):
            if target == "co2":
                return {"ok": True, "target": "co2", "value": 410, "unit": "ppm"}
            return super().read(target)

    executor = ToolExecutor({1: ExtendedAdapter()}, _all_normal_status)

    result = executor.read_data({"target": "co2"})

    assert result["ok"] is True
    assert result["value"] == 410


def test_read_data_state_target_requires_greenhouse_service():
    """greenhouse_service 를 안 넘긴 경우(최소 구성) state target은 미지원 처리."""
    executor = ToolExecutor({1: MockIoTAdapter()}, _all_normal_status)

    result = executor.read_data({"target": "state", "greenhouse_id": 1})

    assert result == {"ok": False, "reason": "unknown_target", "target": "state"}


def _build_greenhouse_service():
    iot_by_id = {1: MockIoTAdapter(), 2: MockIoTAdapter()}
    greenhouses = {
        1: {"name": "1번 온실", "temperature": 24.0, "humidity": 60, "history": []},
        2: {"name": "2번 온실", "temperature": 24.0, "humidity": 82, "history": []},
    }
    return GreenhouseService(iot_by_id, greenhouses, sensor_data={})


def test_read_data_state_target_returns_greenhouse_detail():
    gh_service = _build_greenhouse_service()
    executor = ToolExecutor(
        {1: MockIoTAdapter(), 2: MockIoTAdapter()},
        _all_normal_status,
        greenhouse_service=gh_service,
    )

    result = executor.read_data({"target": "state", "greenhouse_id": 2})

    assert result["ok"] is True
    assert result["status"] == "warning"


def test_read_data_state_target_includes_auto_mode_when_alert_service_present():
    """대시보드 상세(/api/state/{id})와 같은 shape — 음성 조회도 auto 모드 여부를 포함."""
    gh_service = _build_greenhouse_service()
    alert_service = AlertService(gh_service)
    alert_service.set_auto_mode(2, True)
    executor = ToolExecutor(
        {1: MockIoTAdapter(), 2: MockIoTAdapter()},
        _all_normal_status,
        greenhouse_service=gh_service,
        alert_service=alert_service,
    )

    result = executor.read_data({"target": "state", "greenhouse_id": 2})

    assert result["ok"] is True
    assert result["auto"] is True


def test_read_data_state_target_unknown_greenhouse_fails_gracefully():
    gh_service = _build_greenhouse_service()
    executor = ToolExecutor(
        {1: MockIoTAdapter(), 2: MockIoTAdapter()},
        _all_normal_status,
        greenhouse_service=gh_service,
    )

    result = executor.read_data({"target": "state", "greenhouse_id": 999})

    assert result == {"ok": False, "reason": "unknown_greenhouse", "greenhouse_id": 999}


def test_read_data_alerts_target_without_alert_service_is_unknown_target():
    """alert_service 미주입이면 '알림 없음'(거짓 성공)이 아니라 미지원으로 응답해야 한다."""
    executor = ToolExecutor({1: MockIoTAdapter()}, _all_normal_status)

    result = executor.read_data({"target": "alerts"})

    assert result == {"ok": False, "reason": "unknown_target", "target": "alerts"}


def test_read_data_alerts_unknown_greenhouse_fails_instead_of_empty_success():
    """존재하지 않는 온실의 알림 조회는 '알림 없음'이 아니라 unknown_greenhouse —
    음성 AI가 '999번 온실엔 알림이 없어요'라고 잘못 답하는 걸 막는다."""
    gh_service = _build_greenhouse_service()
    alert_service = AlertService(gh_service)
    executor = ToolExecutor(
        {1: MockIoTAdapter(), 2: MockIoTAdapter()},
        _all_normal_status,
        alert_service=alert_service,
    )

    result = executor.read_data({"target": "alerts", "greenhouse_id": 999})

    assert result == {"ok": False, "reason": "unknown_greenhouse", "greenhouse_id": 999}


def test_read_data_alerts_target_lists_active_alerts_filtered_by_greenhouse():
    gh_service = _build_greenhouse_service()
    alert_service = AlertService(gh_service)
    executor = ToolExecutor(
        {1: MockIoTAdapter(), 2: MockIoTAdapter()},
        _all_normal_status,
        alert_service=alert_service,
    )

    all_alerts = executor.read_data({"target": "alerts"})
    gh1_alerts = executor.read_data({"target": "alerts", "greenhouse_id": 1})
    gh2_alerts = executor.read_data({"target": "alerts", "greenhouse_id": 2})

    assert [a["greenhouse_id"] for a in all_alerts["alerts"]] == [2]
    assert gh1_alerts == {"ok": True, "alerts": []}
    assert [a["greenhouse_id"] for a in gh2_alerts["alerts"]] == [2]
