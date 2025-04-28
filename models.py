from main import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    """User model for authentication"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    full_name = db.Column(db.String(128))
    email = db.Column(db.String(120))
    department = db.Column(db.String(64))
    access_level = db.Column(db.String(20), default='operator')  # operator, admin, maintenance
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    rfid_cards = db.relationship('RFIDCard', backref='user', lazy='dynamic')
    access_logs = db.relationship('AccessLog', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'username': self.username,
            'full_name': self.full_name,
            'department': self.department,
            'access_level': self.access_level,
            'user_id': self.id
        }
    
    def __repr__(self):
        return f'<User {self.username}>'


class RFIDCard(db.Model):
    """RFID card model"""
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.String(32), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    active = db.Column(db.Boolean, default=True)
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<RFIDCard {self.card_id}>'


class AccessLog(db.Model):
    """Log of authentication activities"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    card_id = db.Column(db.String(32), nullable=True)
    machine_id = db.Column(db.String(64))
    action = db.Column(db.String(32))  # login, logout, access_denied
    details = db.Column(db.String(256), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AccessLog {self.action} {self.timestamp}>'


class ApiKey(db.Model):
    """API keys for server authentication"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(128))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ApiKey {self.description}>'