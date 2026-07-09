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
