import { useEffect, useRef, useState } from "react";
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

  // 어느 화면에서든 주기적으로 다시 불러온다. 알림 배지/배너/알림함은 채팅 탭에도
  // 보이고, 채팅·음성으로 조치한 뒤에도 습도가 서서히(수 분에 걸쳐) 내려가며 경고가
  // 해제되기 때문 — 대시보드에서만 폴링하면 채팅 화면의 경고가 낡은 채 안 사라진다(실측).
  useEffect(() => {
    const id = setInterval(farm.refresh, 3000);
    return () => clearInterval(id);
  }, [farm.refresh]);

  const criticalNotifications = farm.notifications.filter((n) => n.level === "critical");
  const warningNotifications = farm.notifications.filter((n) => n.level === "warning");

  function handleChangeView(nextView) {
    setSelectedGreenhouseId(null);
    setView(nextView);
    if (nextView === "dashboard") farm.refresh();
  }

  function handleAction(alertId) {
    return farm.runAction(alertId); // 호출한 쪽에서 완료를 기다릴 수 있게 promise 반환
  }

  function handleDismiss(alertId) {
    farm.dismiss(alertId);
  }

  // 알림함 "조치하러 가기" — 장비를 바로 조작하지 않고 해당 온실 브리핑으로 이동
  function handleGoToGreenhouse(greenhouseId) {
    setInboxOpen(false);
    setView("dashboard");
    setSelectedGreenhouseId(greenhouseId);
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
          onGoTo={handleGoToGreenhouse}
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
            onToggleAuto={farm.toggleAutoMode}
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
