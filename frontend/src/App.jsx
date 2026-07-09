import { useRef, useState } from "react";
import ChatScreen from "./components/ChatScreen";
import TopNav from "./components/TopNav";
import Dashboard from "./components/Dashboard/Dashboard";
import GreenhouseDetail from "./components/GreenhouseDetail";
import CriticalBanner from "./components/NotificationCenter/CriticalBanner";
import NotificationInbox from "./components/NotificationCenter/NotificationInbox";
import { useFarmData } from "./lib/useFarmData";

export default function App() {
  const [view, setView] = useState("chat");
  const [selectedGreenhouseId, setSelectedGreenhouseId] = useState(null);
  const [inboxOpen, setInboxOpen] = useState(false);
  const hasInteractedRef = useRef(false);
  const farm = useFarmData();

  const criticalNotifications = farm.notifications.filter((n) => n.level === "critical");
  const warningNotifications = farm.notifications.filter((n) => n.level === "warning");

  function handleChangeView(nextView) {
    setSelectedGreenhouseId(null);
    setView(nextView);
    if (nextView === "dashboard") farm.refresh();
  }

  function handleAction(alertId) {
    farm.runAction(alertId);
  }

  function handleDismiss(alertId) {
    farm.dismiss(alertId);
  }

  function handleReset() {
    farm.resetAll();
  }

  const selectedGreenhouse = farm.greenhouses.find((gh) => gh.id === selectedGreenhouseId);

  return (
    <div
      className="app"
      onClickCapture={() => {
        hasInteractedRef.current = true;
      }}
    >
      <CriticalBanner
        notifications={criticalNotifications}
        onAction={handleAction}
        onDismiss={handleDismiss}
        canPlaySound={hasInteractedRef.current}
      />
      <h1 className="display-face">SolTalk 🌱</h1>
      <div className="header-underline" />
      <TopNav
        view={view}
        onChangeView={handleChangeView}
        warningCount={warningNotifications.length}
        onOpenInbox={() => setInboxOpen(true)}
      />
      {inboxOpen && (
        <NotificationInbox
          notifications={warningNotifications}
          onAction={handleAction}
          onDismiss={handleDismiss}
          onClose={() => setInboxOpen(false)}
        />
      )}
      <div className={view === "chat" ? "screen" : "screen is-hidden"}>
        <ChatScreen />
      </div>
      <div className={view === "dashboard" ? "screen" : "screen is-hidden"}>
        {selectedGreenhouse ? (
          <GreenhouseDetail
            greenhouse={selectedGreenhouse}
            onBack={() => setSelectedGreenhouseId(null)}
            onAction={handleAction}
          />
        ) : (
          <Dashboard
            farm={farm}
            onSelectGreenhouse={setSelectedGreenhouseId}
            onReset={handleReset}
          />
        )}
      </div>
    </div>
  );
}
