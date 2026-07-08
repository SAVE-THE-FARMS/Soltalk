# SolTalk 프론트 UI — 스마트팜 대시보드/알림 설계

> 참고 문서: `Docs/smartfarm_ui_elements.md` (1차 UI 요소 문서)
> 범위: 문서의 2.1(채팅) ~ 2.5(공통) 전체

## 배경 / 제약

- 현재 백엔드는 `/chat`, `/health` 두 엔드포인트뿐이고 mock 데이터도 단일 온실(`temperature`/`humidity`/`production` 값 하나씩)만 존재한다.
- `smartfarm_ui_elements.md`가 요구하는 다중 온실 대시보드/알림/이력 타임라인은 백엔드에 대응하는 API가 없다.
- 결정: **이번 작업은 프론트 전용**. 대시보드/상세/알림 화면은 프론트 내부 목업 데이터(`lib/mockData.js` + `lib/useFarmData.js`)로 동작하며, 챗봇 화면(`/chat` 호출)과는 데이터가 완전히 분리된다. 추후 백엔드 API가 생기면 `useFarmData` 내부만 교체하면 되도록 훅으로 경계를 둔다.
- 새 런타임 의존성(라우터, 차트 라이브러리, 아이콘 라이브러리, 상태관리 라이브러리)은 추가하지 않는다 — React 상태 + 이모지 아이콘 + 직접 그린 SVG로 해결한다.
- 자동화 테스트 프레임워크가 없는 2일 스코프 프로젝트이므로, 이번 작업의 검증은 `npm run dev` 수동 시나리오 체크로 한다.

## 화면 전환

- 새 라이브러리 없이 `App.jsx`의 `useState`로 탭 전환(`"chat" | "dashboard"`)과 온실 상세 진입(`selectedGreenhouseId`)을 관리한다.
- 상세 화면은 별도 라우트가 아니라 대시보드 탭 내부 상태(`selectedGreenhouseId !== null`)로 표현하고, "뒤로가기" 버튼은 `selectedGreenhouseId`를 `null`로 되돌린다. 브라우저 URL/뒤로가기 버튼은 바뀌지 않는다.

## 파일 구조

```
frontend/src/
  App.jsx                    # 탭 상태 + 전역 CriticalBanner 렌더
  api.js                     # (기존, 변경 없음) 백엔드 /chat 호출
  lib/
    mockData.js              # 초기 목업: 온실 3개, 생산량, 이력, 파생 알림
    useFarmData.js            # 목업 상태 + 액션(controlDevice, resetDemo, escalateDemo)
  components/
    TopNav.jsx                 # 챗봇 ↔ 대시보드 탭 전환 + warning 배지
    ChatScreen.jsx              # 기존 App.jsx 채팅 로직 이전 + 2.1 개선
    Dashboard/
      AlertBanner.jsx           # 상단 알림 영역
      GreenhouseCard.jsx        # 온실 요약 카드
      ProductionWidget.jsx      # 생산량 요약 위젯
      HistoryTimeline.jsx       # 오늘 처리 이력 리스트
      DemoControls.jsx          # 리셋 + "경고→위험 승격" 데모 버튼
    GreenhouseDetail.jsx         # 온실 상세 화면
    NotificationCenter/
      CriticalBanner.jsx         # 강제 노출 critical 배너
      NotificationInbox.jsx      # warning 알림함
    ui/
      StatusBadge.jsx            # 신호등 배지
      DeviceIcon.jsx             # 차광막/창문/관수 상태 아이콘
  styles.css                  # 섹션 주석으로 구획하며 확장 (파일 분리 안 함)
```

## 데이터 모델 (`lib/mockData.js`)

```js
greenhouses: [
  {
    id: string,
    name: string,
    status: "normal" | "warning" | "critical",
    temperature: number,
    humidity: number,
    devices: {
      shade: "open" | "closed" | "partial",
      window: "open" | "closed" | "partial",
      irrigation: "on" | "off",
    },
    cause: string | null,               // warning/critical일 때만 원인 문구
    recommendedAction: { label: string, device: string, action: string } | null,
    history: Array<{ time: string, temperature: number, humidity: number }>,
  },
  // 3개: normal 1, warning 1, critical 1
]

production: { today: number, week: number, unit: string, diffPct: number, direction: "up" | "down" }

historyLog: Array<{ time: string, type: "auto" | "manual", text: string }>
```

`notifications`는 별도 저장하지 않고 `greenhouses`의 `status`에서 매번 파생한다(warning/critical 온실마다 1개).

## `useFarmData()` 훅

초기값을 `useState`로 감싸고 다음 액션을 제공한다:

- `controlDevice(greenhouseId, device, action)` — 해당 온실의 `devices[device]`를 갱신하고 `historyLog`에 `type: "manual"` 항목을 추가한다. 각 온실은 `recommendedAction`을 최대 1개만 가지므로, 호출된 `(device, action)`이 그 온실의 `recommendedAction`과 일치하면 `status`를 한 단계 완화한다(`critical→warning`, `warning→normal`). 일치하지 않으면(장비 상태만 바뀌고) `status`는 그대로 둔다.
- `resetDemo()` — 모든 상태를 초기 목업 값으로 되돌린다.
- `escalateDemo()` — `status === "warning"`인 온실 중 하나를 `critical`로 승격한다(대상이 없으면 아무 동작 안 함).

## 화면별 동작

