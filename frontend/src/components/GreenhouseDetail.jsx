import { useCallback, useEffect, useState } from "react";
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
  return isoTimestamp.slice(11, 19); // "2026-07-08T10:00:00" -> "10:00:00"
}

// 라이브 샘플이 쌓이면 라벨 12개가 다 안 들어가므로 처음/중간/끝만 보여준다
function pickTimeLabels(history) {
  if (history.length <= 3) return history;
  return [history[0], history[Math.floor(history.length / 2)], history[history.length - 1]];
}

export default function GreenhouseDetail({ greenhouse, onBack, onAction }) {
  const [detail, setDetail] = useState(null);
  const [toast, setToast] = useState("");
  const width = 260;
  const height = 80;

  const load = useCallback(() => getGreenhouseDetail(greenhouse.id).then(setDetail), [greenhouse.id]);

  useEffect(() => {
    setDetail(null);
    load();
    // 조치 후 습도가 내려가는 걸 그래프에서 볼 수 있게 주기적으로 재조회
    const intervalId = setInterval(load, 3000);
    return () => clearInterval(intervalId);
  }, [load]);

  const history = detail?.history ?? [];
  const humidityPath = buildLinePath(history.map((h) => h.humidity), width, height);

  async function handleAction() {
    const label = greenhouse.activeAlert.action.label;
    await onAction(greenhouse.activeAlert.id);
    load(); // 다음 폴링(3초)을 기다리지 않고 그래프에 바로 반영
    setToast(`${label} 완료했어요.`);
    setTimeout(() => setToast(""), 2000);
  }

  return (
    <div className="greenhouse-detail">
      <button className="greenhouse-detail__back" onClick={onBack}>
        ← 대시보드로
      </button>

      <div className="greenhouse-detail__header">
        <h2>{greenhouse.name}</h2>
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
        <div className="greenhouse-detail__times">
          {pickTimeLabels(history).map((h) => (
            <span key={h.timestamp}>{formatTime(h.timestamp)}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
