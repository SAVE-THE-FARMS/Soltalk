# 🌱 SolTalk

> 자연어(음성·텍스트)로 스마트팜(온실) 장비를 제어하고 현황을 조회하는 AI 에이전트.
> 주체: (주)세이브더팜즈(SAVE THE FARMS)

**"차광막 닫아줘", "지금 온도 몇 도야?"** 한마디면 됩니다.
SolTalk이 말을 알아듣고(의도 파악) → 장비를 제어하거나 데이터를 조회한 뒤 → 자연어로 답합니다.

```
자연어 입력 → 의도 파악(제어/조회 분류 + 개체 추출) → IoT 제어·데이터 조회 → 자연어 응답
```

---

## ✨ 주요 기능

- 💬 **챗봇 UI** — 텍스트 입력 + 🎤 음성 입력(브라우저 STT)
- 🧠 **의도 파악** — LLM이 제어/조회를 분류하고 장비·동작을 추출 (function calling)
- 🎛 **장비 제어** — 차광막(shade) / 창문(window) / 관수(irrigation)
- 📊 **데이터 조회** — 온도 / 습도 / 생산량
- 🔌 **IoT 추상화** — `IoTAdapter` 인터페이스로 Mock ↔ 실장비 교체 가능

## 🏗 아키텍처

```
[React 챗 UI] ──POST /chat──▶ [FastAPI]
   (STT: Web Speech)               │
                                   ▼
                          [LLM 에이전트 / OpenAI]
                          function calling: control_device · read_data
                                   │
                                   ▼
                          [IoTAdapter] ── 인터페이스
                          [MockIoTAdapter] ← 이번 범위 (가상 상태)
                          [RealIoTAdapter] ← 추후 비공개 repo에서 주입
```

- IoT 연동은 **인터페이스로 추상화** → 공개 repo에는 인터페이스 + Mock 구현만 포함
- 실장비 구현은 같은 인터페이스로 나중에 주입 → 앱은 실장비를 몰라도 완결 동작

## 🧰 기술 스택

| 구분 | 사용 |
|---|---|
| 프론트 | React + Vite, Web Speech API(STT) |
| 백엔드 | Python FastAPI, uv |
| LLM | OpenAI `gpt-5.4-mini` (function calling) |
| IoT | Mock (가상 장비 상태) |

## 📁 프로젝트 구조

```
Soltalk/
├─ backend/          # FastAPI + uv
│  └─ app/
│     ├─ server.py       # 진입점, /chat · /health
│     ├─ agent.py        # LLM function calling
│     ├─ iot/            # IoTAdapter 인터페이스 + MockIoTAdapter
│     └─ data/           # mock 센서/생산 데이터
├─ frontend/         # React + Vite 챗 UI
├─ Docs/             # 핸드오프 · 실행계획
├─ todo/             # 파트별 개발 체크리스트 + SETUP
└─ CLAUDE.md         # 프로젝트 컨텍스트 / 규칙
```

## 🚀 실행

> 환경 세팅(도구 설치 포함) 상세: [`todo/SETUP.md`](./todo/SETUP.md)

**백엔드**
```bash
cd backend
cp env/.env.example env/.env    # OPENAI_API_KEY 설정
uv sync
uv run python app/server.py     # http://localhost:8000/docs
```

**프론트**
```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

## 🗣 명령 예시

| 입력 | 종류 |
|---|---|
| 차광막 닫아줘 | 제어 |
| 창문 열어 | 제어 |
| 관수 틀어줘 | 제어 |
| 지금 온도 몇 도야? | 조회 |
| 오늘 생산량 알려줘 | 조회 |
| 창문 열고 온도도 알려줘 | 복합 |

## 📚 문서

- [`todo/README.md`](./todo/README.md) — 개발 시작점(역할 분담·접점 계약·일정)
- [`todo/SETUP.md`](./todo/SETUP.md) — 개발 환경 셋업
- [`Docs/`](./Docs) — 핸드오프 / 실행계획

## ⚠️ 참고

- 이 repo에는 **Mock IoT** 만 포함됩니다. 실장비/솔캐스트 연동은 범위 밖.
- API 키·실데이터는 커밋하지 않습니다 (`.env` 는 `.gitignore` 처리).
- 자세한 규칙은 [`CLAUDE.md`](./CLAUDE.md) 참고.
