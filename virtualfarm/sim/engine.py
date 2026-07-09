"""가상 온실 시뮬레이션 엔진.

목표: 지금 backend 의 MockIoTAdapter 는 센서값이 고정(습도 82% 그대로)이다.
이 엔진은 시간이 흐르고(tick) 장비를 조작하면(control) 환경값이 반응하는
"살아있는" 가상 온실을 만든다.

backend 연동 계약: ../ADAPTER_CONTRACT.md

설계 원칙 (CLAUDE.md 준수):
- backend 의 IoTAdapter 계약과 같은 모양의 control()/read() 를 제공해서,
  나중에 backend 가 MockIoTAdapter ↔ VirtualFarmAdapter 를 갈아끼울 수 있게 한다.
- backend/ 폴더의 코드는 import 하지 않는다 (형상관리 분리 — 이 폴더만으로 완결).
- 실제 농가 데이터 금지. 물리 상수/초기값 전부 시연용 가짜 값.

시뮬레이션 모델 (설계 결정 — 단순하고 테스트 가능한 1차 수렴 모델):
- 모든 환경 변화는 "목표값을 향해 지수적으로 수렴"하는 1차 모델을 쓴다.
  변화량 = (목표 - 현재) * (1 - exp(-rate * seconds))
  → tick 을 잘게 쪼개든 크게 부르든 누적 결과가 같고, 목표를 절대 넘어서지 않는다.
- 창문 open  → 습도가 외기 습도(OUTDOOR_HUMIDITY) 쪽으로 수렴.
- 관수 on    → 습도가 IRRIGATION_TARGET_HUMIDITY 쪽으로 수렴 (무한 상승 방지).
- 온도는 차광막에 따라 목표가 달라짐: open 이면 한낮 온실 효과(+SOLAR), closed 면 완화.
- 창문 open 이 온도에 주는 영향은 1차 범위에서 생략 (단순화 — 필요 시 확장).
- 창문 closed + 관수 off 면 습도는 변하지 않는다 (자연 드리프트 생략 — 단순화).
- 환경값은 현실적인 범위로 clamp: 습도 0~100%, 온도 -20~60℃.
"""

import math


# 시뮬레이션 기본값 (전부 시연용 가짜 값 — 실제 농가 데이터 아님)
_DEFAULT_ENVIRONMENT = {
    "temperature": 24.0,  # ℃
    "humidity": 65.0,     # %
}
_DEFAULT_DEVICES = {
    "shade": "open",        # 차광막
    "window": "closed",     # 창문
    "irrigation": "off",    # 관수
}

# backend/app/iot/mock.py 와 동일한 계약 (import 하지 않고 값을 맞춘다 — 폴더 분리 원칙)
_ACTION_TO_STATE = {"open": "open", "close": "closed", "on": "on", "off": "off"}
_ALLOWED_ACTIONS = {
    "shade": {"open", "close"},
    "window": {"open", "close"},
    "irrigation": {"on", "off"},
}
_UNITS = {"temperature": "℃", "humidity": "%"}

# --- 시뮬레이션 물리 상수 (시연용 가짜 값) ---
OUTDOOR_HUMIDITY = 50.0        # % — 바깥 공기 습도. 창문 열면 이 값으로 수렴
OUTDOOR_TEMPERATURE = 30.0     # ℃ — 한낮 외기 온도
IRRIGATION_TARGET_HUMIDITY = 95.0  # % — 관수 켰을 때 습도 수렴 상한

# 차광막 상태별 온도 목표: open 이면 태양열로 외기보다 +8℃, closed 면 +2℃ 까지만
_TEMP_TARGET_BY_SHADE = {
    "open": OUTDOOR_TEMPERATURE + 8.0,   # 38.0℃
    "closed": OUTDOOR_TEMPERATURE + 2.0, # 32.0℃
}

# 수렴 속도(초당). 60초 tick 기준 목표까지 남은 거리의 약 3% 씩 이동 → 완만한 변화
_WINDOW_HUMIDITY_RATE = 0.0005
_IRRIGATION_HUMIDITY_RATE = 0.001
_TEMPERATURE_RATE = 0.0005

