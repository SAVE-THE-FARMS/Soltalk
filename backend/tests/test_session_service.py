"""SessionStore 테스트.

세션별 최근 대화(사용자/응답 쌍)를 인메모리로 유지해 재질문 흐름에 컨텍스트를 제공한다.
"""

from app.services.session import SessionStore


def test_new_session_has_empty_history():
    store = SessionStore()

    assert store.get_history("s1") == []


def test_append_turn_adds_user_and_assistant_messages():
    store = SessionStore()

    store.append_turn("s1", "차광막 닫아줘", "차광막을 닫았어요.")

    assert store.get_history("s1") == [
        {"role": "user", "content": "차광막 닫아줘"},
        {"role": "assistant", "content": "차광막을 닫았어요."},
    ]


def test_sessions_are_isolated():
    store = SessionStore()
    store.append_turn("s1", "안녕", "안녕하세요.")

    assert store.get_history("s2") == []


def test_history_is_capped_to_max_turns():
    store = SessionStore(max_turns=2)

    for i in range(4):
        store.append_turn("s1", f"명령{i}", f"응답{i}")

    history = store.get_history("s1")
    assert len(history) == 4  # 최근 2턴(=메시지 4개)만
    assert history[0] == {"role": "user", "content": "명령2"}
