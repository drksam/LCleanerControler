from extensions import db, login_manager
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import flask

# Utility function to determine if we're using SQLite or PostgreSQL
def is_using_postgres():
    """Check if we're using PostgreSQL"""
    app = flask.current_app
    database_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    return 'postgresql' in database_url

# Define mixed-in behavior for suite integration
class SuiteIntegrationMixin:
    """Mixin for models that need to be synchronized with the suite database"""
    external_id = db.Column(db.String(100), nullable=True)
    last_synced = db.Column(db.DateTime, nullable=True)
    sync_status = db.Column(db.String(20), default="pending")  # pending, synced, conflict
    source_app = db.Column(db.String(50), default="cleaner_controller")
    
    def mark_synced(self):
        """Mark this record as successfully synced with the suite database"""
        self.last_synced = datetime.utcnow()
        self.sync_status = "synced"
        return self
        
    def to_sync_event(self, event_type):
        """Create a sync event for this record"""
        return SyncEvent(
            event_type=event_type,
            resource_type=self.__tablename__,
            resource_id=self.id,
            source_app="cleaner_controller",
            target_app="core",
            status="pending",
            payload=json.dumps(self.to_dict() if hasattr(self, "to_dict") else {})
        )

# Core shared models - Using the 'core' bind
class SuiteUser(UserMixin, db.Model):
    """User model for shared authentication across the suite"""
    __tablename__ = 'suite_users'
    # Bind key is managed by application, not hardcoded
    # __bind_key__ is managed by application
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True)
    auth_provider = db.Column(db.String(50), default="local")  # local, azure, google, etc.
    external_id = db.Column(db.String(100))  # ID in external auth system
    is_admin = db.Column(db.Boolean, default=False)
    rfid_tag = db.Column(db.String(64))  # Optional RFID association
    created_by_app = db.Column(db.String(50), default="cleaner_controller")  # Which app created this user
    managed_by_app = db.Column(db.String(50), default="cleaner_controller")  # Which app manages this user
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'username': self.username,
            'display_name': self.display_name,
            'email': self.email,
            'external_id': self.external_id,
            'is_admin': self.is_admin,
            'rfid_tag': self.rfid_tag,
            'active': self.active
        }
    
    def __repr__(self):
        return f'<SuiteUser {self.username}>'

class SuitePermission(db.Model):
    """Permissions for users across the suite applications"""
    __tablename__ = 'suite_permissions'
    # Bind key is managed by application, not hardcoded
    # __bind_key__ is managed by application
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('suite_users.id'), nullable=False)
    resource_type = db.Column(db.String(50))  # area, machine, report, etc.
    resource_id = db.Column(db.Integer)  # The ID of the resource
    app_context = db.Column(db.String(50))  # Which app this permission applies to
    permission_level = db.Column(db.String(20))  # view, edit, admin, operate, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('SuiteUser', backref=db.backref('permissions', lazy='dynamic'))
    
    def __repr__(self):
        return f'<SuitePermission {self.user_id} - {self.resource_type}:{self.resource_id}>'

class SyncEvent(db.Model):
    """Events to track synchronization between apps"""
    __tablename__ = 'sync_events'
    # Bind key is managed by application, not hardcoded
    # __bind_key__ is managed by application
    
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50))  # user.created, machine.updated, etc.
    resource_type = db.Column(db.String(50))  # user, machine, area, etc.
    resource_id = db.Column(db.Integer)
    source_app = db.Column(db.String(50))  # Which app generated this event
    target_app = db.Column(db.String(50))  # Which app should process this event
    status = db.Column(db.String(20), default="pending")  # pending, processed, failed
    payload = db.Column(db.Text)  # JSON data for the event
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<SyncEvent {self.event_type} {self.status}>'

# LCleanerController specific models - Keep backward compatibility with local app
# These use the 'cleaner_controller' bind when in PostgreSQL mode

class User(UserMixin, db.Model, SuiteIntegrationMixin):
    """User model for authentication (links to SuiteUser)"""
    __tablename__ = 'user'
    # Bind key is managed by application, not hardcoded
    # __bind_key__ is managed by application
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    full_name = db.Column(db.String(128))
    email = db.Column(db.String(120))
    department = db.Column(db.String(64))
    access_level = db.Column(db.String(20), default='operator')  # operator, admin, maintenance
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    suite_user_id = db.Column(db.Integer)  # Reference to SuiteUser ID for integration
    
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
            'user_id': self.id,
            'suite_user_id': self.suite_user_id
        }
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @classmethod
    def sync_from_suite_user(cls, suite_user):
        """Create or update a local User from a SuiteUser"""
        local_user = cls.query.filter_by(suite_user_id=suite_user.id).first()
        
        if not local_user:
            # Create new local user linked to suite user
            local_user = cls(
                username=suite_user.username,
                full_name=suite_user.display_name,
                email=suite_user.email,
                active=suite_user.active,
                access_level='admin' if suite_user.is_admin else 'operator',
                suite_user_id=suite_user.id,
                external_id=suite_user.external_id
            )
            db.session.add(local_user)
        else:
            # Update existing local user
            local_user.username = suite_user.username
            local_user.full_name = suite_user.display_name
            local_user.email = suite_user.email
            local_user.active = suite_user.active
            local_user.access_level = 'admin' if suite_user.is_admin else 'operator'
            local_user.external_id = suite_user.external_id
        
        local_user.mark_synced()
        return local_user

class RFIDCard(db.Model, SuiteIntegrationMixin):
    """RFID card model"""
    __tablename__ = 'rfid_card'
    # Bind key is managed by application, not hardcoded
    # __bind_key__ is managed by application
    
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.String(32), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    active = db.Column(db.Boolean, default=True)
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<RFIDCard {self.card_id}>'
    
    def to_dict(self):
        return {
            'card_id': self.card_id,
            'user_id': self.user_id,
            'active': self.active,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None
        }

class AccessLog(db.Model):
    """Log of authentication activities"""
    __tablename__ = 'access_log'
    # Bind key is managed by application, not hardcoded
    # __bind_key__ is managed by application
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    card_id = db.Column(db.String(32), nullable=True)
    machine_id = db.Column(db.String(64))
    action = db.Column(db.String(32))  # login, logout, access_denied
    details = db.Column(db.String(256), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AccessLog {self.action} {self.timestamp}>'
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'card_id': self.card_id,
            'machine_id': self.machine_id,
            'action': self.action,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }

class ApiKey(db.Model):
    """API keys for server authentication"""
    __tablename__ = 'api_key'
    # Bind key is managed by application, not hardcoded
    # __bind_key__ is managed by application
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(128))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ApiKey {self.description}>'