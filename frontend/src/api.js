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

export async function transcribeAudio(blob) {
  const form = new FormData();
  form.append("audio", blob, "recording.webm");
  const res = await fetch(`${API_BASE}/api/transcribe`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`음성 인식 실패: ${res.status}`);
  const data = await res.json();
  return data.text;
}

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

export async function setAutoMode(greenhouseId, enabled) {
  return requestJson(`/api/greenhouses/${greenhouseId}/auto-mode`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
}

// --- 실시간 음성 모드 (OpenAI Realtime API) ---
// 백엔드 계약: Docs/voice_feature_backend 기준 (POST /api/realtime/session, POST /api/tools/execute).
// 이 두 엔드포인트가 아직 없거나 응답 형식이 다르면 여기서 던지는 에러를 호출부(useRealtimeSession)가
// 잡아서 텍스트 모드로 안전하게 fallback한다 — 백엔드 준비 여부와 프론트 동작을 분리.

export async function createRealtimeSession() {
  // { client_secret, expires_at } 기대 (OpenAI ephemeral key). 절대 일반 OPENAI_API_KEY를
  // 프론트에 내려주면 안 됨 — 백엔드가 항상 짧은 유효시간의 임시 키만 발급해야 한다.
  return requestJson("/api/realtime/session", { method: "POST" });
}

export async function executeRealtimeTool(toolName, toolArguments) {
  // { result } 기대. 실패해도 예외를 던지되, 호출부가 실패 사실을 그대로
  // function_call_output 으로 모델에 돌려줄 수 있게 한다 (실패를 숨기지 않음).
  return requestJson("/api/tools/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tool_name: toolName, arguments: toolArguments }),
  });
}
