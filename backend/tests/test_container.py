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


def test_container_shares_single_tool_executor_between_chat_and_voice():
    """텍스트 챗봇과 실시간 음성(/api/tools/execute)이 같은 실행기 인스턴스를 써야
    한쪽만 기능이 추가/변경되는 조용한 어긋남이 없다."""
    container = AppContainer()

    assert container.chat_agent._tool_executor is container.tool_executor


def test_container_reset_restores_simulation():
    container = AppContainer()
    container.chat_iot.control("window", "open")

    container.reset_all()

    assert container.chat_iot.state["window"] == "closed"
    assert container.chat_iot.read("humidity")["value"] == pytest.approx(65.0, abs=0.5)
