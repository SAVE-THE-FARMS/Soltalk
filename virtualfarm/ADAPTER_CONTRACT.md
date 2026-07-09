# VirtualGreenhouse ↔ backend 어댑터 계약

> backend 가 MockIoTAdapter 자리에 `VirtualGreenhouse` 를 갈아끼울 때 지켜지는 인터페이스 계약.
> **이 브랜치(VirtualFarm)에서는 backend 를 수정하지 않는다** — 실제 연결은 별도 브랜치에서.

## 1. `control(device, action)` 계약

backend `IoTAdapter.control()` 과 동일.

**입력**
| 파라미터 | 타입 | 허용값 |
|---|---|---|
| `device` | str | `shade` \| `window` \| `irrigation` |
| `action` | str | shade/window: `open`\|`close` · irrigation: `on`\|`off` |

**출력**
```python
# 성공 — action 은 상태로 정규화된다 (close → closed)
{"ok": True, "device": "window", "state": "open"}
# 실패 — 미지원 장비
{"ok": False, "device": "heater", "state": None, "reason": "unknown_device"}
# 실패 — 장비는 있지만 안 되는 동작 (예: 관수에 open). 상태는 바뀌지 않음
{"ok": False, "device": "irrigation", "state": "off", "reason": "invalid_action"}
```

## 2. `read(target)` 계약

backend `IoTAdapter.read()` 와 동일 + `environment` target 추가.

**입력**: `target` = `temperature` | `humidity` | `environment`

**출력**
```python
{"ok": True, "target": "temperature", "value": 24.0, "unit": "℃"}
{"ok": True, "target": "humidity", "value": 65.0, "unit": "%"}
# environment 는 VirtualGreenhouse 전용 확장 (unit 없음)
{"ok": True, "target": "environment", "value": {"temperature": 24.0, "humidity": 65.0}, "unit": None}
# 실패
{"ok": False, "target": "wind_speed", "reason": "unknown_target"}
```

⚠️ backend 의 MockIoTAdapter 가 지원하는 `production`(생산량) target 은 시뮬레이션 범위 밖이라 **없다**.
연동 시 backend 어댑터에서 production 만 기존 MOCK_DATA 로 처리해야 한다 (아래 4절).

## 3. backend 가 필요로 하는 최소 인터페이스

`backend/app/iot/base.py` 의 `IoTAdapter` 추상 클래스 기준:

```python
class IoTAdapter(ABC):
    def control(self, device: str, action: str) -> dict: ...
    def read(self, target: str) -> dict: ...
```

`VirtualGreenhouse` 는 두 메서드를 위 스키마로 제공하므로 형태상 호환.
추가로 시뮬레이션 구동에는 **주기적으로 `tick(seconds)` 를 불러줄 주체**가 필요하다
(backend 쪽 백그라운드 태스크 또는 요청 시점 lazy-tick — 연동 브랜치에서 결정).

## 4. 연동 시 수정 지점 (별도 브랜치에서)

1. **어댑터 클래스 추가** — backend 에 `VirtualFarmAdapter(IoTAdapter)` 를 만들어 내부에서 `VirtualGreenhouse` 를 감싼다.
   - `read("production")` 은 시뮬레이션에 없으므로 기존 `MOCK_DATA` 로 위임.
2. **조립 지점 교체** — `backend/app/container.py` 의 `AppContainer.__init__` 에서
   `MockIoTAdapter()` 대신 `VirtualFarmAdapter(...)` 주입 (온실별 인스턴스 구조는 동일).
3. **tick 구동** — FastAPI lifespan 백그라운드 태스크로 주기 tick, 또는 상태 조회 시 경과 시간만큼 lazy-tick.
4. **환경값 소스 전환** — `greenhouse_service._env_values_for()` 가 정적 `MOCK_DATA`/`GREENHOUSES` 대신
   어댑터의 `read("environment")` 를 쓰도록 변경 (온실 2·3번의 정적 값 → 시뮬레이션 값).
5. **패키징** — virtualfarm 을 backend 의존성으로 넣거나(로컬 경로), sim/ 모듈을 backend 로 복사.
   포트폴리오 데모 기준으로는 로컬 경로 의존이 단순해서 권장.

## 5. 다중 온실

`VirtualFarm(greenhouse_ids=[1, 2, 3])` — 온실별 독립 `VirtualGreenhouse` 보관.
`farm.greenhouse(id)` 로 꺼내 쓰고 `farm.tick_all(seconds)` 로 전체 시간 진행.
backend 의 `IOT_BY_GREENHOUSE: dict[int, adapter]` 구조와 1:1 대응된다.
