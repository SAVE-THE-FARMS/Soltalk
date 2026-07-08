"""
SolTalk 백엔드 진입점 (FastAPI).

실행:  backend/ 에서  ->  uv run python -m app.server
문서:  서버 켠 뒤  http://localhost:8000/docs  에서 API 테스트

흐름:  사용자 입력 → [의도파악/LLM] → [Mock IoT 제어·조회] → [자연어 응답]
"""

import logging
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import agent, alerts_service, greenhouse_service, session_service, state
from .state import iot

# env/ 폴더의 .env 로드  (OPENAI_API_KEY 등)
load_dotenv(Path(__file__).resolve().parent.parent / "env" / ".env")

logger = logging.getLogger(__name__)

app = FastAPI(title="SolTalk API")

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
    reply: str  # 자연어 응답 (예: "차광막을 닫았어요.")
    actions_taken: list[dict] = []
    updated_state: dict = {}


@app.get("/health")
def health():
    """서버 살아있는지 확인용."""
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    session_id = req.session_id or DEFAULT_SESSION_ID
    history = session_service.get_history(session_id)

    try:
        result = agent.handle_message(req.message, history=history)
    except Exception:
        logger.exception("agent.handle_message 처리 실패")
        return ChatResponse(reply=FRIENDLY_ERROR_REPLY, actions_taken=[], updated_state=dict(iot.state))

    session_service.append_turn(session_id, req.message, result["reply"])
    return ChatResponse(
        reply=result["reply"],
        actions_taken=result["actions_taken"],
        updated_state=dict(iot.state),
    )


@app.get("/api/state")
def get_state():
    return {"greenhouses": greenhouse_service.get_dashboard(state.IOT_BY_GREENHOUSE)}


@app.get("/api/state/{greenhouse_id}")
def get_state_detail(greenhouse_id: int):
    detail = greenhouse_service.get_detail(state.IOT_BY_GREENHOUSE, greenhouse_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="온실을 찾을 수 없어요.")
    return detail


@app.get("/api/alerts")
def get_alerts():
    return {"alerts": alerts_service.list_alerts(state.IOT_BY_GREENHOUSE)}


@app.post("/api/alerts/{alert_id}/action")
def run_alert_action(alert_id: str):
    result = alerts_service.execute_action(alert_id, state.IOT_BY_GREENHOUSE)
    if result is None:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없어요.")
    return result


@app.post("/api/alerts/{alert_id}/dismiss")
def dismiss_alert(alert_id: str):
    if not alerts_service.dismiss(alert_id, state.IOT_BY_GREENHOUSE):
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없어요.")
    return {"success": True}


@app.post("/api/reset")
def reset_demo():
    """전체 Mock 상태를 초기값으로 리셋 (리허설/재시연용)."""
    state.reset_all()
    session_service.reset()
    alerts_service.reset()
    return {"success": True}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
