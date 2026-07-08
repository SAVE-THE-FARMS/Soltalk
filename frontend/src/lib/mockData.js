// 대시보드/알림/상세 화면용 목업 데이터.
// 챗봇(/chat) 데이터와는 무관한 독립 데이터다.

export const INITIAL_GREENHOUSES = [
  {
    id: "gh-1",
    name: "1번 온실",
    status: "normal",
    temperature: 23.8,
    humidity: 58,
    devices: { shade: "open", window: "closed", irrigation: "off" },
    cause: null,
    recommendedAction: null,
    history: [
      { time: "06:00", temperature: 19.2, humidity: 55 },
      { time: "09:00", temperature: 21.5, humidity: 57 },
      { time: "12:00", temperature: 23.8, humidity: 58 },
      { time: "15:00", temperature: 24.1, humidity: 56 },
      { time: "18:00", temperature: 22.0, humidity: 59 },
    ],
  },
  {
    id: "gh-2",
    name: "2번 온실",
    status: "warning",
    temperature: 26.4,
    humidity: 82,
    devices: { shade: "open", window: "closed", irrigation: "on" },
    cause: "습도 82%, 임계값 80% 초과 2일 지속",
    recommendedAction: { label: "창문 열기", device: "window", action: "open" },
    history: [
      { time: "06:00", temperature: 24.0, humidity: 76 },
      { time: "09:00", temperature: 25.1, humidity: 78 },
      { time: "12:00", temperature: 26.0, humidity: 80 },
      { time: "15:00", temperature: 26.4, humidity: 82 },
      { time: "18:00", temperature: 26.2, humidity: 82 },
    ],
  },
  {
    id: "gh-3",
    name: "3번 온실",
    status: "critical",
    temperature: 31.2,
    humidity: 45,
    devices: { shade: "closed", window: "closed", irrigation: "off" },
    cause: "차광막이 닫혀 온도가 31.2도까지 상승, 임계값(30도) 초과",
    recommendedAction: { label: "차광막 열기", device: "shade", action: "open" },
    history: [
      { time: "06:00", temperature: 26.0, humidity: 50 },
      { time: "09:00", temperature: 28.4, humidity: 48 },
      { time: "12:00", temperature: 30.1, humidity: 46 },
      { time: "15:00", temperature: 31.2, humidity: 45 },
      { time: "18:00", temperature: 31.0, humidity: 45 },
    ],
  },
];

export const INITIAL_PRODUCTION = {
  today: 128,
  week: 812,
  unit: "kg",
  diffPct: 6,
  direction: "up",
};

export const INITIAL_HISTORY_LOG = [
  { time: "07:12", type: "auto", text: "1번 온실 관수 자동 종료" },
  { time: "10:05", type: "auto", text: "2번 온실 관수 자동 시작" },
  { time: "13:40", type: "manual", text: "3번 온실 차광막 수동 닫힘" },
];
