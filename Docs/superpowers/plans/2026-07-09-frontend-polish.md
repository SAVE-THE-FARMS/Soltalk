# SolTalk 프론트 UI 폴리시 & 비주얼 아이덴티티 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 채팅 퀵리플/자동스크롤, 알림 정리(오디오 재사용+dismiss 일관성), 모바일 반응형, 온실 콘셉트 비주얼 아이덴티티(색/타이포/시그니처)를 기존 SolTalk 프론트에 적용한다.

**Architecture:** 순수 프론트 CSS/컴포넌트 변경. 색 토큰(`:root` CSS 변수)과 웹폰트를 먼저 확립한 뒤, 그 토큰을 소비하는 타이포·컴포넌트·반응형 작업을 순서대로 쌓는다. 백엔드 호출 로직(`api.js`)은 건드리지 않는다.

**Tech Stack:** React 18 + Vite (기존 그대로). 웹폰트는 Google Fonts / jsdelivr CDN `<link>`로 로드 — npm 의존성 아님.

## Global Constraints

- 새 런타임 npm 의존성을 추가하지 않는다. 웹폰트는 `frontend/index.html`의 `<link>` 태그로만 로드한다.
- 백엔드 실연동(`/api/chat`, `/api/transcribe`)과 STT 녹음 UI는 이 계획의 범위 밖이다 — 손대지 않는다.
- 기존 CSS 변수명 `--color-critical`/`--color-warning`/`--color-normal`은 그대로 유지하고 값만 갱신한다(다른 컴포넌트가 이미 이 이름들을 참조하므로 이름을 바꾸면 전부 깨진다).
- 자동화 테스트 프레임워크가 없으므로, 각 태스크의 검증은 `npm run dev` + `npm run build`로 직접 확인하는 수동 시나리오로 한다.
- 참고 스펙: `docs/superpowers/specs/2026-07-09-frontend-polish-design.md`

---

### Task 1: 색 토큰 확장 + 웹폰트 로드 + 카드 셸/시그니처 배경

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Produces: CSS 변수 `--color-paper`, `--color-ink`, `--color-leaf`, `--color-leaf-soft`, `--color-sun`(신규) + 갱신된 `--color-critical`/`--color-warning`/`--color-normal` 값 — Task 2~5가 이 변수들을 그대로 참조한다.

- [ ] **Step 1: `index.html`에 웹폰트 `<link>` 추가**

`</head>` 바로 앞에 추가:

```html
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=IBM+Plex+Mono:wght@400;600&display=swap"
      rel="stylesheet"
    />
    <link
      rel="stylesheet"
      href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css"
    />
```

- [ ] **Step 2: `styles.css`의 `:root` 블록을 새 팔레트로 교체**

기존:
```css
:root {
  --color-critical: #e53935;
  --color-warning: #fbc02d;
  --color-normal: #2e7d32;
}
```

교체:
```css
:root {
  --color-paper: #F4F7ED;
  --color-ink: #232A21;
  --color-leaf: #3B6B3D;
  --color-leaf-soft: #DCEBD1;
  --color-sun: #E8A33D;
  --color-critical: #C4432E;
  --color-warning: #C98A2B;
  --color-normal: var(--color-leaf);
}
```

- [ ] **Step 3: `body`와 `.app`을 토큰/시그니처 배경으로 교체**

기존:
```css
body {
  margin: 0;
  font-family: system-ui, sans-serif;
  background: #f5f5f5;
}

.app {
  max-width: 480px;
  margin: 0 auto;
  padding: 16px;
  height: 100vh;
  display: flex;
  flex-direction: column;
}
```

교체:
```css
body {
  margin: 0;
  font-family: "Pretendard", system-ui, sans-serif;
  background: var(--color-paper);
  color: var(--color-ink);
}

.app {
  max-width: 480px;
  margin: 0 auto;
  padding: 16px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--color-paper);
  background-image:
    repeating-linear-gradient(45deg, rgba(59, 107, 61, 0.04) 0 1px, transparent 1px 24px),
    repeating-linear-gradient(-45deg, rgba(59, 107, 61, 0.04) 0 1px, transparent 1px 24px);
  border-radius: 16px;
  box-shadow: 0 4px 24px rgba(35, 42, 33, 0.08);
}
```

