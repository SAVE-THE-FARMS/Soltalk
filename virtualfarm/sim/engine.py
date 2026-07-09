"""가상 온실 시뮬레이션 엔진 (뼈대).

목표: 지금 backend 의 MockIoTAdapter 는 센서값이 고정(습도 82% 그대로)이다.
이 엔진은 시간이 흐르고(tick) 장비를 조작하면(control) 환경값이 반응하는
"살아있는" 가상 온실을 만든다.

설계 원칙 (CLAUDE.md 준수):
- backend 의 IoTAdapter 계약과 같은 모양의 control()/read() 를 제공해서,
  나중에 backend 가 MockIoTAdapter ↔ VirtualFarmAdapter 를 갈아끼울 수 있게 한다.
- backend/ 폴더의 코드는 import 하지 않는다 (형상관리 분리 — 이 폴더만으로 완결).
- 실제 농가 데이터 금지. 물리 상수/초기값 전부 시연용 가짜 값.

구현은 TDD 로 진행. 아직 뼈대만 있음.
"""


class VirtualGreenhouse:
    """온실 하나의 가상 상태. tick() 할 때마다 환경이 변한다."""

    def __init__(self, initial_state: dict | None = None):
        # TODO: 환경값(temperature/humidity) + 장비 상태(shade/window/irrigation) 초기화
        raise NotImplementedError

    def tick(self, seconds: float = 60.0) -> None:
        """시간을 흘려보낸다. 장비 상태에 따라 환경값이 변한다.
        예: window=open 이면 습도가 외기 쪽으로 수렴, irrigation=on 이면 습도 상승.
        """
        raise NotImplementedError

    def control(self, device: str, action: str) -> dict:
        """backend IoTAdapter.control() 과 같은 반환 스키마를 지킨다.
        성공: {"ok": True, "device": str, "state": str}
        실패: {"ok": False, "device": str, "state": str|None, "reason": ...}
        """
        raise NotImplementedError

    def read(self, target: str) -> dict:
        """backend IoTAdapter.read() 와 같은 반환 스키마를 지킨다.
        성공: {"ok": True, "target": str, "value": ..., "unit": str}
        실패: {"ok": False, "target": str, "reason": "unknown_target"}
        """
        raise NotImplementedError
