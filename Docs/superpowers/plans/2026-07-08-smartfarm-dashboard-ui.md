# SolTalk 스마트팜 대시보드/알림 UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `Docs/smartfarm_ui_elements.md`의 2.1(채팅)~2.5(공통) 전체를 구현한다 — 챗봇 화면 개선, 다중 온실 대시보드, 온실 상세, 인앱 알림(배너/알림함)까지.

**Architecture:** React 상태 기반 탭 전환(챗봇↔대시보드, 새 라우터 없음). 대시보드/상세/알림은 `useFarmData()` 커스텀 훅(순수 React state, 백엔드 미연동)을 `App.jsx`에서 한 번만 호출해 props로 내려주는 단일 소스. 챗봇 화면은 기존 `/chat` 백엔드 호출을 그대로 쓰며 대시보드 데이터와 완전히 분리된다.

**Tech Stack:** React 18 + Vite (기존 그대로). 새 npm 의존성 추가 없음 — 아이콘은 이모지, 차트는 직접 그린 SVG.

## Global Constraints

- 새 런타임 npm 의존성을 추가하지 않는다 (라우터/차트/아이콘/상태관리 라이브러리 금지).
- 백엔드 코드(`backend/`)는 이 계획에서 변경하지 않는다. 대시보드 데이터는 전부 프론트 목업.
- 화면 전환은 URL 라우팅이 아니라 `App.jsx`의 React state로 한다.
- 색상은 `:root`의 CSS 커스텀 프로퍼티(`--color-critical`/`--color-warning`/`--color-normal`)만 참조한다.
- 자동화 테스트 프레임워크가 없으므로(2일 스코프 프로젝트), 각 태스크의 검증은 `npm run dev`로 브라우저에서 직접 확인하는 수동 시나리오로 한다.
- 참고 스펙: `docs/superpowers/specs/2026-07-08-smartfarm-ui-design.md`

---

### Task 1: 채팅 화면 컴포넌트 분리 + 로딩/에러/액션카드 강조

**Files:**
- Create: `frontend/src/components/ChatScreen.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: 기존 `frontend/src/api.js`의 `sendMessage(text: string): Promise<string>` (변경 없음)
- Produces: `ChatScreen` 컴포넌트 (props 없음) — Task 2에서 `App.jsx`가 이 컴포넌트를 탭 안에 그대로 배치한다.

- [ ] **Step 1: `ChatScreen.jsx` 작성**

```jsx
import { useState } from "react";
import { sendMessage } from "../api";

// SolTalk 채팅 화면.
// 완료형 동사 매칭으로 액션 카드를 강조하는 건 실제 NLU 결과가 아니라
// 프론트 단순 텍스트 패턴 매칭(데모용 휴리스틱)이다.
const ACTION_DONE_PATTERN = /(열었어요|닫았어요|틀었어요|껐어요)/;

