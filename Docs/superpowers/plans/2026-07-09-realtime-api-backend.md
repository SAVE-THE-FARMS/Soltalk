# Realtime API 백엔드 핵심 2개 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** OpenAI Realtime API(음성) 연동을 위한 백엔드 엔드포인트 2개 — ephemeral 세션 발급(`POST /api/realtime/session`)과 tool 실행 브릿지(`POST /api/tools/execute`) — 를 추가한다.

**Architecture:** 기존 `ChatAgent`의 tool 실행 로직(`_dispatch`)을 `tool_execution.execute_tool()` 공용 함수로 추출해 텍스트 챗과 Realtime 브릿지가 동일한 실행 경로를 공유하게 한다. Realtime 세션 발급은 새 `RealtimeSessionService`가 OpenAI REST를 직접 호출해 담당한다. 텍스트 채팅과 동일하게 OpenAI 하나의 공급자만 쓴다(Claude 아님, 새 환경변수 없음).

**Tech Stack:** Python + FastAPI (기존 그대로), 신규: `httpx`(OpenAI REST 직접 호출용).

## Global Constraints

- 새 환경변수를 추가하지 않는다 — 기존 `OPENAI_API_KEY` 하나로 텍스트 챗과 Realtime 세션 발급 모두 처리한다.
- Realtime API용 별도 tool 스키마(`realtime_tools_schema.py`)는 이번 스코프에서 만들지 않는다 — 프론트가 WebRTC 연결 후 `session.update`로 직접 처리한다.
- `execute_tool()` 추출 후에도 기존 `backend/tests/test_agent.py`의 모든 테스트가 수정 없이 그대로 통과해야 한다(회귀 방지 기준).
- 테스트는 `uv run pytest`로 실행한다(backend/ 디렉터리에서).
- 참고 스펙: `docs/superpowers/specs/2026-07-09-realtime-api-backend-design.md`

---

### Task 1: `execute_tool()` 공용 함수 추출 + `ChatAgent` 리팩터

**Files:**
- Create: `backend/app/services/tool_execution.py`
- Create: `backend/tests/test_tool_execution.py`
- Modify: `backend/app/services/chat_agent.py:245-297` (`_run_tool`/`_dispatch`/`_is_alerting` 부분)

**Interfaces:**
- Produces: `execute_tool(name: str, args: dict, greenhouse_id: int | None, iot_by_greenhouse: dict[int, IoTAdapter], is_alerting: Callable[[int], bool]) -> dict` — Task 3의 `/api/tools/execute` 엔드포인트가 그대로 재사용한다.
- Produces: `ChatAgent.is_alerting(greenhouse_id: int) -> bool` (기존 `_is_alerting`의 public 버전) — Task 3에서 `container.chat_agent.is_alerting`로 재사용한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_tool_execution.py` 생성:

```python
"""execute_tool() 단위 테스트 — ChatAgent와 Realtime tool 브릿지가 공유하는 실행 로직."""

from app.iot.mock import MockIoTAdapter
from app.services.tool_execution import execute_tool


def _always_normal(greenhouse_id):
    return False


def _always_alerting(greenhouse_id):
    return True


def test_control_device_without_greenhouse_id_is_not_executed():
    result = execute_tool(
        "control_device",
        {"device": "shade", "action": "close"},
        None,
        {1: MockIoTAdapter()},
        _always_normal,
    )
    assert result == {"ok": False, "reason": "missing_greenhouse_id"}


def test_control_device_unknown_greenhouse_fails_gracefully():
    result = execute_tool(
        "control_device",
        {"device": "shade", "action": "close"},
        99,
        {1: MockIoTAdapter()},
        _always_normal,
    )
    assert result == {"ok": False, "reason": "unknown_greenhouse", "greenhouse_id": 99}


def test_control_device_success_on_normal_greenhouse_has_no_note():
    adapter = MockIoTAdapter()

    result = execute_tool(
        "control_device", {"device": "shade", "action": "close"}, 1, {1: adapter}, _always_normal
    )

    assert result["ok"] is True
    assert result["device"] == "shade"
    assert result["state"] == "closed"
    assert result["greenhouse_id"] == 1
    assert "note" not in result


