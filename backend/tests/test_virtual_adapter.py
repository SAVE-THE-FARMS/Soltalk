"""VirtualFarmAdapter 테스트.

virtualfarm 의 VirtualGreenhouse 를 IoTAdapter 계약으로 감싸는 어댑터.
시간 진행은 lazy-tick: control/read 가 불릴 때 지난 실제 시간 × TIME_SCALE 만큼 시뮬레이션을 진행.
테스트에서는 가짜 시계를 주입해 결정적으로 검증한다.
"""

import pytest

from app.iot.virtual import VirtualFarmAdapter


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def _adapter(clock, **kwargs):
    return VirtualFarmAdapter(
        initial_environment={"temperature": 24.0, "humidity": 82.0},
        initial_devices={"shade": "open", "window": "closed", "irrigation": "off"},
        sensor_data={"production": {"value": 120, "unit": "kg"}},
        clock=clock,
        **kwargs,
    )


def test_control_delegates_with_backend_schema():
    adapter = _adapter(FakeClock())

    result = adapter.control("window", "open")

    assert result == {"ok": True, "device": "window", "state": "open"}
    assert adapter.state["window"] == "open"


def test_read_humidity_comes_from_simulation():
    adapter = _adapter(FakeClock())

    result = adapter.read("humidity")

    assert result == {"ok": True, "target": "humidity", "value": 82.0, "unit": "%"}


def test_read_production_delegates_to_sensor_data():
    adapter = _adapter(FakeClock())

    result = adapter.read("production")

    assert result == {"ok": True, "target": "production", "value": 120, "unit": "kg"}


def test_simulation_wins_over_sensor_data_for_environment_targets():
    """sensor_data 에 temperature/humidity 가 섞여 있어도(MOCK_DATA 전체를 넘긴 경우)
    환경값은 반드시 시뮬레이션에서 나와야 한다."""
    adapter = VirtualFarmAdapter(
        initial_environment={"temperature": 24.0, "humidity": 82.0},
        sensor_data={
            "temperature": {"value": 99.9, "unit": "℃"},  # 정적 더미 — 무시돼야 함
            "humidity": {"value": 11.1, "unit": "%"},
            "production": {"value": 120, "unit": "kg"},
        },
        clock=FakeClock(),
    )

    assert adapter.read("temperature")["value"] == pytest.approx(24.0)
    assert adapter.read("humidity")["value"] == pytest.approx(82.0)
    assert adapter.read("production")["value"] == 120


def test_elapsed_time_advances_simulation():
    clock = FakeClock()
    adapter = _adapter(clock, time_scale=60.0)
    adapter.control("window", "open")

    clock.advance(10.0)  # 실제 10초 = 시뮬레이션 600초

    humidity = adapter.read("humidity")["value"]
    assert humidity < 82.0  # 창문이 열려 있었으니 습도 하강


def test_no_elapsed_time_means_no_change():
    clock = FakeClock()
    adapter = _adapter(clock)
    adapter.control("window", "open")

    humidity_1 = adapter.read("humidity")["value"]
    humidity_2 = adapter.read("humidity")["value"]  # 시계가 안 흘렀으면 그대로

    assert humidity_1 == pytest.approx(humidity_2)


def test_reset_restores_initial_environment_and_devices():
    clock = FakeClock()
    adapter = _adapter(clock)
    adapter.control("window", "open")
    clock.advance(100.0)
    adapter.read("humidity")  # 시뮬레이션 진행시켜 상태를 흐트러뜨림

    adapter.reset()

    assert adapter.state == {"shade": "open", "window": "closed", "irrigation": "off"}
    assert adapter.read("humidity")["value"] == pytest.approx(82.0)
