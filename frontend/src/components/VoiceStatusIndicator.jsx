import { VOICE_STATUS } from "../realtime/useRealtimeSession";

const STATUS_ICON = {
  [VOICE_STATUS.CONNECTING]: "🔄",
  [VOICE_STATUS.LISTENING]: "👂",
  [VOICE_STATUS.THINKING]: "💭",
  [VOICE_STATUS.SPEAKING]: "🔊",
  [VOICE_STATUS.RECONNECTING]: "🔄",
  [VOICE_STATUS.ERROR]: "⚠️",
  [VOICE_STATUS.FALLBACK]: "⌨️",
};

export default function VoiceStatusIndicator({ status, statusLabel, errorText }) {
  if (status === VOICE_STATUS.IDLE) return null;

  return (
    <div className={`voice-status voice-status--${status}`}>
      <span className="voice-status__icon" aria-hidden="true">
        {STATUS_ICON[status] || "🎙️"}
      </span>
      <span className="voice-status__text">{statusLabel}</span>
      {status === VOICE_STATUS.SPEAKING && (
        <span className="voice-status__wave" aria-hidden="true">
          <span />
          <span />
          <span />
        </span>
      )}
      {errorText && <span className="voice-status__error">{errorText}</span>}
    </div>
  );
}