def test_control_device_success_on_alerting_greenhouse_adds_note():
    adapter = MockIoTAdapter()

    result = execute_tool(
        "control_device", {"device": "shade", "action": "close"}, 1, {1: adapter}, _always_alerting
    )

    assert result["ok"] is True
    assert "note" in result
    assert "사라집니다" in result["note"]


def test_read_data_returns_target_value():
    adapter = MockIoTAdapter()

    result = execute_tool("read_data", {"target": "temperature"}, 1, {1: adapter}, _always_normal)

    assert result["ok"] is True
    assert result["target"] == "temperature"
    assert result["greenhouse_id"] == 1


def test_unknown_tool_name_fails_gracefully():
    result = execute_tool("delete_everything", {}, 1, {1: MockIoTAdapter()}, _always_normal)

    assert result == {"ok": False, "reason": "unknown_tool"}
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend
uv run pytest tests/test_tool_execution.py -v
```
예상: `ModuleNotFoundError: No module named 'app.services.tool_execution'`로 실패.

- [ ] **Step 3: `tool_execution.py` 작성**

`backend/app/services/tool_execution.py` 생성:

```python
"""ChatAgent(텍스트 챗)와 Realtime tool 브릿지(/api/tools/execute)가 공유하는
control_device / read_data 실행 로직. 이 함수 하나만 바꾸면 두 경로 모두에 반영된다.
"""

from typing import Callable

from ..iot.base import IoTAdapter

ALERT_CLEARED_NOTE = (
    "이 온실은 방금까지 경고/위험 상태였습니다. 이 조치로 습도가 내려가면 "
    "대시보드의 알림과 조치 버튼이 자동으로 사라집니다(=해결됐다는 뜻). "
    "답변에 이 사실을 한 문장으로 짧게 안내하세요."
)


def execute_tool(
    name: str,
    args: dict,
    greenhouse_id: int | None,
    iot_by_greenhouse: dict[int, IoTAdapter],
    is_alerting: Callable[[int], bool],
) -> dict:
    """control_device / read_data 를 실제로 실행하고 결과 dict를 돌려준다.

    greenhouse_id 가 None 이면(control_device 미지정) 실행하지 않는다 — 호출자가
    되묻거나 안내해야 한다는 뜻으로 {"ok": False, "reason": "missing_greenhouse_id"} 를 돌려준다.
    """
    if greenhouse_id is None:
        return {"ok": False, "reason": "missing_greenhouse_id"}
    iot = iot_by_greenhouse.get(greenhouse_id)
    if iot is None:
        return {"ok": False, "reason": "unknown_greenhouse", "greenhouse_id": greenhouse_id}
    if name == "control_device":
        was_alerting = is_alerting(greenhouse_id)
        result = {**iot.control(args["device"], args["action"]), "greenhouse_id": greenhouse_id}
        if result.get("ok") and was_alerting:
            result["note"] = ALERT_CLEARED_NOTE
        return result
    if name == "read_data":
        return {**iot.read(args["target"]), "greenhouse_id": greenhouse_id}
    return {"ok": False, "reason": "unknown_tool"}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
