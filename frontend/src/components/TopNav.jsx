export default function TopNav({ view, onChangeView, warningCount, onOpenInbox }) {
  return (
    <nav className="top-nav">
      <button
        className={`top-nav__tab ${view === "chat" ? "is-active" : ""}`}
        onClick={() => onChangeView("chat")}
      >
        채팅
      </button>
      <button
        className={`top-nav__tab ${view === "dashboard" ? "is-active" : ""}`}
        onClick={() => onChangeView("dashboard")}
      >
        대시보드
      </button>
      {warningCount > 0 && (
        <button className="top-nav__badge" onClick={onOpenInbox}>
          🟡 {warningCount}
        </button>
      )}
    </nav>
  );
}
