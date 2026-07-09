import { useEffect, useState } from "react";
import { getGreenhouseDetail } from "../api";
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

function formatTime(isoTimestamp) {
  return isoTimestamp.slice(11, 16); // "2026-07-08T10:00:00" -> "10:00"
}

export default function GreenhouseDetail({ greenhouse, onBack, onAction }) {
  const [detail, setDetail] = useState(null);
  const [toast, setToast] = useState("");
  const width = 260;
  const height = 80;

  useEffect(() => {
    setDetail(null);
    getGreenhouseDetail(greenhouse.id).then(setDetail);
  }, [greenhouse.id]);

  const history = detail?.history ?? [];
  const humidityPath = buildLinePath(history.map((h) => h.humidity), width, height);

  function handleAction() {
    onAction(greenhouse.activeAlert.id);
    setToast(`${greenhouse.activeAlert.action.label} 완료했어요.`);
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
      {greenhouse.reason && <p className="greenhouse-detail__cause">{greenhouse.reason}</p>}

      {greenhouse.activeAlert && (
        <button className="greenhouse-detail__action" onClick={handleAction}>
          [{greenhouse.activeAlert.action.label}]
        </button>
      )}
      {toast && <p className="greenhouse-detail__toast">{toast}</p>}

      <div className="greenhouse-detail__chart">
        <p>최근 습도 추이</p>
        <svg viewBox={`0 0 ${width} ${height}`} className="greenhouse-detail__svg">
          <path d={humidityPath} className="chart-line chart-line--humidity" fill="none" />
        </svg>
        <div className="greenhouse-detail__legend">
          <span className="chart-legend chart-legend--humidity">● 습도</span>
        </div>
        <div className="greenhouse-detail__times data-face">
          {history.map((h) => (
            <span key={h.timestamp}>{formatTime(h.timestamp)}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
