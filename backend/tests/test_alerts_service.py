"""AlertService 테스트.

list_alerts(now): [{"id","level","greenhouse_id","message","created_at","escalated","action","auto"}, ...]
dismiss(alert_id) -> bool  (현재 활성 알림이어서 닫았으면 True)
execute_action(alert_id) -> {"success","message","updated_state"} | None (없으면 None)

자동 제어 모드: set_auto_mode(gid, enabled) 로 켜두면, 경고/위험인 온실을
list_alerts() 가 조회될 때마다 사람 개입 없이 recommended_action 을 대신 실행한다.

경고 방치 격상: 같은 온실이 warning 상태로 ESCALATION_AFTER 이상 계속되면
(사람이든 자동모드든 해결 안 됐다는 뜻) level 을 critical 로 격상하고 escalated=True.
"""

from datetime import datetime, timedelta

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


# --- 자동 제어 모드 ---


def test_auto_mode_defaults_to_off():
    service, _ = _service()

    assert service.is_auto_mode(2) is False


def test_set_auto_mode_enables_and_is_reflected_in_alert():
    service, _ = _service()

    assert service.set_auto_mode(2, True) is True
    assert service.is_auto_mode(2) is True
    alerts = service.list_alerts(now=FIXED_NOW)
    assert alerts[0]["auto"] is True


def test_set_auto_mode_on_unknown_greenhouse_returns_false():
    service, _ = _service()

    assert service.set_auto_mode(999, True) is False


def test_list_alerts_auto_executes_recommended_action_when_enabled():
    service, iot_by_id = _service()
    service.set_auto_mode(2, True)

    service.list_alerts(now=FIXED_NOW)

    assert iot_by_id[2].state["window"] == "open"  # 사람이 조치 버튼을 안 눌렀는데도 실행됨


def test_list_alerts_does_not_execute_when_auto_mode_disabled():
    service, iot_by_id = _service()

    service.list_alerts(now=FIXED_NOW)

    assert iot_by_id[2].state["window"] == "closed"


def test_reset_clears_auto_mode():
    service, _ = _service()
    service.set_auto_mode(2, True)

    service.reset()

    assert service.is_auto_mode(2) is False


# --- 경고 방치 시 위험으로 격상 ---


def test_freshly_started_warning_is_not_escalated():
    service, _ = _service()

    alerts = service.list_alerts(now=FIXED_NOW)

    assert alerts[0]["level"] == "warning"
    assert alerts[0]["escalated"] is False


def test_warning_escalates_to_critical_after_being_ignored():
    service, _ = _service()
    service.list_alerts(now=FIXED_NOW)  # 경고 시작 시점 기록

    later = FIXED_NOW + timedelta(seconds=30)
    alerts = service.list_alerts(now=later)

    assert alerts[0]["level"] == "critical"
    assert alerts[0]["escalated"] is True


def test_warning_not_yet_escalated_before_threshold():
    service, _ = _service()
    service.list_alerts(now=FIXED_NOW)

    soon = FIXED_NOW + timedelta(seconds=5)
    alerts = service.list_alerts(now=soon)

    assert alerts[0]["level"] == "warning"
    assert alerts[0]["escalated"] is False


def test_actual_critical_humidity_is_not_marked_escalated(monkeypatch):
    """습도 자체가 90% 넘어서 critical 인 경우는 '방치로 격상'된 게 아니다."""
    monkeypatch.setitem(GREENHOUSES[2], "humidity", 95)
    service, _ = _service()

    alerts = service.list_alerts(now=FIXED_NOW)

    assert alerts[0]["level"] == "critical"
    assert alerts[0]["escalated"] is False


def test_escalation_timer_resets_after_greenhouse_recovers(monkeypatch):
    service, _ = _service()
    monkeypatch.setitem(GREENHOUSES[3], "humidity", 85)  # 3번 온실(원래 정상)을 경고로 만듦
    service.list_alerts(now=FIXED_NOW)  # 경고 시작 시점 기록

    monkeypatch.setitem(GREENHOUSES[3], "humidity", 50)  # 정상으로 회복 → 타이머 리셋
    service.list_alerts(now=FIXED_NOW + timedelta(seconds=10))

    monkeypatch.setitem(GREENHOUSES[3], "humidity", 85)  # 다시 경고 (새로 시작이어야 함)
    alerts = service.list_alerts(now=FIXED_NOW + timedelta(seconds=25))
    gh3_alert = next(a for a in alerts if a["greenhouse_id"] == 3)

    # 최초 경고로부터는 25초가 지났지만, 중간에 회복했다 재발한 것이므로
    # 격상 임계값(20초)에 아직 못 미쳐야 한다.
    assert gh3_alert["level"] == "warning"
    assert gh3_alert["escalated"] is False


def test_reset_clears_escalation_timer():
    service, _ = _service()
    service.list_alerts(now=FIXED_NOW)

    service.reset()
    alerts = service.list_alerts(now=FIXED_NOW + timedelta(seconds=30))

    assert alerts[0]["level"] == "warning"  # 리셋됐으니 새로 시작, 아직 격상 안 됨
    assert alerts[0]["escalated"] is False
