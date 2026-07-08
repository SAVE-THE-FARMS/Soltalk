"""
LLM 에이전트 (뼈대).

역할: 사용자 자연어 → LLM 으로 의도 파악 → Mock IoT 어댑터 호출 → 자연어 응답.
권장: OpenAI 의 function calling(tools) 로 control_device / read_data 를 도구로 주고,
      모델이 알아서 어댑터를 호출하게 한다. (프롬프트 JSON 파싱보다 견고)

TODO(학생):
  1. openai 클라이언트 생성 (OPENAI_API_KEY 는 env/.env 에서 로드됨)
  2. control_device / read_data tool(function) 정의
  3. tool 호출 루프 구현 → MockIoTAdapter 호출
  4. 최종 자연어 응답 문자열 반환

지금은 자리만 잡아둠.
"""

from .iot.mock import MockIoTAdapter

# 어댑터는 여기서 한 번 만들어 재사용 (나중에 Real 로 교체 가능)
iot: MockIoTAdapter = MockIoTAdapter()


def handle_message(message: str) -> str:
    """사용자 한 마디를 받아 자연어 응답을 돌려준다."""
    # TODO(학생): OpenAI function calling 으로 구현.
    raise NotImplementedError
