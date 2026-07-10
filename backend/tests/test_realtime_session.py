"""RealtimeSessionService 테스트.

실제 OpenAI 호출은 하지 않고, client.realtime.client_secrets.create() 응답 모양만
흉내 낸 fake client 를 주입해서 검증한다.

핵심 계약: 음성 세션의 지침/도구 설정은 **백엔드가 임시 키 발급 시점에 세션에
바인딩**한다. (프론트가 연결 후 session.update 로 보내는 방식은 payload 형식이
API 계약과 어긋나면 조용히 거부되어 "도구 없는 일반 챗봇"이 되는 사고가
실측으로 확인됨 — 서버에 두면 그 실패 지점 자체가 없다.)
"""

from types import SimpleNamespace

from app.services.realtime_session import RealtimeSessionService

GREENHOUSE_NAMES = {1: "1번 온실(토마토)", 2: "2번 온실(딸기)", 3: "3번 온실(오이)"}


def _fake_client(value="ek_abc123", expires_at=1234567890):
    captured = {}

    def _create(**kwargs):
        captured["kwargs"] = kwargs
        return SimpleNamespace(value=value, expires_at=expires_at)

    client = SimpleNamespace(
        realtime=SimpleNamespace(client_secrets=SimpleNamespace(create=_create))
    )
    return client, captured


def _service(client):
    return RealtimeSessionService(greenhouse_names=GREENHOUSE_NAMES, client=client)


def test_create_session_returns_client_secret_and_expiry():
    client, _ = _fake_client(value="ek_abc123", expires_at=1234567890)

    result = _service(client).create_session()

    assert result == {"client_secret": "ek_abc123", "expires_at": 1234567890}


def test_create_session_never_leaks_raw_client_secrets_object():
    """응답에 client_secret 문자열만 담고, OpenAI 응답 객체 자체를 그대로 흘리지 않는다."""
    client, _ = _fake_client()

    result = _service(client).create_session()

    assert isinstance(result["client_secret"], str)


def test_create_session_requests_realtime_type_session():
    client, captured = _fake_client()

    _service(client).create_session()

    assert captured["kwargs"]["session"]["type"] == "realtime"


def test_create_session_binds_farm_tools_to_session():
    """도구가 키 발급 시점에 세션에 붙어야 음성 모델이 장비 제어/조회를 할 수 있다."""
    client, captured = _fake_client()

    _service(client).create_session()

    session = captured["kwargs"]["session"]
    tool_names = {t["name"] for t in session["tools"]}
    assert tool_names == {"control_device", "query_data"}  # ToolExecutor 가 아는 이름들
    assert session["tool_choice"] == "auto"
    # Realtime 도구는 flat 형식 ({type, name, ...} — Chat Completions 처럼 function 으로 감싸지 않음)
    assert all(t["type"] == "function" for t in session["tools"])


def test_create_session_instructions_include_farm_layout_and_korean():
    """지침에 농장 구성(온실 이름)이 들어가야 '딸기 온실'을 번호로 매핑할 수 있다."""
    client, captured = _fake_client()

    _service(client).create_session()

    instructions = captured["kwargs"]["session"]["instructions"]
    assert "1번 온실(토마토)" in instructions
    assert "2번 온실(딸기)" in instructions
    assert "한국어" in instructions


def test_create_session_instructions_include_smart_judgment_rules():
    """'단순 실행이 아니라 판단하는 AI' — 작물 생리 근거 제안/만류, 모호하면 재질문,
    범위 밖은 정직하게. 텍스트 챗봇과 같은 판단 기준을 음성에도 싣는다."""
    client, captured = _fake_client()

    _service(client).create_session()

    instructions = captured["kwargs"]["session"]["instructions"]
    assert "일소" in instructions  # 작물 생리 관점 판단
    assert "대안" in instructions  # 더 나은 방법 제안
    assert "되물" in instructions or "재질문" in instructions or "확인" in instructions
    assert "정직" in instructions or "솔직" in instructions  # 범위 밖 안내


def test_create_session_embeds_live_farm_status_and_time():
    """연결 시점 온실 상태(경고 수치 포함)와 현재 시각이 지침에 들어가야
    '정오인데 차광막 열어줘' 같은 상황 판단이 가능하다."""
    client, captured = _fake_client()

    def status_provider():
        return [
            {"id": 2, "name": "2번 온실(딸기)", "status": "warning", "temperature": 24.0, "humidity": 82}
        ]

    service = RealtimeSessionService(
        greenhouse_names=GREENHOUSE_NAMES, status_provider=status_provider, client=client
    )
    service.create_session()

    instructions = captured["kwargs"]["session"]["instructions"]
    assert "경고" in instructions
    assert "82" in instructions
    assert "현재 시각" in instructions
    assert "query_data" in instructions  # 통화 중 최신 값 재조회 안내


def test_create_session_survives_status_provider_failure():
    """상태 조회가 죽어도 키 발급(=음성 연결)은 돼야 한다 — 모델이 도구로 조회하면 됨."""
    client, captured = _fake_client()

    def boom():
        raise RuntimeError("dashboard down")

    service = RealtimeSessionService(
        greenhouse_names=GREENHOUSE_NAMES, status_provider=boom, client=client
    )

    result = service.create_session()

    assert result["client_secret"] == "ek_abc123"
    assert "1번 온실(토마토)" in captured["kwargs"]["session"]["instructions"]


def test_create_session_enables_korean_input_transcription():
    """입력 음성 자막(사용자 발화가 채팅 이력에 남는 것)은 세션 설정에 켜야만 온다."""
    client, captured = _fake_client()

    _service(client).create_session()

    transcription = captured["kwargs"]["session"]["audio"]["input"]["transcription"]
    assert transcription["language"] == "ko"
    assert transcription["model"]


def test_tools_schema_restricts_greenhouse_ids_to_known_farm():
    client, captured = _fake_client()

    _service(client).create_session()

    control = next(
        t for t in captured["kwargs"]["session"]["tools"] if t["name"] == "control_device"
    )
    assert control["parameters"]["properties"]["greenhouse_id"]["enum"] == [1, 2, 3]
    assert set(control["parameters"]["required"]) == {"device", "action", "greenhouse_id"}
