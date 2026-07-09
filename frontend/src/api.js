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