uv run pytest tests/test_tool_execution.py -v
```
예상: 6개 테스트 모두 PASS.

- [ ] **Step 5: `chat_agent.py`가 `execute_tool()`을 쓰도록 리팩터**

`backend/app/services/chat_agent.py` 상단 import에 추가:
```python
from .tool_execution import execute_tool
```

기존:
```python
    def _run_tool(self, tool_call, actions_taken: list[dict]) -> dict:
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except (json.JSONDecodeError, TypeError):
            logger.warning("tool 인자 JSON 파싱 실패: %r", tool_call.function.arguments)
            return {"ok": False, "reason": "invalid_arguments"}

        greenhouse_id = args.get("greenhouse_id")
        if greenhouse_id is None and name == "read_data":
            # read_data 는 위험이 낮으므로 미지정 시 기본 온실로 조회 (하위 호환)
            greenhouse_id = self.DEFAULT_GREENHOUSE_ID
        result = self._dispatch(name, args, greenhouse_id)

        if name == "control_device":
            actions_taken.append(
                {
                    "device": args.get("device"),
                    "greenhouse_id": greenhouse_id,
                    "action": args.get("action"),
                    "success": result.get("ok", False),
                }
            )
        return result

    def _dispatch(self, name: str, args: dict, greenhouse_id: int | None) -> dict:
        if greenhouse_id is None:
            # control_device 는 온실 미지정 시 실행하지 않는다 — 모델이 되물어야 한다.
            return {"ok": False, "reason": "missing_greenhouse_id"}
        iot = self._iot_by_greenhouse.get(greenhouse_id)
        if iot is None:
            return {"ok": False, "reason": "unknown_greenhouse", "greenhouse_id": greenhouse_id}
        if name == "control_device":
            was_alerting = self._is_alerting(greenhouse_id)
            result = {**iot.control(args["device"], args["action"]), "greenhouse_id": greenhouse_id}
            if result.get("ok") and was_alerting:
                # 챗으로 경고 중인 온실을 조치하면 대시보드 알림/조치버튼이 습도가
                # 내려가는 대로 조용히 사라진다 — 사용자가 왜 사라졌는지 모를 수
                # 있어(실측 확인) 답변에서 미리 설명하도록 안내를 실어준다.
                result["note"] = (
                    "이 온실은 방금까지 경고/위험 상태였습니다. 이 조치로 습도가 내려가면 "
                    "대시보드의 알림과 조치 버튼이 자동으로 사라집니다(=해결됐다는 뜻). "
                    "답변에 이 사실을 한 문장으로 짧게 안내하세요."
                )
            return result
        if name == "read_data":
            return {**iot.read(args["target"]), "greenhouse_id": greenhouse_id}
        return {"ok": False, "reason": "unknown_tool"}

    def _is_alerting(self, greenhouse_id: int) -> bool:
        return any(
            s["id"] == greenhouse_id and s["status"] != "normal" for s in self._status_provider()
        )
```

교체:
```python
    def _run_tool(self, tool_call, actions_taken: list[dict]) -> dict:
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except (json.JSONDecodeError, TypeError):
            logger.warning("tool 인자 JSON 파싱 실패: %r", tool_call.function.arguments)
            return {"ok": False, "reason": "invalid_arguments"}

        greenhouse_id = args.get("greenhouse_id")
        if greenhouse_id is None and name == "read_data":
            # read_data 는 위험이 낮으므로 미지정 시 기본 온실로 조회 (하위 호환)
            greenhouse_id = self.DEFAULT_GREENHOUSE_ID
        result = execute_tool(name, args, greenhouse_id, self._iot_by_greenhouse, self.is_alerting)

        if name == "control_device":
            actions_taken.append(
                {
                    "device": args.get("device"),
                    "greenhouse_id": greenhouse_id,
                    "action": args.get("action"),
                    "success": result.get("ok", False),
                }
            )
        return result

    def is_alerting(self, greenhouse_id: int) -> bool:
        return any(
            s["id"] == greenhouse_id and s["status"] != "normal" for s in self._status_provider()
        )
