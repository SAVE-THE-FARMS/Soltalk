export default function AlertBanner({ notifications, greenhouses, onSelect }) {
  if (notifications.length === 0) {
    // 알림이 없어도 조치 직후엔 습도가 아직 내려가는 중일 수 있다.
    // 실제로 모든 온실이 정상 범위로 돌아왔을 때만 "정상" 멘트를 띄운다.
    const abnormal = greenhouses.filter((gh) => gh.status !== "normal");
    if (abnormal.length === 0) {
      return <p className="alert-banner alert-banner--ok">모든 온실 정상입니다 ✅</p>;
    }
    // 창문이 열려 있으면 습도가 내려가는 중 → 회복 진행 안내.
    // (알림만 무시하고 조치를 안 한 온실이 있으면 아무 멘트도 띄우지 않는다 —
    //  카드의 경고 배지가 상태를 계속 보여준다.)
    const allRecovering = abnormal.every((gh) => gh.devices.window === "open");
    if (allRecovering) {
      return (
        <p className="alert-banner alert-banner--recovering">
          조치 완료 — 습도가 정상 범위로 돌아오는 중이에요 🌬️
        </p>
      );
    }
    return null;
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
