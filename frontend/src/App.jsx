import { useState } from "react";
import ChatScreen from "./components/ChatScreen";
import TopNav from "./components/TopNav";
import Dashboard from "./components/Dashboard/Dashboard";
import { useFarmData } from "./lib/useFarmData";

export default function App() {
  const [view, setView] = useState("chat"); // "chat" | "dashboard"
  const farm = useFarmData();
  const warningCount = farm.notifications.filter(
    (n) => n.severity === "warning"
  ).length;

  return (
    <div className="app">
      <h1>SolTalk 🌱</h1>
      <TopNav view={view} onChangeView={setView} warningCount={warningCount} />
      <div className={view === "chat" ? "screen" : "screen is-hidden"}>
        <ChatScreen />
      </div>
      <div className={view === "dashboard" ? "screen" : "screen is-hidden"}>
        <Dashboard farm={farm} />
      </div>
    </div>
  );
}
