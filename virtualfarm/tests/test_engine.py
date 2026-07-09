"""VirtualGreenhouse 시뮬레이션 코어 테스트.

반환 스키마는 backend 의 IoTAdapter 계약과 동일하게 유지한다 (ADAPTER_CONTRACT.md 참고):
  control() 성공: {"ok": True, "device": str, "state": str}
  control() 실패: {"ok": False, "device": str, "state": str|None, "reason": "unknown_device"|"invalid_action"}
  read() 성공:    {"ok": True, "target": str, "value": ..., "unit": str}
  read() 실패:    {"ok": False, "target": str, "reason": "unknown_target"}
"""

import pytest

from sim.engine import (
    IRRIGATION_TARGET_HUMIDITY,
    OUTDOOR_HUMIDITY,
    VirtualGreenhouse,
)

TICK = 60.0  # 테스트 기본 tick 간격(초)


# ---------- __init__ ----------


def test_default_environment_and_devices():
    gh = VirtualGreenhouse()

    assert gh.environment == {"temperature": 24.0, "humidity": 65.0}
    assert gh.devices == {"shade": "open", "window": "closed", "irrigation": "off"}


def test_initial_overrides_are_applied():
    gh = VirtualGreenhouse(
        initial_environment={"temperature": 30.0, "humidity": 82.0},
        initial_devices={"shade": "closed", "window": "open", "irrigation": "on"},
    )

    assert gh.environment == {"temperature": 30.0, "humidity": 82.0}
    assert gh.devices == {"shade": "closed", "window": "open", "irrigation": "on"}


def test_partial_environment_override_keeps_other_defaults():
    gh = VirtualGreenhouse(initial_environment={"humidity": 82.0})

    assert gh.environment["humidity"] == 82.0
    assert gh.environment["temperature"] == 24.0


# ---------- control ----------


def test_control_opens_window():
    gh = VirtualGreenhouse()

    result = gh.control("window", "open")

    assert result == {"ok": True, "device": "window", "state": "open"}
    assert gh.devices["window"] == "open"


def test_control_close_action_normalizes_to_closed_state():
    gh = VirtualGreenhouse()

    result = gh.control("shade", "close")

    assert result == {"ok": True, "device": "shade", "state": "closed"}


def test_control_unknown_device_returns_error():
    gh = VirtualGreenhouse()

    result = gh.control("heater", "on")

    assert result == {"ok": False, "device": "heater", "state": None, "reason": "unknown_device"}


def test_control_invalid_action_keeps_state_and_returns_error():
    gh = VirtualGreenhouse()

    result = gh.control("irrigation", "open")  # 관수는 on/off 만 지원

    assert result == {"ok": False, "device": "irrigation", "state": "off", "reason": "invalid_action"}
    assert gh.devices["irrigation"] == "off"


# ---------- read ----------


def test_read_temperature():
    gh = VirtualGreenhouse()

    assert gh.read("temperature") == {"ok": True, "target": "temperature", "value": 24.0, "unit": "℃"}


def test_read_humidity():
    gh = VirtualGreenhouse()

    assert gh.read("humidity") == {"ok": True, "target": "humidity", "value": 65.0, "unit": "%"}


def test_read_environment_returns_all_values():
    gh = VirtualGreenhouse()

    result = gh.read("environment")

    assert result == {
        "ok": True,
        "target": "environment",
        "value": {"temperature": 24.0, "humidity": 65.0},
        "unit": None,
    }


def test_read_unknown_target_returns_error():
    gh = VirtualGreenhouse()

    assert gh.read("wind_speed") == {"ok": False, "target": "wind_speed", "reason": "unknown_target"}


# ---------- tick ----------


def test_tick_rejects_zero_or_negative_seconds():
    gh = VirtualGreenhouse()

    with pytest.raises(ValueError):
        gh.tick(0)
    with pytest.raises(ValueError):
        gh.tick(-5)


def test_window_open_humidity_converges_gradually_toward_outdoor():
    gh = VirtualGreenhouse(initial_environment={"humidity": 82.0})
    gh.control("window", "open")

    gh.tick(TICK)
    after_one = gh.environment["humidity"]
    # 한 번에 급격히 안 떨어짐: 아직 80% 위, 그래도 82보다는 내려감
    assert 80.0 < after_one < 82.0

    previous = after_one
    for _ in range(20):
        gh.tick(TICK)
        current = gh.environment["humidity"]
        assert current < previous  # tick 누적마다 계속 하강
        previous = current

    assert gh.environment["humidity"] > OUTDOOR_HUMIDITY  # 외기 밑으로 뚫고 내려가진 않음


def test_closed_window_without_irrigation_keeps_humidity_constant():
    gh = VirtualGreenhouse(initial_environment={"humidity": 82.0})

    gh.tick(TICK)

    assert gh.environment["humidity"] == pytest.approx(82.0)


def test_irrigation_on_raises_humidity_but_converges_below_ceiling():
    gh = VirtualGreenhouse()
    gh.control("irrigation", "on")

    gh.tick(TICK)
    assert gh.environment["humidity"] > 65.0  # 상승

    for _ in range(500):  # 오래 틀어놔도
        gh.tick(TICK)
    assert gh.environment["humidity"] <= IRRIGATION_TARGET_HUMIDITY + 1e-6  # 무한 상승 없음


def test_shade_closed_suppresses_temperature_rise():
    open_gh = VirtualGreenhouse(initial_devices={"shade": "open"})
    closed_gh = VirtualGreenhouse(initial_devices={"shade": "closed"})

    for _ in range(10):
        open_gh.tick(TICK)
        closed_gh.tick(TICK)

    open_rise = open_gh.environment["temperature"] - 24.0
    closed_rise = closed_gh.environment["temperature"] - 24.0
    assert open_rise > 0  # 낮이라 온도는 오르되
    assert closed_rise < open_rise  # 차광막 닫으면 상승폭이 작다


def test_environment_stays_within_realistic_bounds():
    gh = VirtualGreenhouse(initial_environment={"temperature": 59.9, "humidity": 99.9})
    gh.control("irrigation", "on")

    for _ in range(100):
        gh.tick(TICK)

    assert -20.0 <= gh.environment["temperature"] <= 60.0
    assert 0.0 <= gh.environment["humidity"] <= 100.0
