from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from models import db, Users, Station, Plug, Plug_Raw, Storage
import requests
from datetime import datetime
from dateutil import parser
import numpy as np
from sqlalchemy import desc

DEVICE_ID = "29e137c3-04b5-44f2-8689-5e33fc555a60"  # 장치 ID 상수
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/initdb')
def init_db():
    with app.app_context():
        db.drop_all()  # 모든 테이블 삭제
        db.create_all()  # 모든 테이블 생성
    return "Database initialized!"  # 데이터베이스 초기화 완료 메시지

@app.route('/create_test_data')
def create_test_data():
    with app.app_context():
        # 테스트 사용자 생성
        new_user = Users(name="test_user")
        new_user.set_password("password")
        db.session.add(new_user)
        db.session.commit()

        # 사용자에 대한 테스트 스테이션 생성
        new_station = Station(user_id=new_user.id)
        db.session.add(new_station)
        db.session.commit()

        # 스테이션에 대한 테스트 플러그 생성
        new_plug = Plug(station_id=new_station.id, device_id="29e137c3-04b5-44f2-8689-5e33fc555a60", device_type="godegee", golden_time=10, golden_power=5.0)
        db.session.add(new_plug)
        db.session.commit()

        # 생성된 엔티티의 ID 조회
        user_id = new_user.id
        station_id = new_station.id
        plug_id = new_plug.id

    return jsonify({
        "user_id": user_id,
        "station_id": station_id,
        "plug_id": plug_id
    })

@app.route('/create_plug', methods=['POST'])
def create_plug():
    data = request.get_json()
    station_id = data.get('station_id')
    device_id = data.get('device_id')
    device_type = data.get('device_type')
    golden_time = data.get('golden_time', 10)  # 기본값 10
    golden_power = data.get('golden_power', 5.0)  # 기본값 5.0

    with app.app_context():
        # 스테이션 존재 여부 확인
        station = Station.query.get(station_id)
        if not station:
            return jsonify({"error": "Station not found"}), 404

        # 새로운 플러그 생성 및 데이터베이스에 추가
        new_plug = Plug(station_id=station_id, device_id=device_id, device_type=device_type, golden_time=golden_time, golden_power=golden_power)
        db.session.add(new_plug)
        db.session.commit()

        return jsonify({
            "station_id": new_plug.station_id,
            "plug_id": new_plug.id,
            "device_id": new_plug.device_id,
            "device_type": new_plug.device_type
        })

@app.route('/golden_test/<int:plug_id>')
def golden_test(plug_id):
    with app.app_context():
        plug = Plug.query.get(plug_id)
        if plug:
            data, _ = fetch_data(plug.id, plug.device_id)
            components = data.get('components', {}).get('main', {})
            switch_info = components.get('switch', {}).get('switch', {})

            # 스위치가 켜져 있고 시간 기준을 초과했는지 확인
            if switch_info.get('value', 'off') == 'on':
                start_date_str = switch_info.get('timestamp', datetime.utcnow().isoformat())
                start_date = parser.parse(start_date_str).replace(tzinfo=None)
                current_date = datetime.utcnow()
                time_difference = (current_date - start_date).total_seconds() / 60  # 분 단위로 변환
                if time_difference > plug.golden_time:
                    return jsonify({"status": True, "reason": "Time threshold exceeded"})

            # 전력 기준을 초과했는지 확인
            power_info = components.get('powerMeter', {}).get('power', {})
            power_value = power_info.get('value', 0.0)
            if power_value > plug.golden_power:
                return jsonify({"status": True, "reason": "Power threshold exceeded"})

            return jsonify({"status": False})
        else:
            return "No plug found!"

@app.route('/golden_test/all')
def golden_test_all():
    with app.app_context():
        plugs = Plug.query.all()
        results = []
        for plug in plugs:
            data, _ = fetch_data(plug.id, plug.device_id)
            components = data.get('components', {}).get('main', {})
            switch_info = components.get('switch', {}).get('switch', {})

            # 스위치가 켜져 있고 시간 기준을 초과했는지 확인
            if switch_info.get('value', 'off') == 'on':
                start_date_str = switch_info.get('timestamp', datetime.utcnow().isoformat())
                start_date = parser.parse(start_date_str).replace(tzinfo=None)
                current_date = datetime.utcnow()
                time_difference = (current_date - start_date).total_seconds() / 60  # 분 단위로 변환
                if time_difference > plug.golden_time:
                    results.append({
                        "plug_id": plug.id,
                        "status": True,
                        "reason": "Time threshold exceeded"
                    })
                    continue

            # 전력 기준을 초과했는지 확인
            power_info = components.get('powerMeter', {}).get('power', {})
            power_value = power_info.get('value', 0.0)
            if power_value > plug.golden_power:
                results.append({
                    "plug_id": plug.id,
                    "status": True,
                    "reason": "Power threshold exceeded"
                })
                continue

            results.append({
                "plug_id": plug.id,
                "status": False,
                "reason": None
            })

        return jsonify(results)

@app.route('/read_plugs', methods=['GET'])
def read_plugs():
    with app.app_context():
        plugs = Plug.query.all()
        result = []
        for plug in plugs:
            data, _ = fetch_data(plug.id, plug.device_id)
            components = data.get('components', {}).get('main', {})

            power_info = components.get('powerMeter', {}).get('power', {})
            power_value = power_info.get('value', 0.0)

            power_consumption_info = components.get('powerConsumptionReport', {}).get('powerConsumption', {}).get('value', {})
            total_energy = power_consumption_info.get('energy', 0)

            switch_info = components.get('switch', {}).get('switch', {})
            switch_value = switch_info.get('value', 'off')
            start_date_str = switch_info.get('timestamp', datetime.utcnow().isoformat())

            power_state = switch_value
            current_date = datetime.utcnow()

            # 문자열을 datetime 객체로 변환
            start_date = parser.parse(start_date_str)

            result.append({
                "plug_id": plug.id,
                "device_id": plug.device_id,
                "power_state": power_state,
                "current_power": power_value,
                "total_power_usage": total_energy,
                "current_date": current_date.isoformat(),
                "start_date": start_date.isoformat(),
                "golden_time": plug.golden_time,
                "golden_power": plug.golden_power,
            })

        return jsonify(result)

@app.route('/set_golden_time_by_device_id', methods=['POST'])
def set_golden_time_by_device_id():
    data = request.get_json()
    device_id = data.get('device_id')
    golden_time = data.get('golden_time')

    if not device_id or not golden_time:
        return jsonify({"error": "device_id and golden_time are required"}), 400

    with app.app_context():
        plug = Plug.query.filter_by(device_id=device_id).first()
        if not plug:
            return jsonify({"error": "Plug not found"}), 404

        plug.golden_time = golden_time
        db.session.add(plug)
        try:
            db.session.commit()
            return jsonify({"message": "Golden time updated successfully"})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Failed to update golden time: {e}"}), 500

@app.route('/set_golden_time_by_device_type', methods=['POST'])
def set_golden_time_by_device_type():
    data = request.get_json()
    device_type = data.get('device_type')
    golden_time = data.get('golden_time')

    if not device_type or not golden_time:
        return jsonify({"error": "device_type and golden_time are required"}), 400

    with app.app_context():
        plugs = Plug.query.filter_by(device_type=device_type).all()
        if not plugs:
            return jsonify({"error": "No plugs found with the given device_type"}), 404

        for plug in plugs:
            plug.golden_time = golden_time
            db.session.add(plug)

        try:
            db.session.commit()
            return jsonify({"message": "Golden time updated successfully for all plugs with device_type"})
        except Exception as e:
            db.session
