# SolTalk 프론트 UI 폴리시 & 비주얼 아이덴티티 — 설계

> 대상: 채팅 화면 개선, 알림 정리, 모바일 반응형, 비주얼 아이덴티티(색/타이포/시그니처)
> 범위 밖: 백엔드 실연동(`/api/chat`, `/api/transcribe`) — 별도 팀원 담당. STT 녹음 UI — 별도 작업으로 분리.

## 배경 / 제약

- 백엔드 연동은 다른 팀원이 진행 중이며, 이 설계는 **순수 프론트 UI/UX + 비주얼 폴리시**만 다룬다.
- `todo/FRONTEND_통합_필수.md`에 모바일 반응형(§1)과 "사소하지만 챙기면 좋은 것"(`CriticalBanner` AudioContext 재사용)이 프론트 담당 항목으로 명시돼 있다.
- 새 npm 의존성은 추가하지 않는다. 웹폰트는 CDN `<link>`(Google Fonts, jsdelivr)로 불러온다 — npm 패키지가 아니므로 기존 제약과 상충하지 않는다.
- 고령 농가 사용자가 타겟이므로 글씨/버튼/터치 영역을 크게, 대비를 충분히 유지한다.

## A. 채팅 화면 — 퀵 리플 + 자동 스크롤

**파일:** `frontend/src/components/ChatScreen.jsx`

- 퀵 리플 명령 4개(제어 2 + 조회 2): `"차광막 닫아줘"`, `"창문 열어"`, `"지금 온도 몇 도야?"`, `"오늘 생산량 알려줘"`.
- `messages.length === 0`일 때만(기존 힌트 문구와 같은 조건) 버튼 4개를 렌더링. 첫 메시지가 전송되면 사라짐.
- 버튼 클릭 시 해당 문장으로 즉시 전송. 이를 위해 `handleSend`가 선택적 인자를 받도록 변경: `handleSend(overrideText)` — `overrideText ?? input`을 사용. 기존 입력창 전송과 퀵 리플 전송이 같은 함수를 공유한다.
- 자동 스크롤: `.chat` 목록 맨 아래에 보이지 않는 sentinel `<div ref={bottomRef} />`를 두고, `messages` 배열이 바뀔 때마다 `useEffect`에서 `bottomRef.current?.scrollIntoView({ behavior: "smooth" })` 호출.

## B. 알림 정리 — AudioContext 재사용 + dismiss 일관성

**파일:** `frontend/src/components/NotificationCenter/CriticalBanner.jsx`, `frontend/src/App.jsx`, `frontend/src/components/Dashboard/Dashboard.jsx`

- **AudioContext 재사용**: 지금은 `playBeep()`이 호출될 때마다 `new AudioContext()`를 생성해 누수 위험이 있다(문서에서 명시적으로 지적됨). `CriticalBanner` 내부에 `const audioCtxRef = useRef(null)`을 두고, 최초 호출 시에만 `new (window.AudioContext || window.webkitAudioContext)()`로 생성해 `audioCtxRef.current`에 저장, 이후 호출은 저장된 컨텍스트를 재사용해 `createOscillator()`/`createGain()`만 새로 만든다.
- **dismiss 일관성**: 현재 `App.jsx`가 `criticalNotifications`/`warningNotifications`(dismiss 제외)를 계산해 `CriticalBanner`/`NotificationInbox`에만 넘기고, `Dashboard`에는 `farm.notifications`(dismiss 미반영, 전체)를 그대로 넘겨서 세 곳이 서로 다른 목록을 보여준다. `App.jsx`에서 `visibleNotifications = farm.notifications.filter(n => !dismissedIds.includes(n.greenhouseId))`를 추가로 계산해 `Dashboard`에 `visibleNotifications` prop으로 전달하고, `Dashboard`는 이를 `AlertBanner`에 그대로 넘긴다(`farm.notifications` 대신).

## C. 모바일 반응형

**파일:** `frontend/src/styles.css`

- `.composer input`에 `font-size: 16px` 이상 지정 — 모바일 브라우저에서 입력 포커스 시 자동 확대되는 현상 방지.
- 아이콘/보조 버튼(마이크 🎤, 전송, 알림 닫기 ✕, `top-nav__badge`)의 터치 영역을 최소 `44px × 44px`로 확대(`min-width`/`min-height` + `padding` 조정).
- 작은 글자들 상향: `.demo-controls__btn`(11px→13px), `.history-timeline li`(13px→14px), `.top-nav__badge`(12px→13px), `.greenhouse-detail__times`/`.chart-legend`(11~12px→13px).
- `.app`: `@media (min-width: 600px)`에서 `max-width: 640px`로 확장 + `border-radius`/`box-shadow`로 카드 경계를 명시적으로 부여(현재는 좁은 화면에서만 자연스럽고 넓은 화면에서는 그냥 좁은 회색 배경 위 텍스트처럼 보임).
- `.app`에 `overflow-x: hidden` 안전장치 추가 — 어떤 자식 요소도 가로 스크롤을 유발하지 않도록.

