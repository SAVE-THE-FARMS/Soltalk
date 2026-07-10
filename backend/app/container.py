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
    RealtimeSessionService,
    SessionStore,
    ToolExecutor,
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
        # 도구 실행기는 앱 전체에 딱 하나 — 텍스트 챗봇(ChatAgent)과 실시간 음성 모드
        # (/api/tools/execute)가 같은 인스턴스를 공유한다. "state"/"alerts" target 조회용
        # 서비스까지 여기서 전부 주입해두면 어느 경로로 호출해도 능력이 같다.
        self.tool_executor = ToolExecutor(
            self.iot_by_greenhouse,
            self.greenhouse_service.get_dashboard,
            greenhouse_service=self.greenhouse_service,
            alert_service=self.alert_service,
        )
        self.chat_agent = ChatAgent(
            iot_by_greenhouse=self.iot_by_greenhouse,
            greenhouse_names={gid: record["name"] for gid, record in GREENHOUSES.items()},
            status_provider=self.greenhouse_service.get_dashboard,
            tool_executor=self.tool_executor,
        )
        self.transcription = TranscriptionService()
        self.realtime_session = RealtimeSessionService(
            greenhouse_names={gid: record["name"] for gid, record in GREENHOUSES.items()},
            status_provider=self.greenhouse_service.get_dashboard,
        )

    @property
    def chat_iot(self) -> IoTAdapter:
        """온실 지정 없는 챗 명령의 기본 대상(1번) 어댑터."""
        return self.iot_by_greenhouse[ChatAgent.DEFAULT_GREENHOUSE_ID]

    def reset_all(self) -> None:
        """리허설/재시연용 전체 초기화."""
        for adapter in self.iot_by_greenhouse.values():
            adapter.reset()
        self.greenhouse_service.reset()
        self.sessions.reset()
        self.alert_service.reset()
