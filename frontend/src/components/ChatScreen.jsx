import { useEffect, useRef, useState } from "react";
import { sendMessage, transcribeAudio } from "../api";
import { useRecorder } from "../lib/useRecorder";

const QUICK_REPLIES = [
  "차광막 닫아줘",
  "창문 열어",
  "지금 온도 몇 도야?",
  "오늘 생산량 알려줘",
];

export default function ChatScreen() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [micError, setMicError] = useState("");
  const nextIdRef = useRef(0);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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
        <div ref={bottomRef} />
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
        <button onClick={() => handleSend()}>전송</button>
      </div>
    </div>
  );
}