```

- [ ] **Step 6: 기존 테스트가 그대로 통과하는지 확인 (회귀 검증)**

```bash
uv run pytest tests/test_agent.py -v
```
예상: 리팩터 전과 동일하게 전부 PASS (동작이 바뀌지 않았어야 함).

- [ ] **Step 7: 전체 테스트 통과 확인 + 커밋**

```bash
uv run pytest -v
git add app/services/tool_execution.py app/services/chat_agent.py tests/test_tool_execution.py
git commit -m "refactor(backend): tool 실행 로직을 execute_tool() 공용 함수로 추출"
```

---

### Task 2: `RealtimeSessionService` — ephemeral 세션 발급

**Files:**
- Modify: `backend/pyproject.toml` (`httpx` 의존성 추가)
- Create: `backend/app/services/realtime_session.py`
- Create: `backend/tests/test_realtime_session_service.py`
- Modify: `backend/app/services/__init__.py` (`RealtimeSessionService` export 추가)

**Interfaces:**
- Produces: `RealtimeSessionService(http_client: httpx.Client | None = None)` — `.create_session() -> dict`가 `{"client_secret": str, "expires_at": int}`를 돌려준다. Task 3의 `AppContainer`/`server.py`가 이 클래스를 그대로 쓴다.

- [ ] **Step 1: `pyproject.toml`에 `httpx` 추가**

`backend/pyproject.toml`의 `dependencies` 목록에 추가:
```toml
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "openai",
    "python-dotenv",
    "python-multipart",
    "soltalk-virtualfarm",
    "httpx",
]
```

```bash
cd backend
uv sync
```

- [ ] **Step 2: 실패하는 테스트 작성**

`backend/tests/test_realtime_session_service.py` 생성:

```python
"""RealtimeSessionService 테스트 — 실제 OpenAI 네트워크 호출 없이 httpx.MockTransport로 검증."""

import httpx
import pytest

from app.services.realtime_session import REALTIME_SESSIONS_URL, RealtimeSessionService


