import { useEffect, useRef } from "react";

export default function CriticalBanner({ notifications, onAction, onDismiss, canPlaySound }) {
  const playedIdsRef = useRef(new Set());
  const audioContextRef = useRef(null);

  function playBeep() {
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
    }
    const ctx = audioContextRef.current;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = 880;
    gain.gain.value = 0.15;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.2);
  }

  useEffect(() => {
    if (!canPlaySound) return;
    notifications.forEach((n) => {
      if (!playedIdsRef.current.has(n.id)) {
        playedIdsRef.current.add(n.id);
        try {
          playBeep();
        } catch {
          // 브라우저가 오디오를 지원하지 않으면 조용히 무시
        }
      }
    });
  }, [notifications, canPlaySound]);

  useEffect(() => () => audioContextRef.current?.close(), []);

  if (notifications.length === 0) return null;

  return (
    <div className="critical-banner-stack">
      {notifications.map((n) => (
        <div key={n.id} className="critical-banner">
          <span>🔴 {n.greenhouseName}: {n.message}</span>
          <div className="critical-banner__actions">
            <button onClick={() => onAction(n.id)}>바로 조치</button>
            <button className="critical-banner__dismiss" onClick={() => onDismiss(n.id)}>
              ✕
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
