"""AppContainer 조립 테스트 — 온실 어댑터가 가상 시뮬레이션으로 교체됐는지."""

import pytest

from app.container import AppContainer
from app.iot.virtual import VirtualFarmAdapter


def test_container_wires_virtual_adapters_with_greenhouse_data():
    container = AppContainer()

    # 온실 3개 전부 시뮬레이션 어댑터
    assert set(container.iot_by_greenhouse) == {1, 2, 3}
    for adapter in container.iot_by_greenhouse.values():
        assert isinstance(adapter, VirtualFarmAdapter)

    # 초기 환경값이 온실별 데모 데이터와 일치 (온실2 = 습도 82% 경고 시나리오)
    assert container.iot_by_greenhouse[2].read("humidity")["value"] == pytest.approx(82.0, abs=0.5)
    assert container.iot_by_greenhouse[1].read("humidity")["value"] == pytest.approx(65.0, abs=0.5)

    # 장비 초기 상태 유지
    assert container.iot_by_greenhouse[2].state["window"] == "closed"


def test_container_reset_restores_simulation():
    container = AppContainer()
    container.chat_iot.control("window", "open")

    container.reset_all()

    assert container.chat_iot.state["window"] == "closed"
    assert container.chat_iot.read("humidity")["value"] == pytest.approx(65.0, abs=0.5)
