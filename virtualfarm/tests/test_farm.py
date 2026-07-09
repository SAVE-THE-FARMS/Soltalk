"""VirtualFarm — 온실 여러 개를 독립 상태로 관리하는 간단한 매니저."""

import pytest

from sim.engine import VirtualFarm

TICK = 60.0


def test_farm_creates_independent_greenhouses():
    farm = VirtualFarm(greenhouse_ids=[1, 2, 3])

    assert sorted(farm.greenhouse_ids) == [1, 2, 3]

    # 1번 온실만 창문을 열면 다른 온실은 영향 없음
    farm.greenhouse(1).control("window", "open")

    assert farm.greenhouse(1).devices["window"] == "open"
    assert farm.greenhouse(2).devices["window"] == "closed"
    assert farm.greenhouse(3).devices["window"] == "closed"


def test_tick_all_advances_every_greenhouse():
    farm = VirtualFarm(greenhouse_ids=[1, 2])
    farm.greenhouse(1).control("irrigation", "on")

    farm.tick_all(TICK)

    assert farm.greenhouse(1).environment["humidity"] > 65.0  # 관수 켠 온실은 습도 상승
    assert farm.greenhouse(2).environment["humidity"] == pytest.approx(65.0)  # 나머지는 그대로


def test_unknown_greenhouse_id_raises_keyerror():
    farm = VirtualFarm(greenhouse_ids=[1])

    with pytest.raises(KeyError):
        farm.greenhouse(999)
