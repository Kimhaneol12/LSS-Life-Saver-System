from flask import Flask
import requests
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

DATABASE = 'lss2.db'
TOKEN = "92d19235-9701-4605-b354-6382a7e7a605"

# SmartThings API 정보
API_URL = "https://api.smartthings.com/v1/devices/{}/status"
HEADERS = {"Authorization": "Bearer " + TOKEN}
DEVICES = {
    "door_sensor": "955c5bd3-65f1-4928-bd1e-836bddfc7b40",
    "leak_sensor": "1ed61fa6-04c6-4d25-91c9-343d7ae426f4",
    "motion_sensor": "2ae2d4f9-8308-4338-ab27-ecc3503d2f82"  # 업데이트된 device_id
}

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS door_sensor (id INTEGER PRIMARY KEY, status TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS leak_sensor (id INTEGER PRIMARY KEY, status TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS motion_sensor (id INTEGER PRIMARY KEY, status TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sensor_status (id INTEGER PRIMARY KEY AUTOINCREMENT, door_sensor TEXT, leak_sensor TEXT, motion_sensor TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()

def reset_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''DROP TABLE IF EXISTS sensor_status''')
    c.execute('''CREATE TABLE IF NOT EXISTS sensor_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    door_sensor TEXT, 
                    leak_sensor TEXT, 
                    motion_sensor TEXT, 
                    timestamp TEXT)''')
    conn.commit()
    conn.close()

def insert_data(table, status, timestamp):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(f"INSERT INTO {table} (status, timestamp) VALUES (?, ?)", (status, timestamp))
    conn.commit()
    conn.close()

def get_sensor_data(device_id):
    response = requests.get(API_URL.format(device_id), headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        return None

def fetch_and_store():
    statuses = {}
    timestamp = None

    for sensor_type, device_id in DEVICES.items():
        data = get_sensor_data(device_id)
        if data:
            if sensor_type == "door_sensor":
                statuses['door_sensor'] = data['components']['main']['contactSensor']['contact']['value']
                timestamp = data['components']['main']['contactSensor']['contact']['timestamp']
            elif sensor_type == "leak_sensor":
                statuses['leak_sensor'] = data['components']['main']['waterSensor']['water']['value']
                timestamp = data['components']['main']['waterSensor']['water']['timestamp']
            elif sensor_type == "motion_sensor":
                statuses['motion_sensor'] = data['components']['main']['motionSensor']['motion']['value']
                timestamp = data['components']['main']['motionSensor']['motion']['timestamp']
            
            insert_data(sensor_type, statuses[sensor_type], timestamp)

    insert_data_to_sensor_status(statuses, timestamp)

def insert_data_to_sensor_status(statuses, timestamp):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO sensor_status (door_sensor, leak_sensor, motion_sensor, timestamp) VALUES (?, ?, ?, ?)",
              (statuses.get('door_sensor'), statuses.get('leak_sensor'), statuses.get('motion_sensor'), timestamp))
    conn.commit()
    conn.close()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_store, 'interval', seconds=20)
    scheduler.start()

if __name__ == "__main__":
    init_db()
    start_scheduler()
    app.run(debug=True)
