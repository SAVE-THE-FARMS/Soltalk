# 프론트-백엔드 연동 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SolTalk 프론트엔드를 실제 백엔드(`/api/chat`, `/api/transcribe`, `/api/state`, `/api/alerts*`, `/api/reset`)에 연동하고, 필수 요구사항(챗/STT/모바일 반응형)과 대시보드·알림 실연동까지 마친다.

**Architecture:** `frontend/src/api.js`를 유일한 백엔드 호출 지점으로 유지하고, `useFarmData` 훅이 백엔드 응답을 프론트 camelCase 형태로 변환해 컴포넌트에 내려준다. 컴포넌트는 변환된 형태만 알면 되고 백엔드 wire format을 직접 다루지 않는다.

**Tech Stack:** React 18 + Vite. 테스트 프레임워크 없음(브라우저 수동 검증). 백엔드는 FastAPI, `uv run python -m app.server`로 `http://localhost:8000`에서 실행.

## Global Constraints

- 소스 오브 트루스 = 백엔드. 프론트가 백엔드 계약(필드/타입)에 맞춘다 (`todo/FRONTEND_통합_필수.md`).
- 모바일 우선(360~430px), 가로 스크롤 금지, 터치 영역 44px 이상, 작은 아이콘만으로 기능 숨기지 않기.
- STT는 백엔드의 `gpt-4o-transcribe` 경유 (`POST /api/transcribe`) — 브라우저 Web Speech API 아님.
- 이 프로젝트에 프론트 테스트 러너가 없음 — 각 태스크는 `npm run dev`(프론트) + `uv run python -m app.server`(백엔드)를 함께 띄운 뒤 브라우저에서 수동으로 동작을 확인한다. 새 테스트 프레임워크를 들이지 않는다 (스펙에서 명시적으로 결정).
- 세션/브라우저 저장은 `localStorage`만 사용.
- 상세 설계 근거: `Docs/superpowers/specs/2026-07-09-frontend-backend-integration-design.md`

---

### Task 1: 챗 연동 (`/api/chat` + 세션 유지 + actions_taken 강조)

**Files:**
- Create: `frontend/src/lib/session.js`
- Modify: `frontend/src/api.js` (전체 재작성)
- Modify: `frontend/src/components/ChatScreen.jsx` (전체 재작성)

**Interfaces:**
- Produces: `getSessionId(): string` (session.js) — 이후 다른 태스크는 쓰지 않음, api.js 내부에서만 사용.
- Produces: `sendMessage(message: string): Promise<{reply: string, actions_taken: Array<{device,greenhouse_id,action,success}>, updated_state: object}>` (api.js) — Task 4 이후에도 이 시그니처 유지.

- [ ] **Step 1: `session.js` 작성**

`frontend/src/lib/session.js`:
```js
// 챗 세션 id 관리. 재질문 맥락(히스토리)을 유지하려면 매 요청에 같은 session_id를 보내야 한다.
const STORAGE_KEY = "soltalk_session_id";

export function getSessionId() {
  let id = localStorage.getItem(STORAGE_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(STORAGE_KEY, id);
  }
  return id;
}
```

- [ ] **Step 2: `api.js`를 `/api/chat` 기준으로 재작성**

`frontend/src/api.js` (전체 교체):
```js
// 백엔드 호출 담당.
// 접점 계약: Docs/superpowers/specs/2026-07-09-frontend-backend-integration-design.md

import { getSessionId } from "./lib/session";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function requestJson(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) throw new Error(`서버 오류: ${res.status}`);
  return res.json();
}

export async function sendMessage(message) {
  // { reply, actions_taken, updated_state }
  return requestJson("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: getSessionId() }),
  });
}
```

- [ ] **Step 3: `ChatScreen.jsx`에서 `/chat` 대신 `/api/chat` 사용 + `actions_taken` 기반 강조로 교체**

