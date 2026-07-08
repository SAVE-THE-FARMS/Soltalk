# 백엔드 TODO (개발 A)

> 목표: `POST /chat` 에 자연어를 넣으면 자연어로 답이 나온다.
> 스택: Python + FastAPI + OpenAI SDK, 패키지 관리는 `uv`.
> 공통 규칙/접점 계약: [README.md](./README.md) 먼저 읽기.

## 실행법
```bash
cd backend
cp env/.env.example env/.env    # OPENAI_API_KEY 채우기 (커밋 금지!)
uv run python -m app.server     # http://localhost:8000/docs
```

## 채울 파일 순서
`iot/mock.py` → `agent.py` → `server.py` 연결.
(Mock 부터 하면 LLM 없이도 제어/조회를 테스트할 수 있다.)

---

## 1. `app/iot/mock.py` — 가상 장비 제어/조회
> `IoTAdapter` 인터페이스(`iot/base.py`)를 구현. 실장비 없이 메모리 상태만 바꾼다.

- [ ] `control(device, action)`: `self.state[device]` 를 `action` 으로 바꾸고 결과 상태 반환
- [ ] `read(target)`: `app/data/mock_data.py` 에서 `target` 값 찾아 반환
- [ ] 없는 device / 이상한 action 처리 — 오작동 대비 확인 피드백 (예: `{"ok": false, "reason": ...}`)
- [ ] 반환 형태(dict 스키마)를 정해서 주석/문서에 남기기

## 2. `app/agent.py` — LLM function calling (핵심)
> 모델에게 도구를 주고, 모델이 알아서 어댑터를 호출하게 한다. (프롬프트 JSON 파싱보다 견고 + 복합 명령 처리)

- [ ] openai 클라이언트 생성 (키는 `env/.env` 에서 자동 로드됨)
  - 모델: **`gpt-5.4-mini`** (function calling 지원, 저비용/저지연)
- [ ] tool(function) 2개 정의:
  - `control_device(device, action)` — device: shade|window|irrigation
  - `read_data(target)` — target: temperature|humidity|production ...
- [ ] tool 호출 루프: 모델이 tool 호출 → `MockIoTAdapter` 실행 → 결과를 모델에 돌려줌 → 최종 자연어 응답
- [ ] 시스템 프롬프트: 고령 농가 대상, 짧고 친절한 말투 (기획팀 가이드 반영)
- [ ] `handle_message(message)` 가 최종 응답 문자열 반환

> OpenAI 모델명 / SDK 사용법 / function calling 형식은 **최신 레퍼런스대로**. 막히면 Claude Code 에게 물어보기.

## 3. `app/server.py` — 연결
- [ ] `/chat` 엔드포인트에서 `agent.handle_message(req.message)` 호출하도록 교체
  (지금은 입력을 그대로 되돌려주는 스텁)

## 4. 확인
- [ ] `/docs` 에서 테스트:
  - 제어: "차광막 닫아줘", "창문 열어", "관수 틀어줘"
  - 조회: "지금 온도 몇 도야?", "오늘 생산량 알려줘"
- [ ] 복합 명령도: "창문 열고 온도도 알려줘"

## 절대 하지 말 것
- `.env` / API 키 커밋 금지
- 솔캐스트(Soilcast) 관련 코드·데이터 일체 금지
- 실제 농가 데이터 금지 (mock 만)
