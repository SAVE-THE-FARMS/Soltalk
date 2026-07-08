"""세션별 대화 히스토리 (인메모리).

Docs/smartfarm_api_spec.md 1.1 비고: "세션별 최근 대화 히스토리 유지 (재질문 흐름 대응)".
데모용이라 메모리에만 두고, 세션당 최근 MAX_TURNS 턴(사용자+응답 쌍)만 유지한다.
"""

MAX_TURNS = 3  # 최근 3턴(= 메시지 6개)까지만 컨텍스트로 유지

_sessions: dict[str, list[dict]] = {}


def reset() -> None:
    _sessions.clear()


def get_history(session_id: str) -> list[dict]:
    return list(_sessions.get(session_id, []))


def append_turn(session_id: str, user_message: str, reply: str) -> None:
    history = _sessions.setdefault(session_id, [])
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": reply})
    del history[: -(MAX_TURNS * 2)]
