export const DEVICE_LABEL = { shade: "차광막", window: "창문", irrigation: "관수" };
export const SEVERITY_ORDER = { critical: 2, warning: 1, normal: 0 };

// --- 온실 상세 브리핑 문구 (경고/위험 시 사용자에게 상황을 설명) ---
export const STATUS_HEADLINE = {
  warning: { icon: "⚠️", text: "주의가 필요해요" },
  critical: { icon: "🚨", text: "긴급 조치가 필요해요" },
};

// 습도 임계값 (백엔드 GreenhouseService 판정 기준과 동일하게 유지)
export const HUMIDITY_THRESHOLD = { warning: 80, critical: 90 };

// 권장 조치(device:action)별 위험 설명·조치 효과 설명
export const ACTION_BRIEFING = {
  "window:open": {
    risk: "곰팡이병이 생겨 작물이 상할 수 있어요.",
    remedy: "창문을 열면 바깥 공기가 들어와 습도가 내려가요.",
    buttonIcon: "🪟",
  },
};
