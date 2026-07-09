import AlertBanner from "./AlertBanner";
import GreenhouseCard from "./GreenhouseCard";
import ProductionWidget from "./ProductionWidget";
import HistoryTimeline from "./HistoryTimeline";
import DemoControls from "./DemoControls";

export default function Dashboard({ farm, onSelectGreenhouse, onReset }) {
  return (
    <div className="dashboard">
      <DemoControls onReset={onReset} />
      {farm.loading && <p className="dashboard__status">불러오는 중...</p>}
      {farm.error && <p className="dashboard__status dashboard__status--error">{farm.error}</p>}
      <AlertBanner
        notifications={farm.notifications}
        greenhouses={farm.greenhouses}
        onSelect={onSelectGreenhouse}
      />
      <div className="dashboard__grid">
        {farm.greenhouses.map((gh) => (
          <GreenhouseCard key={gh.id} greenhouse={gh} onClick={onSelectGreenhouse} />
        ))}
      </div>
      <ProductionWidget production={farm.production} />
      <HistoryTimeline entries={farm.historyLog} />
    </div>
  );
}
