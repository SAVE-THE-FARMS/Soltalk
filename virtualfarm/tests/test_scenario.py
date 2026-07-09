"""필수 시나리오: "습도 82% 경고 → 창문 열기 → 몇 tick 후 습도 80% 아래 → 경고 해소".

backend 의 경고 기준(HUMIDITY_WARNING_THRESHOLD = 80)과 같은 값을 쓴다.
read/control/tick 공개 API 조합만으로 재현한다 (내부 상태 직접 접근 없음).
"""

from sim.engine import VirtualGreenhouse

HUMIDITY_WARNING_THRESHOLD = 80.0  # backend greenhouse_service 와 동일 기준
TICK = 60.0


def test_opening_window_clears_humidity_warning_after_several_ticks():
    gh = VirtualGreenhouse(initial_environment={"humidity": 82.0})

    # 1) 경고 상태 확인
    assert gh.read("humidity")["value"] >= HUMIDITY_WARNING_THRESHOLD

    # 2) 창문 열기 (원터치 조치)
    result = gh.control("window", "open")
    assert result["ok"] is True

    # 3) 한 tick 으로는 아직 경고 (급격한 변화 없음)
    gh.tick(TICK)
    assert gh.read("humidity")["value"] >= HUMIDITY_WARNING_THRESHOLD

    # 4) 몇 tick 더 지나면 경고 기준 아래로
    for _ in range(9):
        gh.tick(TICK)

    assert gh.read("humidity")["value"] < HUMIDITY_WARNING_THRESHOLD
