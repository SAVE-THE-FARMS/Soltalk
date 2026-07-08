"""알림(인앱 시뮬레이션) 엔진.

smartfarm_api_spec.md 1.3 (/api/alerts*) 대응.
GreenhouseService 의 warning/critical 판정을 재사용해 알림을 만든다.
장비 제어는 GreenhouseService 가 들고 있는 온실별 어댑터를 통해 수행한다.
"""

from datetime import datetime

from .greenhouse import GreenhouseService


class AlertService:
    _ALERT_MESSAGES = {
        "warning": "습도 {humidity}%, 곰팡이병 위험",
        "critical": "습도 {humidity}%, 곰팡이병 위험 (긴급)",
    }
    _DEVICE_OBJECT = {"shade": "차광막을", "window": "창문을", "irrigation": "관수를"}
    _ACTION_VERB = {"open": "열었습니다", "close": "닫았습니다", "on": "켰습니다", "off": "껐습니다"}

    def __init__(self, greenhouse_service: GreenhouseService):
        self._gh = greenhouse_service
        self._dismissed: set[str] = set()

    def reset(self) -> None:
        self._dismissed.clear()

    @staticmethod
    def _alert_id(greenhouse_id: int) -> str:
        return f"gh{greenhouse_id}-humidity"

    def list_alerts(self, now: datetime | None = None) -> list[dict]:
        now = now or datetime.now()
        alerts = []
        for greenhouse_id in self._gh.greenhouse_ids:
            alert_id = self._alert_id(greenhouse_id)
            if alert_id in self._dismissed:
                continue

            detail = self._gh.get_detail(greenhouse_id, now=now)
            if detail["status"] not in ("warning", "critical"):
                continue

            humidity = detail["current_values"]["humidity"]
            alerts.append(
                {
                    "id": alert_id,
                    "level": detail["status"],
                    "greenhouse_id": greenhouse_id,
                    "message": self._ALERT_MESSAGES[detail["status"]].format(humidity=humidity),
                    "created_at": now.isoformat(),
                    "escalated": False,
                    "action": detail["recommended_action"],
                }
            )

        return sorted(alerts, key=lambda a: 0 if a["level"] == "critical" else 1)

    def dismiss(self, alert_id: str) -> bool:
        active_ids = {a["id"] for a in self.list_alerts()}
        if alert_id not in active_ids:
            return False
        self._dismissed.add(alert_id)
        return True

    def execute_action(self, alert_id: str) -> dict | None:
        active = {a["id"]: a for a in self.list_alerts()}
        alert = active.get(alert_id)
        if alert is None:
            return None

        greenhouse_id = alert["greenhouse_id"]
        action = alert["action"]
        adapter = self._gh.adapter(greenhouse_id)
        result = adapter.control(action["device"], action["action"])
        if result["ok"]:
            self._dismissed.add(alert_id)

        message = (
            f"{greenhouse_id}번 온실 "
            f"{self._DEVICE_OBJECT[action['device']]} {self._ACTION_VERB[action['action']]}."
        )
        return {
            "success": result["ok"],
            "message": message,
            "updated_state": dict(adapter.state),
        }
