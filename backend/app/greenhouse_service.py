"""온실 대시보드 상태 계산.

Docs/smartfarm_api_spec.md 1.2 (/api/state, /api/state/{id}) 대응.
온실 1번의 환경값(temperature/humidity)은 mock_data.py 를 실시간으로 쓰고,
2/3번은 데모용 정적 값(greenhouse_data.py)을 쓴다. 장비 상태는 온실 전부
자기 MockIoTAdapter(state.IOT_BY_GREENHOUSE)에서 읽는다 (알림 원터치 실행이
control() 의 검증 로직을 그대로 타게 하기 위함).

status 판정 (습도 기준):
  humidity >= 90 -> "critical"
  humidity >= 80 -> "warning"
  else            -> "normal"
"""

from datetime import datetime

from .data.greenhouse_data import GREENHOUSES
from .data.mock_data import MOCK_DATA
from .iot.mock import MockIoTAdapter

HUMIDITY_WARNING_THRESHOLD = 80
HUMIDITY_CRITICAL_THRESHOLD = 90


def _status_for(humidity: float) -> str:
    if humidity >= HUMIDITY_CRITICAL_THRESHOLD:
        return "critical"
    if humidity >= HUMIDITY_WARNING_THRESHOLD:
        return "warning"
    return "normal"


def _env_values_for(greenhouse_id: int) -> dict:
    if greenhouse_id == 1:
        return {
            "temperature": MOCK_DATA["temperature"]["value"],
            "humidity": MOCK_DATA["humidity"]["value"],
        }
    record = GREENHOUSES[greenhouse_id]
    return {"temperature": record["temperature"], "humidity": record["humidity"]}


def get_dashboard(iot_by_id: dict[int, MockIoTAdapter], now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    states = []
    for greenhouse_id, record in GREENHOUSES.items():
        env = _env_values_for(greenhouse_id)
        states.append(
            {
                "id": greenhouse_id,
                "name": record["name"],
                "status": _status_for(env["humidity"]),
                "temperature": env["temperature"],
                "humidity": env["humidity"],
                "devices": dict(iot_by_id[greenhouse_id].state),
                "last_updated": now.isoformat(),
            }
        )
    return states


def get_detail(
    iot_by_id: dict[int, MockIoTAdapter], greenhouse_id: int, now: datetime | None = None
) -> dict | None:
    if greenhouse_id not in GREENHOUSES:
        return None

    record = GREENHOUSES[greenhouse_id]
    env = _env_values_for(greenhouse_id)
    status = _status_for(env["humidity"])

    reason = None
    recommended_action = None
    if status in ("warning", "critical"):
        threshold = HUMIDITY_CRITICAL_THRESHOLD if status == "critical" else HUMIDITY_WARNING_THRESHOLD
        reason = f"습도 {env['humidity']}%, 임계값 {threshold}% 초과"
        recommended_action = {"device": "window", "action": "open", "label": "창문 열기"}

    return {
        "id": greenhouse_id,
        "status": status,
        "reason": reason,
        "recommended_action": recommended_action,
        "current_values": env,
        "history": record["history"],
    }
