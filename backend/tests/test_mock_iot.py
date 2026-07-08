"""MockIoTAdapter 테스트.

반환 스키마 (설계 결정):
  control() 성공: {"ok": True, "device": device, "state": new_state}
  control() 실패: {"ok": False, "device": device, "state": state_or_None, "reason": "unknown_device" | "invalid_action"}
  read() 성공:   {"ok": True, "target": target, "value": ..., "unit": ...}
  read() 실패:   {"ok": False, "target": target, "reason": "unknown_target"}
"""

from app.iot.mock import MockIoTAdapter


def test_control_closes_shade():
    iot = MockIoTAdapter()

    result = iot.control("shade", "close")

    assert result == {"ok": True, "device": "shade", "state": "closed"}


def test_control_unknown_device_returns_error():
    iot = MockIoTAdapter()

    result = iot.control("heater", "close")

    assert result == {"ok": False, "device": "heater", "state": None, "reason": "unknown_device"}


def test_control_invalid_action_keeps_state_and_returns_error():
    iot = MockIoTAdapter()

    result = iot.control("irrigation", "close")

    assert result == {"ok": False, "device": "irrigation", "state": "off", "reason": "invalid_action"}
    assert iot.state["irrigation"] == "off"


def test_read_known_target_returns_value():
    iot = MockIoTAdapter()

    result = iot.read("temperature")

    assert result == {"ok": True, "target": "temperature", "value": 24.5, "unit": "℃"}


def test_read_unknown_target_returns_error():
    iot = MockIoTAdapter()

    result = iot.read("wind_speed")

    assert result == {"ok": False, "target": "wind_speed", "reason": "unknown_target"}


def test_custom_initial_state_is_used():
    iot = MockIoTAdapter(initial_state={"shade": "closed", "window": "open", "irrigation": "off"})

    assert iot.state == {"shade": "closed", "window": "open", "irrigation": "off"}


def test_reset_restores_initial_state():
    iot = MockIoTAdapter(initial_state={"shade": "closed", "window": "open", "irrigation": "off"})
    iot.control("shade", "open")

    iot.reset()

    assert iot.state == {"shade": "closed", "window": "open", "irrigation": "off"}
