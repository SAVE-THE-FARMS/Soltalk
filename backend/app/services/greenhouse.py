"""온실 대시보드 상태 계산.

smartfarm_api_spec.md 1.2 (/api/state, /api/state/{id}) 대응.
의존성(온실별 IoT 어댑터, 온실 정적 데이터, 실시간 센서 데이터)은 생성자로 주입받는다.

환경값 규칙: 온실 레코드에 temperature/humidity 가 있으면 그 정적 값을,
없으면(=1번 온실) 실시간 센서 데이터(sensor_data)를 쓴다. 장비 상태는 항상
각 온실의 IoT 어댑터에서 읽는다.

status 판정 (습도 기준): >=90 critical / >=80 warning / else normal
"""

from datetime import datetime, timedelta

from ..iot.base import IoTAdapter


class GreenhouseService:
    HUMIDITY_WARNING_THRESHOLD = 80
    HUMIDITY_CRITICAL_THRESHOLD = 90
    # 상세 조회 시 라이브 습도 샘플링: 그래프가 실시간 변화를 보여주게 한다
    HISTORY_MAX = 12  # seed + 라이브 샘플 합쳐 최근 N개만 유지
    SAMPLE_MIN_INTERVAL = timedelta(seconds=3)

    def __init__(
        self,
        iot_by_id: dict[int, IoTAdapter],
        greenhouses: dict[int, dict],
        sensor_data: dict[str, dict],
    ):
        self._iot_by_id = iot_by_id
        self._greenhouses = greenhouses
        self._sensor_data = sensor_data
        self._seed_history()

    def _seed_history(self) -> None:
        self._history = {gid: list(record["history"]) for gid, record in self._greenhouses.items()}
        self._last_sample_at: dict[int, datetime] = {}

    def reset(self) -> None:
        """리허설/재시연용 — 라이브 샘플을 버리고 정적 seed 히스토리로 복원."""
        self._seed_history()

    @property
    def greenhouse_ids(self) -> list[int]:
        return list(self._greenhouses)

    def adapter(self, greenhouse_id: int) -> IoTAdapter | None:
        return self._iot_by_id.get(greenhouse_id)

    def _status_for(self, humidity: float) -> str:
        if humidity >= self.HUMIDITY_CRITICAL_THRESHOLD:
            return "critical"
        if humidity >= self.HUMIDITY_WARNING_THRESHOLD:
            return "warning"
        return "normal"

    def _env_values_for(self, greenhouse_id: int) -> dict:
        # 어댑터가 환경값을 직접 제공하면(=VirtualFarmAdapter 시뮬레이션) 그게 항상 우선.
        # MockIoTAdapter 는 "environment" 를 모르므로(ok=False) 아래 정적/센서 데이터로 fallback.
        env = self._iot_by_id[greenhouse_id].read("environment")
        if env["ok"]:
            return {
                "temperature": round(env["value"]["temperature"], 1),
                "humidity": round(env["value"]["humidity"], 1),
            }

        record = self._greenhouses[greenhouse_id]
        if "temperature" in record and "humidity" in record:
            return {"temperature": record["temperature"], "humidity": record["humidity"]}
        return {
            "temperature": self._sensor_data["temperature"]["value"],
            "humidity": self._sensor_data["humidity"]["value"],
        }

    def get_dashboard(self, now: datetime | None = None) -> list[dict]:
        now = now or datetime.now()
        states = []
        for greenhouse_id, record in self._greenhouses.items():
            env = self._env_values_for(greenhouse_id)
            states.append(
                {
                    "id": greenhouse_id,
                    "name": record["name"],
                    "status": self._status_for(env["humidity"]),
                    "temperature": env["temperature"],
                    "humidity": env["humidity"],
                    "devices": dict(self._iot_by_id[greenhouse_id].state),
                    "last_updated": now.isoformat(),
                }
            )
        return states

    def get_detail(self, greenhouse_id: int, now: datetime | None = None) -> dict | None:
        if greenhouse_id not in self._greenhouses:
            return None

        now = now or datetime.now()
        env = self._env_values_for(greenhouse_id)
        status = self._status_for(env["humidity"])
        self._record_sample(greenhouse_id, env["humidity"], env["temperature"], now)

        reason = None
        recommended_action = None
        if status in ("warning", "critical"):
            threshold = (
                self.HUMIDITY_CRITICAL_THRESHOLD
                if status == "critical"
                else self.HUMIDITY_WARNING_THRESHOLD
            )
            reason = f"습도 {env['humidity']}%, 임계값 {threshold}% 초과"
            recommended_action = {"device": "window", "action": "open", "label": "창문 열기"}

        return {
            "id": greenhouse_id,
            "status": status,
            "reason": reason,
            "recommended_action": recommended_action,
            "current_values": env,
            "history": list(self._history[greenhouse_id]),
        }

    def _record_sample(
        self, greenhouse_id: int, humidity: float, temperature: float, now: datetime
    ) -> None:
        last = self._last_sample_at.get(greenhouse_id)
        if last is not None and now - last < self.SAMPLE_MIN_INTERVAL:
            return
        self._last_sample_at[greenhouse_id] = now
        history = self._history[greenhouse_id]
        history.append({"timestamp": now.isoformat(), "humidity": humidity, "temperature": temperature})
        del history[: -self.HISTORY_MAX]
