"""
SolTalk 백엔드 진입점 (FastAPI).

실행:  backend/ 에서  ->  uv run python app/server.py
문서:  서버 켠 뒤  http://localhost:8000/docs  에서 API 테스트

흐름:  사용자 입력 → [의도파악/LLM] → [Mock IoT 제어·조회] → [자연어 응답]
서비스 조립은 app/container.py 의 AppContainer 가 담당한다.
"""

import logging
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 스크립트로 직접 실행(uv run python app/server.py)해도 app 패키지를 찾게 backend/ 를 경로에 추가.
# (python -m app.server 로 실행하면 이미 경로에 있어 무해)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.container import AppContainer  # noqa: E402  (위 sys.path 설정 이후에 import)

# env/ 폴더의 .env 로드  (OPENAI_API_KEY 등)
load_dotenv(Path(__file__).resolve().parent.parent / "env" / ".env")

logger = logging.getLogger(__name__)

app = FastAPI(title="SolTalk API")
container = AppContainer()

# React(프론트)에서 호출할 수 있게 CORS 허용 (개발용: 전체 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_SESSION_ID = "default"
FRIENDLY_ERROR_REPLY = "죄송해요, 지금은 요청을 처리할 수 없어요. 잠시 후 다시 시도해 주세요."


class ChatRequest(BaseModel):
    message: str  # 사용자가 입력한 자연어 (예: "차광막 닫아줘")
    session_id: str | None = None  # 생략 시 기본 세션 사용


class ChatResponse(BaseModel):
    reply: str  # 자연어 응답 (예: "1번 온실 차광막을 닫았어요.")
    actions_taken: list[dict] = []
    updated_state: dict = {}  # 온실별 장비 상태 {"1": {...}, "2": {...}, "3": {...}}


def _all_device_states() -> dict:
    return {gid: dict(adapter.state) for gid, adapter in container.iot_by_greenhouse.items()}


@app.get("/health")
def health():
    """서버 살아있는지 확인용."""
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    session_id = req.session_id or DEFAULT_SESSION_ID
    history = container.sessions.get_history(session_id)

    try:
        result = container.chat_agent.handle(req.message, history=history)
    except Exception:
        logger.exception("chat_agent.handle 처리 실패")
        return ChatResponse(
            reply=FRIENDLY_ERROR_REPLY, actions_taken=[], updated_state=_all_device_states()
        )

    container.sessions.append_turn(session_id, req.message, result["reply"])
    return ChatResponse(
        reply=result["reply"],
        actions_taken=result["actions_taken"],
        updated_state=_all_device_states(),
    )


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """마이크 녹음(오디오)을 받아 인식된 텍스트만 돌려준다. 프론트는 이 text 를 /api/chat 으로 다시 보낸다."""
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="빈 오디오예요.")
    try:
        text = container.transcription.transcribe(data, filename=audio.filename or "audio.webm")
    except Exception:
        logger.exception("transcribe 처리 실패")
        raise HTTPException(status_code=502, detail="음성 인식에 실패했어요.")
    return {"text": text}


class AutoModeRequest(BaseModel):
    enabled: bool  # True 면 이 온실은 경고/위험 시 사람 개입 없이 자동으로 조치됨


@app.get("/api/state")
def get_state():
    states = container.greenhouse_service.get_dashboard()
    for s in states:
        s["auto"] = container.alert_service.is_auto_mode(s["id"])
    return {"greenhouses": states}


@app.get("/api/state/{greenhouse_id}")
def get_state_detail(greenhouse_id: int):
    detail = container.greenhouse_service.get_detail(greenhouse_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="온실을 찾을 수 없어요.")
    detail["auto"] = container.alert_service.is_auto_mode(greenhouse_id)
    return detail


@app.post("/api/greenhouses/{greenhouse_id}/auto-mode")
def set_auto_mode(greenhouse_id: int, req: AutoModeRequest):
    """온실별 자동 제어 모드 켜기/끄기. 켜면 경고/위험 시 대시보드 조회 때마다 자동 조치."""
    if not container.alert_service.set_auto_mode(greenhouse_id, req.enabled):
        raise HTTPException(status_code=404, detail="온실을 찾을 수 없어요.")
    return {"greenhouse_id": greenhouse_id, "auto": req.enabled}


@app.get("/api/alerts")
def get_alerts():
    return {"alerts": container.alert_service.list_alerts()}


@app.post("/api/alerts/{alert_id}/action")
def run_alert_action(alert_id: str):
    result = container.alert_service.execute_action(alert_id)
    if result is None:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없어요.")
    return result


@app.post("/api/alerts/{alert_id}/dismiss")
def dismiss_alert(alert_id: str):
    if not container.alert_service.dismiss(alert_id):
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없어요.")
    return {"success": True}


@app.post("/api/reset")
def reset_demo():
    """전체 Mock 상태를 초기값으로 리셋 (리허설/재시연용)."""
    container.reset_all()
    return {"success": True}


@app.post("/api/realtime/session")
def create_realtime_session():
    """실시간 음성 모드용 임시(ephemeral) 키 발급. OPENAI_API_KEY 자체는 절대 응답에 담지 않는다."""
    try:
        return container.realtime_session.create_session()
    except Exception:
        logger.exception("realtime 세션 발급 실패")
        raise HTTPException(status_code=502, detail="음성 세션 발급에 실패했어요.")


class ToolExecuteRequest(BaseModel):
    tool_name: str  # "control_device" | "read_data" | "query_data"
    arguments: dict = {}


@app.post("/api/tools/execute")
def execute_tool(req: ToolExecuteRequest):
    """실시간 음성 세션 중 모델이 요청한 function-call을 브라우저가 대신 실행시키는 브릿지.

    /api/chat 의 ChatAgent와 같은 ToolExecutor 인스턴스를 쓰므로 온실 상태는 텍스트
    채팅·음성·대시보드가 항상 공유한다(음성으로 제어한 결과가 대시보드에도 바로 반영됨).
    """
    try:
        result = container.tool_executor.execute(req.tool_name, req.arguments)
    except Exception:
        # 500 대신 구조화된 실패로 응답 — 프론트가 이걸 function_call_output 으로 모델에
        # 돌려줘서 AI가 "실패했어요"라고 말로 이어갈 수 있게 한다 (/api/chat 의 방침과 동일).
        logger.exception("tool 실행 실패 — tool_name=%r", req.tool_name)
        result = {"ok": False, "reason": "internal_error"}
    return {"result": result}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