- [ ] **Step 4: 기존 하드코딩된 브랜드 그린/블루를 토큰으로 교체**

아래 표대로 정확히 찾아 바꾼다(같은 파일 안에서 여러 셀렉터에 나뉘어 있음):

| 위치 | 기존 | 교체 |
|---|---|---|
| `.composer button` | `background: #2e7d32;` | `background: var(--color-leaf);` |
| `.msg.user` | `background: #d1e7ff;` | `background: var(--color-leaf-soft);` |
| `.msg.bot.action` | `background: #eaf7ea; border-color: #bfe3bf;` | `background: var(--color-leaf-soft); border-color: var(--color-leaf);` |
| `.top-nav__tab.is-active` | `background: #2e7d32;` | `background: var(--color-leaf);` |
| `.alert-banner--ok` | `color: #2e7d32;` | `color: var(--color-leaf);` |
| `.production-widget__diff.is-up` | `color: #2e7d32;` | `color: var(--color-sun);` |
| `.production-widget__diff.is-down` | `color: #e53935;` | `color: var(--color-critical);` |
| `.greenhouse-detail__back` | `color: #2e7d32;` | `color: var(--color-leaf);` |
| `.greenhouse-detail__action` | `background: #2e7d32;` | `background: var(--color-leaf);` |
| `.greenhouse-detail__toast` | `background: #eaf7ea; color: #2e7d32;` | `background: var(--color-leaf-soft); color: var(--color-leaf);` |

- [ ] **Step 5: 수동 검증**

