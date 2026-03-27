from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False) # ID/Roll Number
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'teacher' or 'student'
    
    # Profile details (especially for students)
    name = db.Column(db.String(100), nullable=False)
    course = db.Column(db.String(100), nullable=True)
    year = db.Column(db.String(20), nullable=True)
    avatar = db.Column(db.String(255), nullable=True, default='default.png')
    dob = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    
    # Relationships
    sessions_created = db.relationship('AttendanceSession', backref='teacher', lazy=True)
    attendance_records = db.relationship('AttendanceRecord', backref='student', lazy=True)
    notices_posted = db.relationship('Notice', backref='author', lazy=True)


class AttendanceSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_code = db.Column(db.String(10), unique=True, nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    records = db.relationship('AttendanceRecord', backref='session', lazy=True)


class AttendanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_session.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ensure a student can only mark attendance once per session
    __table_args__ = (db.UniqueConstraint('session_id', 'student_id', name='_session_student_uc'),)


class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
