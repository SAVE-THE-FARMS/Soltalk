"""서비스 계층 — 각 관심사를 클래스로 캡슐화하고 의존성은 생성자로 주입받는다.

- SessionStore          : 세션별 대화 히스토리
- ChatAgent             : LLM(OpenAI function calling) 에이전트
- GreenhouseService     : 온실 대시보드 상태 계산
- AlertService          : 알림 엔진
- ToolExecutor          : control_device/read_data 실행 로직 (ChatAgent·실시간 음성 공용)
- RealtimeSessionService: OpenAI Realtime API 임시 키 발급

조립(어떤 인스턴스를 어떻게 엮을지)은 app/container.py 의 AppContainer 가 담당한다.
"""

from .alerts import AlertService
from .chat_agent import ChatAgent
from .greenhouse import GreenhouseService
from .realtime_session import RealtimeSessionService
from .session import SessionStore
from .tool_executor import ToolExecutor
from .transcription import TranscriptionService

__all__ = [
    "AlertService",
    "ChatAgent",
    "GreenhouseService",
    "RealtimeSessionService",
    "SessionStore",
    "ToolExecutor",
    "TranscriptionService",
]
