import { useCallback, useEffect, useState } from "react";
import { getGreenhouseDetail } from "../api";
import StatusBadge from "./ui/StatusBadge";
import { ACTION_BRIEFING, HUMIDITY_THRESHOLD, STATUS_HEADLINE } from "../lib/labels";

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

// 경고/위험 상태 온실의 브리핑 블록: 상황 → 위험 → 조치 방법 → 조치 버튼
function Briefing({ greenhouse, onAction }) {
  const [acting, setActing] = useState(false);

  const headline = STATUS_HEADLINE[greenhouse.status];
  const threshold = HUMIDITY_THRESHOLD[greenhouse.status];
  const action = greenhouse.activeAlert?.action;
  const briefing = action ? ACTION_BRIEFING[`${action.device}:${action.action}`] : null;
  // 조치가 이미 실행됐으면(알림 사라짐 + 창문 열림) 회복 진행 안내
  const recovering = !greenhouse.activeAlert && greenhouse.devices.window === "open";

  async function handleClick() {
    setActing(true);
    try {
      await onAction(greenhouse.activeAlert.id);
    } finally {
      setActing(false);
    }
  }

  return (
    <div className={`briefing briefing--${greenhouse.status}`}>
      <p className="briefing__headline">
        {headline.icon} 습도 {greenhouse.humidity}% — {headline.text}
      </p>

      <div className="briefing__section">
        <p className="briefing__title">📋 현재 상황</p>
        <p>
          습도가 <strong>{greenhouse.humidity}%</strong>로 정상 범위({threshold}% 미만)를
          넘었어요. 온도는 {greenhouse.temperature}℃예요.
        </p>
      </div>

      {briefing && (
        <>
          <div className="briefing__section">
            <p className="briefing__title">⚠️ 이대로 두면</p>
            <p>{briefing.risk}</p>
          </div>
          <div className="briefing__section">
            <p className="briefing__title">💡 조치 방법</p>
            <p>{briefing.remedy}</p>
          </div>
          <button className="briefing__cta" onClick={handleClick} disabled={acting}>
            {acting ? "조치하는 중..." : `${briefing.buttonIcon} ${action.label}`}
          </button>
        </>
      )}

      {recovering && (
        <p className="briefing__recovering">
          ✅ 조치 완료 — 습도가 내려가는 중이에요. 아래 그래프에서 확인할 수 있어요.
        </p>
      )}
    </div>
  );
}

export default function GreenhouseDetail({ greenhouse, onBack, onAction }) {
  const [detail, setDetail] = useState(null);
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

  async function handleAction(alertId) {
    await onAction(alertId);
    load(); // 다음 폴링(3초)을 기다리지 않고 그래프에 바로 반영
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

      {greenhouse.status !== "normal" && (
        <Briefing greenhouse={greenhouse} onAction={handleAction} />
      )}

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
