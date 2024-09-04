import time
import sqlite3
from database import DATABASE

# 상수 정의
DOOR_CLOSE_TIMEOUT = 20  # 문이 닫힌 신호를 기다리는 최대 시간 (초)
MOTION_DETECTION_TIMEOUT = 600  # 동작 감지가 발생한 최대 시간 (초)

def determine_risk_level():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # 최신 데이터 가져오기
    c.execute("SELECT status, timestamp FROM door_sensor ORDER BY timestamp DESC LIMIT 1")
    row = c.fetchone()
    door_status, door_timestamp = row if row else (None, None)

    c.execute("SELECT status, timestamp FROM motion_sensor ORDER BY timestamp DESC LIMIT 1")
    row = c.fetchone()
    motion_status, motion_timestamp = row if row else (None, None)

    c.execute("SELECT status, timestamp FROM leak_sensor ORDER BY timestamp DESC LIMIT 1")
    row = c.fetchone()
    leak_status, leak_timestamp = row if row else (None, None)

    conn.close()

    # 기본 위험도 수준
    risk_level = 0

    # 문이 열림을 감지한 경우
    if door_status == "open":
        current_time = time.time()
        if motion_timestamp and (current_time - float(motion_timestamp)) <= MOTION_DETECTION_TIMEOUT:
            print("문이 열림을 감지했으며, 10분 안에 동작 감지가 발생했습니다. 화장실 사용으로 판단하여 위험도를 초기화합니다.")
            return 0
        else:
            print("문이 열림을 감지했으나 10분 안에 동작 감지가 발생하지 않았습니다. Risk 1로 설정합니다.")
            return 1

    # 문이 닫힘 신호를 기다리는 경우
    if door_status == "closed":
        current_time = time.time()
        if door_timestamp and (current_time - float(door_timestamp)) <= DOOR_CLOSE_TIMEOUT:
            print("20초 안에 문이 닫힌 신호가 발생했습니다. 위험도를 설정합니다.")
            return 2
        else:
            print("20초 안에 문이 닫히지 않았습니다. 위험도를 설정합니다.")
            return 1

    # 문이 닫힘 신호를 기다리고 10분 안에 동작 감지가 발생하지 않은 경우
    if door_status == "closed" and door_timestamp and (current_time - float(door_timestamp)) <= DOOR_CLOSE_TIMEOUT:
        if not motion_timestamp or (current_time - float(motion_timestamp)) > MOTION_DETECTION_TIMEOUT:
            if leak_status == "detected":
                print("20초 내에 문이 닫혔으며, 10분 안에 동작 감지가 발생하지 않았고 누수가 감지되었습니다. Risk 4로 설정합니다.")
                return 4
            else:
                print("20초 내에 문이 닫혔으며, 10분 안에 동작 감지가 발생하지 않았으나 누수가 감지되지 않았습니다. Risk 2로 설정합니다.")
                return 2

    # 모든 조건을 만족하지 않을 경우 기본 위험도 반환
    return risk_level

# 위험도에 따른 처리
def evaluate_situation():
    risk_level = determine_risk_level()

    if risk_level >= 3:
        response_service(risk_level)
    else:
        print(f"현재 위험도: {risk_level}, 모니터링 계속")

# 응급 서비스 활성화
def response_service(risk_level):
    if risk_level >= 3:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO risk_level (level, timestamp) VALUES (?, datetime('now'))", (risk_level,))
        conn.commit()
        conn.close()
        print(f"위험도 {risk_level}가 데이터베이스에 기록되었습니다.")
        print("응급 서비스 활성화됨")
    else:
        print("응급 서비스 미활성화")
