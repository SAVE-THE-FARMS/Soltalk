"""ChatAgent 테스트.

OpenAI 호출은 외부 네트워크 의존이라 실제 API를 부르지 않고,
OpenAI SDK 응답 모양(choices[0].message.tool_calls 등)만 흉내 낸 fake client 를 주입해서 검증한다.

handle() 반환 스키마: {"reply": str, "actions_taken": [{"device","greenhouse_id","action","success"}, ...]}
"""

from types import SimpleNamespace

from app.iot.mock import MockIoTAdapter
from app.services.chat_agent import ChatAgent


def _message(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _response(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _tool_call(call_id, name, arguments_json):
    function = SimpleNamespace(name=name, arguments=arguments_json)
    return SimpleNamespace(id=call_id, function=function)


class FakeOpenAI:
    """정해진 응답을 순서대로 돌려주는 가짜 OpenAI 클라이언트."""

    def __init__(self, responses):
        self._responses = iter(responses)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        return next(self._responses)


GREENHOUSE_NAMES = {1: "1번 온실(토마토)", 2: "2번 온실(딸기)", 3: "3번 온실(오이)"}


def _all_normal_status():
    return [
        {"id": gid, "name": name, "status": "normal", "temperature": 24.0, "humidity": 60}
        for gid, name in GREENHOUSE_NAMES.items()
    ]


def _agent(responses, iot_by_greenhouse=None, status_provider=None):
    return ChatAgent(
        iot_by_greenhouse=iot_by_greenhouse or {1: MockIoTAdapter()},
        greenhouse_names=GREENHOUSE_NAMES,
        status_provider=status_provider or _all_normal_status,
        client=FakeOpenAI(responses),
    )


def test_handle_never_returns_none_reply():
    result = _agent([_response(_message(content=None))]).handle("...")

    assert isinstance(result["reply"], str)
    assert result["reply"] != ""


def test_handle_returns_plain_reply_when_no_tool_needed():
    result = _agent([_response(_message(content="안녕하세요! 무엇을 도와드릴까요?"))]).handle("안녕")

    assert result == {"reply": "안녕하세요! 무엇을 도와드릴까요?", "actions_taken": []}


def test_handle_executes_control_device_tool_call():
    tool_call = _tool_call(
        "call1", "control_device", '{"device": "shade", "action": "close", "greenhouse_id": 1}'
    )
    iot = MockIoTAdapter()
    agent = _agent(
        [
            _response(_message(tool_calls=[tool_call])),
            _response(_message(content="1번 온실 차광막을 닫았어요.")),
        ],
        iot_by_greenhouse={1: iot},
    )

    result = agent.handle("1번 온실 차광막 닫아줘")

    assert result == {
        "reply": "1번 온실 차광막을 닫았어요.",
        "actions_taken": [{"device": "shade", "greenhouse_id": 1, "action": "close", "success": True}],
    }
    assert iot.state["shade"] == "closed"


def test_handle_executes_read_data_tool_call_without_actions_taken():
    tool_call = _tool_call("call1", "read_data", '{"target": "temperature"}')
    agent = _agent(
        [
            _response(_message(tool_calls=[tool_call])),
            _response(_message(content="지금 온도는 24.5도예요.")),
        ]
    )

    result = agent.handle("지금 온도 몇 도야?")

    assert result == {"reply": "지금 온도는 24.5도예요.", "actions_taken": []}


def test_handle_recovers_from_malformed_tool_arguments():
    """모델이 깨진 JSON 을 반환해도 예외로 죽지 않고 안내 응답으로 이어져야 한다."""
    bad_call = _tool_call("call1", "control_device", "{not valid json")
    agent = _agent(
        [
            _response(_message(tool_calls=[bad_call])),
            _response(_message(content="죄송해요, 다시 말씀해 주세요.")),
        ]
    )

    result = agent.handle("차광막 닫아줘")

    assert result["reply"] == "죄송해요, 다시 말씀해 주세요."
    assert result["actions_taken"] == []


def test_handle_includes_prior_history_in_prompt():
    captured = {}

    class RecordingOpenAI(FakeOpenAI):
        def _create(self, **kwargs):
            captured["messages"] = kwargs["messages"]
            return super()._create(**kwargs)

    agent = ChatAgent(
        iot_by_greenhouse={1: MockIoTAdapter()},
        greenhouse_names=GREENHOUSE_NAMES,
        status_provider=_all_normal_status,
        client=RecordingOpenAI([_response(_message(content="네, 다시 닫았어요."))]),
    )
    history = [
        {"role": "user", "content": "차광막 닫아줘"},
        {"role": "assistant", "content": "차광막을 닫았어요."},
    ]

    agent.handle("그거 다시 닫아줘", history=history)

    assert captured["messages"][1:3] == history


# --- 온실 지정 제어/조회 ("2번 온실 창문 열어줘", "딸기 온실 습도 몇이야?") ---


def _two_greenhouses():
    return {1: MockIoTAdapter(), 2: MockIoTAdapter()}


def test_control_routes_to_specified_greenhouse():
    tool_call = _tool_call(
        "call1", "control_device", '{"device": "window", "action": "open", "greenhouse_id": 2}'
    )
    iot_by_greenhouse = _two_greenhouses()
    agent = _agent(
        [
            _response(_message(tool_calls=[tool_call])),
            _response(_message(content="2번 온실 창문을 열었어요.")),
        ],
        iot_by_greenhouse=iot_by_greenhouse,
    )

    result = agent.handle("2번 온실 창문 열어줘")

    assert result["actions_taken"] == [
        {"device": "window", "greenhouse_id": 2, "action": "open", "success": True}
    ]
    assert iot_by_greenhouse[2].state["window"] == "open"
    assert iot_by_greenhouse[1].state["window"] == "closed"  # 다른 온실엔 영향 없음


def test_control_device_schema_requires_greenhouse_id():
    """온실 미지정 시 자동으로 1번에 적용하지 않고 모델이 되묻게 하려면
    greenhouse_id 가 선택이 아니라 필수 스키마여야 한다."""
    agent = _agent([_response(_message(content="dummy"))])

    control_tool = next(t for t in agent._tools if t["function"]["name"] == "control_device")

    assert "greenhouse_id" in control_tool["function"]["parameters"]["required"]


def test_control_without_greenhouse_id_is_not_silently_applied():
    """모델이 (오작동으로) greenhouse_id 없이 control_device 를 호출해도
    1번 온실에 대신 적용하면 안 된다 — 실행 실패로 처리."""
    tool_call = _tool_call("call1", "control_device", '{"device": "window", "action": "open"}')
    iot_by_greenhouse = _two_greenhouses()
    agent = _agent(
        [
            _response(_message(tool_calls=[tool_call])),
            _response(_message(content="몇 번 온실인지 알려주시겠어요?")),
        ],
        iot_by_greenhouse=iot_by_greenhouse,
    )

    result = agent.handle("창문 열어줘")

    assert result["actions_taken"] == [
        {"device": "window", "greenhouse_id": None, "action": "open", "success": False}
    ]
    assert iot_by_greenhouse[1].state["window"] == "closed"
    assert iot_by_greenhouse[2].state["window"] == "closed"


def test_control_unknown_greenhouse_fails_gracefully():
    tool_call = _tool_call(
        "call1", "control_device", '{"device": "window", "action": "open", "greenhouse_id": 99}'
    )
    iot_by_greenhouse = _two_greenhouses()
    agent = _agent(
        [
            _response(_message(tool_calls=[tool_call])),
            _response(_message(content="99번 온실은 없어요.")),
        ],
        iot_by_greenhouse=iot_by_greenhouse,
    )

    result = agent.handle("99번 온실 창문 열어줘")

    assert result["actions_taken"] == [
        {"device": "window", "greenhouse_id": 99, "action": "open", "success": False}
    ]
    assert iot_by_greenhouse[1].state["window"] == "closed"
    assert iot_by_greenhouse[2].state["window"] == "closed"


def test_read_data_still_defaults_to_greenhouse_1_when_unspecified():
    """조회는 위험이 낮아 (장비를 바꾸지 않음) 기존처럼 미지정 시 1번 온실 기본값을 유지한다."""
    tool_call = _tool_call("call1", "read_data", '{"target": "temperature"}')
    iot_by_greenhouse = _two_greenhouses()
    agent = _agent(
        [
            _response(_message(tool_calls=[tool_call])),
            _response(_message(content="1번 온실은 24도예요.")),
        ],
        iot_by_greenhouse=iot_by_greenhouse,
    )

    result = agent.handle("온도 몇 도야?")

    assert result["reply"] == "1번 온실은 24도예요."


def test_read_data_routes_to_specified_greenhouse():
    captured = {}

    class RecordingOpenAI(FakeOpenAI):
        def _create(self, **kwargs):
            captured.setdefault("calls", []).append(kwargs)
            return super()._create(**kwargs)

    class FixedHumidityAdapter(MockIoTAdapter):
        def read(self, target):
            return {"ok": True, "target": target, "value": 82, "unit": "%"}

    tool_call = _tool_call("call1", "read_data", '{"target": "humidity", "greenhouse_id": 2}')
    agent = ChatAgent(
        iot_by_greenhouse={1: MockIoTAdapter(), 2: FixedHumidityAdapter()},
        greenhouse_names=GREENHOUSE_NAMES,
        status_provider=_all_normal_status,
        client=RecordingOpenAI(
            [
                _response(_message(tool_calls=[tool_call])),
                _response(_message(content="2번 온실 습도는 82%예요.")),
            ]
        ),
    )

    result = agent.handle("딸기 온실 습도 몇이야?")

    assert result["reply"] == "2번 온실 습도는 82%예요."
    tool_result_message = captured["calls"][1]["messages"][-1]
    assert '"value": 82' in tool_result_message["content"]


def test_system_prompt_describes_farm_layout():
    """모델이 '딸기 온실'을 2번으로 매핑하려면 프롬프트에 온실 구성이 있어야 한다."""
    captured = {}

    class RecordingOpenAI(FakeOpenAI):
        def _create(self, **kwargs):
            captured["messages"] = kwargs["messages"]
            return super()._create(**kwargs)

    agent = ChatAgent(
        iot_by_greenhouse={1: MockIoTAdapter(), 2: MockIoTAdapter()},
        greenhouse_names=GREENHOUSE_NAMES,
        status_provider=_all_normal_status,
        client=RecordingOpenAI([_response(_message(content="안녕하세요!"))]),
    )

    agent.handle("안녕")

    system_prompt = captured["messages"][0]["content"]
    assert "1번 온실(토마토)" in system_prompt
    assert "2번 온실(딸기)" in system_prompt


def test_system_prompt_instructs_asking_back_when_greenhouse_unspecified():
    captured = {}

    class RecordingOpenAI(FakeOpenAI):
        def _create(self, **kwargs):
            captured["messages"] = kwargs["messages"]
            return super()._create(**kwargs)

    agent = ChatAgent(
        iot_by_greenhouse={1: MockIoTAdapter()},
        greenhouse_names=GREENHOUSE_NAMES,
        status_provider=_all_normal_status,
        client=RecordingOpenAI([_response(_message(content="안녕하세요!"))]),
    )

    agent.handle("안녕")

    system_prompt = captured["messages"][0]["content"]
    assert "되물어" in system_prompt or "확인" in system_prompt


def test_system_prompt_includes_live_status_and_flags_warning_greenhouse():
    """경고 중인 온실이 있으면 모델이 그걸 근거로 되물을 수 있게 상태를 프롬프트에 넣는다."""
    captured = {}

    class RecordingOpenAI(FakeOpenAI):
        def _create(self, **kwargs):
            captured.setdefault("prompts", []).append(kwargs["messages"][0]["content"])
            return super()._create(**kwargs)

    def status_with_warning():
        return [
            {"id": 1, "name": "1번 온실(토마토)", "status": "normal", "temperature": 24.0, "humidity": 60},
            {"id": 2, "name": "2번 온실(딸기)", "status": "warning", "temperature": 24.0, "humidity": 82},
        ]

    agent = ChatAgent(
        iot_by_greenhouse={1: MockIoTAdapter(), 2: MockIoTAdapter()},
        greenhouse_names=GREENHOUSE_NAMES,
        status_provider=status_with_warning,
        client=RecordingOpenAI([_response(_message(content="안녕하세요!"))]),
    )

    agent.handle("안녕")

    prompt = captured["prompts"][0]
    assert "2번 온실(딸기)" in prompt
    assert "경고" in prompt
    assert "82" in prompt  # 습도 수치


def test_ask_back_hint_points_directly_at_the_single_abnormal_greenhouse():
    """경고 온실이 정확히 하나면, 모델이 목록에서 스스로 찾게 두지 않고
    코드가 그 온실을 직접 지목하는 문장을 만들어준다 (실측: 모델에만 맡기면
    지시를 놓치고 목록형 되묻기를 하는 경우가 있었음)."""
    status = [
        {"id": 1, "name": "1번 온실(토마토)", "status": "normal", "temperature": 24.0, "humidity": 60},
        {"id": 2, "name": "2번 온실(딸기)", "status": "warning", "temperature": 24.0, "humidity": 82},
        {"id": 3, "name": "3번 온실(오이)", "status": "normal", "temperature": 27.0, "humidity": 55},
    ]

    hint = ChatAgent._ask_back_target_hint(status)

    assert "2번 온실(딸기)" in hint
    assert "그대로 사용" in hint  # 표현을 바꾸지 말고 리터럴 문장을 쓰라는 지시


def test_ask_back_hint_lists_all_when_no_single_abnormal_greenhouse():
    all_normal = [
        {"id": 1, "name": "1번 온실(토마토)", "status": "normal", "temperature": 24.0, "humidity": 60},
        {"id": 2, "name": "2번 온실(딸기)", "status": "normal", "temperature": 24.0, "humidity": 70},
    ]
    two_abnormal = [
        {"id": 1, "name": "1번 온실(토마토)", "status": "warning", "temperature": 24.0, "humidity": 81},
        {"id": 2, "name": "2번 온실(딸기)", "status": "critical", "temperature": 24.0, "humidity": 95},
    ]

    for status in (all_normal, two_abnormal):
        hint = ChatAgent._ask_back_target_hint(status)
        assert "1번 온실(토마토)" in hint
        assert "2번 온실(딸기)" in hint


def test_system_prompt_status_is_refreshed_on_every_call():
    """온실 상태는 대화 중에도 바뀌므로 매 handle() 호출 때 새로 반영해야 한다."""
    captured = []
    current_status = {"value": "normal"}

    class RecordingOpenAI(FakeOpenAI):
        def _create(self, **kwargs):
            captured.append(kwargs["messages"][0]["content"])
            return super()._create(**kwargs)

    agent = ChatAgent(
        iot_by_greenhouse={1: MockIoTAdapter()},
        greenhouse_names=GREENHOUSE_NAMES,
        status_provider=lambda: [
            {"id": 1, "name": "1번 온실(토마토)", "status": current_status["value"], "temperature": 24.0, "humidity": 60}
        ],
        client=RecordingOpenAI(
            [_response(_message(content="안녕!")), _response(_message(content="또 안녕!"))]
        ),
    )

    agent.handle("안녕")
    current_status["value"] = "critical"
    agent.handle("안녕")

    assert "정상" in captured[0] or "normal" in captured[0].lower()
    assert "위험" in captured[1] or "critical" in captured[1].lower()
