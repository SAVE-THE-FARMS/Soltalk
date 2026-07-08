"""조립 루트(composition root).

Mock IoT 어댑터와 서비스들을 한 곳에서 생성하고 서로 주입해 엮는다.
전역 상태 대신 이 컨테이너 인스턴스 하나가 앱의 상태를 소유한다.
server.py 가 이걸 만들어 각 엔드포인트에서 사용한다.
"""

from .data.greenhouse_data import GREENHOUSES
from .data.mock_data import MOCK_DATA
from .iot.mock import MockIoTAdapter
from .services import (
    AlertService,
    ChatAgent,
    GreenhouseService,
    SessionStore,
    TranscriptionService,
)


class AppContainer:
    def __init__(self):
        # 온실마다 자체 어댑터 (대시보드/알림 원터치 실행도 control() 검증 로직을 그대로 타게)
        self.iot_by_greenhouse: dict[int, MockIoTAdapter] = {
            greenhouse_id: MockIoTAdapter(initial_state=record.get("initial_devices"))
            for greenhouse_id, record in GREENHOUSES.items()
        }
        self.greenhouse_service = GreenhouseService(self.iot_by_greenhouse, GREENHOUSES, MOCK_DATA)
        self.alert_service = AlertService(self.greenhouse_service)
        self.sessions = SessionStore()
        self.chat_agent = ChatAgent(iot=self.iot_by_greenhouse[ChatAgent.CHAT_GREENHOUSE_ID])
        self.transcription = TranscriptionService()

    @property
    def chat_iot(self) -> MockIoTAdapter:
        """챗봇이 제어하는 온실(1번)의 어댑터."""
        return self.iot_by_greenhouse[ChatAgent.CHAT_GREENHOUSE_ID]

    def reset_all(self) -> None:
        """리허설/재시연용 전체 초기화."""
        for adapter in self.iot_by_greenhouse.values():
            adapter.reset()
        self.sessions.reset()
        self.alert_service.reset()
