"""TranscriptionService 테스트.

실제 OpenAI 음성 API를 부르지 않고, 응답 모양(result.text)만 흉내 낸 fake client 를 주입한다.
"""

from types import SimpleNamespace

from app.services.transcription import TranscriptionService


class FakeTranscribeClient:
    """audio.transcriptions.create(...).text 를 흉내 내는 가짜 클라이언트."""

    def __init__(self, text):
        self._text = text
        self.calls = []
        self.audio = SimpleNamespace(
            transcriptions=SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text=self._text)


def test_transcribe_returns_text():
    client = FakeTranscribeClient("차광막 닫아줘")
    service = TranscriptionService(client=client)

    text = service.transcribe(b"fake-audio-bytes", filename="cmd.webm")

    assert text == "차광막 닫아줘"


def test_transcribe_passes_model_language_and_file():
    client = FakeTranscribeClient("창문 열어")
    service = TranscriptionService(client=client)

    service.transcribe(b"bytes", filename="cmd.webm")

    call = client.calls[0]
    assert call["model"] == "gpt-4o-transcribe"
    assert call["language"] == "ko"
    assert call["file"] == ("cmd.webm", b"bytes")
