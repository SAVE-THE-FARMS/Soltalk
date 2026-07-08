import { useState } from "react";
import { sendMessage } from "./api";

// SolTalk 챗 화면 (뼈대).
// 동작하는 것: 메시지 목록 렌더 + 입력/전송 + 백엔드 호출.
// TODO(학생): 음성 입력(STT), 로딩/에러 UI 다듬기.

export default function App() {
  const [messages, setMessages] = useState([]); // { role: "user"|"bot", text }
  const [input, setInput] = useState("");

  async function handleSend() {
    const text = input.trim();
    if (!text) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");

    try {
      const reply = await sendMessage(text);
      setMessages((m) => [...m, { role: "bot", text: reply }]);
    } catch (e) {
      // TODO(학생): 에러 UI 개선 (백엔드 꺼져있을 때 등)
      setMessages((m) => [...m, { role: "bot", text: `⚠️ ${e.message}` }]);
    }
  }

  function handleMic() {
    // TODO(학생): 브라우저 Web Speech API 로 음성 인식 →
    //   인식된 텍스트를 setInput(...) 에 넣기 (원하면 바로 handleSend 까지)
    alert("음성 입력은 아직 미구현 (Web Speech API 연결하기)");
  }

  return (
    <div className="app">
      <h1>SolTalk 🌱</h1>

      <div className="chat">
        {messages.length === 0 && (
          <p className="hint">예: "차광막 닫아줘", "지금 온도 몇 도야?"</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.text}
          </div>
        ))}
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
