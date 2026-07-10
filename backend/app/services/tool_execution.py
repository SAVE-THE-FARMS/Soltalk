"""ChatAgent(텍스트 챗)와 Realtime tool 브릿지(/api/tools/execute)가 공유하는
control_device / read_data 실행 로직. 이 함수 하나만 바꾸면 두 경로 모두에 반영된다.

Realtime(음성) 프론트는 조회 도구를 "query_data"라는 이름으로 호출한다(텍스트 챗의
OpenAI tool 스키마는 "read_data"). 두 이름 모두 같은 조회 로직을 타도록 받아준다.
"""

from typing import Callable

from ..iot.base import IoTAdapter

ALERT_CLEARED_NOTE = (
    "이 온실은 방금까지 경고/위험 상태였습니다. 이 조치로 습도가 내려가면 "
    "대시보드의 알림과 조치 버튼이 자동으로 사라집니다(=해결됐다는 뜻). "
    "답변에 이 사실을 한 문장으로 짧게 안내하세요."
)


def execute_tool(
    name: str,
    args: dict,
    greenhouse_id: int | None,
    iot_by_greenhouse: dict[int, IoTAdapter],
    is_alerting: Callable[[int], bool],
) -> dict:
    """control_device / read_data 를 실제로 실행하고 결과 dict를 돌려준다.

    greenhouse_id 가 None 이면(control_device 미지정) 실행하지 않는다 — 호출자가
    되묻거나 안내해야 한다는 뜻으로 {"ok": False, "reason": "missing_greenhouse_id"} 를 돌려준다.
    """
    if greenhouse_id is None:
        return {"ok": False, "reason": "missing_greenhouse_id"}
    iot = iot_by_greenhouse.get(greenhouse_id)
    if iot is None:
        return {"ok": False, "reason": "unknown_greenhouse", "greenhouse_id": greenhouse_id}
    if name == "control_device":
        was_alerting = is_alerting(greenhouse_id)
        result = {**iot.control(args["device"], args["action"]), "greenhouse_id": greenhouse_id}
        if result.get("ok") and was_alerting:
            result["note"] = ALERT_CLEARED_NOTE
        return result
    if name in ("read_data", "query_data"):
        return {**iot.read(args["target"]), "greenhouse_id": greenhouse_id}
    return {"ok": False, "reason": "unknown_tool"}
