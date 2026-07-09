"""조립 루트(composition root).

Mock IoT 어댑터와 서비스들을 한 곳에서 생성하고 서로 주입해 엮는다.
전역 상태 대신 이 컨테이너 인스턴스 하나가 앱의 상태를 소유한다.
server.py 가 이걸 만들어 각 엔드포인트에서 사용한다.
"""

from .data.greenhouse_data import GREENHOUSES
from .data.mock_data import MOCK_DATA
from .iot.base import IoTAdapter
from .iot.virtual import VirtualFarmAdapter
from .services import (
    AlertService,
    ChatAgent,
    GreenhouseService,
    SessionStore,
    TranscriptionService,
)


def _initial_environment_for(record: dict) -> dict:
    """온실 레코드의 정적 환경값을 시뮬레이션 초기값으로. 없으면(온실1) 센서 더미 데이터."""
    if "temperature" in record and "humidity" in record:
        return {"temperature": record["temperature"], "humidity": record["humidity"]}
    return {
        "temperature": MOCK_DATA["temperature"]["value"],
        "humidity": MOCK_DATA["humidity"]["value"],
    }


class AppContainer:
    def __init__(self):
        # 온실마다 자체 가상 시뮬레이션 어댑터 (virtualfarm/ADAPTER_CONTRACT.md 4절)
        # — 창문을 열면 시간이 지나며 습도가 실제로 내려간다 (lazy-tick)
        self.iot_by_greenhouse: dict[int, IoTAdapter] = {
            greenhouse_id: VirtualFarmAdapter(
                initial_environment=_initial_environment_for(record),
                initial_devices=record.get("initial_devices"),
                sensor_data=MOCK_DATA,  # production 등 시뮬레이션 밖 target 의 fallback
            )
            for greenhouse_id, record in GREENHOUSES.items()
        }
        self.greenhouse_service = GreenhouseService(self.iot_by_greenhouse, GREENHOUSES, MOCK_DATA)
        self.alert_service = AlertService(self.greenhouse_service)
        self.sessions = SessionStore()
        self.chat_agent = ChatAgent(iot=self.iot_by_greenhouse[ChatAgent.CHAT_GREENHOUSE_ID])
        self.transcription = TranscriptionService()

    @property
    def chat_iot(self) -> IoTAdapter:
        """챗봇이 제어하는 온실(1번)의 어댑터."""
        return self.iot_by_greenhouse[ChatAgent.CHAT_GREENHOUSE_ID]

    def reset_all(self) -> None:
        """리허설/재시연용 전체 초기화."""
        for adapter in self.iot_by_greenhouse.values():
            adapter.reset()
        self.greenhouse_service.reset()
        self.sessions.reset()
        self.alert_service.reset()
