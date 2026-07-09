# 스마트팜 AI 에이전트 — 1차 API 문서

> 대상: 자연어 제어·조회 + 대시보드 + 인앱 알림 (음성/카카오톡 연동/솔캐스트 예측은 2차 확장)

---

## 1.1 자연어 채팅 (제어/조회 통합)

**`POST /api/chat`**

| 항목 | 내용 |
|---|---|
| 설명 | 사용자의 자연어 명령/질문을 받아 의도 파악 → 장비 제어 또는 데이터 조회 실행 → 자연어 응답 반환 |
| Request Body | `{ "session_id": "string", "message": "string" }` |
| Response Body | `{ "reply": "string", "actions_taken": [ { "device": "shade", "greenhouse_id": 1, "action": "close", "success": true } ], "updated_state": { "1": { "shade": "open", ... }, "2": {...}, "3": {...} } }` |
| 비고 | 세션별 최근 대화 히스토리 유지 (재질문 흐름 대응). 온실 지정 명령 지원 ("2번 온실 창문 열어줘", "딸기 온실 습도 몇이야?") — 미지정 시 1번 온실 대상. `updated_state` 는 온실 번호별 장비 상태 |

---

## 1.2 대시보드 전체 상태 조회

**`GET /api/state`**

| 항목 | 내용 |
|---|---|
| 설명 | 전체 온실의 현재 상태 요약 (대시보드 메인 화면용) |
| Response Body | `{ "greenhouses": [ { "id": 1, "name": "1번 온실(토마토)", "status": "normal|warning|critical", "temperature": 26.4, "humidity": 68, "devices": { "shade": "open", "window": "closed", "irrigation": "off" }, "last_updated": "..." } ] }` |
| 비고 | `status` 필드 기준으로 프론트에서 카드 정렬(critical→warning→normal) |

**`GET /api/state/{greenhouse_id}`**

| 항목 | 내용 |
|---|---|
| 설명 | 특정 온실 상세 상태 (카드 클릭 시 상세화면용) |
| Response Body | `{ "id": 1, "status": "warning", "reason": "습도 82%, 임계값 80% 초과 2일 지속", "recommended_action": { "device": "window", "action": "open", "label": "창문 열기" }, "current_values": {...}, "history": [ { "timestamp": "...", "humidity": 78 }, ... ] }` |
| 비고 | `reason`, `recommended_action`은 Claude가 생성한 설명을 캐싱해서 내려줌 |

---

## 1.3 알림(인앱 시뮬레이션)

**`GET /api/alerts`**

| 항목 | 내용 |
|---|---|
| 설명 | 미해결 알림 목록 (심각도순 정렬) |
| Response Body | `{ "alerts": [ { "id": "a1", "level": "critical|warning|info", "greenhouse_id": 2, "message": "습도 82%, 곰팡이병 위험", "created_at": "...", "escalated": false, "action": { "device": "window", "action": "open", "label": "창문 열기" } } ] }` |

**`POST /api/alerts/{alert_id}/action`**

| 항목 | 내용 |
|---|---|
| 설명 | 알림 내 원터치 실행 버튼 클릭 시 즉시 장비 제어 실행 |
| Response Body | `{ "success": true, "message": "2번 온실 창문을 열었습니다.", "updated_state": {...} }` |

**`POST /api/alerts/{alert_id}/dismiss`**

| 항목 | 내용 |
|---|---|
| 설명 | 알림 확인/닫기 처리 |

---

## 1.4 처리 이력 로그

**`GET /api/logs/today`**

| 항목 | 내용 |
|---|---|
| 설명 | 오늘 AI가 자동/수동으로 처리한 액션 이력 (대시보드 하단 표시용) |
| Response Body | `{ "logs": [ { "timestamp": "...", "type": "auto|manual", "description": "2번 온실 습도 급상승 감지 → 창문 자동 개방" } ] }` |

---

## 1.5 생산량 요약

**`GET /api/production/summary?period=today|week|month`**

| 항목 | 내용 |
|---|---|
| 설명 | 기간별 생산량 및 평균 대비 증감률 |
| Response Body | `{ "period": "today", "total_kg": 42, "compare_to_avg_percent": 7.7, "trend": [ { "date": "...", "kg": 40 } ] }` |

---

## 1.6 데모 유틸리티

**`POST /api/reset`**

| 항목 | 내용 |
|---|---|
| 설명 | 전체 Mock 상태를 초기값으로 리셋 (리허설/재시연용) |

---

## 우선순위

| 1차 필수 | 시간 남으면 |
|---|---|
| 1.1, 1.2, 1.3, 1.6 | 1.4, 1.5 |
