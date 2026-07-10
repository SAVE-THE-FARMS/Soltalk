# Realtime API 음성 기능 — 백엔드 핵심 2개 설계

> 참고 원본: `Docs/voice_feature_backend (1).md`, `Docs/voice_feature_frontend (1).md`
> 범위: 문서의 8개 체크리스트 중 **핵심 2개만** — `POST /api/realtime/session`, `POST /api/tools/execute`.
> 나머지(환경변수 2종 관리, Realtime용 별도 tool 스키마 작성, farm_state 공유 확인 등)는 이번 스코프 밖.

## 배경 / 원본 문서 정정

원본 문서는 "기존 텍스트 채팅은 Claude(Anthropic) 기반, Realtime만 신규 OpenAI"라는 전제였으나,
실제 `backend/app/services/chat_agent.py`를 확인한 결과 **텍스트 채팅도 이미 OpenAI**(`gpt-5.4-mini`,
Chat Completions API)를 쓰고 있다. 사용자 확인: Claude로 바꾸지 않고 OpenAI로 통일 유지.

**결과**: 원본 문서의 "이중 공급자 관리" 리스크, "환경변수 2종(`ANTHROPIC_API_KEY`+`OPENAI_API_KEY`)"
항목은 해당 없음 — 기존 `OPENAI_API_KEY` 하나로 충분하다. 이번 스코프에서 새 환경변수는 추가하지 않는다.

## 범위 밖 (명시)

- Realtime API용 별도 tool 스키마(`realtime_tools_schema.py`) 작성 — 프론트 문서 4절에 따르면 프론트가
  WebRTC 연결 후 `session.update`로 tool 목록을 직접 OpenAI에 전달하는 구조이므로, 이 스코프(세션 발급 +
  tool 실행 브릿지)에는 필요 없다.
- 프론트엔드 작업(WebRTC 연결, UI 상태, function-call 이벤트 수신) — 다른 팀원 담당.
- 텍스트 채팅(`/api/chat`)의 백업 경로 재확인, 발표 환경 리허설 — 이번 스코프 밖.

## 1. `POST /api/realtime/session` — ephemeral 세션 발급

- 새 서비스 `RealtimeSessionService`(`backend/app/services/realtime_session.py`)를 만든다.
- `create_session() -> dict`가 OpenAI Realtime 세션 생성 REST 엔드포인트
  (`POST https://api.openai.com/v1/realtime/sessions`, `Authorization: Bearer {OPENAI_API_KEY}`)를
  직접 HTTP로 호출해 세션을 만들고, 응답에서 `client_secret`/`expires_at`만 추출해 돌려준다.
  - SDK의 특정 헬퍼 메서드 이름에 의존하지 않고 REST를 직접 호출한다 — SDK 버전에 따라 메서드 경로가
    바뀔 수 있어 REST 스펙이 더 안정적인 기준이기 때문. `httpx`를 새 의존성으로 추가한다
    (`openai` 패키지가 이미 내부적으로 쓰는 라이브러리라 무겁지 않음).
  - 모델명은 상수 `RealtimeSessionService.MODEL = "gpt-5.4-mini-realtime"`로 한 곳에 모아둔다(기존
    `ChatAgent.MODEL = "gpt-5.4-mini"` 명명 규칙과 통일). 코드 주석으로 "실제 OpenAI 키로 첫 호출 시
    계정에서 사용 가능한 Realtime 모델명이 다르면 이 상수만 바꾸면 된다"를 남긴다.
  - `ChatAgent`/`TranscriptionService`와 같은 패턴으로 HTTP 클라이언트를 **lazy 생성**한다(생성자 시점에
    API 키가 없어도 import 가능하게).
  - OpenAI 쪽 호출이 실패하면(네트워크 오류, 4xx/5xx) 예외를 그대로 올려서 `server.py`가 502로 변환한다.
- `AppContainer`에 `self.realtime_sessions = RealtimeSessionService()`를 추가.
- `server.py`에 엔드포인트 추가:
  ```python
  @app.post("/api/realtime/session")
  def create_realtime_session():
      try:
          return container.realtime_sessions.create_session()
      except Exception:
          logger.exception("realtime session 발급 실패")
          raise HTTPException(status_code=502, detail="음성 세션을 시작할 수 없어요.")
  ```

## 2. `POST /api/tools/execute` — tool 실행 브릿지

- `ChatAgent._dispatch`(장비 제어/조회 실행 로직 + 알림 해제 note 삽입)를 **공용 모듈**
  `backend/app/services/tool_execution.py`의 `execute_tool()` 함수로 추출한다. `ChatAgent`는 이 함수를
  호출하도록 바꾸고, 기존 `_dispatch` 메서드는 제거한다(중복 제거, 동작은 동일하게 유지).
- `ChatAgent._is_alerting`은 이름의 언더스코어를 떼고 `is_alerting`(public)으로 바꿔서 `server.py`에서도
  `container.chat_agent.is_alerting(greenhouse_id)`로 재사용할 수 있게 한다.
- `server.py`에 엔드포인트 추가:
  ```python
  class ToolExecuteRequest(BaseModel):
      tool_name: str
      arguments: dict

  @app.post("/api/tools/execute")
  def execute_tool_endpoint(req: ToolExecuteRequest):
      greenhouse_id = req.arguments.get("greenhouse_id")
      if req.tool_name == "read_data" and greenhouse_id is None:
          greenhouse_id = ChatAgent.DEFAULT_GREENHOUSE_ID
      result = execute_tool(
          req.tool_name,
          req.arguments,
          greenhouse_id,
          container.iot_by_greenhouse,
          container.chat_agent.is_alerting,
      )
      return {"result": result}
  ```
- 기존 `handle()`의 관찰 가능한 동작(텍스트 챗 tool 실행 결과)은 이 리팩터로 바뀌지 않아야 한다 —
  `test_agent.py`의 기존 테스트가 전부 `handle()`을 통해서만 검증하므로 그대로 회귀 방지망이 된다.

## 검증 계획

- `uv run pytest`로 기존 테스트(`test_agent.py` 등)가 리팩터 후에도 그대로 통과하는지 확인 — 이게 깨지면
  `execute_tool()` 추출이 기존 동작을 바꿨다는 뜻.
- 새 테스트: `execute_tool()` 단위 테스트(온실 미지정/미존재 온실/정상 제어/경고 온실 해제 note), 새
  엔드포인트 2개의 FastAPI `TestClient` 테스트(`RealtimeSessionService.create_session`은 monkeypatch로
  대체, 실제 OpenAI 호출 없음).
- `/docs`에서 두 엔드포인트가 스키마대로 노출되는지 수동 확인(실제 OpenAI 키 필요한 `/api/realtime/session`
  실제 호출은 이번 검증 범위 밖 — 프론트 연동 시점에 함께 확인).
