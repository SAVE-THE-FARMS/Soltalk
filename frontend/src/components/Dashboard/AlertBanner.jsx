export default function AlertBanner({ notifications, onSelect }) {
  if (notifications.length === 0) {
    return <p className="alert-banner alert-banner--ok">모든 온실 정상입니다 ✅</p>;
  }

  return (
    <div className="alert-banner-list">
      {notifications.map((n) => (
        <button
          key={n.id}
          className={`alert-banner alert-banner--${n.level}`}
          onClick={() => onSelect?.(n.greenhouseId)}
        >
          {n.level === "critical" ? "🔴" : "🟡"} {n.greenhouseName}: {n.message}
        </button>
      ))}
    </div>
  );
}
