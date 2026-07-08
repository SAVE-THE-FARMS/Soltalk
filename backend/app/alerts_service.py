"""알림(인앱 시뮬레이션) 엔진.

Docs/smartfarm_api_spec.md 1.3 (/api/alerts*) 대응.
greenhouse_service 의 warning/critical 판정을 재사용해 알림을 만든다.
"""

from datetime import datetime

from . import greenhouse_service
from .data.greenhouse_data import GREENHOUSES
from .iot.mock import MockIoTAdapter

_ALERT_MESSAGES = {
    "warning": "습도 {humidity}%, 곰팡이병 위험",
    "critical": "습도 {humidity}%, 곰팡이병 위험 (긴급)",
}

_DEVICE_OBJECT = {"shade": "차광막을", "window": "창문을", "irrigation": "관수를"}
_ACTION_VERB = {"open": "열었습니다", "close": "닫았습니다", "on": "켰습니다", "off": "껐습니다"}

_dismissed: set[str] = set()


def reset() -> None:
    _dismissed.clear()


def _alert_id(greenhouse_id: int) -> str:
    return f"gh{greenhouse_id}-humidity"


def list_alerts(iot_by_id: dict[int, MockIoTAdapter], now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    alerts = []
    for greenhouse_id in GREENHOUSES:
        alert_id = _alert_id(greenhouse_id)
        if alert_id in _dismissed:
            continue

        detail = greenhouse_service.get_detail(iot_by_id, greenhouse_id, now=now)
        if detail["status"] not in ("warning", "critical"):
            continue

        alerts.append(
            {
                "id": alert_id,
                "level": detail["status"],
                "greenhouse_id": greenhouse_id,
                "message": _ALERT_MESSAGES[detail["status"]].format(humidity=detail["current_values"]["humidity"]),
                "created_at": now.isoformat(),
                "escalated": False,
                "action": detail["recommended_action"],
            }
        )

    return sorted(alerts, key=lambda a: 0 if a["level"] == "critical" else 1)


def dismiss(alert_id: str, iot_by_id: dict[int, MockIoTAdapter]) -> bool:
    active_ids = {a["id"] for a in list_alerts(iot_by_id)}
    if alert_id not in active_ids:
        return False

    _dismissed.add(alert_id)
    return True


def execute_action(alert_id: str, iot_by_id: dict[int, MockIoTAdapter]) -> dict | None:
    active_ids = {a["id"]: a for a in list_alerts(iot_by_id)}
    alert = active_ids.get(alert_id)
    if alert is None:
        return None

    greenhouse_id = alert["greenhouse_id"]
    action = alert["action"]
    result = iot_by_id[greenhouse_id].control(action["device"], action["action"])
    if result["ok"]:
        _dismissed.add(alert_id)

    message = f"{greenhouse_id}번 온실 {_DEVICE_OBJECT[action['device']]} {_ACTION_VERB[action['action']]}."
    return {
        "success": result["ok"],
        "message": message,
        "updated_state": dict(iot_by_id[greenhouse_id].state),
    }
