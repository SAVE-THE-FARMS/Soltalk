"""control_device / read_data(query_data) 실행 로직.

텍스트 챗봇(ChatAgent, OpenAI Chat Completions 함수 스키마)과 실시간 음성 모드
(POST /api/tools/execute, OpenAI Realtime 함수 스키마)는 도구 이름·파라미터 형식이
서로 다르게 노출되지만(voice_feature_backend.md 3절 "스키마 이중 관리"), 실제로
온실 장비를 조작/조회하는 로직은 여기 하나만 두고 양쪽이 재사용한다 — 운영에서는
container 가 만든 인스턴스 하나를 두 경로가 공유한다.

greenhouse_service/alert_service 는 "state"/"alerts" 조회에 쓰인다 — 주입하지 않은
최소 구성(일부 테스트 등)에서는 해당 target이 unknown_target으로 처리된다.
센서/생산 등 그 외 target 의 유효성 판정은 IoT 어댑터에 위임한다(어댑터가 단일
진실 공급원 — 여기 목록을 두면 어댑터에 target 을 추가할 때 조용히 어긋난다).
"""

from typing import Callable

from ..iot.base import IoTAdapter


class ToolExecutor:
    DEFAULT_GREENHOUSE_ID = 1  # 조회(read_data/query_data)는 위험이 낮아 미지정 시 기본 온실 적용

    def __init__(
        self,
        iot_by_greenhouse: dict[int, IoTAdapter],
        status_provider: Callable[[], list[dict]],
        greenhouse_service=None,
        alert_service=None,
    ):
        self._iot_by_greenhouse = iot_by_greenhouse
        self._status_provider = status_provider
        self._greenhouse_service = greenhouse_service
        self._alert_service = alert_service

    def execute(self, tool_name: str, args: dict) -> dict:
        if tool_name == "control_device":
            return self.control_device(args)
        if tool_name in ("read_data", "query_data"):
            return self.read_data(args)
        return {"ok": False, "reason": "unknown_tool"}

    def control_device(self, args: dict) -> dict:
        """장비 조작 — 온실 미지정/미존재 시 실행하지 않는다(모델이 되물어야 함)."""
        device, action = args.get("device"), args.get("action")
        if device is None or action is None:
            # LLM 스키마(required)가 보장해주는 경로와 달리 /api/tools/execute 는 외부에서
            # 임의 JSON이 그대로 들어온다 — KeyError 500 대신 구조화된 실패로 응답한다.
            return {"ok": False, "reason": "invalid_arguments"}
        greenhouse_id = args.get("greenhouse_id")
        if greenhouse_id is None:
            return {"ok": False, "reason": "missing_greenhouse_id"}
        iot = self._iot_by_greenhouse.get(greenhouse_id)
        if iot is None:
            return {"ok": False, "reason": "unknown_greenhouse", "greenhouse_id": greenhouse_id}

        was_alerting = self._is_alerting(greenhouse_id)
        result = {**iot.control(device, action), "greenhouse_id": greenhouse_id}
        if result.get("ok") and was_alerting:
            # 경고/위험 중이던 온실을 조치하면 습도가 내려가는 대로 대시보드의 알림/조치버튼이
            # 조용히 사라진다 — 사용자가 왜 사라졌는지 모를 수 있어 답변에서 미리 설명하도록 안내.
            result["note"] = (
                "이 온실은 방금까지 경고/위험 상태였습니다. 이 조치로 습도가 내려가면 "
                "대시보드의 알림과 조치 버튼이 자동으로 사라집니다(=해결됐다는 뜻). "
                "답변에 이 사실을 한 문장으로 짧게 안내하세요."
            )
        return result

    def read_data(self, args: dict) -> dict:
        target = args.get("target")
        greenhouse_id = args.get("greenhouse_id")
        if target is None:
            return {"ok": False, "reason": "invalid_arguments"}

        # "state"/"alerts" 는 IoT 어댑터가 아니라 서비스 계층이 답하는 target —
        # 서비스가 주입되지 않은 실행기(ChatAgent 내부용)에서는 unknown_target 처리.
        if target == "alerts":
            if self._alert_service is None:
                return {"ok": False, "reason": "unknown_target", "target": target}
            if greenhouse_id is not None and greenhouse_id not in self._iot_by_greenhouse:
                return {"ok": False, "reason": "unknown_greenhouse", "greenhouse_id": greenhouse_id}
            alerts = self._alert_service.list_alerts()
            if greenhouse_id is not None:
                alerts = [a for a in alerts if a["greenhouse_id"] == greenhouse_id]
            return {"ok": True, "alerts": alerts}

        if greenhouse_id is None:
            greenhouse_id = self.DEFAULT_GREENHOUSE_ID

        if target == "state":
            if self._greenhouse_service is None:
                return {"ok": False, "reason": "unknown_target", "target": target}
            detail = self._greenhouse_service.get_detail(greenhouse_id)
            if detail is None:
                return {"ok": False, "reason": "unknown_greenhouse", "greenhouse_id": greenhouse_id}
            if self._alert_service is not None:
                # 대시보드 상세(/api/state/{id})와 같은 shape — 음성 조회도 auto 모드 여부를 알 수 있게
                detail["auto"] = self._alert_service.is_auto_mode(greenhouse_id)
            return {"ok": True, **detail}

        # 그 외 센서/생산 target 은 어댑터에 위임 — 어떤 target 이 유효한지는 어댑터가
        # 단일 진실 공급원이다(여기 목록을 두면 어댑터에 target 을 추가할 때 조용히 어긋난다).
        iot = self._iot_by_greenhouse.get(greenhouse_id)
        if iot is None:
            return {"ok": False, "reason": "unknown_greenhouse", "greenhouse_id": greenhouse_id}
        return {**iot.read(target), "greenhouse_id": greenhouse_id}

    def _is_alerting(self, greenhouse_id: int) -> bool:
        return any(
            s["id"] == greenhouse_id and s["status"] != "normal" for s in self._status_provider()
        )
