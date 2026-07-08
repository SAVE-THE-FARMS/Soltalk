"""
SolTalk 백엔드 진입점 (FastAPI).

실행:  backend/ 에서  ->  uv run python app/server.py
문서:  서버 켠 뒤  http://localhost:8000/docs  에서 API 테스트

흐름:  사용자 입력 → [의도파악/LLM] → [Mock IoT 제어·조회] → [자연어 응답]
지금은 뼈대만 있고, 아래 TODO 부분을 학생들이 채운다.
"""

from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# env/ 폴더의 .env 로드  (ANTHROPIC_API_KEY 등)
load_dotenv(Path(__file__).resolve().parent.parent / "env" / ".env")

app = FastAPI(title="SolTalk API")

# React(프론트)에서 호출할 수 있게 CORS 허용 (개발용: 전체 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str  # 사용자가 입력한 자연어 (예: "차광막 닫아줘")


class ChatResponse(BaseModel):
    reply: str  # 자연어 응답 (예: "차광막을 닫았어요.")


@app.get("/health")
def health():
    """서버 살아있는지 확인용."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """
    핵심 엔드포인트.

    TODO(학생): 여기서 app/agent.py 를 호출해서
      1) LLM(OpenAI) 로 의도 파악 (제어/조회 + 장비/동작 추출)
      2) Mock IoT 어댑터로 제어하거나 데이터 조회
      3) 결과를 자연어 문장으로 응답
    지금은 입력을 그대로 되돌려주는 자리만 잡아둠.
    """
    return ChatResponse(reply=f"(아직 미구현) 받은 말: {req.message}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
