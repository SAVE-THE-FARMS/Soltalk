# 음성 인식 기능 — 백엔드 요구사항 (Realtime API 연동, 옵션 B)

> 채택 방식 변경: 브라우저 Web Speech API(옵션 A) → **OpenAI Realtime API 연동(옵션 B)**
> ⚠️ Claude API에는 Realtime API가 없으므로, 음성 대화 전용으로 **OpenAI Realtime API를 별도 도입**하는 구조입니다. 기존 Claude 기반 텍스트 채팅(`/api/chat`)은 그대로 유지하고, 음성 모드만 별도 파이프라인으로 추가합니다.

---

## 1. 아키텍처 개요

```
[브라우저]
   ├─ 텍스트 채팅 → 기존 /api/chat → Claude API (기존과 동일)
   │
   └─ 음성 모드 → ephemeral key 발급 요청 → 우리 백엔드
                     ↓
              OpenAI에 세션 생성 요청 (서버가 보유한 OPENAI_API_KEY 사용)
                     ↓
              ephemeral key를 브라우저에 전달
                     ↓
       [브라우저] ←──WebRTC 실시간 오디오──→ [OpenAI Realtime API]
                     ↓ (모델이 장비제어/조회가 필요하다고 판단하면)
              function-call 이벤트를 브라우저로 전달
                     ↓
       [브라우저] → 우리 백엔드 /api/tools/execute 호출 (실제 실행)
                     ↓
       [브라우저] → 실행 결과를 다시 OpenAI 세션에 주입 → 음성 응답 생성
```

**핵심 포인트**: 오디오 스트림 자체는 브라우저와 OpenAI가 **직접** WebRTC로 통신합니다(우리 서버를 거치지 않음 — 지연시간과 서버 부담을 줄이기 위한 OpenAI 권장 방식). 우리 백엔드는 ① 임시 인증키 발급, ② 실제 장비 제어/조회 실행 두 가지만 담당합니다.

---

## 2. 신규 API

### 2.1 Realtime 세션용 임시 키 발급

**`POST /api/realtime/session`**

| 항목 | 내용 |
|---|---|
| 설명 | 서버가 보유한 `OPENAI_API_KEY`로 OpenAI에 세션 생성을 요청하고, 클라이언트에 전달할 임시(ephemeral) 키를 발급 |
| Request Body | 없음 (또는 `{ "session_id": "string" }`) |
| Response Body | `{ "client_secret": "string", "expires_at": "..." }` |
| 비고 | 임시 키는 유효시간이 짧음(대략 1분 내외) — 프론트에서 연결 시점에 매번 새로 요청 |
| 보안 | **`OPENAI_API_KEY`는 절대 클라이언트에 노출하지 않음.** 이 키는 서버 환경변수에만 저장 |

### 2.2 Tool 실행 브릿지

**`POST /api/tools/execute`**

| 항목 | 내용 |
|---|---|
| 설명 | Realtime 세션 중 모델이 function-call을 요청하면, 브라우저가 이 엔드포인트로 실행을 위임함. 기존 `tools.py`의 `control_device` / `query_data` 로직을 **그대로 재사용** |
| Request Body | `{ "tool_name": "control_device", "arguments": { "greenhouse_id": 2, "device": "window", "action": "open" } }` |
| Response Body | `{ "result": { ... } }` (기존 tool 실행 결과와 동일 포맷) |
| 비고 | 기존 `/api/chat`에서 쓰던 tool 실행 함수를 공용 모듈로 분리해서 여기서도 호출 (코드 중복 방지) |

---

## 3. Tool 스키마 이중 관리 이슈 (중요)

- Claude의 tool 스키마(Anthropic 형식)와 OpenAI Realtime API의 tool 스키마(OpenAI 형식)는 **형식이 다름** — 같은 기능(`control_device`, `query_data`)을 **두 가지 스키마로 각각 정의**해야 함
- **실행 로직(farm_state를 실제로 바꾸는 함수)은 공용으로 하나만 두고**, 스키마 정의 파일만 `claude_tools_schema.py` / `realtime_tools_schema.py`로 분리 관리 추천
- 두 스키마가 서로 어긋나면(파라미터 이름 등) 한쪽만 오작동할 수 있으므로, 스키마 변경 시 양쪽 다 반영하는 체크리스트 필요

---

## 4. 환경변수 / 키 관리

```
ANTHROPIC_API_KEY=...   (기존 텍스트 채팅용)
OPENAI_API_KEY=...      (신규, Realtime 세션 발급 서버측 전용)
```

- 두 개의 서로 다른 공급자 키를 관리해야 함 — `.env` 및 배포 환경변수에 둘 다 등록 필요
- OpenAI 계정 및 Realtime API 사용 권한(결제수단 등록 여부) 사전 확인 필요

---

## 5. 세션 관리

- ephemeral key는 짧은 시간 후 만료 → 프론트에서 연결 시도마다 `/api/realtime/session`을 새로 호출하는 구조로 설계
- 음성 세션과 텍스트 채팅 세션(`session_id`)은 별도로 관리하되, **온실 상태(farm_state)는 공유** — 음성으로 제어한 결과가 대시보드/텍스트 채팅에도 즉시 반영되어야 함

---

## 6. 리스크

| 리스크 | 설명 |
|---|---|
| 이중 공급자 관리 | Anthropic + OpenAI 두 회사 API를 동시에 운영 → 키/과금/장애 대응이 두 배 |
| 스키마 불일치 | 두 tool 스키마를 따로 관리하다 한쪽만 업데이트하면 기능 불일치 발생 |
| 실시간 오디오 안정성 | 발표장 네트워크 환경에서 WebRTC 연결 실패/지연 가능성 (Web Speech API 대비 실패 지점이 늘어남) |
| 개발 일정 | 2일 데모 기준으로 세션 발급 + WebRTC 연결 + function-call 브릿지까지 한 번에 안정화하기엔 시간이 빠듯함 |

**권장**: 음성 모드가 불안정할 경우를 대비해, **텍스트 채팅(Claude)은 항상 정상 동작하는 백업 경로로 유지** — 데모 중 음성이 실패해도 텍스트로 즉시 전환 가능하게.

---

## 7. 체크리스트 (백엔드)

- [x] OpenAI 계정/API 키 발급 및 결제수단 등록 — 기존 `OPENAI_API_KEY`로 실제 발급 성공 확인
- [x] `POST /api/realtime/session` 구현 (ephemeral key 발급) — `RealtimeSessionService`
- [x] `POST /api/tools/execute` 구현 (기존 tool 실행 로직 재사용) — `ToolExecutor` 공용화
- [x] Realtime API용 tool 스키마 별도 작성 — 프론트 `frontend/src/realtime/realtimeTools.js`에 이미 있음
- [x] farm_state 공유 구조 확인 (음성 제어 → 대시보드 즉시 반영) — `/api/tools/execute`로 제어 후 `/api/state`에 즉시 반영됨을 확인
- [x] 환경변수 관리 — **정정**: 실제 구현은 텍스트 챗봇도 OpenAI(Claude 아님)를 쓰므로 `OPENAI_API_KEY` 하나만 필요. 문서 상단 2절의 "두 공급자 관리" 리스크는 이 프로젝트에는 해당 없음.
- [x] 텍스트 채팅 백업 경로 정상 동작 재확인 — 기존 백엔드 테스트 92건 모두 통과 유지
