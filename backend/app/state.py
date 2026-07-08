"""공유 상태 싱글턴.

agent.py / server.py / greenhouse_service.py / alerts_service.py 가 같은 MockIoTAdapter
인스턴스를 보게 여기서 한 번만 만든다.

온실마다 자체 MockIoTAdapter 를 두는 이유: 대시보드/알림의 "원터치 실행"이 어떤 온실이든
control() 의 검증 로직(존재하지 않는 device/action 방어)을 그대로 타게 하기 위함.
챗봇(agent.py)이 실제로 대화로 제어하는 건 1번 온실뿐 (CLAUDE.md 의 NLU 계약: {device, action}, 온실 구분 없음).
"""

from .data.greenhouse_data import GREENHOUSES
from .iot.mock import MockIoTAdapter

IOT_BY_GREENHOUSE: dict[int, MockIoTAdapter] = {
    greenhouse_id: MockIoTAdapter(initial_state=record.get("initial_devices"))
    for greenhouse_id, record in GREENHOUSES.items()
}

iot = IOT_BY_GREENHOUSE[1]  # 챗봇이 제어하는 온실


def reset_all() -> None:
    for adapter in IOT_BY_GREENHOUSE.values():
        adapter.reset()
