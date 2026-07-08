"""
MockIoTAdapter (뼈대).

실장비 없이 '가상 상태'를 메모리에 저장/변경한다.
학생들은 이 파일만 채우면 제어/조회가 동작하게 된다. (실장비는 몰라도 됨)
"""

from .base import IoTAdapter


class MockIoTAdapter(IoTAdapter):
    def __init__(self):
        # 가상 장비 상태 (시작값)
        self.state = {
            "shade": "open",        # 차광막
            "window": "closed",     # 창문
            "irrigation": "off",    # 관수
        }

    def control(self, device: str, action: str) -> dict:
        # TODO(학생): device 상태를 action 으로 바꾸고, 결과 상태를 반환.
        #   - 없는 device / 이상한 action 처리(확인 피드백)도 고민.
        raise NotImplementedError

    def read(self, target: str) -> dict:
        # TODO(학생): app/data/mock_data.py 의 더미 데이터에서 target 을 찾아 반환.
        raise NotImplementedError
