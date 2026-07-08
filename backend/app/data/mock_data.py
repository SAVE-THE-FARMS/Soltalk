"""
조회용 더미 데이터 (뼈대).

경고: 실제 농가/생산 데이터는 절대 넣지 말 것. 시연은 전부 가짜 데이터로.
TODO(학생): 조회 명령("오늘 생산량", "지금 온도")에 맞춰 값을 채운다.
"""

MOCK_DATA = {
    "temperature": {"value": 24.5, "unit": "℃"},   # 지금 온도
    "humidity": {"value": 65, "unit": "%"},          # 습도
    "production": {"value": 120, "unit": "kg"},       # 오늘 생산량
}
