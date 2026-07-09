import StatusBadge from "../ui/StatusBadge";
import DeviceIcon from "../ui/DeviceIcon";

export default function GreenhouseCard({ greenhouse, onClick }) {
  // 경고가 방치돼 격상(escalated)되면 위험처럼 보이게 — 상단 배너와 일치시킨다
  const displayStatus = greenhouse.escalated ? "critical" : greenhouse.status;

  return (
    <button
      className={`greenhouse-card greenhouse-card--${displayStatus}`}
      onClick={() => onClick?.(greenhouse.id)}
    >
      <div className="greenhouse-card__header">
        <span className="greenhouse-card__name">
          {greenhouse.name} {greenhouse.auto && <span title="자동 조치 켜짐">🤖</span>}
        </span>
        <StatusBadge status={displayStatus} />
      </div>
      <div className="greenhouse-card__metrics data-face">
        <span>🌡️ {greenhouse.temperature}℃</span>
        <span>💧 {greenhouse.humidity}%</span>
      </div>
      <div className="greenhouse-card__devices">
        <DeviceIcon device="shade" state={greenhouse.devices.shade} />
        <DeviceIcon device="window" state={greenhouse.devices.window} />
        <DeviceIcon device="irrigation" state={greenhouse.devices.irrigation} />
      </div>
    </button>
  );
}
