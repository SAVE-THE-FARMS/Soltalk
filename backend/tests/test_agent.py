"""agent.handle_message 테스트.

OpenAI 호출은 외부 네트워크 의존이라 실제 API를 부르지 않고,
OpenAI SDK 응답 모양(choices[0].message.tool_calls 등)만 흉내 낸 fake client 를 주입해서 검증한다.

반환 스키마: {"reply": str, "actions_taken": [{"device", "greenhouse_id", "action", "success"}, ...]}
"""

from types import SimpleNamespace

from app.agent import handle_message
from app.iot.mock import MockIoTAdapter


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


def test_handle_message_never_returns_none_reply():
    client = FakeOpenAI([_response(_message(content=None))])

    result = handle_message("...", client=client, iot=MockIoTAdapter())

    assert isinstance(result["reply"], str)
    assert result["reply"] != ""


def test_handle_message_returns_plain_reply_when_no_tool_needed():
    client = FakeOpenAI([_response(_message(content="안녕하세요! 무엇을 도와드릴까요?"))])
    iot = MockIoTAdapter()

    result = handle_message("안녕", client=client, iot=iot)

    assert result == {"reply": "안녕하세요! 무엇을 도와드릴까요?", "actions_taken": []}


def test_handle_message_executes_control_device_tool_call():
    tool_call = _tool_call("call1", "control_device", '{"device": "shade", "action": "close"}')
    client = FakeOpenAI(
        [
            _response(_message(tool_calls=[tool_call])),
            _response(_message(content="차광막을 닫았어요.")),
        ]
    )
    iot = MockIoTAdapter()

    result = handle_message("차광막 닫아줘", client=client, iot=iot)

    assert result == {
        "reply": "차광막을 닫았어요.",
        "actions_taken": [{"device": "shade", "greenhouse_id": 1, "action": "close", "success": True}],
    }
    assert iot.state["shade"] == "closed"


def test_handle_message_executes_read_data_tool_call_without_actions_taken():
    tool_call = _tool_call("call1", "read_data", '{"target": "temperature"}')
    client = FakeOpenAI(
        [
            _response(_message(tool_calls=[tool_call])),
            _response(_message(content="지금 온도는 24.5도예요.")),
        ]
    )
    iot = MockIoTAdapter()

    result = handle_message("지금 온도 몇 도야?", client=client, iot=iot)

    assert result == {"reply": "지금 온도는 24.5도예요.", "actions_taken": []}


def test_handle_message_includes_prior_history_in_prompt():
    captured = {}

    class RecordingOpenAI(FakeOpenAI):
        def _create(self, **kwargs):
            captured["messages"] = kwargs["messages"]
            return super()._create(**kwargs)

    client = RecordingOpenAI([_response(_message(content="네, 다시 닫았어요."))])
    history = [
        {"role": "user", "content": "차광막 닫아줘"},
        {"role": "assistant", "content": "차광막을 닫았어요."},
    ]

    handle_message("그거 다시 닫아줘", client=client, iot=MockIoTAdapter(), history=history)

    assert captured["messages"][1:3] == history