def _client_with(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_create_session_returns_client_secret_and_expiry(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    def handler(request):
        assert str(request.url) == REALTIME_SESSIONS_URL
        assert request.headers["authorization"] == "Bearer sk-test-key"
        return httpx.Response(
            200,
            json={"client_secret": {"value": "ek_abc123", "expires_at": 1234567890}},
        )

    service = RealtimeSessionService(http_client=_client_with(handler))

    result = service.create_session()

    assert result == {"client_secret": "ek_abc123", "expires_at": 1234567890}


def test_create_session_sends_configured_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    sent_bodies = []

    def handler(request):
        sent_bodies.append(request.read())
        return httpx.Response(
            200, json={"client_secret": {"value": "ek_x", "expires_at": 1}}
        )

    service = RealtimeSessionService(http_client=_client_with(handler))
    service.create_session()

    assert RealtimeSessionService.MODEL.encode() in sent_bodies[0]


def test_create_session_raises_on_openai_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    def handler(request):
        return httpx.Response(500, json={"error": "boom"})

    service = RealtimeSessionService(http_client=_client_with(handler))

    with pytest.raises(httpx.HTTPStatusError):
        service.create_session()
```

- [ ] **Step 3: 테스트 실패 확인**

```bash
uv run pytest tests/test_realtime_session_service.py -v
```
예상: `ModuleNotFoundError: No module named 'app.services.realtime_session'`로 실패.

- [ ] **Step 4: `realtime_session.py` 작성**

`backend/app/services/realtime_session.py` 생성:

```python
"""OpenAI Realtime API용 ephemeral 세션 발급.

브라우저(프론트)가 OpenAI에 직접 WebRTC로 연결하려면 짧은 시간만 유효한
"ephemeral key"가 필요하다. 이 키는 서버가 보유한 OPENAI_API_KEY로만 발급받을
수 있고, 프론트에는 절대 OPENAI_API_KEY 자체를 넘기지 않는다.

SDK의 특정 헬퍼 메서드 이름에 의존하지 않고 REST 엔드포인트를 직접 호출한다
(SDK 버전마다 메서드 경로가 바뀔 수 있어 REST 스펙이 더 안정적인 기준).
"""

import os

import httpx

REALTIME_SESSIONS_URL = "https://api.openai.com/v1/realtime/sessions"


class RealtimeSessionService:
    # 실제 OpenAI 계정에서 쓸 수 있는 Realtime 모델명이 다르면 이 상수만 바꾸면 된다.
    MODEL = "gpt-5.4-mini-realtime"

    def __init__(self, http_client: httpx.Client | None = None):
        self._http_client = http_client  # None 이면 최초 호출 때 lazy 생성 (import 시 API 키 불필요)

    def _client_or_default(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=10.0)
        return self._http_client

    def create_session(self) -> dict:
        """OpenAI에 Realtime 세션을 만들고 프론트에 넘길 {"client_secret", "expires_at"}만 추출해 돌려준다."""
        client = self._client_or_default()
        response = client.post(
            REALTIME_SESSIONS_URL,
            json={"model": self.MODEL},
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        )
        response.raise_for_status()
        data = response.json()
        client_secret = data["client_secret"]
        return {"client_secret": client_secret["value"], "expires_at": client_secret["expires_at"]}
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
uv run pytest tests/test_realtime_session_service.py -v
```
예상: 3개 테스트 모두 PASS.

- [ ] **Step 6: `services/__init__.py`에 export 추가**

`backend/app/services/__init__.py` 전체를 아래로 교체:

```python
"""서비스 계층 — 각 관심사를 클래스로 캡슐화하고 의존성은 생성자로 주입받는다.

- SessionStore          : 세션별 대화 히스토리
- ChatAgent             : LLM(OpenAI function calling) 에이전트
- GreenhouseService     : 온실 대시보드 상태 계산
- AlertService          : 알림 엔진
- RealtimeSessionService: OpenAI Realtime API ephemeral 세션 발급

조립(어떤 인스턴스를 어떻게 엮을지)은 app/container.py 의 AppContainer 가 담당한다.
"""

from .alerts import AlertService
from .chat_agent import ChatAgent
from .greenhouse import GreenhouseService
from .realtime_session import RealtimeSessionService
from .session import SessionStore
from .transcription import TranscriptionService

__all__ = [
    "AlertService",
    "ChatAgent",
    "GreenhouseService",
    "RealtimeSessionService",
    "SessionStore",
    "TranscriptionService",
]
```

- [ ] **Step 7: 전체 테스트 통과 확인 + 커밋**

```bash
uv run pytest -v
git add pyproject.toml uv.lock app/services/realtime_session.py app/services/__init__.py tests/test_realtime_session_service.py
git commit -m "feat(backend): RealtimeSessionService — OpenAI ephemeral 세션 발급"
```

---

### Task 3: `server.py` 엔드포인트 2개 연결

**Files:**
- Modify: `backend/app/container.py`
- Modify: `backend/app/server.py`
- Modify: `backend/tests/test_server.py`

**Interfaces:**
- Consumes: Task 1의 `execute_tool()`, `ChatAgent.is_alerting()`; Task 2의 `RealtimeSessionService`.
- Produces: `POST /api/realtime/session` → `{"client_secret": str, "expires_at": int}`. `POST /api/tools/execute` (body `{"tool_name": str, "arguments": dict}`) → `{"result": dict}`.

- [ ] **Step 1: `container.py`에 `realtime_sessions` 추가**

`backend/app/container.py` 상단 import에 추가:
```python
from .services import (
    AlertService,
    ChatAgent,
    GreenhouseService,
    RealtimeSessionService,
    SessionStore,
    TranscriptionService,
)
```
(기존 `from .services import (...)` 줄을 이 목록으로 교체 — `RealtimeSessionService` 추가.)

`AppContainer.__init__`의 `self.transcription = TranscriptionService()` 바로 아래에 추가:
```python
        self.transcription = TranscriptionService()
        self.realtime_sessions = RealtimeSessionService()
```

- [ ] **Step 2: 실패하는 테스트 작성**

`backend/tests/test_server.py` 파일 끝에 추가:

```python
def test_realtime_session_returns_client_secret(monkeypatch):
    monkeypatch.setattr(
        server.container.realtime_sessions,
        "create_session",
        lambda: {"client_secret": "ek_test", "expires_at": 1234567890},
    )
    client = TestClient(server.app)

    resp = client.post("/api/realtime/session")

    assert resp.status_code == 200
    assert resp.json() == {"client_secret": "ek_test", "expires_at": 1234567890}


def test_realtime_session_returns_502_when_openai_call_fails(monkeypatch):
    def boom():
        raise RuntimeError("openai down")

    monkeypatch.setattr(server.container.realtime_sessions, "create_session", boom)
    client = TestClient(server.app)

    resp = client.post("/api/realtime/session")

    assert resp.status_code == 502


def test_tools_execute_runs_control_device():
    _reset_all()
    client = TestClient(server.app)

    resp = client.post(
        "/api/tools/execute",
        json={
            "tool_name": "control_device",
            "arguments": {"device": "shade", "action": "close", "greenhouse_id": 1},
        },
    )

    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["ok"] is True
    assert result["device"] == "shade"
    assert result["state"] == "closed"
    assert result["greenhouse_id"] == 1


def test_tools_execute_read_data_defaults_to_greenhouse_1():
    _reset_all()
    client = TestClient(server.app)

    resp = client.post(
        "/api/tools/execute",
        json={"tool_name": "read_data", "arguments": {"target": "temperature"}},
    )

    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["ok"] is True
    assert result["greenhouse_id"] == 1


def test_tools_execute_control_device_without_greenhouse_id_is_not_applied():
    _reset_all()
    client = TestClient(server.app)

    resp = client.post(
        "/api/tools/execute",
        json={"tool_name": "control_device", "arguments": {"device": "shade", "action": "close"}},
    )

    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result == {"ok": False, "reason": "missing_greenhouse_id"}
```

- [ ] **Step 3: 테스트 실패 확인**

```bash
uv run pytest tests/test_server.py -v
```
예상: `AttributeError: 'AppContainer' object has no attribute 'realtime_sessions'` 및 404(엔드포인트 없음)로 실패.

- [ ] **Step 4: `server.py`에 엔드포인트 추가**

`backend/app/server.py` 상단 import에 추가:
```python
from app.container import AppContainer  # noqa: E402  (위 sys.path 설정 이후에 import)
from app.services.chat_agent import ChatAgent  # noqa: E402
from app.services.tool_execution import execute_tool  # noqa: E402
```
(기존 `from app.container import AppContainer` 줄 다음에 나머지 두 줄을 추가.)

파일 끝(`if __name__ == "__main__":` 바로 위)에 추가:

```python
class ToolExecuteRequest(BaseModel):
    tool_name: str
    arguments: dict


@app.post("/api/realtime/session")
def create_realtime_session():
    try:
        return container.realtime_sessions.create_session()
    except Exception:
        logger.exception("realtime session 발급 실패")
        raise HTTPException(status_code=502, detail="음성 세션을 시작할 수 없어요.")


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

- [ ] **Step 5: 테스트 통과 확인**

```bash
uv run pytest tests/test_server.py -v
```
예상: 새 테스트 5개 포함 전부 PASS.

- [ ] **Step 6: 전체 테스트 스위트 통과 확인**

```bash
uv run pytest -v
```
예상: 전체 PASS, 0 실패.

- [ ] **Step 7: 수동 확인**

```bash
uv run python -m app.server
```
브라우저에서 `http://localhost:8000/docs` 열어 `/api/realtime/session`, `/api/tools/execute`가 스키마와 함께 노출되는지 확인. (`OPENAI_API_KEY`가 `.env`에 없으면 `/api/realtime/session`을 실제로 호출하면 500대 에러가 날 수 있음 — 이번 검증은 `/docs`에 노출되는지만 확인하면 충분하고, 실제 OpenAI 호출 검증은 프론트 연동 시점에 키가 준비된 후 진행.)

- [ ] **Step 8: 커밋**

```bash
git add app/container.py app/server.py tests/test_server.py
git commit -m "feat(backend): /api/realtime/session + /api/tools/execute 엔드포인트 연결"
```

---

## 계획 완료 후 남는 것 (원본 문서 기준)

- Realtime API용 별도 tool 스키마(`realtime_tools_schema.py`) 작성 — 프론트가 `session.update`로 직접 처리하는 구조라 이번엔 불필요했지만, 실제 연동 중 필요해지면 별도 작업.
- 환경변수 관리, farm_state 공유 확인, 텍스트 채팅 백업 경로 재확인 — 해당 없음/이미 충족(같은 컨테이너의 `iot_by_greenhouse`를 그대로 쓰므로 상태는 자동으로 공유됨).
- 실제 OpenAI 계정으로 `/api/realtime/session` 실호출 검증 — API 키/결제수단 준비된 후 프론트 연동 시점에.
