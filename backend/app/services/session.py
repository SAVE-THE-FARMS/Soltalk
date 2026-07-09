"""세션별 대화 히스토리 (인메모리).

세션당 최근 max_turns 턴(사용자+응답 쌍)만 유지해 재질문 흐름에 컨텍스트를 준다.
데모용이라 메모리에만 둔다.
"""


class SessionStore:
    def __init__(self, max_turns: int = 3):
        self._max_turns = max_turns
        self._sessions: dict[str, list[dict]] = {}

    def reset(self) -> None:
        self._sessions.clear()

    def get_history(self, session_id: str) -> list[dict]:
        return list(self._sessions.get(session_id, []))

    def append_turn(self, session_id: str, user_message: str, reply: str) -> None:
        history = self._sessions.setdefault(session_id, [])
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply})
        if self._max_turns > 0:
            # 최근 max_turns 턴(= 메시지 max_turns*2 개)만 남긴다.
            del history[: -(self._max_turns * 2)]
