# VirtualFarm TODO (가상 농장 시뮬레이션)

> 목표: 센서값이 고정인 Mock 을 넘어, 시간·장비 조작에 반응하는 가상 온실.
> 작업 위치: **`virtualfarm/` 폴더만** (backend/frontend 는 이 브랜치에서 안 건드림 — merge 충돌 방지).
> 셋업/실행: [virtualfarm/README.md](../virtualfarm/README.md)

## 1. 시뮬레이션 코어 (`sim/engine.py`) — TDD 로
- [ ] `VirtualGreenhouse.__init__`: 환경값(온도/습도) + 장비 상태 초기화
- [ ] `control(device, action)`: backend 와 같은 반환 스키마로 장비 상태 변경
- [ ] `tick(seconds)`: 시간 경과에 따른 환경 변화
  - 창문 open → 습도가 외기값 쪽으로 서서히 수렴
  - 관수 on → 습도 상승
  - 차광막 close → 온도 상승 억제
- [ ] `read(target)`: 현재 환경값 조회 (backend 와 같은 반환 스키마)

## 2. 시나리오 검증
- [ ] "습도 82% 경고 → 창문 열기 → 몇 tick 후 습도 80% 아래로 → 경고 해소" 시나리오가 테스트로 재현되는지

## 3. backend 연동 준비 (구현은 나중에, 별도 브랜치에서)
- [ ] backend 가 갈아끼울 수 있는 어댑터 명세 문서화 (control/read 계약 확인)
- [ ] (선택) 다중 온실 지원 — 온실 3개 각각 독립 시뮬레이션

## 절대 하지 말 것
- backend/, frontend/ 파일 수정 금지 (이 브랜치에서는)
- 실제 농가 데이터/솔캐스트 금지 (`CLAUDE.md`)
