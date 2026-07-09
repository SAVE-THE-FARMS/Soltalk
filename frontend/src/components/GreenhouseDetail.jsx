import { useState } from "react";
import StatusBadge from "./ui/StatusBadge";

function buildLinePath(values, width, height) {
  if (values.length === 0) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const stepX = width / (values.length - 1 || 1);

  return values
    .map((v, i) => {
      const x = i * stepX;
      const y = height - ((v - min) / range) * height;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export default function GreenhouseDetail({ greenhouse, onBack, onControlDevice }) {
  const [toast, setToast] = useState("");
  const width = 260;
  const height = 80;
  const tempPath = buildLinePath(
    greenhouse.history.map((h) => h.temperature),
    width,
    height
  );
  const humidityPath = buildLinePath(
    greenhouse.history.map((h) => h.humidity),
    width,
    height
  );

  function handleAction() {
    onControlDevice(
      greenhouse.id,
      greenhouse.recommendedAction.device,
      greenhouse.recommendedAction.action
    );
    setToast(`${greenhouse.recommendedAction.label} 완료했어요.`);
    setTimeout(() => setToast(""), 2000);
  }

  return (
    <div className="greenhouse-detail">
      <button className="greenhouse-detail__back" onClick={onBack}>
        ← 대시보드로
      </button>

      <div className="greenhouse-detail__header">
        <h2 className="display-face">{greenhouse.name}</h2>
        <StatusBadge status={greenhouse.status} />
      </div>
      {greenhouse.cause && (
        <p className="greenhouse-detail__cause">{greenhouse.cause}</p>
      )}

      {greenhouse.recommendedAction && (
        <button className="greenhouse-detail__action" onClick={handleAction}>
          [{greenhouse.recommendedAction.label}]
        </button>
      )}
      {toast && <p className="greenhouse-detail__toast">{toast}</p>}

      <div className="greenhouse-detail__chart">
        <p>최근 온도·습도 추이</p>
        <svg viewBox={`0 0 ${width} ${height}`} className="greenhouse-detail__svg">
          <path d={tempPath} className="chart-line chart-line--temp" fill="none" />
          <path d={humidityPath} className="chart-line chart-line--humidity" fill="none" />
        </svg>
        <div className="greenhouse-detail__legend">
          <span className="chart-legend chart-legend--temp">● 온도</span>
          <span className="chart-legend chart-legend--humidity">● 습도</span>
        </div>
        <div className="greenhouse-detail__times data-face">
          {greenhouse.history.map((h) => (
            <span key={h.time}>{h.time}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