`frontend/src/components/ChatScreen.jsx` (전체 교체 — 마이크 부분은 Task 2에서 다시 손댐):
```jsx
import { useRef, useState } from "react";
import { sendMessage } from "../api";

export default function ChatScreen() {
  const [messages, setMessages] = useState([]); // { id, role: "user"|"bot", text, pending?, success? }
  const [input, setInput] = useState("");
  const nextIdRef = useRef(0);

  async function handleSend() {
    const text = input.trim();
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
      const { reply, actions_taken } = await sendMessage(text);
      const success = actions_taken.some((a) => a.success);
      setMessages((m) =>
        m.map((msg) =>
          msg.id === botId ? { id: botId, role: "bot", text: reply, success } : msg
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
    // TODO(Task 2): MediaRecorder 기반 녹음으로 교체.
    alert("음성 입력은 아직 미구현");
  }

  return (
    <div className="chat-screen">
      <div className="chat">
        {messages.length === 0 && (
          <p className="hint">예: "차광막 닫아줘", "지금 온도 몇 도야?"</p>
        )}
        {messages.map((m) => {
          const isAction = m.role === "bot" && !m.pending && m.success;
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

- [ ] **Step 4: 수동 검증**

터미널 1: `cd backend && uv run python -m app.server`
터미널 2: `cd frontend && npm run dev` → `http://localhost:5173` 접속

확인:
1. "차광막 닫아줘" 전송 → 응답 말풍선에 ✅ 강조 표시(실제 `actions_taken[0].success === true`이기 때문).
2. "지금 온도 몇 도야?" 전송 → 강조 없이 일반 말풍선.
3. 브라우저 개발자도구 → Application → Local Storage에 `soltalk_session_id` 키가 생성됐는지 확인.
4. 페이지를 새로고침한 뒤 "그거 다시 열어줘" 전송 → 이전 맥락("차광막")을 참조해 응답하는지 확인 (세션이 유지되고 있다는 증거).

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/session.js frontend/src/api.js frontend/src/components/ChatScreen.jsx
git commit -m "feat(frontend): /api/chat 연동 + 세션 유지 + actions_taken 기반 액션 강조"
```

---

### Task 2: STT (음성 입력) — 녹음/무음 자동종료/`/api/transcribe`

**Files:**
- Create: `frontend/src/lib/useRecorder.js`
- Modify: `frontend/src/api.js` (함수 추가)
- Modify: `frontend/src/components/ChatScreen.jsx` (마이크 핸들러 교체)
- Modify: `frontend/src/styles.css` (녹음 표시 스타일 추가)

**Interfaces:**
- Consumes: Task 1의 `sendMessage` (변경 없음).
- Produces: `useRecorder({onStop, onError}): {isRecording: boolean, elapsedSeconds: number, start(): void, stop(): void}` — 이후 태스크에서는 쓰지 않음(ChatScreen 내부 전용).
- Produces: `transcribeAudio(blob: Blob): Promise<string>` (api.js).

- [ ] **Step 1: `useRecorder.js` 작성 — 녹음 + 무음 감지**

`frontend/src/lib/useRecorder.js`:
```js
import { useCallback, useEffect, useRef, useState } from "react";

const SILENCE_THRESHOLD = 0.02; // 0~1 RMS 기준, 이 아래면 "무음"
const SILENCE_DURATION_MS = 2500; // 무음이 이만큼 지속되면 자동 종료

