import { useCallback, useEffect, useState } from "react";
import { dismissAlert, getAlerts, getState, resetDemo, runAlertAction, setAutoMode } from "../api";
import { INITIAL_HISTORY_LOG, INITIAL_PRODUCTION } from "./mockData";
import { SEVERITY_ORDER } from "./labels";

function joinGreenhousesWithAlerts(greenhouses, alerts) {
  const alertByGreenhouseId = new Map(alerts.map((a) => [a.greenhouse_id, a]));
  return greenhouses.map((gh) => {
    const alert = alertByGreenhouseId.get(gh.id);
    return {
      id: gh.id,
      name: gh.name,
      status: gh.status, // 실제 습도 기준 상태 (임계값 설명 등 정확한 수치용)
      // 경고가 방치되면 alert.escalated 가 true 가 되는데, 카드가 여전히
      // "경고"만 보여주면 상단 위험 배너와 모순돼 보인다(실측 확인) — 카드
      // 색/배지는 escalated 도 함께 반영해서 위험처럼 보이게 한다.
      escalated: alert?.escalated ?? false,
      temperature: gh.temperature,
      humidity: gh.humidity,
      devices: gh.devices,
      auto: gh.auto,
      reason: alert?.message ?? null,
      activeAlert: alert
        ? { id: alert.id, action: alert.action, message: alert.message, auto: alert.auto }
        : null,
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

  const toggleAutoMode = useCallback(
    async (greenhouseId, enabled) => {
      await setAutoMode(greenhouseId, enabled);
      await refresh();
    },
    [refresh]
  );

  return {
    greenhouses,
    notifications,
    production,
    historyLog,
    loading,
    error,
    refresh,
    runAction,
    dismiss,
    resetAll,
    toggleAutoMode,
  };
}
