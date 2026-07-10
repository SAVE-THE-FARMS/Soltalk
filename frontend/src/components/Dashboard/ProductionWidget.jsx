export default function ProductionWidget({ production }) {
  const arrow = production.direction === "up" ? "▲" : "▼";
  const arrowClass = production.direction === "up" ? "is-up" : "is-down";

  return (
    <div className="production-widget">
      <p className="production-widget__caption">전체 온실 수확량 합계</p>
      <div className="production-widget__row">
        <div>
          <span className="production-widget__label">오늘</span>
          <span className="production-widget__value data-face">
            {production.today}{production.unit}
          </span>
        </div>
        <div>
          <span className="production-widget__label">이번주</span>
          <span className="production-widget__value data-face">
            {production.week}{production.unit}
          </span>
        </div>
        <span className={`production-widget__diff ${arrowClass}`}>
          {arrow} {production.diffPct}% (지난주 대비)
        </span>
      </div>
    </div>
  );
}
