// 생산량 위젯 / 처리 이력 위젯용 목업 데이터.
// 백엔드에 대응 API가 없어(GET /api/production, GET /api/logs 미구현) 계속 목데이터로 유지한다.
// 근거: Docs/superpowers/specs/2026-07-09-frontend-backend-integration-design.md

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
