# SolTalk VirtualFarm — 가상 농장 시뮬레이션

> 시간이 흐르고(tick) 장비를 조작하면(control) 환경값이 실제처럼 반응하는 가상 온실 엔진.
> 지금 backend 의 Mock 은 센서값이 고정이라 "창문을 열어도 습도가 안 떨어지는" 한계가 있는데, 이걸 해결한다.

## 형상관리 원칙

- **이 폴더(`virtualfarm/`)만 사용한다.** `backend/`, `frontend/` 는 이 브랜치에서 건드리지 않는다 → merge 충돌 없음.
- backend 코드를 import 하지 않는다. 대신 backend 의 `IoTAdapter` 계약(control/read 반환 스키마)과 **같은 모양**을 지켜서, 나중에 backend 쪽에서 어댑터 한 장으로 갈아끼울 수 있게 한다.
- 실제 농가 데이터 금지 — 초기값/물리 상수 전부 시연용 가짜 값 (`CLAUDE.md` 참고).

## 셋업 & 실행

```bash
cd virtualfarm
uv sync                          # 의존성 설치 (pytest)
uv run python -m pytest tests/   # 테스트 실행
```

## 구조

```
virtualfarm/
├── sim/
│   └── engine.py          # VirtualGreenhouse(tick/control/read) + VirtualFarm(다중 온실)
├── tests/
│   ├── test_engine.py     # 초기화/제어/조회/tick 물리 모델
│   ├── test_farm.py       # 다중 온실 독립성
│   ├── test_scenario.py   # "경고 → 창문 열기 → 경고 해소" 필수 시나리오
│   └── test_smoke.py
├── ADAPTER_CONTRACT.md    # backend 연동 계약 (연동 자체는 별도 브랜치)
└── pyproject.toml         # 자체 uv 프로젝트 (backend 와 독립)
```

## 시뮬레이션 모델 요약

- 모든 변화는 "목표값으로 지수 수렴"하는 1차 모델 — tick 을 쪼개든 크게 부르든 결과 동일, 목표 초과 없음.
- 창문 open → 습도가 외기(50%)로 서서히 수렴 · 관수 on → 습도가 95% 상한으로 수렴 · 차광막 closed → 온도 상승 억제(목표 38℃→32℃).
- 습도 0~100%, 온도 -20~60℃ 로 clamp.

## 다음 할 일

`todo/VIRTUALFARM.md` 참고.
