export default function ProductionWidget({ production }) {
  const arrow = production.direction === "up" ? "▲" : "▼";
  const arrowClass = production.direction === "up" ? "is-up" : "is-down";

  return (
    <div className="production-widget">
      <div>
        <span className="production-widget__label">오늘</span>
        <span className="production-widget__value">
          {production.today}{production.unit}
        </span>
      </div>
      <div>
        <span className="production-widget__label">이번주</span>
        <span className="production-widget__value">
          {production.week}{production.unit}
        </span>
      </div>
      <span className={`production-widget__diff ${arrowClass}`}>
        {arrow} {production.diffPct}%
      </span>
    </div>
  );
}
