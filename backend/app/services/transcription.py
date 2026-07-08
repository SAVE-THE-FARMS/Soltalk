"""음성 → 텍스트 (STT).

OpenAI 트랜스크립션 API(gpt-4o-transcribe)로 업로드된 오디오를 한국어 텍스트로 변환한다.
챗 흐름과는 분리 — 프론트가 마이크 녹음을 업로드하면 텍스트만 돌려주고,
그 텍스트는 기존 /api/chat 으로 다시 태운다.
"""

import logging

from openai import OpenAI

logger = logging.getLogger(__name__)


class TranscriptionService:
    MODEL = "gpt-4o-transcribe"  # 배치 파일 트랜스크립션, 한국어 지원
    LANGUAGE = "ko"  # 입력 언어 지정 → 정확도/지연 개선

    def __init__(self, client: OpenAI | None = None, model: str | None = None):
        self._client = client  # None 이면 최초 호출 때 lazy 생성
        self._model = model or self.MODEL

    def _client_or_default(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI()
        return self._client

    def transcribe(self, audio: bytes, filename: str = "audio.webm") -> str:
        """오디오 바이트를 받아 인식된 텍스트를 돌려준다."""
        client = self._client_or_default()
        result = client.audio.transcriptions.create(
            model=self._model,
            file=(filename, audio),  # SDK 는 (파일명, 바이트) 튜플을 받는다
            language=self.LANGUAGE,
        )
        return result.text
