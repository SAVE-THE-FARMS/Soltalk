# 프론트-백엔드 연동 설계

> 배경: `todo/FRONTEND_통합_필수.md` 의 필수 요구사항(챗 연동/STT/모바일 반응형) + 여유 항목(대시보드·알림 실연동)을 전부 이번에 반영한다.
> 소스 오브 트루스는 백엔드 — 프론트가 백엔드 계약(필드명/타입)에 맞춘다.

## 범위

1. 챗 연동 (`/api/chat`)
2. STT (`/api/transcribe`)
3. 모바일 반응형 디자인
4. 대시보드/알림 실연동 (`/api/state`, `/api/alerts*`, `/api/reset`)

---

## 1. 챗 연동

- `api.js`: 엔드포인트 `/chat` → `/api/chat`. 요청 body에 `session_id` 추가. 응답에서 `{reply, actions_taken, updated_state}` 전부 받아 호출부에 전달 (지금처럼 `reply` 문자열만 리턴하지 않음).
- **세션 유지**: 첫 로드 시 `crypto.randomUUID()`로 생성한 UUID를 `localStorage`(`soltalk_session_id`)에 저장, 이후 재사용. 브라우저를 닫아도 유지 — 재질문 맥락이 끊기지 않게.
- **액션 강조 로직 교체**: `ChatScreen`의 기존 `ACTION_DONE_PATTERN` 정규식(응답 텍스트에서 "닫았어요" 등 완료형 동사 매칭) 제거. 대신 `actions_taken` 배열에 `success: true` 인 항목이 하나라도 있으면 해당 말풍선을 강조(✅) 표시.

## 2. STT (음성 입력)

- `handleMic()` 스텁을 실제 녹음 흐름으로 교체:
  1. 버튼 클릭 → `getUserMedia({audio:true})` → `MediaRecorder` 시작. 버튼에 펄스 애니메이션 + 경과 시간(타이머) 표시.
  2. `AudioContext` + `AnalyserNode`로 볼륨을 폴링(`requestAnimationFrame`). 볼륨이 임계값 이하로 **2~3초 연속** 지속되면 자동으로 `mediaRecorder.stop()`.
  3. 버튼 재클릭 시 수동 종료도 가능.
  4. 정지되면 수집된 오디오 Blob을 `POST /api/transcribe`(multipart/form-data, 필드명 `audio`)로 전송 → 응답의 `text`를 입력창에 채움 (바로 전송하지는 않음 — 사용자가 확인 후 보내도록).
- 예외 처리: 마이크 권한 거부, `getUserMedia` 미지원 브라우저 → 안내 문구로 대체(크롬 권장).
- 코드/주석에 남아있는 옛 "Web Speech API" 언급 제거.

## 3. 모바일 반응형

- `.app`은 모바일 우선(360~430px 기준)을 그대로 유지하되, 아래처럼 단계적으로 넓힌다:
  - 기본(< 600px): `max-width: 480px` (현재와 동일)
  - `min-width: 600px`: `max-width: 600px`
  - `min-width: 900px`: `max-width: 720px`, 대시보드 그리드(`dashboard__grid`)의 `minmax` 컬럼 폭을 넓혀 카드가 더 여유 있게 배치되도록.
- 가로 스크롤 발생 요소(온실 상세의 SVG 추이 차트 등)는 해당 컨테이너 안에서만 스크롤되도록 `overflow-x` 처리, 페이지 전체는 가로 스크롤 없음.
- 터치 영역/글씨 크기는 기존보다 키움 (버튼 최소 44px 높이 기준).

## 4. 대시보드/알림 실연동

### 데이터 흐름
- `useFarmData` 훅을 실제 API 기반으로 교체:
  - 마운트 시 `GET /api/state` + `GET /api/alerts` 를 함께 호출.
  - 액션 실행/알림 닫기/리셋 **이후에도** 두 엔드포인트를 다시 호출해 최신 상태 반영.
  - **폴링 없음** — 데모 규모(단일 사용자, 3개 온실)에 실시간 폴링은 과함. 화면 진입·액션 시 refetch로 충분.
- production(생산량 위젯)과 dashboard 하단 "처리 이력(HistoryTimeline)"은 백엔드에 대응 API가 없으므로 `mockData.js`의 정적 값을 그대로 유지 (변경 없음).

### 데이터 모델
> (설계 수정: 처음엔 "매핑 레이어 없이 백엔드 필드명 그대로"로 정했으나, 기존 프론트 컴포넌트가 전부
> camelCase(`greenhouseId`, `severity`, `recommendedAction`) 컨벤션이라 snake_case를 그대로 섞으면
> 오히려 일관성이 깨지고 실수하기 쉬움. `useFarmData` 한 곳에서 백엔드 응답 → 프론트 camelCase 형태로
> 얇게 변환하는 어댑터 역할을 하도록 수정. 컴포넌트는 여전히 하나의 일관된 형태만 본다.)

`useFarmData`가 만들어내는 온실 객체 형태:
```js
{
  id: 1,                 // 정수 (백엔드 그대로)
  name: "1번 온실(토마토)",
  status: "warning",
  temperature: 24.0,
  humidity: 82,
  devices: { shade: "open", window: "closed", irrigation: "off" },
  reason: "습도 82%, 임계값 80% 초과",              // 백엔드 detail.reason (구 cause)
  activeAlert: { id: "gh2-humidity", action: { device, action, label }, message } | null,
}
```
알림(notification) 객체 형태:
```js
{ id: "gh2-humidity", level: "warning", greenhouseId: 2, greenhouseName: "2번 온실(딸기)", message, action }
```

