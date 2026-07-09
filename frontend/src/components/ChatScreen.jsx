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