export function useRecorder({ onStop, onError }) {
  const [isRecording, setIsRecording] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const silenceStartRef = useRef(null);
  const rafRef = useRef(null);
  const timerRef = useRef(null);

  const cleanup = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    clearInterval(timerRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    audioContextRef.current?.close();
    audioContextRef.current = null;
    streamRef.current = null;
    silenceStartRef.current = null;
  }, []);

  const stop = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const monitorVolume = useCallback(() => {
    const analyser = analyserRef.current;
    if (!analyser) return;
    const data = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(data);
    const rms = Math.sqrt(
      data.reduce((sum, v) => sum + ((v - 128) / 128) ** 2, 0) / data.length
    );

    if (rms < SILENCE_THRESHOLD) {
      if (silenceStartRef.current == null) silenceStartRef.current = performance.now();
      else if (performance.now() - silenceStartRef.current > SILENCE_DURATION_MS) {
        stop();
        return;
      }
    } else {
      silenceStartRef.current = null;
    }
    rafRef.current = requestAnimationFrame(monitorVolume);
  }, [stop]);

  const start = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);
      audioContextRef.current = audioContext;
      analyserRef.current = analyser;

      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        cleanup();
        setIsRecording(false);
        onStop?.(blob);
      };
      mediaRecorderRef.current = recorder;
      recorder.start();

      setIsRecording(true);
      setElapsedSeconds(0);
      silenceStartRef.current = null;
      timerRef.current = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
      rafRef.current = requestAnimationFrame(monitorVolume);
    } catch (e) {
      onError?.(e);
    }
  }, [cleanup, monitorVolume, onStop, onError]);

  useEffect(() => cleanup, [cleanup]);

  return { isRecording, elapsedSeconds, start, stop };
}
```

- [ ] **Step 2: `api.js`에 `transcribeAudio` 추가**

`frontend/src/api.js` 맨 끝에 추가:
```js

export async function transcribeAudio(blob) {
  const form = new FormData();
  form.append("audio", blob, "recording.webm");
  const res = await fetch(`${API_BASE}/api/transcribe`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`음성 인식 실패: ${res.status}`);
  const data = await res.json();
  return data.text;
}
```

- [ ] **Step 3: `ChatScreen.jsx`에서 마이크 버튼을 실제 녹음 흐름으로 교체**

`frontend/src/components/ChatScreen.jsx` (전체 교체):
```jsx
import { useRef, useState } from "react";
import { sendMessage, transcribeAudio } from "../api";
import { useRecorder } from "../lib/useRecorder";

