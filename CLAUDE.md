# CLAUDE.md

이 파일은 Claude Code가 이 repo에서 작업할 때 참고하는 프로젝트 컨텍스트다.
전체 기획/결정 배경은 `Docs/2026.07.08_01_[Ref]_SolTalk_HANDOFF.md` 참고.

## 프로젝트

**SolTalk** — 자연어(음성/텍스트) 명령으로 스마트팜(온실) 장비를 제어하고 현황을 조회하는 AI 에이전트.
주체: (주)세이브더팜즈(SAVE THE FARMS).

흐름: `자연어 입력 → 의도파악(제어/조회 분류 + 개체추출) → IoT 제어/데이터 조회 → 자연어 응답`

- 의도파악·응답생성: **OpenAI(LLM)** 로 처리
- 제어 대상 장비(가상): 차광막(shade), 창문(window), 관수(irrigation)
- 명령 예시: "차광막 닫아줘", "창문 열어", "오늘 생산량 알려줘", "지금 온도 몇 도야?"

## 1차 구현 범위

기획 프로세스 Step 1 → 2 → 3-A/3-B → 4 → 5:
1. 자연어 명령/질문 입력 (챗봇 UI, STT는 선택)
2. 의도 파악 — 제어/조회 분류 + 개체 추출 (LLM)
3-A. (제어) IoT 장비에 명령 전달 — **Mock API** (가상 장비 상태 변경)
3-B. (조회) 센서/생산 데이터 조회 — **Mock 데이터**
4. 결과를 자연어 문장으로 변환 (LLM)
5. 사용자에게 전달

## 핵심 아키텍처 원칙

**IoT 연동을 인터페이스로 추상화**해서 Mock ↔ 실장비를 갈아끼운다.

- 공개 repo에는 `IoTAdapter` **인터페이스 + `MockIoTAdapter`(가상 상태) 구현만** 포함
- 실장비/솔캐스트 구현은 회사가 **같은 인터페이스로 비공개 repo에서 주입**
- 학생 코드는 실장비·솔캐스트를 몰라도 완결 동작해야 함
- NLU 출력 형태: `{ intent: control|query, device, action }`
- 오작동 대비 확인 피드백(상태 반환)을 설계에 반영

## 절대 하지 말 것 (public repo — 히스토리 영구 잔존)

1. **솔캐스트(Soilcast) 코드/데이터 일체 포함 금지** — 2차 과제, 별도 비공개 repo. 엔진·토양 데이터 전부.
2. **실제 크리덴셜 커밋 금지** — IoT 벤더 API 키, 온실 접속 정보 → `.env` + `.gitignore`. 배포는 환경변수.
3. **실제 농가/생산 데이터 커밋 금지** — 시연은 더미 데이터로. 실데이터 섞지 말 것.

> 공개 OK: 음성/챗봇 UI, 의도분류·개체추출 로직, Mock IoT 어댑터, 응답 생성 — 전부.

## 확정 사항

- repo 이름: `soltalk` / **공개(public)** — 학생 2명 포트폴리오용
- 소유권: owner = 회사 계정, 학생은 collaborator
- **구현 기간: 이틀** (스코프는 이 안에 end-to-end 데모 가능하게 유지)

### 기술 스택 (확정)

- **프론트: React** — 챗봇 UI, STT(브라우저 **Web Speech API**)로 음성 입력 처리
- **백엔드: Python FastAPI** — LLM 호출(function calling 에이전트) + `IoTAdapter`/`MockIoTAdapter`
- **LLM: OpenAI** — OpenAI **Python SDK**, **function calling(tools)** 방식
  - 모델에게 `control_device` / `read_data` tool 제공 → 모델이 Mock 어댑터 호출
  - (프롬프트로 intent JSON 파싱·분기하는 방식보다 견고 + 복합 명령 처리 용이)
- **채널: 웹** (카카오톡 연동은 확장 과제로 문서화)

> Mock 대상은 **IoT/센서 raw data 하나뿐**. 챗봇(LLM)·STT는 실제 연동.

## 미확정 (작업 전 사용자 확인 필요)

- STT 업그레이드 여부 — 1차는 Web Speech, 시간 남으면 서버 STT(Whisper 등)
- 라이선스 문구

## 문서 규칙

- `Docs/` 파일명 컨벤션: `YYYY.MM.DD_NN_[태그]_제목.md` (예: `[Ref]` 참고문서)
