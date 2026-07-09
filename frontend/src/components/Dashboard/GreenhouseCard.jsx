import StatusBadge from "../ui/StatusBadge";
import DeviceIcon from "../ui/DeviceIcon";

export default function GreenhouseCard({ greenhouse, onClick }) {
  return (
    <button
      className={`greenhouse-card greenhouse-card--${greenhouse.status}`}
      onClick={() => onClick?.(greenhouse.id)}
    >
      <div className="greenhouse-card__header">
        <span className="greenhouse-card__name">{greenhouse.name}</span>
        <StatusBadge status={greenhouse.status} />
      </div>
      <div className="greenhouse-card__metrics">
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
