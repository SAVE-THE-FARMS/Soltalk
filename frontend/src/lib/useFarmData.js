import { useCallback, useEffect, useState } from "react";
import { dismissAlert, getAlerts, getState, resetDemo, runAlertAction } from "../api";
import { INITIAL_HISTORY_LOG, INITIAL_PRODUCTION } from "./mockData";
import { SEVERITY_ORDER } from "./labels";

function joinGreenhousesWithAlerts(greenhouses, alerts) {
  const alertByGreenhouseId = new Map(alerts.map((a) => [a.greenhouse_id, a]));
  return greenhouses.map((gh) => {
    const alert = alertByGreenhouseId.get(gh.id);
    return {
      id: gh.id,
      name: gh.name,
      status: gh.status,
      temperature: gh.temperature,
      humidity: gh.humidity,
      devices: gh.devices,
      reason: alert?.message ?? null,
      activeAlert: alert ? { id: alert.id, action: alert.action, message: alert.message } : null,
    };
  });
}

function toNotifications(alerts, greenhouses) {
  const nameById = new Map(greenhouses.map((gh) => [gh.id, gh.name]));
  return [...alerts]
    .sort((a, b) => SEVERITY_ORDER[b.level] - SEVERITY_ORDER[a.level])
    .map((a) => ({
      id: a.id,
      level: a.level,
      greenhouseId: a.greenhouse_id,
      greenhouseName: nameById.get(a.greenhouse_id) ?? `${a.greenhouse_id}번 온실`,
      message: a.message,
      action: a.action,
    }));
}

export function useFarmData() {
  const [greenhouses, setGreenhouses] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [production] = useState(INITIAL_PRODUCTION);
  const [historyLog] = useState(INITIAL_HISTORY_LOG);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [rawGreenhouses, rawAlerts] = await Promise.all([getState(), getAlerts()]);
      setGreenhouses(joinGreenhousesWithAlerts(rawGreenhouses, rawAlerts));
      setNotifications(toNotifications(rawAlerts, rawGreenhouses));
      setError(null);
    } catch (e) {
      setError("대시보드 데이터를 불러오지 못했어요.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const runAction = useCallback(
    async (alertId) => {
      await runAlertAction(alertId);
      await refresh();
    },
    [refresh]
  );

  const dismiss = useCallback(
    async (alertId) => {
      await dismissAlert(alertId);
      await refresh();
    },
    [refresh]
  );

  const resetAll = useCallback(async () => {
    await resetDemo();
    await refresh();
  }, [refresh]);

  return {
    greenhouses,
    notifications,
    production,
    historyLog,
    loading,
    error,
    runAction,
    dismiss,
    resetAll,
  };
}
