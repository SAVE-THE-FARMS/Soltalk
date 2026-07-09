import { useCallback, useEffect, useState } from "react";
import { getGreenhouseDetail } from "../api";
import StatusBadge from "./ui/StatusBadge";
import { ACTION_BRIEFING, HUMIDITY_THRESHOLD, STATUS_HEADLINE } from "../lib/labels";

// history 는 { timestamp, humidity, temperature? } 배열. temperature 는 라이브
// 샘플부터만 있어서(seed 더미엔 없음) key 가 없는 지점은 건너뛰되, x 축은
// history 전체 길이를 기준으로 맞춰서 습도선과 시간이 어긋나 보이지 않게 한다.
function buildSparseLinePath(history, key, width, height) {
  const points = history
    .map((h, i) => (h[key] != null ? { i, v: h[key] } : null))
    .filter(Boolean);
  if (points.length === 0) return "";

  const values = points.map((p) => p.v);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const stepX = width / (history.length - 1 || 1);

  return points
    .map((p, idx) => {
      const x = p.i * stepX;
      const y = height - ((p.v - min) / range) * height;
      return `${idx === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
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

// 대시보드/상세가 3초마다 각자 폴링하다 보니, 토글 클릭 직후 다른 폴링이
// 아직-갱신-안 된 상태를 덮어써서 체크박스가 잠깐 원래대로 돌아가 보이는
// 깜빡임이 있었다(실측 확인). props 를 매번 반영하지 않고 마운트 시점
// 값으로만 시작해서, 이후엔 사용자의 클릭이 유일한 진실 소스가 되게 한다.
function AutoToggle({ greenhouseId, initialChecked, onToggle }) {
  const [checked, setChecked] = useState(initialChecked);

  function handleChange(e) {
    const next = e.target.checked;
    setChecked(next);
    onToggle(greenhouseId, next);
  }

  return (
    <label className="auto-toggle">
      <input type="checkbox" checked={checked} onChange={handleChange} />
      🤖 자동 조치 {checked ? "켜짐" : "꺼짐"} — 문제가 생기면 사람 없이 자동으로 처리해요
    </label>
  );
}

// 경고/위험 상태 온실의 브리핑 블록: 상황 → 위험 → 조치 방법(또는 자동 조치 안내)
function Briefing({ greenhouse, onAction }) {
  const [acting, setActing] = useState(false);

  // 경고가 방치돼 격상(escalated)되면 배지/테두리는 위험처럼 보이되,
  // "정상 범위(N% 미만)" 설명은 실제 측정된 습도 기준(warning=80%) 그대로 써야
  // 한다 — 습도 82%인데 "90% 미만을 넘었다"고 하면 틀린 말이 된다.
  const displayStatus = greenhouse.escalated ? "critical" : greenhouse.status;
  const headline = STATUS_HEADLINE[displayStatus];
  const threshold = HUMIDITY_THRESHOLD[greenhouse.status];
  const action = greenhouse.activeAlert?.action;
  const briefing = action ? ACTION_BRIEFING[`${action.device}:${action.action}`] : null;
  const autoHandling = greenhouse.auto && greenhouse.activeAlert != null;
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
    <div className={`briefing briefing--${displayStatus}`}>
      <p className="briefing__headline">
        {headline.icon} 습도 {greenhouse.humidity}% — {headline.text}
      </p>

      {greenhouse.escalated && (
        <p className="briefing__escalated-note">
          ⏱️ 경고가 오래 방치되어 위험 수준으로 격상됐어요. 빨리 조치해주세요.
        </p>
      )}

      <div className="briefing__section">
        <p className="briefing__title">📋 현재 상황</p>
        <p>
          습도가 <strong>{greenhouse.humidity}%</strong>로 정상 범위({threshold}% 미만)를
          넘었어요. 온도는 {greenhouse.temperature}℃예요.
        </p>
      </div>

      {briefing && (
        <div className="briefing__section">
          <p className="briefing__title">⚠️ 이대로 두면</p>
          <p>{briefing.risk}</p>
        </div>
      )}

      {briefing && !autoHandling && (
        <>
          <div className="briefing__section">
            <p className="briefing__title">💡 조치 방법</p>
            <p>{briefing.remedy}</p>
          </div>
          <button className="briefing__cta" onClick={handleClick} disabled={acting}>
            {acting ? "조치하는 중..." : `${briefing.buttonIcon} ${action.label}`}
          </button>
        </>
      )}

      {briefing && autoHandling && (
        <p className="briefing__auto-active">
          🤖 자동 조치가 켜져 있어서 시스템이 스스로 {action.label} 처리하고 있어요.
        </p>
      )}

      {recovering && (
        <p className="briefing__recovering">
          ✅ 조치 완료 — 습도가 내려가는 중이에요. 아래 그래프에서 확인할 수 있어요.
        </p>
      )}
    </div>
  );
}

export default function GreenhouseDetail({ greenhouse, onBack, onAction, onToggleAuto }) {
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
  const humidityPath = buildSparseLinePath(history, "humidity", width, height);
  const temperaturePath = buildSparseLinePath(history, "temperature", width, height);

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

      <AutoToggle
        key={greenhouse.id}
        greenhouseId={greenhouse.id}
        initialChecked={!!greenhouse.auto}
        onToggle={onToggleAuto}
      />

      {greenhouse.status !== "normal" && (
        <Briefing greenhouse={greenhouse} onAction={handleAction} />
      )}

      <div className="greenhouse-detail__chart">
        <p>최근 습도·온도 추이</p>
        <svg viewBox={`0 0 ${width} ${height}`} className="greenhouse-detail__svg">
          <path d={humidityPath} className="chart-line chart-line--humidity" fill="none" />
          <path d={temperaturePath} className="chart-line chart-line--temp" fill="none" />
        </svg>
        <div className="greenhouse-detail__legend">
          <span className="chart-legend chart-legend--humidity">● 습도</span>
          <span className="chart-legend chart-legend--temp">● 온도</span>
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
