"""
MockIoTAdapter.

실장비 없이 '가상 상태'를 메모리에 저장/변경한다.

반환 스키마:
  control() 성공: {"ok": True, "device": str, "state": str}
  control() 실패: {"ok": False, "device": str, "state": str|None, "reason": "unknown_device"|"invalid_action"}
  read() 성공:    {"ok": True, "target": str, "value": ..., "unit": str}
  read() 실패:    {"ok": False, "target": str, "reason": "unknown_target"}
"""

from ..data.mock_data import MOCK_DATA
from .base import IoTAdapter

# action(동작) -> state(결과 상태) 정규화. "close" 동작의 결과 상태는 "closed".
_ACTION_TO_STATE = {"open": "open", "close": "closed", "on": "on", "off": "off"}

# device 별로 허용되는 action.
_ALLOWED_ACTIONS = {
    "shade": {"open", "close"},
    "window": {"open", "close"},
    "irrigation": {"on", "off"},
}


_DEFAULT_INITIAL_STATE = {
    "shade": "open",        # 차광막
    "window": "closed",     # 창문
    "irrigation": "off",    # 관수
}


class MockIoTAdapter(IoTAdapter):
    def __init__(self, initial_state: dict | None = None):
        self._initial_state = dict(initial_state or _DEFAULT_INITIAL_STATE)
        self.state = dict(self._initial_state)

    def reset(self) -> None:
        self.state = dict(self._initial_state)

    def control(self, device: str, action: str) -> dict:
        if device not in self.state:
            return {"ok": False, "device": device, "state": None, "reason": "unknown_device"}

        if action not in _ALLOWED_ACTIONS[device]:
            return {"ok": False, "device": device, "state": self.state[device], "reason": "invalid_action"}

        new_state = _ACTION_TO_STATE[action]
        self.state[device] = new_state
        return {"ok": True, "device": device, "state": new_state}

    def read(self, target: str) -> dict:
        if target not in MOCK_DATA:
            return {"ok": False, "target": target, "reason": "unknown_target"}

        entry = MOCK_DATA[target]
        return {"ok": True, "target": target, "value": entry["value"], "unit": entry["unit"]}
