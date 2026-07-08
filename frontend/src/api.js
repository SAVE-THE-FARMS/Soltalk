// 백엔드 호출 담당.
// 접점 계약:  POST /chat  { message } -> { reply }

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function sendMessage(message) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error(`서버 오류: ${res.status}`);
  const data = await res.json();
  return data.reply; // 자연어 응답 문자열
}
