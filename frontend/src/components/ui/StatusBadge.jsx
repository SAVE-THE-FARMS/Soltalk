const LABEL = { normal: "정상", warning: "경고", critical: "위험" };

export default function StatusBadge({ status }) {
  return (
    <span className={`status-badge status-badge--${status}`}>
      {LABEL[status]}
    </span>
  );
}
