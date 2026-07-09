# 프론트 통합 — 필수 준수사항 (우리가 강조하는 것)

> 현재 프론트는 완성도 좋지만 **백엔드와 미연동 + 자체 목데이터**로 돌고 있음.
> 백엔드에 붙이면서 아래는 **반드시** 지킨다. 나머지 구현/디자인 디테일은 자유.
> 리뷰 상세는 코드 리뷰 참고. 백엔드 계약은 `Docs/SolTalk.postman_collection.json` 으로도 확인 가능.

---

## 1. 디자인 — 모바일 기반 반응형 (필수)

- **모바일 우선(mobile-first).** 폰 화면(약 360~430px)에서 먼저 완벽하게 보이고 동작하게 만든 뒤, 태블릿/데스크톱으로 넓히는 반응형으로.
- **가로 스크롤 금지.** 넓은 요소(차트·표)는 자기 영역 안에서만 스크롤.
- **고령 농가 대상** — 글씨·버튼·터치 영역 크게, 대비 충분히. (작은 아이콘만으로 기능 숨기지 말 것)
- 현재 `.app { max-width: 480px }` 는 모바일 지향이라 유지하되, 그 이상 화면에서도 깨지지 않게 반응형 규칙을 명시적으로.

## 2. 음성 입력(STT) — 동작 방식 (필수)

**"버튼 누르면 말하고, 조용하면 알아서 꺼지는" 형태로 만든다.**

- 🎤 버튼을 누르면 **녹음 시작** — 말하는 동안 계속 녹음(스트리밍처럼 이어서 말하는 경험).
- 녹음 중 **시각 표시** 필수 (버튼 펄스/파형/타이머 등 — 지금 켜져 있다는 걸 보여줄 것).
- **무음이 몇 초(권장 2~3초) 지속되면 자동 종료.** (다시 누르면 수동 종료도 가능하게)
- 종료되면 녹음 오디오를 **`POST /api/transcribe`** 로 업로드 → 받은 `text` 를 입력창에 채움(또는 바로 전송).
- **모델은 백엔드의 gpt-4o-transcribe(한국어).** 브라우저 Web Speech API 아님 — 코드/주석의 옛 Web Speech 흔적 제거.

> 구현 힌트: `MediaRecorder` 로 녹음, WebAudio `AnalyserNode` 로 음량을 모니터링해 무음 감지 → `stop()`.
> 실시간 부분 자막까지는 불필요 — "누르면 말하고 조용하면 꺼진다" 경험이면 충분.

## 3. 백엔드 연동 — 계약 (백엔드가 기준)

**소스 오브 트루스 = 백엔드.** 프론트가 백엔드 계약(필드/타입)에 맞춘다.

- baseURL: `VITE_API_BASE` (기본 `http://localhost:8000`)
- **챗 (필수)**: `POST /api/chat`  `{ message, session_id? }` → `{ reply, actions_taken[], updated_state }`
  - ⚠️ 경로는 **`/api/chat`** — 지금 `api.js` 의 `/chat` 은 404 남.
  - 액션 강조는 **reply 텍스트 정규식 말고 `actions_taken`** 로 판단 (device/action/success 들어있음).
- **STT (필수)**: `POST /api/transcribe` (multipart/form-data, 필드명 **`audio`**) → `{ text }`

## 4. 대시보드/알림 연동 (2순위 — 여유 시)

붙일 거면 아래 엔드포인트 + **데이터 모델 매핑** 주의:

| 항목 | 프론트(현재 목) | 백엔드(실제) |
|---|---|---|
| 온실 id | `"gh-1"` 문자열 | `1` 정수 |
| 사유 | `cause` | `reason` |
| 추천동작 | `recommendedAction` | `recommended_action` |
| 상세 history | `{time,temperature,humidity}` | `{timestamp, humidity}` — **온도 없음** |
| 생산량 | `production{...}` | **엔드포인트 없음** |
| 알림 | `{greenhouseId, severity}` | `{greenhouse_id, level, action}` |

- 엔드포인트: `GET /api/state`, `GET /api/state/{id}`, `GET /api/alerts`, `POST /api/alerts/{id}/action`, `POST /api/alerts/{id}/dismiss`, `POST /api/reset`
- ⚠️ **백엔드에 생산량 API·history 온도값이 없음** → 그 부분은 목 유지하거나 백엔드팀에 요청.

---

## 우선순위 정리
1. ✅ (필수) 챗 `/api/chat` 실연동 + `actions_taken` 활용
2. ✅ (필수) STT — §2 방식대로 (녹음→무음 자동종료→`/api/transcribe`)
3. ✅ (필수) 모바일 반응형 디자인
4. ⏳ (여유) 대시보드/알림 실연동 (위 매핑 주의)

## 사소하지만 챙기면 좋은 것
- `CriticalBanner`: `AudioContext` 를 알림마다 새로 만들지 말고 재사용(누수 방지).
- 챗 에러/로딩 상태 UI (백엔드 꺼졌을 때 안내).
