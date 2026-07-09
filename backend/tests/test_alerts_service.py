"""AlertService 테스트.

list_alerts(now): [{"id","level","greenhouse_id","message","created_at","escalated","action"}, ...]
dismiss(alert_id) -> bool  (현재 활성 알림이어서 닫았으면 True)
execute_action(alert_id) -> {"success","message","updated_state"} | None (없으면 None)
"""

from datetime import datetime

from app.data.greenhouse_data import GREENHOUSES
from app.data.mock_data import MOCK_DATA
from app.iot.mock import MockIoTAdapter
from app.services.alerts import AlertService
from app.services.greenhouse import GreenhouseService

FIXED_NOW = datetime(2026, 7, 8, 13, 0, 0)


def _default_iot_by_id():
    return {
        1: MockIoTAdapter(),
        2: MockIoTAdapter(initial_state={"shade": "open", "window": "closed", "irrigation": "off"}),
        3: MockIoTAdapter(initial_state={"shade": "closed", "window": "open", "irrigation": "off"}),
    }


def _service(iot_by_id=None):
    iot_by_id = iot_by_id or _default_iot_by_id()
    greenhouse_service = GreenhouseService(iot_by_id, GREENHOUSES, MOCK_DATA)
    return AlertService(greenhouse_service), iot_by_id


def test_list_alerts_returns_only_warning_or_critical_greenhouses():
    service, _ = _service()

    alerts = service.list_alerts(now=FIXED_NOW)

    assert [a["greenhouse_id"] for a in alerts] == [2]
    assert alerts[0]["level"] == "warning"
    assert alerts[0]["message"] == "습도 82%, 곰팡이병 위험"
    assert alerts[0]["action"] == {"device": "window", "action": "open", "label": "창문 열기"}


def test_dismiss_hides_alert_from_future_listings():
    service, _ = _service()

    dismissed = service.dismiss("gh2-humidity")

    assert dismissed is True
    assert service.list_alerts(now=FIXED_NOW) == []


def test_dismiss_unknown_alert_returns_false():
    service, _ = _service()

    assert service.dismiss("gh999-humidity") is False


def test_dismiss_inactive_alert_returns_false():
    service, _ = _service()  # 온실 1은 습도 정상 -> gh1-humidity 는 활성 알림이 아님

    assert service.dismiss("gh1-humidity") is False


def test_execute_action_controls_device_and_dismisses_alert():
    service, iot_by_id = _service()

    result = service.execute_action("gh2-humidity")

    assert result == {
        "success": True,
        "message": "2번 온실 창문을 열었습니다.",
        "updated_state": {"shade": "open", "window": "open", "irrigation": "off"},
    }
    assert iot_by_id[2].state["window"] == "open"
    assert service.list_alerts(now=FIXED_NOW) == []


def test_execute_action_on_unknown_alert_returns_none():
    service, _ = _service()

    assert service.execute_action("gh999-humidity") is None


class _FailingIoT:
    """control() 이 항상 실패하는 가짜 어댑터 (현재 데이터로는 재현 불가능한 실패 경로 검증용)."""

    def __init__(self, state):
        self.state = dict(state)

    def control(self, device, action):
        return {"ok": False, "device": device, "state": self.state[device], "reason": "simulated_failure"}

    def read(self, target):
        # IoTAdapter 계약 준수: environment 미지원 → 정적 데이터 fallback 경로를 타게 한다
        return {"ok": False, "target": target, "reason": "unknown_target"}


def test_execute_action_keeps_alert_active_when_control_fails():
    iot_by_id = _default_iot_by_id()
    iot_by_id[2] = _FailingIoT({"shade": "open", "window": "closed", "irrigation": "off"})
    service, _ = _service(iot_by_id)

    result = service.execute_action("gh2-humidity")

    assert result["success"] is False
    assert [a["id"] for a in service.list_alerts()] == ["gh2-humidity"]