export default function ChatScreen() {
  const [messages, setMessages] = useState([]); // { role: "user"|"bot", text, pending? }
  const [input, setInput] = useState("");

  async function handleSend() {
    const text = input.trim();
    if (!text) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setMessages((m) => [...m, { role: "bot", text: "...", pending: true }]);

    try {
      const reply = await sendMessage(text);
      setMessages((m) => {
        const next = [...m];
        next[next.length - 1] = { role: "bot", text: reply };
        return next;
      });
    } catch (e) {
      setMessages((m) => {
        const next = [...m];
        next[next.length - 1] = {
          role: "bot",
          text: "⚠️ 서버에 연결할 수 없어요. 잠시 후 다시 시도해주세요.",
        };
        return next;
      });
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
          <p className="hint">예: "차광막 닫아줘", "지금 온도 몇 도야?"</p>
        )}
        {messages.map((m, i) => {
          const isAction =
            m.role === "bot" && !m.pending && ACTION_DONE_PATTERN.test(m.text);
          return (
            <div
              key={i}
              className={`msg ${m.role}${m.pending ? " pending" : ""}${
                isAction ? " action" : ""
              }`}
            >
              {isAction && <span className="action-check">✅ </span>}
              {m.text}
            </div>
          );
        })}
      </div>

      <div className="composer">
        <button onClick={handleMic} title="음성 입력">🎤</button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="명령을 입력하세요"
        />
        <button onClick={handleSend}>전송</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: `App.jsx`를 `ChatScreen`을 쓰도록 교체**

```jsx
import ChatScreen from "./components/ChatScreen";

export default function App() {
  return (
    <div className="app">
      <h1>SolTalk 🌱</h1>
      <ChatScreen />
    </div>
  );
}
```

- [ ] **Step 3: `styles.css`에서 `.app`/`.chat` 블록을 아래로 교체하고 로딩/액션 스타일 추가**

`.app { ... }` 바로 아래, 기존 `.chat { ... }` 블록을 찾아 그 위에 `.chat-screen` 규칙을 추가하고, 파일 맨 끝에 액션/로딩 스타일을 추가한다.

```css
.chat-screen {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
```

파일 끝에 추가:

```css
.msg.pending { color: #999; font-style: italic; }
.msg.bot.action { background: #eaf7ea; border-color: #bfe3bf; }
.action-check { margin-right: 2px; }
```

- [ ] **Step 4: 수동 검증**

```bash
cd frontend
npm run dev
```
브라우저에서 http://localhost:5173 열어:
- 메시지 전송 시 "..." 로딩 말풍선이 잠깐 보였다가 응답으로 바뀌는지
- 백엔드(`uv run python app/server.py`)를 꺼둔 상태로 전송하면 "⚠️ 서버에 연결할 수 없어요..." 문구가 뜨는지
- (백엔드가 "닫았어요"/"열었어요" 같은 완료형 응답을 준다면) 해당 말풍선이 연한 초록 배경 "✅ 액션 카드"로 보이는지

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/components/ChatScreen.jsx frontend/src/App.jsx frontend/src/styles.css
git commit -m "feat(frontend): 채팅 화면 컴포넌트 분리 + 로딩/에러/액션카드"
```

---

### Task 2: 목업 데이터 + `useFarmData` 훅 + 탭 전환 뼈대

**Files:**
- Create: `frontend/src/lib/labels.js`
- Create: `frontend/src/lib/mockData.js`
- Create: `frontend/src/lib/useFarmData.js`
- Create: `frontend/src/components/TopNav.jsx`
- Create: `frontend/src/components/Dashboard/Dashboard.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: 없음 (독립 모듈)
- Produces:
  - `useFarmData(): { greenhouses, production, historyLog, notifications, controlDevice(greenhouseId, device, action), resetDemo(), escalateDemo() }` — Task 3~6에서 이 반환값(`farm`)을 그대로 props로 내려받아 쓴다.
  - `greenhouses[i]` shape: `{ id, name, status: "normal"|"warning"|"critical", temperature, humidity, devices: {shade, window, irrigation}, cause, recommendedAction: {label, device, action}|null, history: [{time, temperature, humidity}] }`
  - `notifications[i]` shape: `{ id, severity, greenhouseId, greenhouseName, message }`
  - `<TopNav view onChangeView warningCount />` — Task 6에서 `onOpenInbox` prop이 추가된다.
  - `<Dashboard farm />` — Task 3~4에서 이 컴포넌트를 계속 확장한다.

- [ ] **Step 1: `lib/labels.js` 작성**

```js
export const DEVICE_LABEL = { shade: "차광막", window: "창문", irrigation: "관수" };
export const ACTION_LABEL = {
  open: "열림",
  closed: "닫힘",
  partial: "부분개방",
  on: "켜짐",
  off: "꺼짐",
};
```

- [ ] **Step 2: `lib/mockData.js` 작성**

```js
// 대시보드/알림/상세 화면용 목업 데이터.
// 챗봇(/chat) 데이터와는 무관한 독립 데이터다.

export const INITIAL_GREENHOUSES = [
  {
    id: "gh-1",
    name: "1번 온실",
    status: "normal",
    temperature: 23.8,
    humidity: 58,
    devices: { shade: "open", window: "closed", irrigation: "off" },
    cause: null,
    recommendedAction: null,
    history: [
      { time: "06:00", temperature: 19.2, humidity: 55 },
      { time: "09:00", temperature: 21.5, humidity: 57 },
      { time: "12:00", temperature: 23.8, humidity: 58 },
      { time: "15:00", temperature: 24.1, humidity: 56 },
      { time: "18:00", temperature: 22.0, humidity: 59 },
    ],
  },
  {
    id: "gh-2",
    name: "2번 온실",
    status: "warning",
    temperature: 26.4,
    humidity: 82,
    devices: { shade: "open", window: "closed", irrigation: "on" },
    cause: "습도 82%, 임계값 80% 초과 2일 지속",
    recommendedAction: { label: "창문 열기", device: "window", action: "open" },
    history: [
      { time: "06:00", temperature: 24.0, humidity: 76 },
      { time: "09:00", temperature: 25.1, humidity: 78 },
      { time: "12:00", temperature: 26.0, humidity: 80 },
      { time: "15:00", temperature: 26.4, humidity: 82 },
      { time: "18:00", temperature: 26.2, humidity: 82 },
    ],
  },
  {
    id: "gh-3",
    name: "3번 온실",
    status: "critical",
    temperature: 31.2,
    humidity: 45,
    devices: { shade: "closed", window: "closed", irrigation: "off" },
    cause: "차광막이 닫혀 온도가 31.2도까지 상승, 임계값(30도) 초과",
    recommendedAction: { label: "차광막 열기", device: "shade", action: "open" },
    history: [
      { time: "06:00", temperature: 26.0, humidity: 50 },
      { time: "09:00", temperature: 28.4, humidity: 48 },
      { time: "12:00", temperature: 30.1, humidity: 46 },
      { time: "15:00", temperature: 31.2, humidity: 45 },
      { time: "18:00", temperature: 31.0, humidity: 45 },
    ],
  },
];

export const INITIAL_PRODUCTION = {
  today: 128,
  week: 812,
  unit: "kg",
  diffPct: 6,
  direction: "up",
};

export const INITIAL_HISTORY_LOG = [
  { time: "07:12", type: "auto", text: "1번 온실 관수 자동 종료" },
  { time: "10:05", type: "auto", text: "2번 온실 관수 자동 시작" },
  { time: "13:40", type: "manual", text: "3번 온실 차광막 수동 닫힘" },
];
```

- [ ] **Step 3: `lib/useFarmData.js` 작성**

```js
import { useCallback, useState } from "react";
import {
  INITIAL_GREENHOUSES,
  INITIAL_HISTORY_LOG,
  INITIAL_PRODUCTION,
} from "./mockData";
import { ACTION_LABEL, DEVICE_LABEL } from "./labels";

const STATUS_STEP_DOWN = { critical: "warning", warning: "normal" };
const SEVERITY_ORDER = { critical: 2, warning: 1, normal: 0 };

function formatNow() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, "0")}:${String(
    d.getMinutes()
  ).padStart(2, "0")}`;
}