- 온실 `id`: 문자열(`"gh-1"`) → 정수(`1`)로 전환. 컴포넌트의 `key`/비교 로직 모두 정수 기준으로 통일.
- `cause` → `reason` (백엔드 detail 응답 필드명을 그대로 씀). `recommendedAction`은 이름은 유지하되 내용은 백엔드 `recommended_action`에서 매핑.
- `severity` → `level` 로 통일 (알림 심각도 필드는 백엔드 용어를 따름 — `AlertBanner`/`CriticalBanner`/`NotificationInbox`/`App.jsx` 전부 이 이름으로 통일).
- 알림 목록(`GET /api/alerts`)에는 `greenhouse_id`만 있고 이름이 없음 → `useFarmData`에서 온실 목록과 조인해 각 알림에 `greenhouseName`을 붙여서 내려준다.
- 온실 상세 화면에서 "바로 조치" 버튼이 정확한 `alert_id`를 알아야 `POST /api/alerts/{id}/action`을 호출할 수 있음 → `useFarmData`가 온실별로 매칭되는 활성 알림을 조인해 `greenhouse.activeAlert = {id, action, message} | null` 형태로 함께 내려준다. `GreenhouseDetail`/`GreenhouseCard`/`CriticalBanner`/`NotificationInbox` 전부 이 조인된 데이터를 사용 (device/action 직접 지정 방식 제거, 항상 `activeAlert.id`로 액션/닫기 호출).
- 추이 차트: 백엔드 `history`가 `{timestamp, humidity}`만 제공 → **온도 라인 제거**, 습도만 표시. 시간 라벨은 `timestamp`(ISO)에서 시:분만 추출해서 표시.

### 데모 컨트롤
- "리셋": `POST /api/reset` 호출 → 성공 시 `useFarmData` 강제 refetch.
- "승격(escalate)" 버튼: **제거**. 백엔드에 대응 API가 없고(상태는 습도값에서 파생되는 값이라 임의로 못 올림), 실연동 원칙(소스 오브 트루스=백엔드)과 맞지 않음.

### 컴포넌트별 영향
| 파일 | 변경 |
|---|---|
| `lib/useFarmData.js` | 전체 재작성 — API 호출 + 조인 로직 |
| `lib/mockData.js` | 온실 목록(`INITIAL_GREENHOUSES`) 제거, `INITIAL_PRODUCTION`/`INITIAL_HISTORY_LOG`만 유지 |
| `lib/labels.js` | 필드명 변경에 맞춰 점검 (device/action 라벨 자체는 백엔드와 이미 일치) |
| `api.js` | `/api/chat`, `/api/transcribe`, `/api/state`, `/api/state/{id}`, `/api/alerts`, `/api/alerts/{id}/action`, `/api/alerts/{id}/dismiss`, `/api/reset` 클라이언트 함수 추가 |
| `App.jsx` | `dismissedIds` 로컬 상태 제거(백엔드가 활성 알림의 소스 오브 트루스), `handleEscalate`/승격 버튼 제거 |
| `components/ChatScreen.jsx` | 엔드포인트/세션/액션 강조 로직, STT 녹음 흐름 |
| `components/Dashboard/*`, `components/GreenhouseDetail.jsx`, `components/NotificationCenter/*` | 필드명 전환(`reason`, `recommended_action`, `activeAlert`), 온도 차트 라인 제거 |
| `components/NotificationCenter/CriticalBanner.jsx` | (사소하지만 챙기는 항목) `playBeep()`이 알림마다 `new AudioContext()`를 새로 만드는 걸 컴포넌트 레벨에서 하나 생성해 재사용하도록 수정 — 문서에서 명시적으로 지적한 누수 |

---

## 테스트 방침
- 프론트는 이 프로젝트에 테스트 러너가 없음(Vite + React, 테스트 셋업 없음) — 새로 테스트 프레임워크를 들이는 건 스코프 밖으로 판단. 대신 각 단계 구현 후 `npm run dev`로 실제 브라우저에서 동작 확인(백엔드도 같이 켜서 end-to-end로).
- 백엔드 쪽은 기존 계약을 변경하지 않으므로 추가 백엔드 테스트는 불필요.

## 리스크 / 자체 검토
- **STT 브라우저 호환성**: `MediaRecorder`/`AnalyserNode`는 최신 크롬 기준으로 설계. 사파리 등에서 mimeType 이슈 가능성 — 크롬 권장 안내로 대응(문서에도 이미 명시됨).
- **알림-온실 조인**: 알림 스키마가 향후 온실당 여러 알림 타입을 지원하게 되면(`gh{id}-humidity` 외 타입 추가) 조인 로직이 "온실당 최대 1개 알림" 가정을 깨뜨릴 수 있음 — 현재 백엔드가 그 가정을 지키고 있어 문제 없지만, 확장 시 재검토 필요.
- **세션 UUID 브라우저 미지원**: `crypto.randomUUID()`는 매우 최신 API — HTTPS/최신 브라우저 기준으로만 보장됨. 로컬 데모(localhost)는 문제 없음.
