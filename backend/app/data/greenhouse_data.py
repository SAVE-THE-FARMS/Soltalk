"""대시보드용 온실 정적 더미 데이터.

경고: 실제 농가 데이터 절대 금지. 전부 시연용 가짜 값.

온실 1번은 대시보드에서 실시간 값(MockIoTAdapter 상태 + mock_data.py)을 쓰고,
2/3번은 여기 정적 값을 그대로 쓴다 (챗봇으로 제어되지 않는 시연용 카드).
"""

GREENHOUSES = {
    1: {
        "name": "1번 온실(토마토)",
        "history": [
            {"timestamp": "2026-07-08T10:00:00", "humidity": 63},
            {"timestamp": "2026-07-08T11:00:00", "humidity": 64},
            {"timestamp": "2026-07-08T12:00:00", "humidity": 65},
        ],
    },
    2: {
        "name": "2번 온실(딸기)",
        "temperature": 24.0,
        "humidity": 82,
        "initial_devices": {"shade": "open", "window": "closed", "irrigation": "off"},
        "history": [
            {"timestamp": "2026-07-08T10:00:00", "humidity": 78},
            {"timestamp": "2026-07-08T11:00:00", "humidity": 80},
            {"timestamp": "2026-07-08T12:00:00", "humidity": 82},
        ],
    },
    3: {
        "name": "3번 온실(오이)",
        "temperature": 27.1,
        "humidity": 55,
        "initial_devices": {"shade": "closed", "window": "open", "irrigation": "off"},
        "history": [
            {"timestamp": "2026-07-08T10:00:00", "humidity": 58},
            {"timestamp": "2026-07-08T11:00:00", "humidity": 56},
            {"timestamp": "2026-07-08T12:00:00", "humidity": 55},
        ],
    },
}
