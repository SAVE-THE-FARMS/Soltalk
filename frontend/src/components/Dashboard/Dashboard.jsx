import GreenhouseCard from "./GreenhouseCard";

const SEVERITY_ORDER = { critical: 2, warning: 1, normal: 0 };

export default function Dashboard({ farm, onSelectGreenhouse }) {
  const sorted = [...farm.greenhouses].sort(
    (a, b) => SEVERITY_ORDER[b.status] - SEVERITY_ORDER[a.status]
  );

  return (
    <div className="dashboard">
      <div className="dashboard__grid">
        {sorted.map((gh) => (
          <GreenhouseCard key={gh.id} greenhouse={gh} onClick={onSelectGreenhouse} />
        ))}
      </div>
    </div>
  );
}
