"""알림(인앱 시뮬레이션) 엔진.

smartfarm_api_spec.md 1.3 (/api/alerts*) 대응.
GreenhouseService 의 warning/critical 판정을 재사용해 알림을 만든다.
장비 제어는 GreenhouseService 가 들고 있는 온실별 어댑터를 통해 수행한다.

자동 제어 모드: set_auto_mode(gid, True) 로 켜두면, list_alerts() 가 호출될
때마다(대시보드 폴링 주기) 경고/위험인 온실의 recommended_action 을 사람 개입
없이 대신 실행한다 — 스마트팜의 "센서→자동 구동" 원리를 데모 규모로 재현.

경고 방치 격상: 같은 온실이 warning 으로 ESCALATION_AFTER 이상 계속되면
(자동 모드도 없고 사람도 조치하지 않았다는 뜻) level 을 critical 로 격상한다.
"""

from datetime import datetime, timedelta

from .greenhouse import GreenhouseService

ESCALATION_AFTER = timedelta(seconds=20)


class AlertService:
    _ALERT_MESSAGES = {
        "warning": "습도 {humidity}%, 곰팡이병 위험",
        "critical": "습도 {humidity}%, 곰팡이병 위험 (긴급)",
    }
    _ESCALATED_MESSAGE = "습도 {humidity}%, 곰팡이병 위험 — 방치되어 위험으로 격상됨"
    _DEVICE_OBJECT = {"shade": "차광막을", "window": "창문을", "irrigation": "관수를"}
    _ACTION_VERB = {"open": "열었습니다", "close": "닫았습니다", "on": "켰습니다", "off": "껐습니다"}

    def __init__(self, greenhouse_service: GreenhouseService):
        self._gh = greenhouse_service
        self._dismissed: set[str] = set()
        self._auto_mode: dict[int, bool] = {gid: False for gid in greenhouse_service.greenhouse_ids}
        self._warning_since: dict[int, datetime] = {}

    def reset(self) -> None:
        self._dismissed.clear()
        self._auto_mode = {gid: False for gid in self._gh.greenhouse_ids}
        self._warning_since.clear()

    def set_auto_mode(self, greenhouse_id: int, enabled: bool) -> bool:
        if greenhouse_id not in self._auto_mode:
            return False
        self._auto_mode[greenhouse_id] = enabled
        return True

    def is_auto_mode(self, greenhouse_id: int) -> bool:
        return self._auto_mode.get(greenhouse_id, False)

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
                self._warning_since.pop(greenhouse_id, None)
                continue

            action = detail["recommended_action"]
            auto = self._auto_mode.get(greenhouse_id, False)
            if auto and action:
                self._gh.adapter(greenhouse_id).control(action["device"], action["action"])

            level, escalated = self._effective_level(greenhouse_id, detail["status"], now)
            humidity = detail["current_values"]["humidity"]
            message_template = self._ESCALATED_MESSAGE if escalated else self._ALERT_MESSAGES[level]
            alerts.append(
                {
                    "id": alert_id,
                    "level": level,
                    "greenhouse_id": greenhouse_id,
                    "message": message_template.format(humidity=humidity),
                    "created_at": now.isoformat(),
                    "escalated": escalated,
                    "action": action,
                    "auto": auto,
                }
            )

        return sorted(alerts, key=lambda a: 0 if a["level"] == "critical" else 1)

    def _effective_level(self, greenhouse_id: int, status: str, now: datetime) -> tuple[str, bool]:
        """경고가 ESCALATION_AFTER 이상 방치되면 심각도를 위험으로 격상한다."""
        if status == "critical":
            self._warning_since.pop(greenhouse_id, None)
            return "critical", False

        started_at = self._warning_since.setdefault(greenhouse_id, now)
        if now - started_at >= ESCALATION_AFTER:
            return "critical", True
        return "warning", False

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
