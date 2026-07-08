import { useCallback, useState } from "react";
import {
  INITIAL_GREENHOUSES,
  INITIAL_HISTORY_LOG,
  INITIAL_PRODUCTION,
} from "./mockData";
import { ACTION_LABEL, DEVICE_LABEL, SEVERITY_ORDER } from "./labels";

const STATUS_STEP_DOWN = { critical: "warning", warning: "normal" };

function formatNow() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, "0")}:${String(
    d.getMinutes()
  ).padStart(2, "0")}`;
}

export function useFarmData() {
  const [greenhouses, setGreenhouses] = useState(INITIAL_GREENHOUSES);
  const [production] = useState(INITIAL_PRODUCTION);
  const [historyLog, setHistoryLog] = useState(INITIAL_HISTORY_LOG);

  const controlDevice = useCallback(
    (greenhouseId, device, action) => {
      const target = greenhouses.find((gh) => gh.id === greenhouseId);
      if (!target) return;

      const matchesRecommended =
        target.recommendedAction &&
        target.recommendedAction.device === device &&
        target.recommendedAction.action === action;
      const nextStatus = matchesRecommended
        ? STATUS_STEP_DOWN[target.status] ?? target.status
        : target.status;
      const resolved = matchesRecommended && nextStatus === "normal";

      setGreenhouses((prev) =>
        prev.map((gh) =>
          gh.id === greenhouseId
            ? {
                ...gh,
                devices: { ...gh.devices, [device]: action },
                status: nextStatus,
                cause: resolved ? null : gh.cause,
                recommendedAction: resolved ? null : gh.recommendedAction,
              }
            : gh
        )
      );

      setHistoryLog((prev) => [
        {
          time: formatNow(),
          type: "manual",
          text: `${target.name} ${DEVICE_LABEL[device]} ${
            ACTION_LABEL[action] ?? action
          }`,
        },
        ...prev,
      ]);
    },
    [greenhouses]
  );

  const resetDemo = useCallback(() => {
    setGreenhouses(INITIAL_GREENHOUSES);
    setHistoryLog(INITIAL_HISTORY_LOG);
  }, []);

  const escalateDemo = useCallback(() => {
    setGreenhouses((prev) => {
      const idx = prev.findIndex((gh) => gh.status === "warning");
      if (idx === -1) return prev;
      return prev.map((gh, i) =>
        i === idx ? { ...gh, status: "critical" } : gh
      );
    });
  }, []);

  const notifications = greenhouses
    .filter((gh) => gh.status !== "normal")
    .sort((a, b) => SEVERITY_ORDER[b.status] - SEVERITY_ORDER[a.status])
    .map((gh) => ({
      id: gh.id,
      severity: gh.status,
      greenhouseId: gh.id,
      greenhouseName: gh.name,
      message: gh.cause,
    }));

  return {
    greenhouses,
    production,
    historyLog,
    notifications,
    controlDevice,
    resetDemo,
    escalateDemo,
  };
}
