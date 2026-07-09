export default function NotificationInbox({ notifications, onGoTo, onDismiss, onClose }) {
  return (
    <div className="notification-inbox">
      <div className="notification-inbox__header">
        <span>알림함</span>
        <button onClick={onClose}>닫기</button>
      </div>
      {notifications.length === 0 && (
        <p className="notification-inbox__empty">알림이 없어요.</p>
      )}
      <ul>
        {notifications.map((n) => (
          <li key={n.id}>
            <span>🟡 {n.greenhouseName}: {n.message}</span>
            <div>
              <button
                className="notification-inbox__go"
                onClick={() => onGoTo(n.greenhouseId)}
              >
                조치하러 가기
              </button>
              <button onClick={() => onDismiss(n.id)}>✕</button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
