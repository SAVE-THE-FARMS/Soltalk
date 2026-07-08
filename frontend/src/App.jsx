import { useState } from "react";
import ChatScreen from "./components/ChatScreen";
import TopNav from "./components/TopNav";
import Dashboard from "./components/Dashboard/Dashboard";
import GreenhouseDetail from "./components/GreenhouseDetail";
import { useFarmData } from "./lib/useFarmData";

export default function App() {
  const [view, setView] = useState("chat");
  const [selectedGreenhouseId, setSelectedGreenhouseId] = useState(null);
  const farm = useFarmData();
  const warningCount = farm.notifications.filter(
    (n) => n.severity === "warning"
  ).length;

  function handleChangeView(nextView) {
    setSelectedGreenhouseId(null);
    setView(nextView);
  }

  const selectedGreenhouse = farm.greenhouses.find(
    (gh) => gh.id === selectedGreenhouseId
  );

  return (
    <div className="app">
      <h1>SolTalk 🌱</h1>
      <TopNav view={view} onChangeView={handleChangeView} warningCount={warningCount} />
      <div className={view === "chat" ? "screen" : "screen is-hidden"}>
        <ChatScreen />
      </div>
      <div className={view === "dashboard" ? "screen" : "screen is-hidden"}>
        {selectedGreenhouse ? (
          <GreenhouseDetail
            greenhouse={selectedGreenhouse}
            onBack={() => setSelectedGreenhouseId(null)}
            onControlDevice={farm.controlDevice}
          />
        ) : (
          <Dashboard farm={farm} onSelectGreenhouse={setSelectedGreenhouseId} />
        )}
      </div>
    </div>
  );
}
