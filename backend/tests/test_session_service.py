"""session_service 테스트.

세션별 최근 대화(사용자/응답 쌍)를 인메모리로 유지해 재질문 흐름에 컨텍스트를 제공한다.
"""

from app import session_service


def test_new_session_has_empty_history():
    session_service.reset()

    assert session_service.get_history("s1") == []


def test_append_turn_adds_user_and_assistant_messages():
    session_service.reset()

    session_service.append_turn("s1", "차광막 닫아줘", "차광막을 닫았어요.")

    assert session_service.get_history("s1") == [
        {"role": "user", "content": "차광막 닫아줘"},
        {"role": "assistant", "content": "차광막을 닫았어요."},
    ]


def test_sessions_are_isolated():
    session_service.reset()
    session_service.append_turn("s1", "안녕", "안녕하세요.")

    assert session_service.get_history("s2") == []
