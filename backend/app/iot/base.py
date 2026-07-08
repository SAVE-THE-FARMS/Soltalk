"""
IoTAdapter 인터페이스 (뼈대).

핵심 원칙: IoT 연동을 인터페이스로 추상화해서 Mock ↔ 실장비를 갈아끼운다.
- 공개 repo에는 이 인터페이스 + MockIoTAdapter 만 둔다.
- 실장비 구현(RealIoTAdapter)은 나중에 회사가 같은 인터페이스로 비공개 repo에서 주입.

장비(device): "shade"(차광막), "window"(창문), "irrigation"(관수)
동작(action): "open" / "close" 등
"""

from abc import ABC, abstractmethod


class IoTAdapter(ABC):
    """모든 IoT 어댑터가 지켜야 하는 계약(interface)."""

    @abstractmethod
    def control(self, device: str, action: str) -> dict:
        """
        장비를 제어한다.  (예: control("shade", "close"))
        반환: 처리 결과 상태 (오작동 확인 피드백용).
        TODO(학생): 반환 형태를 팀에서 정해서 문서화.
        """
        ...

    @abstractmethod
    def read(self, target: str) -> dict:
        """
        센서/생산 데이터를 조회한다.  (예: read("temperature"))
        반환: 조회 결과.
        """
        ...
