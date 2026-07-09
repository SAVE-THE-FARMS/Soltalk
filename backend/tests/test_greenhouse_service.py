"""GreenhouseService 테스트.

get_dashboard(now): [{"id","name","status","temperature","humidity","devices","last_updated"}, ...]
get_detail(id, now): {"id","status","reason","recommended_action","current_values","history"} | None

status: humidity >= 90 -> "critical", >= 80 -> "warning", else "normal"
"""

from datetime import datetime, timedelta

import pytest

from app.data.greenhouse_data import GREENHOUSES
from app.data.mock_data import MOCK_DATA
from app.iot.mock import MockIoTAdapter
from app.iot.virtual import VirtualFarmAdapter
from app.services.greenhouse import GreenhouseService

FIXED_NOW = datetime(2026, 7, 8, 13, 0, 0)


def _service():
    iot_by_id = {
        1: MockIoTAdapter(),
        2: MockIoTAdapter(initial_state={"shade": "open", "window": "closed", "irrigation": "off"}),
        3: MockIoTAdapter(initial_state={"shade": "closed", "window": "open", "irrigation": "off"}),
    }
    return GreenhouseService(iot_by_id, GREENHOUSES, MOCK_DATA), iot_by_id


def test_dashboard_lists_all_greenhouses_in_order():
    service, _ = _service()

    states = service.get_dashboard(now=FIXED_NOW)

    assert [g["id"] for g in states] == [1, 2, 3]


def test_dashboard_flags_high_humidity_greenhouse_as_warning():
    service, _ = _service()

    states = service.get_dashboard(now=FIXED_NOW)

    by_id = {g["id"]: g for g in states}
    assert by_id[1]["status"] == "normal"   # mock_data 습도 65%
    assert by_id[2]["status"] == "warning"  # 정적 습도 82%
    assert by_id[3]["status"] == "normal"   # 정적 습도 55%


def test_dashboard_greenhouse1_reflects_live_device_control():
    service, iot_by_id = _service()
    iot_by_id[1].control("shade", "close")

    states = service.get_dashboard(now=FIXED_NOW)

    by_id = {g["id"]: g for g in states}
    assert by_id[1]["devices"]["shade"] == "closed"


def test_dashboard_greenhouse2_reflects_its_own_device_control():
    service, iot_by_id = _service()
    iot_by_id[2].control("window", "open")

    states = service.get_dashboard(now=FIXED_NOW)

    by_id = {g["id"]: g for g in states}
    assert by_id[2]["devices"]["window"] == "open"
    assert by_id[1]["devices"]["window"] == "closed"  # 다른 온실엔 영향 없음


def test_detail_for_warning_greenhouse_includes_reason_and_recommendation():
    service, _ = _service()

    detail = service.get_detail(2, now=FIXED_NOW)

    assert detail["status"] == "warning"
    assert detail["reason"] == "습도 82%, 임계값 80% 초과"
    assert detail["recommended_action"] == {"device": "window", "action": "open", "label": "창문 열기"}
    assert detail["current_values"] == {"temperature": 24.0, "humidity": 82}


def test_detail_for_unknown_greenhouse_returns_none():
    service, _ = _service()

    assert service.get_detail(999, now=FIXED_NOW) is None


def test_detail_critical_reason_cites_critical_threshold(monkeypatch):
    monkeypatch.setitem(GREENHOUSES[2], "humidity", 95)
    service, _ = _service()

    detail = service.get_detail(2, now=FIXED_NOW)

    assert detail["status"] == "critical"
    assert detail["reason"] == "습도 95%, 임계값 90% 초과"


def _fixed_clock():
    return 1000.0


def test_env_values_come_from_adapter_simulation_when_available():
    """어댑터가 환경값(environment)을 제공하면(=VirtualFarmAdapter) 정적 레코드보다 우선한다.

    온실 2의 정적 레코드는 습도 82 이지만, 시뮬레이션 어댑터가 70 을 주면 70 이 보여야 한다.
    MockIoTAdapter 온실은 기존처럼 정적/센서 데이터를 쓴다 (fallback).
    """
    iot_by_id = {
        1: MockIoTAdapter(),
        2: VirtualFarmAdapter(
            initial_environment={"temperature": 25.0, "humidity": 70.0},
            initial_devices={"shade": "open", "window": "closed", "irrigation": "off"},
            clock=_fixed_clock,
        ),
        3: MockIoTAdapter(initial_state={"shade": "closed", "window": "open", "irrigation": "off"}),
    }
    service = GreenhouseService(iot_by_id, GREENHOUSES, MOCK_DATA)

    by_id = {g["id"]: g for g in service.get_dashboard(now=FIXED_NOW)}

    assert by_id[2]["humidity"] == pytest.approx(70.0)  # 시뮬레이션 값 (정적 82 아님)
    assert by_id[2]["status"] == "normal"               # 70% → 경고 아님
    assert by_id[3]["humidity"] == 55                    # Mock 온실은 기존 정적 값 유지


# --- 상세 조회 시 라이브 습도 히스토리 샘플링 ---
# 그래프가 "최근 습도 추이"를 실제로 보여주려면 get_detail 이 현재 습도를
# 히스토리에 쌓아야 한다 (정적 seed 뒤에 이어붙임).


def test_detail_appends_live_humidity_and_temperature_sample():
    """온도 그래프도 그리려면 습도뿐 아니라 온도도 같이 기록해야 한다.
    (기존 seed 데이터엔 온도가 없음 — todo/FRONTEND_통합_필수.md 4절에 이미
    알려진 갭. 라이브 샘플부터는 온도도 채운다.)"""
    service, _ = _service()
    seed_len = len(GREENHOUSES[2]["history"])

    detail = service.get_detail(2, now=FIXED_NOW)

    assert len(detail["history"]) == seed_len + 1
    last = detail["history"][-1]
    assert last == {"timestamp": FIXED_NOW.isoformat(), "humidity": 82, "temperature": 24.0}


def test_detail_does_not_resample_within_min_interval():
    service, _ = _service()
    seed_len = len(GREENHOUSES[2]["history"])

    service.get_detail(2, now=FIXED_NOW)
    detail = service.get_detail(2, now=FIXED_NOW + timedelta(seconds=1))

    assert len(detail["history"]) == seed_len + 1  # 1초 뒤 재조회는 샘플 추가 안 함


def test_detail_history_is_capped():
    service, _ = _service()

    detail = None
    for i in range(GreenhouseService.HISTORY_MAX + 5):
        detail = service.get_detail(2, now=FIXED_NOW + timedelta(seconds=3 * i))

    assert len(detail["history"]) == GreenhouseService.HISTORY_MAX


def test_reset_restores_seed_history():
    service, _ = _service()
    service.get_detail(2, now=FIXED_NOW)

    service.reset()
    detail = service.get_detail(2, now=FIXED_NOW)

    # 리셋 후엔 seed + 방금 샘플 1개만 남는다
    assert len(detail["history"]) == len(GREENHOUSES[2]["history"]) + 1


def test_detail_sampling_does_not_mutate_static_record():
    service, _ = _service()

    service.get_detail(2, now=FIXED_NOW)

    assert len(GREENHOUSES[2]["history"]) == 3  # 원본 정적 데이터는 그대로
