"""스캐폴딩 검증용 스모크 테스트 — 패키지 임포트가 되는지만 확인.

실제 시뮬레이션 동작 테스트는 TDD 로 구현하면서 추가한다.
"""

from sim.engine import VirtualGreenhouse


def test_engine_module_imports():
    assert VirtualGreenhouse is not None
