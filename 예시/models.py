from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# SQLAlchemy 인스턴스 생성
db = SQLAlchemy()


# 사용자 모델 정의
class Users(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)  # 기본 키, 자동 증가 정수
    name = db.Column(db.String(80), unique=True, nullable=False)  # 사용자 이름, 고유, 필수
    password_hash = db.Column(db.String(128), nullable=False)  # 해시된 비밀번호, 필수
    station = db.relationship('Station', backref='user')  # 사용자와 스테이션 간의 일대일 관계

    # 비밀번호 설정 메서드
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # 비밀번호 확인 메서드
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.id}>'


# 스테이션 모델 정의
class Station(db.Model):
    __tablename__ = 'stations'

    id = db.Column(db.Integer, primary_key=True)  # 기본 키, 자동 증가 정수
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)  # 사용자 ID, 고유, 필수
    plugs = db.relationship('Plug', backref='station')  # 스테이션과 플러그 간의 일대다 관계

    def __repr__(self):
        return f'<Station {self.id}>'


# 플러그 모델 정의
class Plug(db.Model):
    __tablename__ = 'plugs'

    id = db.Column(db.Integer, primary_key=True)  # 기본 키, 자동 증가 정수
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)  # 스테이션 ID, 필수
    device_id = db.Column(db.String(80), nullable=False)  # 장치 ID, 필수
    device_type = db.Column(db.String(80), nullable=False)  # 장치 유형, 필수
    golden_time = db.Column(db.Integer, nullable=False, default=0)  # 기준 시간, 필수, 기본값 0
    golden_power = db.Column(db.Float, nullable=False, default=0)  # 기준 전력, 필수, 기본값 0
    plug_raws = db.relationship('Plug_Raw', backref='plug')  # 플러그와 플러그 원시 데이터 간의 일대다 관계
    storages = db.relationship('Storage', backref='plug')  # 플러그와 스토리지 간의 일대다 관계

    def __repr__(self):
        return f'<Plug {self.id}>'


# 플러그 원시 데이터 모델 정의
class Plug_Raw(db.Model):
    __tablename__ = 'plug_raws'

    id = db.Column(db.Integer, primary_key=True)  # 기본 키, 자동 증가 정수
    plug_id = db.Column(db.Integer, db.ForeignKey('plugs.id'), nullable=False)  # 플러그 ID, 필수
    power_state = db.Column(db.String(80), nullable=False)  # 전력 상태, 필수
    current_power = db.Column(db.Float, nullable=False)  # 현재 전력, 필수
    total_power_usage = db.Column(db.Float, nullable=False)  # 총 전력 사용량, 필수
    current_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # 현재 날짜, 필수, 기본값 UTC 현재 시간
    start_date = db.Column(db.DateTime, nullable=False)  # 시작 날짜, 필수

    def __repr__(self):
        return f'<Plug_Raw {self.id}>'


# 스토리지 모델 정의
class Storage(db.Model):
    __tablename__ = 'storages'

    id = db.Column(db.Integer, primary_key=True)  # 기본 키, 자동 증가 정수
    plug_id = db.Column(db.Integer, db.ForeignKey('plugs.id'), nullable=False)  # 플러그 ID, 필수
    register_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # 등록 날짜, 필수, 기본값 UTC 현재 시간
    daily_usage_time = db.Column(db.Integer, nullable=False, default=0)  # 일일 사용 시간, 필수, 기본값 0
    daily_power_usage = db.Column(db.Float, nullable=False, default=0)  # 일일 전력 사용량, 필수, 기본값 0

    def __repr__(self):
        return f'<Storage {self.id}>'