export function useFarmData() {
  const [greenhouses, setGreenhouses] = useState(INITIAL_GREENHOUSES);
  const [production] = useState(INITIAL_PRODUCTION);
  const [historyLog, setHistoryLog] = useState(INITIAL_HISTORY_LOG);

  const controlDevice = useCallback(
    (greenhouseId, device, action) => {
      const target = greenhouses.find((gh) => gh.id === greenhouseId);
      if (!target) return;

      const matchesRecommended =
        target.recommendedAction &&
        target.recommendedAction.device === device &&
        target.recommendedAction.action === action;
      const nextStatus = matchesRecommended
        ? STATUS_STEP_DOWN[target.status] ?? target.status
        : target.status;
      const resolved = matchesRecommended && nextStatus === "normal";

      setGreenhouses((prev) =>
        prev.map((gh) =>
          gh.id === greenhouseId
            ? {
                ...gh,
                devices: { ...gh.devices, [device]: action },
                status: nextStatus,
                cause: resolved ? null : gh.cause,
                recommendedAction: resolved ? null : gh.recommendedAction,
              }
            : gh
        )
      );

      setHistoryLog((prev) => [
        {
          time: formatNow(),
          type: "manual",
          text: `${target.name} ${DEVICE_LABEL[device]} ${
            ACTION_LABEL[action] ?? action
          }`,
        },
        ...prev,
      ]);
    },
    [greenhouses]
  );

  const resetDemo = useCallback(() => {
    setGreenhouses(INITIAL_GREENHOUSES);
    setHistoryLog(INITIAL_HISTORY_LOG);
  }, []);

  const escalateDemo = useCallback(() => {
    setGreenhouses((prev) => {
      const idx = prev.findIndex((gh) => gh.status === "warning");
      if (idx === -1) return prev;
      return prev.map((gh, i) =>
        i === idx ? { ...gh, status: "critical" } : gh
      );
    });
  }, []);

  const notifications = greenhouses
    .filter((gh) => gh.status !== "normal")
    .sort((a, b) => SEVERITY_ORDER[b.status] - SEVERITY_ORDER[a.status])
    .map((gh) => ({
      id: gh.id,
      severity: gh.status,
      greenhouseId: gh.id,
      greenhouseName: gh.name,
      message: gh.cause,
    }));

  return {
    greenhouses,
    production,
    historyLog,
    notifications,
    controlDevice,
    resetDemo,
    escalateDemo,
  };
}
```

- [ ] **Step 4: `components/TopNav.jsx` 작성**

```jsx
export default function TopNav({ view, onChangeView, warningCount }) {
  return (
    <nav className="top-nav">
      <button
        className={`top-nav__tab ${view === "chat" ? "is-active" : ""}`}
        onClick={() => onChangeView("chat")}
      >
        채팅
      </button>
      <button
        className={`top-nav__tab ${view === "dashboard" ? "is-active" : ""}`}
        onClick={() => onChangeView("dashboard")}
      >
        대시보드
      </button>
      {warningCount > 0 && (
        <span className="top-nav__badge">{warningCount}</span>
      )}
    </nav>
  );
}
```

- [ ] **Step 5: `components/Dashboard/Dashboard.jsx` 작성 (최소 버전)**

```jsx
export default function Dashboard({ farm }) {
  const { greenhouses } = farm;

  return (
    <div className="dashboard">
      <ul className="dashboard__debug-list">
        {greenhouses.map((gh) => (
          <li key={gh.id}>
            {gh.name} — {gh.status}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 6: `App.jsx`를 탭 전환 + `useFarmData` 사용하도록 교체**

```jsx
import { useState } from "react";
import ChatScreen from "./components/ChatScreen";
import TopNav from "./components/TopNav";
import Dashboard from "./components/Dashboard/Dashboard";
import { useFarmData } from "./lib/useFarmData";

export default function App() {
  const [view, setView] = useState("chat"); // "chat" | "dashboard"
  const farm = useFarmData();
  const warningCount = farm.notifications.filter(
    (n) => n.severity === "warning"
  ).length;

  return (
    <div className="app">
      <h1>SolTalk 🌱</h1>
      <TopNav view={view} onChangeView={setView} warningCount={warningCount} />
      <div className={view === "chat" ? "screen" : "screen is-hidden"}>
        <ChatScreen />
      </div>
      <div className={view === "dashboard" ? "screen" : "screen is-hidden"}>
        <Dashboard farm={farm} />
      </div>
    </div>
  );
}
```

`view === "dashboard" ? ... : "screen is-hidden"`처럼 두 화면을 항상 마운트해두고 `display:none`으로만 숨기는 이유: 조건부 마운트(`{view === "chat" && <ChatScreen/>}`)를 쓰면 대시보드 탭을 봤다가 채팅으로 돌아올 때 `ChatScreen`이 언마운트→재마운트되어 대화 내역이 사라진다.

- [ ] **Step 7: `styles.css`에 탭/뱃지 스타일 추가**

파일 끝에 추가:

```css
.screen.is-hidden { display: none; }

.top-nav { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.top-nav__tab {
  border: none;
  background: #eee;
  padding: 8px 14px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  color: #555;
}
.top-nav__tab.is-active { background: #2e7d32; color: #fff; }
.top-nav__badge {
  background: #fbc02d;
  color: #3a2a00;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 12px;
}
```

- [ ] **Step 8: 수동 검증**

```bash
npm run dev
```
- 기본 진입 시 채팅 탭이 보이고 기존처럼 동작하는지
- "대시보드" 탭 클릭 → "1번 온실 — normal", "2번 온실 — warning", "3번 온실 — critical" 목록이 보이는지
- "대시보드" 탭 옆에 노란 배지 "1"이 보이는지 (warning 1개)
- 채팅 탭으로 돌아갔다가 다시 대시보드로 가도 메시지가 유지되는지

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/lib frontend/src/components/TopNav.jsx frontend/src/components/Dashboard/Dashboard.jsx frontend/src/App.jsx frontend/src/styles.css
git commit -m "feat(frontend): 목업 데이터 + useFarmData 훅 + 탭 전환 뼈대"
```

---

### Task 3: 공통 UI(StatusBadge, DeviceIcon) + GreenhouseCard + 반응형 그리드

**Files:**
- Create: `frontend/src/components/ui/StatusBadge.jsx`
- Create: `frontend/src/components/ui/DeviceIcon.jsx`
- Create: `frontend/src/components/Dashboard/GreenhouseCard.jsx`
- Modify: `frontend/src/components/Dashboard/Dashboard.jsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `farm.greenhouses` (Task 2), `DEVICE_LABEL` (Task 2 `lib/labels.js`)
- Produces:
  - `<StatusBadge status="normal"|"warning"|"critical" />` — Task 5에서도 재사용.
  - `<DeviceIcon device="shade"|"window"|"irrigation" state={...} />` — Task 5에서도 쓰이진 않지만 동일 컴포넌트를 그대로 재사용 가능하도록 범용으로 만든다.
  - `<GreenhouseCard greenhouse onClick(id) />` — `onClick`은 optional, Task 5에서 실제로 연결된다.

- [ ] **Step 1: `ui/StatusBadge.jsx` 작성**

```jsx
const LABEL = { normal: "정상", warning: "경고", critical: "위험" };

export default function StatusBadge({ status }) {
  return (
    <span className={`status-badge status-badge--${status}`}>
      {LABEL[status]}
    </span>
  );
}
```

- [ ] **Step 2: `ui/DeviceIcon.jsx` 작성**

```jsx
import { DEVICE_LABEL } from "../../lib/labels";

const DEVICE_EMOJI = { shade: "🌤️", window: "🪟", irrigation: "💧" };

function stateClass(device, state) {
  if (device === "irrigation") {
    return state === "on" ? "device-icon--on" : "device-icon--off";
  }
  if (state === "open") return "device-icon--on";
  if (state === "partial") return "device-icon--partial";
  return "device-icon--off";
}

export default function DeviceIcon({ device, state }) {
  return (
    <span
      className={`device-icon ${stateClass(device, state)}`}
      title={`${DEVICE_LABEL[device]}: ${state}`}
    >
      {DEVICE_EMOJI[device]}
    </span>
  );
}
```

- [ ] **Step 3: `Dashboard/GreenhouseCard.jsx` 작성**

```jsx
import StatusBadge from "../ui/StatusBadge";
import DeviceIcon from "../ui/DeviceIcon";

export default function GreenhouseCard({ greenhouse, onClick }) {
  const isCompact = greenhouse.status === "normal";

  return (
    <button
      className={`greenhouse-card greenhouse-card--${greenhouse.status}${
        isCompact ? " greenhouse-card--compact" : ""
      }`}
      onClick={() => onClick?.(greenhouse.id)}
    >
      <div className="greenhouse-card__header">
        <span className="greenhouse-card__name">{greenhouse.name}</span>
        <StatusBadge status={greenhouse.status} />
      </div>
      <div className="greenhouse-card__metrics">
        <span>🌡️ {greenhouse.temperature}℃</span>
        <span>💧 {greenhouse.humidity}%</span>
      </div>
      <div className="greenhouse-card__devices">
        <DeviceIcon device="shade" state={greenhouse.devices.shade} />
        <DeviceIcon device="window" state={greenhouse.devices.window} />
        <DeviceIcon device="irrigation" state={greenhouse.devices.irrigation} />
      </div>
    </button>
  );
}
```

- [ ] **Step 4: `Dashboard.jsx`를 카드 그리드로 교체**

```jsx
import GreenhouseCard from "./GreenhouseCard";

const SEVERITY_ORDER = { critical: 2, warning: 1, normal: 0 };

export default function Dashboard({ farm, onSelectGreenhouse }) {
  const sorted = [...farm.greenhouses].sort(
    (a, b) => SEVERITY_ORDER[b.status] - SEVERITY_ORDER[a.status]
  );

  return (
    <div className="dashboard">
      <div className="dashboard__grid">
        {sorted.map((gh) => (
          <GreenhouseCard key={gh.id} greenhouse={gh} onClick={onSelectGreenhouse} />
        ))}
      </div>
    </div>
  );
}
```

(`App.jsx`는 아직 `onSelectGreenhouse`를 넘기지 않으므로 지금은 카드를 클릭해도 아무 반응이 없다 — Task 5에서 연결한다.)

- [ ] **Step 5: `styles.css`에 색상 토큰 + 카드/그리드 스타일 추가**

파일 맨 위, `* { box-sizing: border-box; }` 바로 아래에 추가:

```css
:root {
  --color-critical: #e53935;
  --color-warning: #fbc02d;
  --color-normal: #2e7d32;
}
```

파일 끝에 추가:

```css
.status-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
}
.status-badge--normal { background: var(--color-normal); }
.status-badge--warning { background: var(--color-warning); color: #3a2a00; }
.status-badge--critical { background: var(--color-critical); }

.device-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  font-size: 16px;
  margin-right: 4px;
  background: #eee;
  opacity: 0.4;
}
.device-icon--on { opacity: 1; background: #e3f6e3; }
.device-icon--partial { opacity: 0.7; background: #fff6db; }
.device-icon--off { opacity: 0.4; background: #eee; }

.dashboard { flex: 1; overflow-y: auto; padding: 8px 0; }

.dashboard__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.greenhouse-card {
  text-align: left;
  border: none;
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.greenhouse-card--warning { border: 2px solid var(--color-warning); }
.greenhouse-card--critical { border: 2px solid var(--color-critical); }
.greenhouse-card--compact { padding: 8px 14px; gap: 4px; opacity: 0.85; }

.greenhouse-card__header { display: flex; justify-content: space-between; align-items: center; font-weight: 600; }
.greenhouse-card__metrics { display: flex; gap: 12px; font-size: 14px; color: #555; }
.greenhouse-card__devices { display: flex; }

@media (max-width: 480px) {
  .dashboard__grid { grid-template-columns: 1fr; }
}
```

- [ ] **Step 6: 수동 검증**

```bash
npm run dev
```
- 대시보드 탭 → 카드 3개가 위험(빨강 테두리) → 경고(노랑 테두리) → 정상(컴팩트) 순으로 정렬되어 보이는지
- 각 카드에 온도/습도 숫자, 신호등 배지, 장비 아이콘 3개(투명도로 on/off 구분)가 보이는지
- 브라우저 창을 좁혀서(또는 개발자 도구 모바일 뷰) 그리드가 1열로 바뀌는지
- 카드를 클릭해도 에러 없이 아무 반응이 없는지(Task 5에서 연결 예정이므로 정상)

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/components/ui frontend/src/components/Dashboard/GreenhouseCard.jsx frontend/src/components/Dashboard/Dashboard.jsx frontend/src/styles.css
git commit -m "feat(frontend): 온실 요약 카드 + 반응형 대시보드 그리드"
```

---

### Task 4: AlertBanner + ProductionWidget + HistoryTimeline + DemoControls로 대시보드 완성

**Files:**
- Create: `frontend/src/components/Dashboard/AlertBanner.jsx`
- Create: `frontend/src/components/Dashboard/ProductionWidget.jsx`
- Create: `frontend/src/components/Dashboard/HistoryTimeline.jsx`
- Create: `frontend/src/components/Dashboard/DemoControls.jsx`
- Modify: `frontend/src/components/Dashboard/Dashboard.jsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `farm.notifications`, `farm.production`, `farm.historyLog`, `farm.resetDemo()`, `farm.escalateDemo()` (Task 2)
- Produces: `Dashboard`가 `onReset`/`onEscalate`를 각각 `farm.resetDemo`/`farm.escalateDemo`에 직접 연결한 상태 — Task 6에서 리셋 시 알림 dismiss 상태도 같이 지우기 위해 `onReset` prop을 추가해 이 직결을 바꾼다.

- [ ] **Step 1: `AlertBanner.jsx` 작성**

```jsx
export default function AlertBanner({ notifications, onSelect }) {
  if (notifications.length === 0) {
    return <p className="alert-banner alert-banner--ok">모든 온실 정상입니다 ✅</p>;
  }

  return (
    <div className="alert-banner-list">
      {notifications.map((n) => (
        <button
          key={n.id}
          className={`alert-banner alert-banner--${n.severity}`}
          onClick={() => onSelect?.(n.greenhouseId)}
        >
          {n.severity === "critical" ? "🔴" : "🟡"} {n.greenhouseName}: {n.message}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: `ProductionWidget.jsx` 작성**

```jsx
export default function ProductionWidget({ production }) {
  const arrow = production.direction === "up" ? "▲" : "▼";
  const arrowClass = production.direction === "up" ? "is-up" : "is-down";

  return (
    <div className="production-widget">
      <div>
        <span className="production-widget__label">오늘</span>
        <span className="production-widget__value">
          {production.today}{production.unit}
        </span>
      </div>
      <div>
        <span className="production-widget__label">이번주</span>
        <span className="production-widget__value">
          {production.week}{production.unit}
        </span>
      </div>
      <span className={`production-widget__diff ${arrowClass}`}>
        {arrow} {production.diffPct}%
      </span>
    </div>
  );
}
```

- [ ] **Step 3: `HistoryTimeline.jsx` 작성**

```jsx
const TYPE_ICON = { auto: "🤖", manual: "🖐️" };

export default function HistoryTimeline({ entries }) {
  return (
    <ul className="history-timeline">
      {entries.map((entry, i) => (
        <li key={i}>
          <span className="history-timeline__time">{entry.time}</span>
          <span className="history-timeline__icon">{TYPE_ICON[entry.type]}</span>
          <span>{entry.text}</span>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 4: `DemoControls.jsx` 작성**

```jsx
export default function DemoControls({ onReset, onEscalate }) {
  return (
    <div className="demo-controls">
      <button className="demo-controls__btn" onClick={onEscalate}>
        데모: 경고→위험 승격
      </button>
      <button className="demo-controls__btn demo-controls__btn--reset" onClick={onReset}>
        리셋
      </button>
    </div>
  );
}
```

- [ ] **Step 5: `Dashboard.jsx`를 전체 위젯 조합으로 교체**

```jsx
import AlertBanner from "./AlertBanner";
import GreenhouseCard from "./GreenhouseCard";
import ProductionWidget from "./ProductionWidget";
import HistoryTimeline from "./HistoryTimeline";
import DemoControls from "./DemoControls";

const SEVERITY_ORDER = { critical: 2, warning: 1, normal: 0 };

export default function Dashboard({ farm, onSelectGreenhouse }) {
  const sorted = [...farm.greenhouses].sort(
    (a, b) => SEVERITY_ORDER[b.status] - SEVERITY_ORDER[a.status]
  );

  return (
    <div className="dashboard">
      <DemoControls onReset={farm.resetDemo} onEscalate={farm.escalateDemo} />
      <AlertBanner notifications={farm.notifications} onSelect={onSelectGreenhouse} />
      <div className="dashboard__grid">
        {sorted.map((gh) => (
          <GreenhouseCard key={gh.id} greenhouse={gh} onClick={onSelectGreenhouse} />
        ))}
      </div>
      <ProductionWidget production={farm.production} />
      <HistoryTimeline entries={farm.historyLog} />
    </div>
  );
}
```

- [ ] **Step 6: `styles.css`에 위젯 스타일 추가**

파일 끝에 추가:

```css
.demo-controls { display: flex; justify-content: flex-end; gap: 6px; margin-bottom: 8px; }
.demo-controls__btn {
  font-size: 11px;
  padding: 4px 8px;
  border: 1px solid #ccc;
  border-radius: 6px;
  background: #fafafa;
  color: #888;
  cursor: pointer;
}
.demo-controls__btn--reset { color: #555; }

.alert-banner {
  display: block;
  width: 100%;
  text-align: left;
  border: none;
  border-radius: 10px;
  padding: 10px 14px;
  margin-bottom: 8px;
  font-weight: 600;
  cursor: pointer;
}
.alert-banner--ok { background: none; color: #2e7d32; text-align: center; cursor: default; font-weight: 500; }
.alert-banner--warning { background: #fff8e1; color: #8a6d00; }
.alert-banner--critical { background: #ffebee; color: #b71c1c; }
.alert-banner-list { display: flex; flex-direction: column; }

.production-widget {
  display: flex;
  align-items: baseline;
  gap: 16px;
  background: #fff;
  border-radius: 12px;
  padding: 12px 14px;
  margin: 12px 0;
}
.production-widget__label { display: block; font-size: 12px; color: #888; }
.production-widget__value { font-size: 18px; font-weight: 700; }
.production-widget__diff.is-up { color: #2e7d32; }
.production-widget__diff.is-down { color: #e53935; }

.history-timeline { list-style: none; margin: 0; padding: 0; }
.history-timeline li {
  display: flex;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid #eee;
  font-size: 13px;
}
.history-timeline__time { color: #999; min-width: 40px; }
```

- [ ] **Step 7: 수동 검증**

```bash
npm run dev
```
- 대시보드 상단에 경고(노랑)/위험(빨강) 알림 카드 2개가 보이는지, 하나 클릭해도 아직 반응 없는지(Task 5 예정)
- "데모: 경고→위험 승격" 클릭 → 2번 온실이 위험으로 바뀌고 알림 카드가 위험 2개로 바뀌는지
- "리셋" 클릭 → 온실 상태가 초기값(정상/경고/위험 1개씩)으로 돌아오는지
- 생산량 위젯에 오늘/이번주 값과 초록 ▲ 화살표가 보이는지
- 이력 리스트에 auto/manual 아이콘이 다르게 보이는지

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/components/Dashboard frontend/src/styles.css
git commit -m "feat(frontend): 알림 배너·생산량 위젯·이력 타임라인·데모 컨트롤"
```

---

### Task 5: 온실 상세 화면 (SVG 추이 차트 포함) + 진입/복귀 연결

**Files:**
- Create: `frontend/src/components/GreenhouseDetail.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `greenhouse` shape (Task 2), `farm.controlDevice` (Task 2), `StatusBadge` (Task 3)
- Produces: `<GreenhouseDetail greenhouse onBack() onControlDevice(id, device, action) />` — App.jsx가 `selectedGreenhouseId` state로 이 화면과 `Dashboard`를 전환한다. Task 6은 이 `App.jsx` 버전을 다시 확장한다.

- [ ] **Step 1: `GreenhouseDetail.jsx` 작성**

```jsx
import { useState } from "react";
import StatusBadge from "./ui/StatusBadge";

function buildLinePath(values, width, height) {
  if (values.length === 0) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const stepX = width / (values.length - 1 || 1);

  return values
    .map((v, i) => {
      const x = i * stepX;
      const y = height - ((v - min) / range) * height;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export default function GreenhouseDetail({ greenhouse, onBack, onControlDevice }) {
  const [toast, setToast] = useState("");
  const width = 260;
  const height = 80;
  const tempPath = buildLinePath(
    greenhouse.history.map((h) => h.temperature),
    width,
    height
  );
  const humidityPath = buildLinePath(
    greenhouse.history.map((h) => h.humidity),
    width,
    height
  );

  function handleAction() {
    onControlDevice(
      greenhouse.id,
      greenhouse.recommendedAction.device,
      greenhouse.recommendedAction.action
    );
    setToast(`${greenhouse.recommendedAction.label} 완료했어요.`);
    setTimeout(() => setToast(""), 2000);
  }

  return (
    <div className="greenhouse-detail">
      <button className="greenhouse-detail__back" onClick={onBack}>
        ← 대시보드로
      </button>

      <div className="greenhouse-detail__header">
        <h2>{greenhouse.name}</h2>
        <StatusBadge status={greenhouse.status} />
      </div>
      {greenhouse.cause && (
        <p className="greenhouse-detail__cause">{greenhouse.cause}</p>
      )}

      {greenhouse.recommendedAction && (
        <button className="greenhouse-detail__action" onClick={handleAction}>
          [{greenhouse.recommendedAction.label}]
        </button>
      )}
      {toast && <p className="greenhouse-detail__toast">{toast}</p>}

      <div className="greenhouse-detail__chart">
        <p>최근 온도·습도 추이</p>
        <svg viewBox={`0 0 ${width} ${height}`} className="greenhouse-detail__svg">
          <path d={tempPath} className="chart-line chart-line--temp" fill="none" />
          <path d={humidityPath} className="chart-line chart-line--humidity" fill="none" />
        </svg>
        <div className="greenhouse-detail__legend">
          <span className="chart-legend chart-legend--temp">● 온도</span>
          <span className="chart-legend chart-legend--humidity">● 습도</span>
        </div>
        <div className="greenhouse-detail__times">
          {greenhouse.history.map((h) => (
            <span key={h.time}>{h.time}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: `App.jsx`에 상세 화면 진입/복귀 상태 연결**

```jsx
import { useState } from "react";
import ChatScreen from "./components/ChatScreen";
import TopNav from "./components/TopNav";
import Dashboard from "./components/Dashboard/Dashboard";
import GreenhouseDetail from "./components/GreenhouseDetail";
import { useFarmData } from "./lib/useFarmData";

export default function App() {
  const [view, setView] = useState("chat");
  const [selectedGreenhouseId, setSelectedGreenhouseId] = useState(null);
  const farm = useFarmData();
  const warningCount = farm.notifications.filter(
    (n) => n.severity === "warning"
  ).length;

  function handleChangeView(nextView) {
    setSelectedGreenhouseId(null);
    setView(nextView);
  }

  const selectedGreenhouse = farm.greenhouses.find(
    (gh) => gh.id === selectedGreenhouseId
  );

  return (
    <div className="app">
      <h1>SolTalk 🌱</h1>
      <TopNav view={view} onChangeView={handleChangeView} warningCount={warningCount} />
      <div className={view === "chat" ? "screen" : "screen is-hidden"}>
        <ChatScreen />
      </div>
      <div className={view === "dashboard" ? "screen" : "screen is-hidden"}>
        {selectedGreenhouse ? (
          <GreenhouseDetail
            greenhouse={selectedGreenhouse}
            onBack={() => setSelectedGreenhouseId(null)}
            onControlDevice={farm.controlDevice}
          />
        ) : (
          <Dashboard farm={farm} onSelectGreenhouse={setSelectedGreenhouseId} />
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: `styles.css`에 상세 화면/차트 스타일 추가**

파일 끝에 추가:

```css
.greenhouse-detail { flex: 1; overflow-y: auto; padding: 8px 0; display: flex; flex-direction: column; gap: 10px; }
.greenhouse-detail__back { align-self: flex-start; border: none; background: none; color: #2e7d32; cursor: pointer; padding: 4px 0; }
.greenhouse-detail__header { display: flex; align-items: center; gap: 8px; }
.greenhouse-detail__cause { color: #b71c1c; font-size: 14px; }
.greenhouse-detail__action {
  align-self: flex-start;
  background: #2e7d32;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 16px;
  cursor: pointer;
}
.greenhouse-detail__toast { background: #eaf7ea; color: #2e7d32; padding: 6px 10px; border-radius: 8px; font-size: 13px; }
.greenhouse-detail__chart { background: #fff; border-radius: 12px; padding: 12px; }
.greenhouse-detail__svg { width: 100%; height: 80px; }
.chart-line--temp { stroke: #e53935; stroke-width: 2; }
.chart-line--humidity { stroke: #1e88e5; stroke-width: 2; }
.greenhouse-detail__legend { display: flex; gap: 12px; font-size: 12px; margin-top: 4px; }
.chart-legend--temp { color: #e53935; }
.chart-legend--humidity { color: #1e88e5; }
.greenhouse-detail__times { display: flex; justify-content: space-between; font-size: 11px; color: #999; margin-top: 2px; }
```

- [ ] **Step 4: 수동 검증**

```bash
npm run dev
```
- 대시보드에서 경고(2번 온실) 카드 클릭 → 상세 화면 진입, 원인 문구 + `[창문 열기]` 버튼 + 빨강(온도)/파랑(습도) SVG 라인 + 시간 라벨이 보이는지
- `[창문 열기]` 클릭 → 토스트 "창문 열기 완료했어요." 표시, 장비 아이콘 상태 변경, 상태가 경고→정상으로 완화되어 원인 문구/버튼이 사라지는지
- "← 대시보드로" 클릭 → 대시보드로 복귀, 방금 그 온실이 정상(컴팩트) 카드로 보이는지
- 위험(3번) 카드도 같은 방식으로 확인(`[차광막 열기]` → 위험→경고로 완화)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/components/GreenhouseDetail.jsx frontend/src/App.jsx frontend/src/styles.css
git commit -m "feat(frontend): 온실 상세 화면(SVG 추이 차트) + 진입/복귀 연결"
```

---

### Task 6: 알림 센터(CriticalBanner + NotificationInbox) + 데모 승격 연출 + 알림음

**Files:**
- Create: `frontend/src/components/NotificationCenter/CriticalBanner.jsx`
- Create: `frontend/src/components/NotificationCenter/NotificationInbox.jsx`
- Modify: `frontend/src/components/TopNav.jsx`
- Modify: `frontend/src/components/Dashboard/Dashboard.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `farm.notifications`, `farm.greenhouses`, `farm.controlDevice`, `farm.resetDemo` (Task 2, 4)
- Produces: 최종 `App.jsx` — 이 태스크로 계획의 모든 화면이 연결된다.

- [ ] **Step 1: `NotificationCenter/CriticalBanner.jsx` 작성**

```jsx
import { useEffect, useRef } from "react";

function playBeep() {
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
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

  useEffect(() => {
    if (!canPlaySound) return;
    notifications.forEach((n) => {
      if (!playedIdsRef.current.has(n.id)) {
        playedIdsRef.current.add(n.id);
        try {
          playBeep();
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

- [ ] **Step 2: `NotificationCenter/NotificationInbox.jsx` 작성**

```jsx
export default function NotificationInbox({ notifications, onAction, onDismiss, onClose }) {
  return (
    <div className="notification-inbox">
      <div className="notification-inbox__header">
        <span>알림함</span>
        <button onClick={onClose}>닫기</button>
      </div>
      {notifications.length === 0 && (
        <p className="notification-inbox__empty">알림이 없어요.</p>
      )}
      <ul>
        {notifications.map((n) => (
          <li key={n.id}>
            <span>🟡 {n.greenhouseName}: {n.message}</span>
            <div>
              <button onClick={() => onAction(n.greenhouseId)}>조치</button>
              <button onClick={() => onDismiss(n.greenhouseId)}>✕</button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 3: `TopNav.jsx`를 배지 클릭 가능하도록 교체**

```jsx
export default function TopNav({ view, onChangeView, warningCount, onOpenInbox }) {
  return (
    <nav className="top-nav">
      <button
        className={`top-nav__tab ${view === "chat" ? "is-active" : ""}`}
        onClick={() => onChangeView("chat")}
      >
        채팅
      </button>
      <button
        className={`top-nav__tab ${view === "dashboard" ? "is-active" : ""}`}
        onClick={() => onChangeView("dashboard")}
      >
        대시보드
      </button>
      {warningCount > 0 && (
        <button className="top-nav__badge" onClick={onOpenInbox}>
          🟡 {warningCount}
        </button>
      )}
    </nav>
  );
}
```

- [ ] **Step 4: `Dashboard.jsx`의 리셋 버튼을 `onReset` prop으로 위임**

`Dashboard.jsx`에서 함수 시그니처와 `DemoControls` 호출 부분만 아래처럼 바꾼다 (나머지는 Task 4와 동일).

```jsx
export default function Dashboard({ farm, onSelectGreenhouse, onReset }) {
  const sorted = [...farm.greenhouses].sort(
    (a, b) => SEVERITY_ORDER[b.status] - SEVERITY_ORDER[a.status]
  );

  return (
    <div className="dashboard">
      <DemoControls onReset={onReset} onEscalate={farm.escalateDemo} />
      <AlertBanner notifications={farm.notifications} onSelect={onSelectGreenhouse} />
      <div className="dashboard__grid">
        {sorted.map((gh) => (
          <GreenhouseCard key={gh.id} greenhouse={gh} onClick={onSelectGreenhouse} />
        ))}
      </div>
      <ProductionWidget production={farm.production} />
      <HistoryTimeline entries={farm.historyLog} />
    </div>
  );
}
```

- [ ] **Step 5: `App.jsx`를 알림 센터까지 연결한 최종본으로 교체**

```jsx
import { useRef, useState } from "react";
import ChatScreen from "./components/ChatScreen";
import TopNav from "./components/TopNav";
import Dashboard from "./components/Dashboard/Dashboard";
import GreenhouseDetail from "./components/GreenhouseDetail";
import CriticalBanner from "./components/NotificationCenter/CriticalBanner";
import NotificationInbox from "./components/NotificationCenter/NotificationInbox";
import { useFarmData } from "./lib/useFarmData";

export default function App() {
  const [view, setView] = useState("chat");
  const [selectedGreenhouseId, setSelectedGreenhouseId] = useState(null);
  const [inboxOpen, setInboxOpen] = useState(false);
  const [dismissedIds, setDismissedIds] = useState([]);
  const hasInteractedRef = useRef(false);
  const farm = useFarmData();

  const criticalNotifications = farm.notifications.filter(
    (n) => n.severity === "critical" && !dismissedIds.includes(n.greenhouseId)
  );
  const warningNotifications = farm.notifications.filter(
    (n) => n.severity === "warning" && !dismissedIds.includes(n.greenhouseId)
  );

  function handleChangeView(nextView) {
    setSelectedGreenhouseId(null);
    setView(nextView);
  }

  function handleAction(greenhouseId) {
    const gh = farm.greenhouses.find((g) => g.id === greenhouseId);
    if (gh?.recommendedAction) {
      farm.controlDevice(
        greenhouseId,
        gh.recommendedAction.device,
        gh.recommendedAction.action
      );
    }
  }

  function handleDismiss(greenhouseId) {
    setDismissedIds((prev) => [...prev, greenhouseId]);
  }

  function handleReset() {
    farm.resetDemo();
    setDismissedIds([]);
  }

  const selectedGreenhouse = farm.greenhouses.find(
    (gh) => gh.id === selectedGreenhouseId
  );

  return (
    <div
      className="app"
      onClickCapture={() => {
        hasInteractedRef.current = true;
      }}
    >
      <CriticalBanner
        notifications={criticalNotifications}
        onAction={handleAction}
        onDismiss={handleDismiss}
        canPlaySound={hasInteractedRef.current}
      />
      <h1>SolTalk 🌱</h1>
      <TopNav
        view={view}
        onChangeView={handleChangeView}
        warningCount={warningNotifications.length}
        onOpenInbox={() => setInboxOpen(true)}
      />
      {inboxOpen && (
        <NotificationInbox
          notifications={warningNotifications}
          onAction={handleAction}
          onDismiss={handleDismiss}
          onClose={() => setInboxOpen(false)}
        />
      )}
      <div className={view === "chat" ? "screen" : "screen is-hidden"}>
        <ChatScreen />
      </div>
      <div className={view === "dashboard" ? "screen" : "screen is-hidden"}>
        {selectedGreenhouse ? (
          <GreenhouseDetail
            greenhouse={selectedGreenhouse}
            onBack={() => setSelectedGreenhouseId(null)}
            onControlDevice={farm.controlDevice}
          />
        ) : (
          <Dashboard
            farm={farm}
            onSelectGreenhouse={setSelectedGreenhouseId}
            onReset={handleReset}
          />
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 6: `styles.css`에 알림 센터 스타일 추가**

파일 끝에 추가:

```css
.critical-banner-stack { display: flex; flex-direction: column; }
.critical-banner {
  background: var(--color-critical);
  color: #fff;
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  animation: banner-in 0.3s ease-out;
}
.critical-banner__actions { display: flex; gap: 8px; }
.critical-banner__actions button { border: none; border-radius: 6px; padding: 4px 10px; cursor: pointer; }
.critical-banner__dismiss { background: transparent; color: #fff; }

@keyframes banner-in {
  from { transform: translateY(-100%); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.top-nav__badge {
  border: none;
  border-radius: 999px;
  background: var(--color-warning);
  color: #3a2a00;
  padding: 2px 8px;
  font-size: 12px;
  cursor: pointer;
  margin-left: 4px;
}

.notification-inbox { background: #fff; border: 1px solid #eee; border-radius: 10px; padding: 10px; margin: 8px 0; }
.notification-inbox__header { display: flex; justify-content: space-between; font-weight: 600; margin-bottom: 6px; }
.notification-inbox ul { list-style: none; margin: 0; padding: 0; }
.notification-inbox li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
}
```

(기존 `.top-nav__badge`는 Task 2에서 `<span>`용으로 추가했던 규칙을 이 `<button>`용 규칙이 덮어쓴다 — 같은 선택자이므로 파일 끝에 다시 적으면 나중 규칙이 우선 적용된다.)

- [ ] **Step 7: 수동 검증**

```bash
npm run dev
```
- 처음 진입 시 3번 온실(위험) 빨간 배너가 화면 최상단에 슬라이드인 애니메이션과 함께 보이는지
- 아무 버튼이나 한 번 클릭한 뒤(사운드 활성화) 배너가 새로 뜰 때 짧은 비프음이 나는지
- 배너의 "바로 조치" 클릭 → 위험→경고로 완화, 배너가 사라지는지 / "✕" 클릭 → 배너만 닫히고 상태는 안 바뀌는지
- "대시보드" 탭 옆 노란 배지 클릭 → 알림함이 열리고 경고 온실 목록이 보이는지, "조치"/"✕" 동작 확인
- "리셋" 클릭 → 온실 상태와 닫았던 알림이 모두 초기화되는지
- "데모: 경고→위험 승격" 클릭 → 새 크리티컬 배너가 애니메이션과 함께 나타나는지 (노랑→빨강 승격 데모 임팩트 포인트)

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/components/NotificationCenter frontend/src/components/TopNav.jsx frontend/src/components/Dashboard/Dashboard.jsx frontend/src/App.jsx frontend/src/styles.css
git commit -m "feat(frontend): 크리티컬 배너·알림함·데모 승격 연출·알림음"
```

---

## 계획 완료 후 남는 것 (`Docs/smartfarm_ui_elements.md` 기준)

- STT(Web Speech API) 연결 — `todo/FRONTEND.md`의 별도 TODO, 이 계획 범위 아님
- 실제 백엔드 다중 온실 API 연동 — `useFarmData.js` 내부만 교체하면 되도록 경계를 둠