## D. 비주얼 아이덴티티

**파일:** `frontend/index.html`(폰트 `<link>` 추가), `frontend/src/styles.css`(토큰/타이포/시그니처)

### 색 토큰 (`:root`)

기존 `--color-critical`/`--color-warning`/`--color-normal` 변수명은 유지하고 값과 팔레트를 확장한다:

```css
:root {
  --color-paper: #F4F7ED;      /* 배경 — 온실 유리에 스민 옅은 초록빛 안개 */
  --color-ink: #232A21;        /* 본문 텍스트 — 순검정 대신 흙빛 도는 짙은 녹갈색 */
  --color-leaf: #3B6B3D;       /* 브랜드/주요 액션 — 잎사귀 초록 */
  --color-leaf-soft: #DCEBD1;  /* 사용자 말풍선 등 옅은 표면 */
  --color-sun: #E8A33D;        /* 생산량 증가 등 포인트 강조 — 수확·햇살 골드 */
  --color-critical: #C4432E;   /* 기존보다 따뜻한 톤의 위험색 */
  --color-warning: #C98A2B;    /* 기존보다 따뜻한 톤의 경고색 */
  --color-normal: var(--color-leaf);
}
```

`body` 배경은 `--color-paper`, 기본 텍스트는 `--color-ink`를 사용하도록 갱신(기존 `background:#f5f5f5`, 텍스트 기본 검정 대체).

### 타이포그래피

`frontend/index.html`의 `<head>`에 폰트 `<link>` 3종 추가:
- **Fraunces** (Google Fonts) — "SolTalk" 워드마크/화면 제목 전용, 절제해서 사용.
- **Pretendard** (jsdelivr CDN: `cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css`) — 본문/버튼/라벨 등 한글이 대부분인 UI 텍스트 전체의 기본 폰트.
- **IBM Plex Mono** (Google Fonts) — 온도·습도·생산량 숫자, 타임스탬프 등 "센서 계기판" 성격의 수치 표기 전용.

`styles.css`에 유틸리티 클래스 추가:
```css
body { font-family: "Pretendard", system-ui, sans-serif; }
.display-face { font-family: "Fraunces", serif; }
.data-face { font-family: "IBM Plex Mono", monospace; font-variant-numeric: tabular-nums; }
```
- `App.jsx`의 `<h1>SolTalk 🌱</h1>`과 각 화면 제목(`GreenhouseDetail`의 `<h2>`)에 `display-face` 클래스 적용.
- 온도/습도/생산량 숫자(`GreenhouseCard`, `GreenhouseDetail`, `ProductionWidget`)와 이력 타임스탬프(`HistoryTimeline`)에 `data-face` 클래스 적용.

### 시그니처 요소 — 온실 유리 격자 배경

`.app` 배경에 아주 옅은 대각선 격자 무늬를 CSS `repeating-linear-gradient`로 추가해 "온실 유리 너머로 보는 화면" 느낌을 은은하게 준다. 저채도·저대비로 텍스트 가독성에 영향 없게 한다:

```css
.app {
  background-image:
    repeating-linear-gradient(45deg, rgba(59,107,61,0.04) 0 1px, transparent 1px 24px),
    repeating-linear-gradient(-45deg, rgba(59,107,61,0.04) 0 1px, transparent 1px 24px);
}
```

### 레이아웃 디테일

- `.app`: `border-radius: 16px`, `box-shadow: 0 4px 24px rgba(35,42,33,0.08)` 추가로 카드 경계 부여(섹션 C의 640px 확장과 함께 적용).
- 헤더 아래 골드 그라데이션 언더라인: `<h1>` 바로 아래 `<div className="header-underline" />` 추가, `background: linear-gradient(90deg, var(--color-sun), transparent)`, `height: 3px`.
- `.top-nav__tab.is-active`: 배경을 `var(--color-leaf)`로(기존 `#2e7d32`와 유사하지만 토큰 사용으로 통일).

## 스코프 밖 (이번에 안 함)

- 백엔드 실연동(`/api/chat` 전환, `actions_taken` 기반 액션카드, `/api/transcribe` 연결) — 팀원 담당.
- STT 녹음 UI(MediaRecorder, 무음 감지) — 별도 작업으로 분리, 이번 스코프 아님.
- 대시보드/알림 실 백엔드 데이터 연동(필드 매핑 등) — 2순위, 여유 시 별도 진행.