### 3.1 채팅 (`ChatScreen.jsx`)
- 기존 `App.jsx`의 상태/로직(`messages`, `input`, `handleSend`, `handleMic`)을 그대로 이전한다.
- 전송 후 응답 대기 중에는 `{role: "bot", pending: true}` 같은 임시 메시지로 "..." 로딩 말풍선을 보여주고, 응답 도착 시 교체한다.
- AI 응답 텍스트에 "열었어요"/"닫았어요"/"틀었어요"/"껐어요" 등 완료형 동사가 포함되면 일반 말풍선 대신 연한 배경의 "✅ 액션 카드"로 렌더링한다. **이건 프론트 단순 텍스트 패턴 매칭이며 실제 NLU 결과가 아니라는 점을 코드 주석으로 남긴다.**
- `sendMessage()` 호출이 실패(reject)하면 `⚠️ ${e.message}` 대신 "서버에 연결할 수 없어요. 잠시 후 다시 시도해주세요." 문구로 대체한다.

### 3.2 대시보드
- `AlertBanner`: `notifications`(파생값)가 있으면 critical(빨강)/warning(노랑) 카드를 심각도순으로 나열하고 클릭 시 해당 온실 상세로 이동. 없으면 "모든 온실 정상입니다 ✅" 한 줄만 표시.
- `GreenhouseCard`: 온실명, `StatusBadge`, 온도/습도, `DeviceIcon` 3종. 정렬은 critical → warning → normal 순. `status === "normal"`인 카드는 압축된(컴팩트) 스타일로 렌더링.
- `ProductionWidget`: `production.today`/`production.week` + `direction`에 따라 ▲(초록)/▼(빨강) 화살표와 `diffPct` 표시.
- `HistoryTimeline`: `historyLog`를 시간순으로 나열하고 `type`에 따라 다른 아이콘(예: 🤖 auto, 🖐️ manual) 표시.
- `DemoControls`: 우측 상단 눈에 띄지 않는 위치에 작은 "리셋" 버튼과 "데모: 경고→위험" 버튼을 함께 배치.

### 3.3 온실 상세 (`GreenhouseDetail.jsx`)
- 상단: `StatusBadge` + `cause` 한 줄.
- 중단: `recommendedAction`이 있으면 버튼(예: `[창문 열기]`)으로 렌더링, 클릭 시 `controlDevice` 호출 → 성공 토스트 표시.
- 하단: `history` 배열로 최근 온도/습도 추이를 직접 그린 SVG 라인 차트로 시각화(외부 차트 라이브러리 없음).
- "뒤로가기" 버튼 → `selectedGreenhouseId`를 `null`로 설정해 대시보드로 복귀.

### 3.4 알림 (`NotificationCenter`)
- `CriticalBanner`: critical 온실이 하나라도 있으면 화면 상단에 강제 노출. 내장 원터치 액션 버튼(해당 온실의 `recommendedAction` 재사용), 닫기(dismiss) 가능. Web Audio API `OscillatorNode`로 짧은 비프음을 재생하되, 브라우저 자동재생 정책 때문에 사용자가 이미 한 번 상호작용(메시지 전송, 버튼 클릭 등)한 이후에만 재생을 시도한다.
- warning은 `TopNav`의 배지 카운트만 증가시키고, 배지 클릭 시 `NotificationInbox`(리스트 + 항목별 액션/닫기 버튼)를 연다.
- `escalateDemo()` 실행으로 warning→critical 전환 시 배너 등장에 CSS transition(색상/높이)을 적용해 승격 연출을 만든다.

## 스타일 / 공통 컴포넌트 (2.5)

- `:root`에 CSS 커스텀 프로퍼티로 색상 토큰 정의: `--color-critical`(빨강) / `--color-warning`(노랑) / `--color-normal`(초록). 전 화면에서 이 토큰만 참조.
- 아이콘은 이모지 기반 유지(예: 차광막 🌤️, 창문 🪟, 관수 💧) — on/off/partial은 투명도·배경색 차이로 구분. 기존 프로젝트 톤(🌱, 🎤)과 일치.
- `styles.css` 파일 하나를 유지하되 `/* == Chat == */`, `/* == Dashboard == */`, `/* == Detail == */`, `/* == Notification == */` 섹션 주석으로 구획한다. 컴포넌트별 CSS 파일 분리는 하지 않는다.
- 모바일 대응: 기존 `.app { max-width: 480px }` 컨테이너 폭 유지, 대시보드 카드 그리드는 좁은 화면에서 1열로 자동 축소(`grid-template-columns` + media query 또는 `auto-fit/minmax`).

## 검증 계획

자동화 테스트는 추가하지 않는다(스코프 밖). `npm run dev`로 아래 시나리오를 수동 확인한다:

- [ ] 채팅: 메시지 전송 → "..." 로딩 → 응답, 액션성 응답이 카드로 강조되는지
- [ ] 백엔드를 끈 상태에서 전송 → 친절한 에러 문구가 뜨는지
- [ ] 대시보드 탭 진입 → 온실 3개(정상/경고/위험)가 우선순위 정렬로 보이는지
- [ ] warning/critical 카드 클릭 → 상세 화면 이동, 원인 텍스트/추천 조치 버튼 확인
- [ ] 추천 조치 버튼 클릭 → 장비 상태 변경 + 이력에 manual 항목 추가, 상태 완화 확인
- [ ] "데모: 경고→위험 승격" 클릭 → 크리티컬 배너가 전환 애니메이션과 함께 등장, 원터치 액션/닫기 동작 확인
- [ ] "리셋" 클릭 → 모든 상태가 초기값으로 복원되는지

## 스코프 밖 (이번에 안 함)

- 실제 백엔드 API 연동 (다중 온실 조회, 알림 영속화 등) — `useFarmData` 내부 교체로 나중에 연결 가능하도록만 경계를 둠
- STT(Web Speech API) 구현 — `todo/FRONTEND.md`의 별도 TODO 항목
- react-router-dom 등 라우팅 라이브러리 도입
- 자동화 테스트 코드 작성
