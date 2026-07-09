"""VirtualFarmAdapter — virtualfarm 시뮬레이션을 IoTAdapter 계약으로 감싼다.

계약/설계 근거: virtualfarm/ADAPTER_CONTRACT.md

시간 진행(lazy-tick): 별도 백그라운드 태스크 없이, control/read 가 불릴 때마다
"지난 실제 경과 시간 × TIME_SCALE" 만큼 시뮬레이션을 진행한다.
→ 데모에서 창문을 열고 몇 초 지나 대시보드를 새로고침하면 습도가 내려가 있다.

production(생산량)은 시뮬레이션 범위 밖이라 sensor_data(더미 데이터)로 위임한다.
"""

import time

from sim.engine import VirtualGreenhouse

from .base import IoTAdapter

# 시뮬레이션 배속: 실제 1초 = 시뮬레이션 60초 (데모에서 변화가 눈에 보이는 속도)
DEFAULT_TIME_SCALE = 60.0


class VirtualFarmAdapter(IoTAdapter):
    def __init__(
        self,
        initial_environment: dict | None = None,
        initial_devices: dict | None = None,
        sensor_data: dict[str, dict] | None = None,
        clock=time.monotonic,
        time_scale: float = DEFAULT_TIME_SCALE,
    ):
        self._initial_environment = dict(initial_environment or {})
        self._initial_devices = dict(initial_devices or {})
        self._sensor_data = sensor_data or {}
        self._clock = clock
        self._time_scale = time_scale
        self._greenhouse = VirtualGreenhouse(
            initial_environment=self._initial_environment,
            initial_devices=self._initial_devices,
        )
        self._last_tick_at = clock()

    @property
    def state(self) -> dict:
        """장비 상태 dict — MockIoTAdapter.state 와 같은 모양 (기존 호출부 호환)."""
        return self._greenhouse.devices

    def reset(self) -> None:
        self._greenhouse = VirtualGreenhouse(
            initial_environment=self._initial_environment,
            initial_devices=self._initial_devices,
        )
        self._last_tick_at = self._clock()

    def _advance(self) -> None:
        now = self._clock()
        elapsed = now - self._last_tick_at
        if elapsed > 0:
            self._greenhouse.tick(elapsed * self._time_scale)
        self._last_tick_at = now

    def control(self, device: str, action: str) -> dict:
        self._advance()
        return self._greenhouse.control(device, action)

    def read(self, target: str) -> dict:
        self._advance()

        # 시뮬레이션이 아는 값(temperature/humidity/environment)이 항상 우선.
        # sensor_data 는 시뮬레이션 밖 데이터(production 등)의 fallback 일 뿐이다.
        result = self._greenhouse.read(target)
        if result["ok"]:
            return result

        if target in self._sensor_data:
            entry = self._sensor_data[target]
            return {"ok": True, "target": target, "value": entry["value"], "unit": entry["unit"]}

        return result  # unknown_target 에러 그대로
