"""greenhouse_service 테스트.

반환 스키마 (설계 결정):
  get_dashboard(iot_by_id, now): [{"id", "name", "status", "temperature", "humidity", "devices", "last_updated"}, ...]
  get_detail(iot_by_id, id, now): {"id", "status", "reason", "recommended_action", "current_values", "history"} | None

status: humidity >= 90 -> "critical", >= 80 -> "warning", else "normal"

온실별로 MockIoTAdapter 를 따로 두는 이유: 대시보드/알림이 어떤 온실을 다루든
control() 의 검증 로직(존재하지 않는 device/action 방어)을 그대로 타게 하기 위함.
"""

from datetime import datetime

from app.data.greenhouse_data import GREENHOUSES
from app.greenhouse_service import get_dashboard, get_detail
from app.iot.mock import MockIoTAdapter

FIXED_NOW = datetime(2026, 7, 8, 13, 0, 0)


def _iot_by_id():
    return {
        1: MockIoTAdapter(),
        2: MockIoTAdapter(initial_state={"shade": "open", "window": "closed", "irrigation": "off"}),
        3: MockIoTAdapter(initial_state={"shade": "closed", "window": "open", "irrigation": "off"}),
    }


def test_dashboard_lists_all_greenhouses_in_order():
    states = get_dashboard(_iot_by_id(), now=FIXED_NOW)

    assert [g["id"] for g in states] == [1, 2, 3]


def test_dashboard_flags_high_humidity_greenhouse_as_warning():
    states = get_dashboard(_iot_by_id(), now=FIXED_NOW)

    by_id = {g["id"]: g for g in states}
    assert by_id[1]["status"] == "normal"   # mock_data 습도 65%
    assert by_id[2]["status"] == "warning"  # 정적 습도 82%
    assert by_id[3]["status"] == "normal"   # 정적 습도 55%


def test_dashboard_greenhouse1_reflects_live_device_control():
    iot_by_id = _iot_by_id()
    iot_by_id[1].control("shade", "close")

    states = get_dashboard(iot_by_id, now=FIXED_NOW)

    by_id = {g["id"]: g for g in states}
    assert by_id[1]["devices"]["shade"] == "closed"


def test_dashboard_greenhouse2_reflects_its_own_device_control():
    iot_by_id = _iot_by_id()
    iot_by_id[2].control("window", "open")

    states = get_dashboard(iot_by_id, now=FIXED_NOW)

    by_id = {g["id"]: g for g in states}
    assert by_id[2]["devices"]["window"] == "open"
    assert by_id[1]["devices"]["window"] == "closed"  # 다른 온실엔 영향 없음


def test_detail_for_warning_greenhouse_includes_reason_and_recommendation():
    detail = get_detail(_iot_by_id(), 2, now=FIXED_NOW)

    assert detail["status"] == "warning"
    assert detail["reason"] == "습도 82%, 임계값 80% 초과"
    assert detail["recommended_action"] == {"device": "window", "action": "open", "label": "창문 열기"}
    assert detail["current_values"] == {"temperature": 24.0, "humidity": 82}


def test_detail_for_unknown_greenhouse_returns_none():
    assert get_detail(_iot_by_id(), 999, now=FIXED_NOW) is None


def test_detail_critical_reason_cites_critical_threshold(monkeypatch):
    monkeypatch.setitem(GREENHOUSES[2], "humidity", 95)

    detail = get_detail(_iot_by_id(), 2, now=FIXED_NOW)

    assert detail["status"] == "critical"
    assert detail["reason"] == "습도 95%, 임계값 90% 초과"
