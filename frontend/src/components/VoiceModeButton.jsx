import { VOICE_STATUS } from "../realtime/useRealtimeSession";

const ACTIVE_STATUSES = new Set([
  VOICE_STATUS.CONNECTING,
  VOICE_STATUS.LISTENING,
  VOICE_STATUS.THINKING,
  VOICE_STATUS.SPEAKING,
  VOICE_STATUS.RECONNECTING,
]);

export default function VoiceModeButton({ status, muted, onStart, onStop, onToggleMute }) {
  const isActive = ACTIVE_STATUSES.has(status);

  if (!isActive) {
    return (
      <button className="voice-mode-btn voice-mode-btn--start" onClick={onStart}>
        🎙️ 대화하기
      </button>
    );
  }

  return (
    <div className="voice-mode-controls">
      <button
        className={`voice-mode-btn voice-mode-btn--mute${muted ? " is-muted" : ""}`}
        onClick={onToggleMute}
        title={muted ? "음소거 해제" : "음소거"}
      >
        {muted ? "🔇 음소거 중" : "🎤 음소거"}
      </button>
      <button className="voice-mode-btn voice-mode-btn--stop" onClick={onStop}>
        ⏹ 통화 종료
      </button>
    </div>
  );
}
