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


def _agent(responses, iot=None):
    return ChatAgent(iot=iot or MockIoTAdapter(), client=FakeOpenAI(responses))


def test_handle_never_returns_none_reply():
    result = _agent([_response(_message(content=None))]).handle("...")

    assert isinstance(result["reply"], str)
    assert result["reply"] != ""


def test_handle_returns_plain_reply_when_no_tool_needed():
    result = _agent([_response(_message(content="안녕하세요! 무엇을 도와드릴까요?"))]).handle("안녕")

    assert result == {"reply": "안녕하세요! 무엇을 도와드릴까요?", "actions_taken": []}


def test_handle_executes_control_device_tool_call():
    tool_call = _tool_call("call1", "control_device", '{"device": "shade", "action": "close"}')
    iot = MockIoTAdapter()
    agent = _agent(
        [
            _response(_message(tool_calls=[tool_call])),
            _response(_message(content="차광막을 닫았어요.")),
        ],
        iot=iot,
    )

    result = agent.handle("차광막 닫아줘")

    assert result == {
        "reply": "차광막을 닫았어요.",
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
        iot=MockIoTAdapter(),
        client=RecordingOpenAI([_response(_message(content="네, 다시 닫았어요."))]),
    )
    history = [
        {"role": "user", "content": "차광막 닫아줘"},
        {"role": "assistant", "content": "차광막을 닫았어요."},
    ]

    agent.handle("그거 다시 닫아줘", history=history)

    assert captured["messages"][1:3] == history
