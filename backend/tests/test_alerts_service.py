"""alerts_service 테스트.

반환 스키마 (설계 결정):
  list_alerts(iot_by_id, now): [{"id","level","greenhouse_id","message","created_at","escalated","action"}, ...]
  dismiss(alert_id, iot_by_id) -> bool  (현재 활성 알림이어서 닫았으면 True)
  execute_action(alert_id, iot_by_id) -> {"success","message","updated_state"} | None (없으면 None)
"""

from datetime import datetime

from app import alerts_service
from app.iot.mock import MockIoTAdapter

FIXED_NOW = datetime(2026, 7, 8, 13, 0, 0)


def _iot_by_id():
    return {
        1: MockIoTAdapter(),
        2: MockIoTAdapter(initial_state={"shade": "open", "window": "closed", "irrigation": "off"}),
        3: MockIoTAdapter(initial_state={"shade": "closed", "window": "open", "irrigation": "off"}),
    }


def test_list_alerts_returns_only_warning_or_critical_greenhouses():
    alerts_service.reset()

    alerts = alerts_service.list_alerts(_iot_by_id(), now=FIXED_NOW)

    assert [a["greenhouse_id"] for a in alerts] == [2]
    assert alerts[0]["level"] == "warning"
    assert alerts[0]["message"] == "습도 82%, 곰팡이병 위험"
    assert alerts[0]["action"] == {"device": "window", "action": "open", "label": "창문 열기"}


def test_dismiss_hides_alert_from_future_listings():
    alerts_service.reset()
    iot_by_id = _iot_by_id()

    dismissed = alerts_service.dismiss("gh2-humidity", iot_by_id)

    assert dismissed is True
    assert alerts_service.list_alerts(iot_by_id, now=FIXED_NOW) == []


def test_dismiss_unknown_alert_returns_false():
    alerts_service.reset()

    assert alerts_service.dismiss("gh999-humidity", _iot_by_id()) is False


def test_dismiss_inactive_alert_returns_false():
    alerts_service.reset()
    iot_by_id = _iot_by_id()  # 온실 1은 습도 정상 -> gh1-humidity 는 활성 알림이 아님

    assert alerts_service.dismiss("gh1-humidity", iot_by_id) is False


def test_execute_action_controls_device_and_dismisses_alert():
    alerts_service.reset()
    iot_by_id = _iot_by_id()

    result = alerts_service.execute_action("gh2-humidity", iot_by_id)

    assert result == {
        "success": True,
        "message": "2번 온실 창문을 열었습니다.",
        "updated_state": {"shade": "open", "window": "open", "irrigation": "off"},
    }
    assert iot_by_id[2].state["window"] == "open"
    assert alerts_service.list_alerts(iot_by_id, now=FIXED_NOW) == []


def test_execute_action_on_unknown_alert_returns_none():
    alerts_service.reset()

    assert alerts_service.execute_action("gh999-humidity", _iot_by_id()) is None


class _FailingIoT:
    """control() 이 항상 실패하는 가짜 어댑터 (현재 데이터로는 재현 불가능한 실패 경로 검증용)."""

    def __init__(self, state):
        self.state = dict(state)

    def control(self, device, action):
        return {"ok": False, "device": device, "state": self.state[device], "reason": "simulated_failure"}


def test_execute_action_keeps_alert_active_when_control_fails():
    alerts_service.reset()
    iot_by_id = _iot_by_id()
    iot_by_id[2] = _FailingIoT({"shade": "open", "window": "closed", "irrigation": "off"})

    result = alerts_service.execute_action("gh2-humidity", iot_by_id)

    assert result["success"] is False
    assert [a["id"] for a in alerts_service.list_alerts(iot_by_id)] == ["gh2-humidity"]
