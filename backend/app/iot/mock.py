"""
MockIoTAdapter (뼈대).

실장비 없이 '가상 상태'를 메모리에 저장/변경한다.
학생들은 이 파일만 채우면 제어/조회가 동작하게 된다. (실장비는 몰라도 됨)
"""

from .base import IoTAdapter

# action(동작) -> state(결과 상태) 정규화. "close" 동작의 결과 상태는 "closed".
_ACTION_TO_STATE = {"open": "open", "close": "closed", "on": "on", "off": "off"}

# device 별로 허용되는 action.
_ALLOWED_ACTIONS = {
    "shade": {"open", "close"},
    "window": {"open", "close"},
    "irrigation": {"on", "off"},
}


class MockIoTAdapter(IoTAdapter):
    def __init__(self):
        # 가상 장비 상태 (시작값)
        self.state = {
            "shade": "open",        # 차광막
            "window": "closed",     # 창문
            "irrigation": "off",    # 관수
        }

    def control(self, device: str, action: str) -> dict:
        if device not in self.state:
            return {"ok": False, "device": device, "state": None, "reason": "unknown_device"}

        new_state = _ACTION_TO_STATE.get(action, action)
        self.state[device] = new_state
        return {"ok": True, "device": device, "state": new_state}

    def read(self, target: str) -> dict:
        # TODO(학생): app/data/mock_data.py 의 더미 데이터에서 target 을 찾아 반환.
        raise NotImplementedError
