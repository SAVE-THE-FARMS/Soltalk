# SolTalk 개발 TODO (인덱스)

> 이틀 안에 **자연어 → 의도파악(OpenAI) → Mock IoT 제어·조회 → 자연어 응답** end-to-end 데모 완성.
> 배경/결정: `../Docs/2026.07.08_01_[Ref]_SolTalk_HANDOFF.md` · 프로젝트 규칙: `../CLAUDE.md`

## 파트별 TODO 문서
- 🛠 [BACKEND.md](./BACKEND.md) — 개발 A (FastAPI, OpenAI function calling, Mock IoT)
- 💬 [FRONTEND.md](./FRONTEND.md) — 개발 B (React 챗 UI, 음성 입력)
- 📋 [PLANNING.md](./PLANNING.md) — 기획 (데모 시나리오, mock 데이터, README)

---

## 역할 분담

| 사람 | 트랙 | 주로 만지는 곳 |
|---|---|---|
| 기획 1명 | 기획·데모 | `PLANNING.md` |
| 개발 A | 백엔드 | `backend/app/` |
| 개발 B | 프론트 | `frontend/src/` |
| +1 (미정) | 합류 대기 | 도착하면 막히는 트랙 투입 (우선순위: 프론트 UI 다듬기 → 데모 테스트 → 백엔드 튜닝) |

> **원칙: 프론트/백엔드는 서로 파일을 안 건드린다.** 접점은 아래 `/chat` API 하나뿐.
> 이 계약만 먼저 맞춰두면 둘이 동시에 따로 개발 가능.

## 접점 계약 (프론트 ↔ 백엔드) — 제일 먼저 합의
- 요청: `POST /chat`  body `{ "message": "차광막 닫아줘" }`
- 응답: `{ "reply": "차광막을 닫았어요." }`
- (이미 `backend/app/server.py` 와 `frontend/src/api.js` 에 이 형태로 잡혀 있음)

---

## 공통 준비 (제일 먼저, 다같이)
- [ ] 각자 repo 받기 (git clone) — 깃 처음이면 멘토가 5분 설명
- [ ] `ANTHROPIC_API_KEY` 발급·공유 (**커밋 금지!** 각자 로컬 `.env` 에만)
- [ ] 백엔드 실행 확인: `cd backend` → `cp env/.env.example env/.env` → `uv run python app/server.py` → http://localhost:8000/docs
- [ ] 프론트 실행 확인: `cd frontend` → `npm install` → `npm run dev` → http://localhost:5173
- [ ] 위 "접점 계약" 팀 전체 합의

## 일정 (이틀)
- **Day 1**: 공통 준비 → 각자 트랙 뼈대 채우기 (백엔드 `/chat` 혼자 동작, 프론트 화면 뜸)
- **Day 2**: 통합(프론트↔백엔드) → 음성 붙이기 → 데모 리허설 → (여유되면 배포)

## 통합 (Day 2, 다같이)
- [ ] 프론트 ↔ 백엔드 실제로 붙여서 end-to-end 동작
- [ ] 데모 시나리오 5~6개 전부 통과 확인
- [ ] (여유되면) 배포 — 데모 URL
- [ ] (여유되면) STT 업그레이드(서버 STT), 오류 응답 다듬기

> 막히면 혼자 오래 붙잡지 말고 Claude Code / 팀에 바로 질문.
