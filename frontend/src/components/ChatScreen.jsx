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