```bash
cd frontend
npm run build
npm run dev
```
브라우저(http://localhost:5173)에서:
- 배경이 옅은 초록빛 종이 톤으로 바뀌고, `.app` 카드 가장자리에 아주 은은한 대각선 격자무늬가 보이는지 (너무 튀면 안 됨 — 거의 안 보일 정도가 맞음)
- 전송 버튼/활성 탭/사용자 말풍선이 새 초록 톤으로 바뀌었는지
- 생산량 위젯의 ▲ 증가 화살표가 초록이 아니라 골드 톤으로 바뀌었는지

- [ ] **Step 6: 커밋**

```bash
git add frontend/index.html frontend/src/styles.css
git commit -m "feat(frontend): 색 토큰 확장 + 웹폰트 로드 + 카드 셸/시그니처 배경"
```

---

### Task 2: 타이포그래피 적용 (display-face / data-face)

**Files:**
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/GreenhouseDetail.jsx`
- Modify: `frontend/src/components/Dashboard/GreenhouseCard.jsx`
- Modify: `frontend/src/components/Dashboard/ProductionWidget.jsx`
- Modify: `frontend/src/components/Dashboard/HistoryTimeline.jsx`

**Interfaces:**
- Consumes: Task 1의 `--color-sun` 등 색 토큰(헤더 언더라인에 사용)
- Produces: CSS 유틸리티 클래스 `.display-face`, `.data-face` — 이후 다른 화면에 폰트를 적용할 때도 이 두 클래스를 그대로 재사용한다.

- [ ] **Step 1: `styles.css`에 유틸리티 클래스 추가**

파일 끝에 추가:
```css
.display-face { font-family: "Fraunces", serif; }
.data-face { font-family: "IBM Plex Mono", monospace; font-variant-numeric: tabular-nums; }

.header-underline {
  height: 3px;
  margin-bottom: 8px;
  background: linear-gradient(90deg, var(--color-sun), transparent);
}
```

- [ ] **Step 2: `App.jsx`의 헤더에 적용**

기존:
```jsx
      <h1>SolTalk 🌱</h1>
```

교체:
```jsx
      <h1 className="display-face">SolTalk 🌱</h1>
      <div className="header-underline" />
```

- [ ] **Step 3: `GreenhouseDetail.jsx`의 제목에 적용**

기존:
```jsx
        <h2>{greenhouse.name}</h2>
```

교체:
```jsx
        <h2 className="display-face">{greenhouse.name}</h2>
```

- [ ] **Step 4: `GreenhouseDetail.jsx`의 타임스탬프에 `data-face` 적용**

기존:
```jsx
        <div className="greenhouse-detail__times">
          {greenhouse.history.map((h) => (
            <span key={h.time}>{h.time}</span>
          ))}
        </div>
```

교체:
```jsx
        <div className="greenhouse-detail__times data-face">
          {greenhouse.history.map((h) => (
            <span key={h.time}>{h.time}</span>
          ))}
        </div>
```

- [ ] **Step 5: `GreenhouseCard.jsx`의 온도/습도 숫자에 `data-face` 적용**

기존:
```jsx
      <div className="greenhouse-card__metrics">
        <span>🌡️ {greenhouse.temperature}℃</span>
        <span>💧 {greenhouse.humidity}%</span>
      </div>
```

교체:
```jsx
      <div className="greenhouse-card__metrics data-face">
        <span>🌡️ {greenhouse.temperature}℃</span>
        <span>💧 {greenhouse.humidity}%</span>
      </div>
```

- [ ] **Step 6: `ProductionWidget.jsx`의 숫자 값에 `data-face` 적용**

기존:
```jsx
        <span className="production-widget__value">
          {production.today}{production.unit}
        </span>
      </div>
      <div>
        <span className="production-widget__label">이번주</span>
        <span className="production-widget__value">
          {production.week}{production.unit}
        </span>
```

교체:
```jsx
        <span className="production-widget__value data-face">
          {production.today}{production.unit}
        </span>
      </div>
      <div>
        <span className="production-widget__label">이번주</span>
        <span className="production-widget__value data-face">
          {production.week}{production.unit}
        </span>
```

- [ ] **Step 7: `HistoryTimeline.jsx`의 시각 표기에 `data-face` 적용**

기존:
```jsx
          <span className="history-timeline__time">{entry.time}</span>
```

교체:
```jsx
          <span className="history-timeline__time data-face">{entry.time}</span>
```

- [ ] **Step 8: 수동 검증**

```bash
npm run build
npm run dev
```
- "SolTalk 🌱" 제목이 세리프(Fraunces) 폰트로 보이고, 그 아래 골드 그라데이션 밑줄이 보이는지
- 대시보드 카드의 온도/습도 숫자, 생산량 숫자, 이력 타임스탬프, 온실 상세의 시간 라벨이 모노스페이스(IBM Plex Mono) 폰트로 또박또박 보이는지
- 온실 상세 화면 제목도 세리프로 보이는지

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/styles.css frontend/src/App.jsx frontend/src/components/GreenhouseDetail.jsx frontend/src/components/Dashboard/GreenhouseCard.jsx frontend/src/components/Dashboard/ProductionWidget.jsx frontend/src/components/Dashboard/HistoryTimeline.jsx
git commit -m "feat(frontend): 타이포그래피 적용 (display-face/data-face)"
```

---

### Task 3: 채팅 화면 — 퀵 리플 버튼 + 자동 스크롤

**Files:**
- Modify: `frontend/src/components/ChatScreen.jsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: Task 1의 `--color-leaf` 토큰
- Produces: `ChatScreen`의 `handleSend`가 이제 선택적 인자 `handleSend(overrideText?: string)`를 받는다 — 인자가 없으면 `input` state를 사용한다(다른 태스크는 이 시그니처를 참조하지 않는다).

- [ ] **Step 1: `ChatScreen.jsx` 전체를 아래로 교체**

```jsx
import { useEffect, useRef, useState } from "react";
import { sendMessage } from "../api";

// SolTalk 채팅 화면.
// 완료형 동사 매칭으로 액션 카드를 강조하는 건 실제 NLU 결과가 아니라
// 프론트 단순 텍스트 패턴 매칭(데모용 휴리스틱)이다.
const ACTION_DONE_PATTERN = /(열었어요|닫았어요|틀었어요|껐어요)/;

const QUICK_REPLIES = [
  "차광막 닫아줘",
  "창문 열어",
  "지금 온도 몇 도야?",
  "오늘 생산량 알려줘",
];

export default function ChatScreen() {
  const [messages, setMessages] = useState([]); // { id, role: "user"|"bot", text, pending? }
  const [input, setInput] = useState("");
  const nextIdRef = useRef(0);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(overrideText) {
    const text = (overrideText ?? input).trim();
    if (!text) return;
    const userId = nextIdRef.current++;
    const botId = nextIdRef.current++;
    setMessages((m) => [
      ...m,
      { id: userId, role: "user", text },
      { id: botId, role: "bot", text: "...", pending: true },
    ]);
    setInput("");

    try {
      const reply = await sendMessage(text);
      setMessages((m) =>
        m.map((msg) =>
          msg.id === botId ? { id: botId, role: "bot", text: reply } : msg
        )
      );
    } catch (e) {
      setMessages((m) =>
        m.map((msg) =>
          msg.id === botId
            ? {
                id: botId,
                role: "bot",
                text: "⚠️ 서버에 연결할 수 없어요. 잠시 후 다시 시도해주세요.",
              }
            : msg
        )
      );
    }
  }

  function handleMic() {
    // TODO(학생): 브라우저 Web Speech API 로 음성 인식 →
    //   인식된 텍스트를 setInput(...) 에 넣기 (원하면 바로 handleSend 까지)
    alert("음성 입력은 아직 미구현 (Web Speech API 연결하기)");
  }

  return (
    <div className="chat-screen">
      <div className="chat">
        {messages.length === 0 && (
          <>
            <p className="hint">예: "차광막 닫아줘", "지금 온도 몇 도야?"</p>
            <div className="quick-replies">
              {QUICK_REPLIES.map((cmd) => (
                <button
                  key={cmd}
                  className="quick-reply"
                  onClick={() => handleSend(cmd)}
                >
                  {cmd}
                </button>
              ))}
            </div>
          </>
        )}
        {messages.map((m) => {
          const isAction =
            m.role === "bot" && !m.pending && ACTION_DONE_PATTERN.test(m.text);
          return (
            <div
              key={m.id}
              className={`msg ${m.role}${m.pending ? " pending" : ""}${
                isAction ? " action" : ""
              }`}
            >
              {isAction && <span className="action-check">✅ </span>}
              {m.text}
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      <div className="composer">
        <button onClick={handleMic} title="음성 입력">🎤</button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="명령을 입력하세요"
        />
        <button onClick={() => handleSend()}>전송</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: `styles.css`에 퀵 리플 스타일 추가**

파일 끝에 추가:
```css
.quick-replies {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 12px;
}
.quick-reply {
  border: 1px solid var(--color-leaf);
  background: #fff;
  color: var(--color-leaf);
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 14px;
  cursor: pointer;
}
```

- [ ] **Step 3: 수동 검증**

```bash
npm run build
npm run dev
```
- 채팅 탭 첫 진입 시 힌트 문구 아래 퀵 리플 버튼 4개가 보이는지
- 버튼 하나를 클릭하면 그 문장이 즉시 전송되고("..." 로딩 → 응답), 버튼 줄은 사라지는지
- 메시지를 여러 개 주고받으면 항상 최신 메시지가 보이도록 자동으로 아래로 스크롤되는지
- 백엔드가 꺼져 있어도(현재 `/chat` 스텁 또는 팀원의 `/api/chat`과 경로가 달라 404여도) 에러 문구가 정상적으로 뜨는지 — 이 태스크는 요청 경로를 바꾸지 않으므로 기존과 동일한 방식으로 실패/성공한다

- [ ] **Step 4: 커밋**

```bash
git add frontend/src/components/ChatScreen.jsx frontend/src/styles.css
git commit -m "feat(frontend): 채팅 퀵 리플 버튼 + 자동 스크롤"
```

---

### Task 4: 알림 정리 — AudioContext 재사용 + dismiss 일관성

**Files:**
- Modify: `frontend/src/components/NotificationCenter/CriticalBanner.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/Dashboard/Dashboard.jsx`

**Interfaces:**
- Produces: `App.jsx`의 새 파생값 `visibleNotifications`(dismiss 제외한 전체 알림 배열, `farm.notifications`와 같은 원소 shape) — `Dashboard`가 `visibleNotifications` prop으로 받는다.

- [ ] **Step 1: `CriticalBanner.jsx`를 AudioContext 재사용 버전으로 교체**

전체 파일을 아래로 교체:
```jsx
import { useEffect, useRef } from "react";

function createAudioContext() {
  return new (window.AudioContext || window.webkitAudioContext)();
}

function playBeep(ctx) {
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = "sine";
  osc.frequency.value = 880;
  gain.gain.value = 0.15;
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start();
  osc.stop(ctx.currentTime + 0.2);
}

export default function CriticalBanner({ notifications, onAction, onDismiss, canPlaySound }) {
  const playedIdsRef = useRef(new Set());
  const audioCtxRef = useRef(null);

  useEffect(() => {
    if (!canPlaySound) return;
    notifications.forEach((n) => {
      if (!playedIdsRef.current.has(n.id)) {
        playedIdsRef.current.add(n.id);
        try {
          if (!audioCtxRef.current) {
            audioCtxRef.current = createAudioContext();
          }
          playBeep(audioCtxRef.current);
        } catch {
          // 브라우저가 오디오를 지원하지 않으면 조용히 무시
        }
      }
    });
  }, [notifications, canPlaySound]);

  if (notifications.length === 0) return null;

  return (
    <div className="critical-banner-stack">
      {notifications.map((n) => (
        <div key={n.id} className="critical-banner">
          <span>🔴 {n.greenhouseName}: {n.message}</span>
          <div className="critical-banner__actions">
            <button onClick={() => onAction(n.greenhouseId)}>바로 조치</button>
            <button
              className="critical-banner__dismiss"
              onClick={() => onDismiss(n.greenhouseId)}
            >
              ✕
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: `App.jsx`에 `visibleNotifications` 계산 추가**

기존:
```jsx
  const criticalNotifications = farm.notifications.filter(
    (n) => n.severity === "critical" && !dismissedIds.includes(n.greenhouseId)
  );
  const warningNotifications = farm.notifications.filter(
    (n) => n.severity === "warning" && !dismissedIds.includes(n.greenhouseId)
  );
```

교체:
```jsx
  const visibleNotifications = farm.notifications.filter(
    (n) => !dismissedIds.includes(n.greenhouseId)
  );
  const criticalNotifications = visibleNotifications.filter(
    (n) => n.severity === "critical"
  );
  const warningNotifications = visibleNotifications.filter(
    (n) => n.severity === "warning"
  );
```

- [ ] **Step 3: `App.jsx`의 `Dashboard` 호출에 `visibleNotifications` 전달**

기존:
```jsx
          <Dashboard
            farm={farm}
            onSelectGreenhouse={setSelectedGreenhouseId}
            onReset={handleReset}
            onEscalate={handleEscalate}
          />
```

교체:
```jsx
          <Dashboard
            farm={farm}
            onSelectGreenhouse={setSelectedGreenhouseId}
            onReset={handleReset}
            onEscalate={handleEscalate}
            visibleNotifications={visibleNotifications}
          />
```

- [ ] **Step 4: `Dashboard.jsx`가 `visibleNotifications`를 받아 `AlertBanner`에 전달**

기존:
```jsx
export default function Dashboard({ farm, onSelectGreenhouse, onReset, onEscalate }) {
  const sorted = [...farm.greenhouses].sort(
    (a, b) => SEVERITY_ORDER[b.status] - SEVERITY_ORDER[a.status]
  );

  return (
    <div className="dashboard">
      <DemoControls onReset={onReset} onEscalate={onEscalate} />
      <AlertBanner notifications={farm.notifications} onSelect={onSelectGreenhouse} />
```

교체:
```jsx
export default function Dashboard({ farm, onSelectGreenhouse, onReset, onEscalate, visibleNotifications }) {
  const sorted = [...farm.greenhouses].sort(
    (a, b) => SEVERITY_ORDER[b.status] - SEVERITY_ORDER[a.status]
  );

  return (
    <div className="dashboard">
      <DemoControls onReset={onReset} onEscalate={onEscalate} />
      <AlertBanner notifications={visibleNotifications} onSelect={onSelectGreenhouse} />
```

- [ ] **Step 5: 수동 검증**

```bash
npm run build
npm run dev
```
- 대시보드 탭에서 경고 알림 배지를 클릭 → 알림함에서 경고 항목을 "✕"로 닫기
- 대시보드로 돌아가서 상단 `AlertBanner`에 방금 닫은 알림이 더 이상 보이지 않는지 확인(전에는 계속 보였음)
- "리셋" 클릭 → 닫았던 알림과 온실 상태가 모두 초기화되는지(기존 동작 유지 확인)
- 위험 알림이 뜰 때 소리가 나는지(브라우저에서 한 번 클릭한 뒤) — 여러 번 위험 알림을 발생시켜도 브라우저 콘솔에 오디오 관련 경고가 없는지(개발자 도구 콘솔 확인)

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/NotificationCenter/CriticalBanner.jsx frontend/src/App.jsx frontend/src/components/Dashboard/Dashboard.jsx
git commit -m "fix(frontend): AudioContext 재사용 + 대시보드 알림 dismiss 일관성"
```

---

### Task 5: 모바일 반응형 폴리시

**Files:**
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: Task 3의 `.quick-reply` 클래스, Task 1의 `.app` 규칙(같은 셀렉터에 새 선언을 추가한다 — 기존 선언과 충돌하지 않음)

- [ ] **Step 1: 입력창 폰트 크기 조정 (iOS 자동확대 방지)**

기존:
```css
.composer input {
  flex: 1;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 8px;
}
```

교체:
```css
.composer input {
  flex: 1;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 8px;
  font-size: 16px;
}
```

- [ ] **Step 2: 터치 영역 44px 이상 확보 + 작은 글자 상향 + 가로 스크롤 방지**

파일 끝에 추가:
```css
/* 모바일 반응형 폴리시 */
.composer button,
.top-nav__badge,
.critical-banner__actions button,
.notification-inbox button,
.quick-reply {
  min-height: 44px;
  min-width: 44px;
}

.demo-controls__btn { font-size: 13px; }
.history-timeline li { font-size: 14px; }
.top-nav__badge { font-size: 13px; }
.greenhouse-detail__times span { font-size: 13px; }
.chart-legend { font-size: 13px; }

.app {
  overflow-x: hidden;
}

@media (min-width: 600px) {
  .app {
    max-width: 640px;
  }
}
```

- [ ] **Step 3: 수동 검증**

```bash
npm run build
npm run dev
```
브라우저 개발자 도구에서 반응형 모드로 전환해 확인:
- 폭 375px(iPhone SE급)에서 어떤 화면(채팅/대시보드/온실상세)도 가로 스크롤이 생기지 않는지
- 마이크/전송/알림 닫기(✕)/배지 버튼이 손가락으로 누르기 편한 크기로 보이는지
- 폭 900px(데스크톱)로 넓히면 `.app`이 640px까지 넓어지고 카드 그림자가 화면 중앙에 보이는지
- 온실 상세의 SVG 차트가 좁은 화면에서도 컨테이너 폭에 맞게 줄어들고 넘치지 않는지

- [ ] **Step 4: 커밋**

```bash
git add frontend/src/styles.css
git commit -m "feat(frontend): 모바일 반응형 폴리시 (터치 영역/폰트/가로스크롤/데스크톱 폭)"
```

---

## 계획 완료 후 남는 것

- 백엔드 실연동(`/api/chat` 전환, `actions_taken` 기반 액션카드, `/api/transcribe`) — 팀원 담당, 별도 계획
- STT 녹음 UI(MediaRecorder, 무음 감지) — 별도 계획
- 대시보드/알림 실 백엔드 데이터 연동 — 2순위, 여유 시 별도 진행