export default function ChatScreen() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [micError, setMicError] = useState("");
  const nextIdRef = useRef(0);

  const { isRecording, elapsedSeconds, start, stop } = useRecorder({
    onStop: async (blob) => {
      try {
        const text = await transcribeAudio(blob);
        setInput(text);
      } catch (e) {
        setMicError("음성 인식에 실패했어요. 다시 시도해주세요.");
      }
    },
    onError: () => {
      setMicError("마이크를 사용할 수 없어요. 브라우저 권한을 확인해주세요 (크롬 권장).");
    },
  });

  async function handleSend() {
    const text = input.trim();
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
      const { reply, actions_taken } = await sendMessage(text);
      const success = actions_taken.some((a) => a.success);
      setMessages((m) =>
        m.map((msg) =>
          msg.id === botId ? { id: botId, role: "bot", text: reply, success } : msg
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
    setMicError("");
    if (isRecording) stop();
    else start();
  }

  return (
    <div className="chat-screen">
      <div className="chat">
        {messages.length === 0 && (
          <p className="hint">예: "차광막 닫아줘", "지금 온도 몇 도야?"</p>
        )}
        {messages.map((m) => {
          const isAction = m.role === "bot" && !m.pending && m.success;
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
      </div>

      {micError && <p className="mic-error">{micError}</p>}

      <div className="composer">
        <button
          className={`mic-btn${isRecording ? " mic-btn--recording" : ""}`}
          onClick={handleMic}
          title="음성 입력"
        >
          {isRecording ? `⏹ ${elapsedSeconds}s` : "🎤"}
        </button>
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

- [ ] **Step 4: 녹음 표시 스타일 추가**

`frontend/src/styles.css` 맨 끝에 추가:
```css

.mic-btn {
  padding: 10px 14px;
  border: none;
  border-radius: 8px;
  background: #eee;
  cursor: pointer;
  font-size: 16px;
  min-width: 44px;
  min-height: 44px;
}
.mic-btn--recording {
  background: #e53935;
  color: #fff;
  animation: mic-pulse 1s ease-in-out infinite;
}
@keyframes mic-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(229, 57, 53, 0.5); }
  50% { box-shadow: 0 0 0 8px rgba(229, 57, 53, 0); }
}
.mic-error { color: #b71c1c; font-size: 13px; margin: 4px 0; }
```

- [ ] **Step 5: 수동 검증**

백엔드/프론트 둘 다 켠 상태에서:
1. 🎤 클릭 → 버튼이 빨갛게 펄스 애니메이션 + `⏹ 0s`부터 타이머 증가 확인.
2. "차광막 닫아줘"라고 말한 뒤 2~3초간 조용히 있기 → 자동으로 녹음 종료, 입력창에 인식된 텍스트가 채워지는지 확인.
3. 녹음 중 다시 버튼 클릭 → 수동 종료도 되는지 확인.
4. 브라우저 마이크 권한을 거부한 상태로 🎤 클릭 → `mic-error` 문구가 뜨는지 확인.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/lib/useRecorder.js frontend/src/api.js frontend/src/components/ChatScreen.jsx frontend/src/styles.css
git commit -m "feat(frontend): STT 녹음(무음 자동종료) + /api/transcribe 연동"
```

---

### Task 3: 모바일 반응형 디자인

**Files:**
- Modify: `frontend/src/styles.css`

**Interfaces:** 없음 (스타일만 변경, JS 인터페이스 없음).

- [ ] **Step 1: 반응형 브레이크포인트 + 가로 스크롤 방지 + 터치 영역 확대**

`frontend/src/styles.css` 맨 끝에 추가:
```css

@media (min-width: 600px) {
  .app { max-width: 600px; }
}
@media (min-width: 900px) {
  .app { max-width: 720px; }
  .dashboard__grid { grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }
}

.greenhouse-detail__chart { overflow-x: auto; }

.composer button,
.composer input,
.top-nav__tab {
  min-height: 44px;
}
```

- [ ] **Step 2: 수동 검증**

Chrome 개발자도구 → 기기 툴바(Ctrl+Shift+M)로 아래 폭에서 확인:
1. 375px (iPhone SE급): 가로 스크롤 없음, 버튼/입력창이 손가락으로 누르기 충분한 크기인지.
2. 768px (태블릿): `.app` 폭이 600px로 넓어지는지.
3. 1280px (데스크톱): `.app` 폭이 720px, 대시보드 그리드 컬럼이 더 넓게 배치되는지.
4. 온실 상세 화면의 SVG 차트가 있는 온실을 열어서, 화면이 좁을 때 차트 영역 안에서만 스크롤되고 전체 페이지가 가로로 밀리지 않는지.

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/styles.css
git commit -m "feat(frontend): 모바일 우선 반응형 브레이크포인트 + 터치 영역 확대"
```

---

### Task 4: 대시보드 데이터 계층 (`useFarmData` 실 API 연동)

**Files:**
- Modify: `frontend/src/api.js` (함수 추가)
- Modify: `frontend/src/lib/mockData.js` (온실 목록 제거, production/history_log만 유지)
- Modify: `frontend/src/lib/labels.js` (미사용 `ACTION_LABEL` 제거)
- Modify: `frontend/src/lib/useFarmData.js` (전체 재작성)

**Interfaces:**
- Produces: `getState(): Promise<Array<{id:number,name,status,temperature,humidity,devices,last_updated}>>` (api.js)
- Produces: `getGreenhouseDetail(id:number): Promise<{id,status,reason,recommended_action,current_values,history: Array<{timestamp,humidity}>}>` (api.js) — Task 6에서 `GreenhouseDetail.jsx`가 직접 사용.
- Produces: `getAlerts(): Promise<Array<{id:string,level,greenhouse_id,message,created_at,escalated,action}>>` (api.js)
- Produces: `runAlertAction(alertId:string): Promise<{success,message,updated_state}>`, `dismissAlert(alertId:string): Promise<{success}>`, `resetDemo(): Promise<{success}>` (api.js)
- Produces: `useFarmData(): {greenhouses: Array<{id,name,status,temperature,humidity,devices,reason,activeAlert:{id,action,message}|null}>, notifications: Array<{id,level,greenhouseId,greenhouseName,message,action}>, production, historyLog, loading, error, runAction(alertId), dismiss(alertId), resetAll()}` — Task 5/6이 이 형태를 그대로 소비.

- [ ] **Step 1: `api.js`에 대시보드/알림 관련 함수 추가**

`frontend/src/api.js` 맨 끝에 추가:
```js

export async function getState() {
  const { greenhouses } = await requestJson("/api/state");
  return greenhouses;
}

export async function getGreenhouseDetail(id) {
  return requestJson(`/api/state/${id}`);
}

export async function getAlerts() {
  const { alerts } = await requestJson("/api/alerts");
  return alerts;
}

export async function runAlertAction(alertId) {
  return requestJson(`/api/alerts/${alertId}/action`, { method: "POST" });
}

export async function dismissAlert(alertId) {
  return requestJson(`/api/alerts/${alertId}/dismiss`, { method: "POST" });
}

export async function resetDemo() {
  return requestJson("/api/reset", { method: "POST" });
}
```

- [ ] **Step 2: `mockData.js`에서 온실 목록 제거 (생산량/이력만 유지)**

`frontend/src/lib/mockData.js` (전체 교체):
```js
// 생산량 위젯 / 처리 이력 위젯용 목업 데이터.
// 백엔드에 대응 API가 없어(GET /api/production, GET /api/logs 미구현) 계속 목데이터로 유지한다.
// 근거: Docs/superpowers/specs/2026-07-09-frontend-backend-integration-design.md

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

- [ ] **Step 3: `labels.js`에서 미사용 `ACTION_LABEL` 제거**

`frontend/src/lib/labels.js` (전체 교체):
```js
export const DEVICE_LABEL = { shade: "차광막", window: "창문", irrigation: "관수" };
export const SEVERITY_ORDER = { critical: 2, warning: 1, normal: 0 };
```

- [ ] **Step 4: `useFarmData.js`를 실 API 기반으로 재작성**

`frontend/src/lib/useFarmData.js` (전체 교체):
```js
import { useCallback, useEffect, useState } from "react";
import { dismissAlert, getAlerts, getState, resetDemo, runAlertAction } from "../api";
import { INITIAL_HISTORY_LOG, INITIAL_PRODUCTION } from "./mockData";
import { SEVERITY_ORDER } from "./labels";

function joinGreenhousesWithAlerts(greenhouses, alerts) {
  const alertByGreenhouseId = new Map(alerts.map((a) => [a.greenhouse_id, a]));
  return greenhouses.map((gh) => {
    const alert = alertByGreenhouseId.get(gh.id);
    return {
      id: gh.id,
      name: gh.name,
      status: gh.status,
      temperature: gh.temperature,
      humidity: gh.humidity,
      devices: gh.devices,
      reason: alert?.message ?? null,
      activeAlert: alert ? { id: alert.id, action: alert.action, message: alert.message } : null,
    };
  });
}

function toNotifications(alerts, greenhouses) {
  const nameById = new Map(greenhouses.map((gh) => [gh.id, gh.name]));
  return [...alerts]
    .sort((a, b) => SEVERITY_ORDER[b.level] - SEVERITY_ORDER[a.level])
    .map((a) => ({
      id: a.id,
      level: a.level,
      greenhouseId: a.greenhouse_id,
      greenhouseName: nameById.get(a.greenhouse_id) ?? `${a.greenhouse_id}번 온실`,
      message: a.message,
      action: a.action,
    }));
}

export function useFarmData() {
  const [greenhouses, setGreenhouses] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [production] = useState(INITIAL_PRODUCTION);
  const [historyLog] = useState(INITIAL_HISTORY_LOG);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [rawGreenhouses, rawAlerts] = await Promise.all([getState(), getAlerts()]);
      setGreenhouses(joinGreenhousesWithAlerts(rawGreenhouses, rawAlerts));
      setNotifications(toNotifications(rawAlerts, rawGreenhouses));
      setError(null);
    } catch (e) {
      setError("대시보드 데이터를 불러오지 못했어요.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const runAction = useCallback(
    async (alertId) => {
      await runAlertAction(alertId);
      await refresh();
    },
    [refresh]
  );

  const dismiss = useCallback(
    async (alertId) => {
      await dismissAlert(alertId);
      await refresh();
    },
    [refresh]
  );

  const resetAll = useCallback(async () => {
    await resetDemo();
    await refresh();
  }, [refresh]);

  return {
    greenhouses,
    notifications,
    production,
    historyLog,
    loading,
    error,
    runAction,
    dismiss,
    resetAll,
  };
}
```

- [ ] **Step 5: 수동 검증**

이 단계에서는 아직 `App.jsx`가 옛 필드명(`severity`, `recommendedAction`, `cause`)을 쓰고 있어 화면이 깨질 수 있음 — Task 5에서 맞춘다. 지금은 콘솔 확인만:
1. 브라우저 개발자도구 콘솔에서 에러 없이 앱이 로드되는지 확인 (화면 내용이 이상해도 괜찮음, JS 에러가 없는지만 확인).
2. Network 탭에서 `/api/state`, `/api/alerts` 요청이 200으로 성공하는지 확인.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/api.js frontend/src/lib/mockData.js frontend/src/lib/labels.js frontend/src/lib/useFarmData.js
git commit -m "feat(frontend): useFarmData를 실제 백엔드(/api/state, /api/alerts) 기반으로 교체"
```

---

### Task 5: App/Dashboard 연동 (승격 버튼 제거, 실 데이터 와이어링)

**Files:**
- Modify: `frontend/src/App.jsx` (전체 재작성)
- Modify: `frontend/src/components/Dashboard/Dashboard.jsx` (전체 재작성)
- Modify: `frontend/src/components/Dashboard/DemoControls.jsx` (전체 재작성)
- Modify: `frontend/src/styles.css` (로딩/에러 표시 스타일 추가)

**Interfaces:**
- Consumes: Task 4의 `useFarmData()` 반환 형태 그대로.
- Produces: `App`이 `CriticalBanner`/`NotificationInbox`/`GreenhouseDetail`에 `onAction(alertId)`/`onDismiss(alertId)` 콜백을 내려줌 — Task 6이 이 시그니처(그린하우스 id가 아니라 **alert id**를 받음)에 맞춰 구현.

- [ ] **Step 1: `App.jsx`에서 `dismissedIds`/승격 로직 제거, alertId 기반 콜백으로 교체**

`frontend/src/App.jsx` (전체 교체):
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
  const hasInteractedRef = useRef(false);
  const farm = useFarmData();

  const criticalNotifications = farm.notifications.filter((n) => n.level === "critical");
  const warningNotifications = farm.notifications.filter((n) => n.level === "warning");

  function handleChangeView(nextView) {
    setSelectedGreenhouseId(null);
    setView(nextView);
  }

  function handleAction(alertId) {
    farm.runAction(alertId);
  }

  function handleDismiss(alertId) {
    farm.dismiss(alertId);
  }

  function handleReset() {
    farm.resetAll();
  }

  const selectedGreenhouse = farm.greenhouses.find((gh) => gh.id === selectedGreenhouseId);

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
            onAction={handleAction}
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

- [ ] **Step 2: `Dashboard.jsx`에서 승격 제거 + 로딩/에러 표시**

`frontend/src/components/Dashboard/Dashboard.jsx` (전체 교체):
```jsx
import AlertBanner from "./AlertBanner";
import GreenhouseCard from "./GreenhouseCard";
import ProductionWidget from "./ProductionWidget";
import HistoryTimeline from "./HistoryTimeline";
import DemoControls from "./DemoControls";
import { SEVERITY_ORDER } from "../../lib/labels";

export default function Dashboard({ farm, onSelectGreenhouse, onReset }) {
  const sorted = [...farm.greenhouses].sort(
    (a, b) => SEVERITY_ORDER[b.status] - SEVERITY_ORDER[a.status]
  );

  return (
    <div className="dashboard">
      <DemoControls onReset={onReset} />
      {farm.loading && <p className="dashboard__status">불러오는 중...</p>}
      {farm.error && <p className="dashboard__status dashboard__status--error">{farm.error}</p>}
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

- [ ] **Step 3: `DemoControls.jsx`에서 승격 버튼 제거**

`frontend/src/components/Dashboard/DemoControls.jsx` (전체 교체):
```jsx
export default function DemoControls({ onReset }) {
  return (
    <div className="demo-controls">
      <button className="demo-controls__btn demo-controls__btn--reset" onClick={onReset}>
        리셋
      </button>
    </div>
  );
}
```

- [ ] **Step 4: 로딩/에러 상태 스타일 추가**

`frontend/src/styles.css` 맨 끝에 추가:
```css

.dashboard__status { text-align: center; color: #888; font-size: 13px; margin: 8px 0; }
.dashboard__status--error { color: #b71c1c; }
```

- [ ] **Step 5: 수동 검증**

(이 단계까지 마쳐도 `GreenhouseCard`/`AlertBanner`/`CriticalBanner`/`NotificationInbox`/`GreenhouseDetail`은 Task 6에서 필드명을 맞추기 전까지 일부 표시가 어긋날 수 있음 — 아래는 이 태스크 범위에서 확인 가능한 것만.)
1. 대시보드 탭 진입 시 "불러오는 중..." 문구가 잠깐 보였다가 사라지는지.
2. "승격" 버튼이 더 이상 없는지.
3. "리셋" 클릭 시 Network 탭에서 `POST /api/reset` 이후 `GET /api/state`, `GET /api/alerts`가 다시 호출되는지.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/App.jsx frontend/src/components/Dashboard/Dashboard.jsx frontend/src/components/Dashboard/DemoControls.jsx frontend/src/styles.css
git commit -m "feat(frontend): App/Dashboard를 alertId 기반 콜백으로 연결, 승격 데모 버튼 제거"
```

---

### Task 6: 알림/상세 화면 필드명 전환 + `activeAlert` 기반 액션 + 온도 라인 제거

**Files:**
- Modify: `frontend/src/components/Dashboard/AlertBanner.jsx` (전체 재작성)
- Modify: `frontend/src/components/NotificationCenter/CriticalBanner.jsx` (전체 재작성 — `AudioContext` 재사용 포함)
- Modify: `frontend/src/components/NotificationCenter/NotificationInbox.jsx` (전체 재작성)
- Modify: `frontend/src/components/GreenhouseDetail.jsx` (전체 재작성)

**Interfaces:**
- Consumes: Task 4의 `notifications` 형태(`{id, level, greenhouseId, greenhouseName, message, action}`), Task 5의 `onAction(alertId)`/`onDismiss(alertId)` 콜백, Task 4의 `getGreenhouseDetail(id)`.

- [ ] **Step 1: `AlertBanner.jsx`를 `severity`→`level`로 교체**

`frontend/src/components/Dashboard/AlertBanner.jsx` (전체 교체):
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
          className={`alert-banner alert-banner--${n.level}`}
          onClick={() => onSelect?.(n.greenhouseId)}
        >
          {n.level === "critical" ? "🔴" : "🟡"} {n.greenhouseName}: {n.message}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: `CriticalBanner.jsx` — `AudioContext` 재사용 + alertId 기반 콜백**

`frontend/src/components/NotificationCenter/CriticalBanner.jsx` (전체 교체):
```jsx
import { useEffect, useRef } from "react";

export default function CriticalBanner({ notifications, onAction, onDismiss, canPlaySound }) {
  const playedIdsRef = useRef(new Set());
  const audioContextRef = useRef(null);

  function playBeep() {
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
    }
    const ctx = audioContextRef.current;
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

  useEffect(() => () => audioContextRef.current?.close(), []);

  if (notifications.length === 0) return null;

  return (
    <div className="critical-banner-stack">
      {notifications.map((n) => (
        <div key={n.id} className="critical-banner">
          <span>🔴 {n.greenhouseName}: {n.message}</span>
          <div className="critical-banner__actions">
            <button onClick={() => onAction(n.id)}>바로 조치</button>
            <button className="critical-banner__dismiss" onClick={() => onDismiss(n.id)}>
              ✕
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: `NotificationInbox.jsx` — alertId 기반 콜백**

`frontend/src/components/NotificationCenter/NotificationInbox.jsx` (전체 교체):
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
              <button onClick={() => onAction(n.id)}>조치</button>
              <button onClick={() => onDismiss(n.id)}>✕</button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 4: `GreenhouseDetail.jsx` — 상세 데이터 자체 조회 + 온도 라인 제거 + `reason`/`activeAlert` 사용**

`frontend/src/components/GreenhouseDetail.jsx` (전체 교체):
```jsx
import { useEffect, useState } from "react";
import { getGreenhouseDetail } from "../api";
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

function formatTime(isoTimestamp) {
  return isoTimestamp.slice(11, 16); // "2026-07-08T10:00:00" -> "10:00"
}

export default function GreenhouseDetail({ greenhouse, onBack, onAction }) {
  const [detail, setDetail] = useState(null);
  const [toast, setToast] = useState("");
  const width = 260;
  const height = 80;

  useEffect(() => {
    setDetail(null);
    getGreenhouseDetail(greenhouse.id).then(setDetail);
  }, [greenhouse.id]);

  const history = detail?.history ?? [];
  const humidityPath = buildLinePath(history.map((h) => h.humidity), width, height);

  function handleAction() {
    onAction(greenhouse.activeAlert.id);
    setToast(`${greenhouse.activeAlert.action.label} 완료했어요.`);
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
      {greenhouse.reason && <p className="greenhouse-detail__cause">{greenhouse.reason}</p>}

      {greenhouse.activeAlert && (
        <button className="greenhouse-detail__action" onClick={handleAction}>
          [{greenhouse.activeAlert.action.label}]
        </button>
      )}
      {toast && <p className="greenhouse-detail__toast">{toast}</p>}

      <div className="greenhouse-detail__chart">
        <p>최근 습도 추이</p>
        <svg viewBox={`0 0 ${width} ${height}`} className="greenhouse-detail__svg">
          <path d={humidityPath} className="chart-line chart-line--humidity" fill="none" />
        </svg>
        <div className="greenhouse-detail__legend">
          <span className="chart-legend chart-legend--humidity">● 습도</span>
        </div>
        <div className="greenhouse-detail__times">
          {history.map((h) => (
            <span key={h.timestamp}>{formatTime(h.timestamp)}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: 수동 검증 (전체 시나리오 end-to-end)**

백엔드 `POST /api/reset` 호출 또는 서버 재시작으로 깨끗한 상태에서 시작:
1. 대시보드 탭 → 2번 온실 카드가 경고(🟡) 테두리로 표시되는지 확인 (실제 백엔드 mock 습도 82%).
2. 상단 알림 배너에 "2번 온실(딸기): 습도 82%, 곰팡이병 위험" 문구가 뜨는지 확인.
3. 그 배너를 클릭 → 온실 상세로 이동, 습도 추이 차트(온도 라인 없음)와 "[창문 열기]" 버튼, 사유 문구가 보이는지.
4. "[창문 열기]" 클릭 → 토스트 "창문 열기 완료했어요." 표시, 잠시 후 대시보드로 돌아가면 해당 온실 카드가 정상(초록)으로 바뀌고 알림이 사라졌는지 확인 (백엔드 `/api/alerts`가 실제로 dismiss됐는지 Network 탭으로도 확인 가능).
5. 상단 네비의 경고 배지(🟡 N) → 클릭해서 알림함이 뜨고, 알림함에서도 "조치"/"✕" 둘 다 동작하는지.
6. 크리티컬 알림 예시가 없다면(현재 mock 데이터엔 critical 케이스가 없음) 이 부분은 생략 가능 — `CriticalBanner`는 경고만으로도 렌더 로직이 같으므로 코드 리뷰로 충분.
7. "리셋" 버튼 클릭 → 위에서 바꾼 상태(창문 open)가 초기값(closed)으로 돌아오는지 확인.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/Dashboard/AlertBanner.jsx frontend/src/components/NotificationCenter/CriticalBanner.jsx frontend/src/components/NotificationCenter/NotificationInbox.jsx frontend/src/components/GreenhouseDetail.jsx
git commit -m "feat(frontend): 알림/상세 화면을 백엔드 alert_id 기반 액션으로 전환, 온도 차트 라인 제거"
```