# 환경값 clamp 범위
_HUMIDITY_BOUNDS = (0.0, 100.0)
_TEMPERATURE_BOUNDS = (-20.0, 60.0)


def _approach(current: float, target: float, rate: float, seconds: float) -> float:
    """1차 수렴: 목표를 향해 지수적으로 다가간다 (목표를 절대 넘지 않음)."""
    return current + (target - current) * (1.0 - math.exp(-rate * seconds))


def _clamp(value: float, bounds: tuple[float, float]) -> float:
    low, high = bounds
    return max(low, min(high, value))


class VirtualGreenhouse:
    """온실 하나의 가상 상태. tick() 할 때마다 환경이 변한다."""

    def __init__(
        self,
        initial_environment: dict | None = None,
        initial_devices: dict | None = None,
    ):
        self.environment = {**_DEFAULT_ENVIRONMENT, **(initial_environment or {})}
        self.devices = {**_DEFAULT_DEVICES, **(initial_devices or {})}

    def tick(self, seconds: float = 60.0) -> None:
        """시간을 흘려보낸다. 장비 상태에 따라 환경값이 변한다."""
        if seconds <= 0:
            raise ValueError(f"seconds 는 양수여야 합니다: {seconds}")

        humidity = self.environment["humidity"]
        if self.devices["window"] == "open":
            humidity = _approach(humidity, OUTDOOR_HUMIDITY, _WINDOW_HUMIDITY_RATE, seconds)
        if self.devices["irrigation"] == "on":
            humidity = _approach(humidity, IRRIGATION_TARGET_HUMIDITY, _IRRIGATION_HUMIDITY_RATE, seconds)
        self.environment["humidity"] = _clamp(humidity, _HUMIDITY_BOUNDS)

        temp_target = _TEMP_TARGET_BY_SHADE[self.devices["shade"]]
        temperature = _approach(self.environment["temperature"], temp_target, _TEMPERATURE_RATE, seconds)
        self.environment["temperature"] = _clamp(temperature, _TEMPERATURE_BOUNDS)

    def control(self, device: str, action: str) -> dict:
        """backend IoTAdapter.control() 과 같은 반환 스키마를 지킨다."""
        if device not in self.devices:
            return {"ok": False, "device": device, "state": None, "reason": "unknown_device"}

        if action not in _ALLOWED_ACTIONS[device]:
            return {"ok": False, "device": device, "state": self.devices[device], "reason": "invalid_action"}

        new_state = _ACTION_TO_STATE[action]
        self.devices[device] = new_state
        return {"ok": True, "device": device, "state": new_state}

    def read(self, target: str) -> dict:
        """backend IoTAdapter.read() 와 같은 반환 스키마를 지킨다.

        추가 target "environment": 환경값 전체를 dict 로 반환 (unit 은 None).
        """
        if target == "environment":
            return {"ok": True, "target": "environment", "value": dict(self.environment), "unit": None}

        if target not in self.environment:
            return {"ok": False, "target": target, "reason": "unknown_target"}

        return {"ok": True, "target": target, "value": self.environment[target], "unit": _UNITS[target]}


class VirtualFarm:
    """온실 여러 개를 독립 상태로 관리하는 간단한 매니저.

    각 온실은 자기 VirtualGreenhouse 인스턴스를 가진다 (상태 완전 독립).
    온실별 초기값 차별화가 필요해지면 greenhouse_ids 대신 설정 dict 를 받도록 확장.
    """

    def __init__(self, greenhouse_ids: list[int] | tuple[int, ...] = (1, 2, 3)):
        self._greenhouses = {gid: VirtualGreenhouse() for gid in greenhouse_ids}

    @property
    def greenhouse_ids(self) -> list[int]:
        return list(self._greenhouses)

    def greenhouse(self, greenhouse_id: int) -> VirtualGreenhouse:
        return self._greenhouses[greenhouse_id]  # 없는 id 는 KeyError

    def tick_all(self, seconds: float = 60.0) -> None:
        for gh in self._greenhouses.values():
            gh.tick(seconds)
