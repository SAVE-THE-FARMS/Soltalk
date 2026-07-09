import AlertBanner from "./AlertBanner";
import GreenhouseCard from "./GreenhouseCard";
import ProductionWidget from "./ProductionWidget";
import HistoryTimeline from "./HistoryTimeline";
import DemoControls from "./DemoControls";
import { SEVERITY_ORDER } from "../../lib/labels";

export default function Dashboard({ farm, onSelectGreenhouse, onReset, onEscalate, visibleNotifications }) {
  const sorted = [...farm.greenhouses].sort(
    (a, b) => SEVERITY_ORDER[b.status] - SEVERITY_ORDER[a.status]
  );

  return (
    <div className="dashboard">
      <DemoControls onReset={onReset} onEscalate={onEscalate} />
      <AlertBanner notifications={visibleNotifications} onSelect={onSelectGreenhouse} />
      <div className="dashboard__grid">
        {sorted.map((gh) => (
          <GreenhouseCard key={gh.id} greenhouse={gh} onClick={onSelectGreenhouse} />
        ))}
      </div>
      <ProductionWidget production={farm.production} />
      <HistoryTimeline entries={farm.historyLog} />
    </div>
  );
}
