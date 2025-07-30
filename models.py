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
    created_at = db.Column(db.DateTime, default=datetime.now)  # Use local time for user records
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
    issue_date = db.Column(db.DateTime, default=datetime.now)  # Use local time for user-facing dates
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
    timestamp = db.Column(db.DateTime, default=datetime.now)  # Use local time for user activity logs
    
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

class UserSession(db.Model):
    """Track user sessions and performance metrics"""
    __tablename__ = 'user_session'
    # Bind key is managed by application, not hardcoded
    # __bind_key__ is managed by application
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.now)  # Use local time instead of UTC
    logout_time = db.Column(db.DateTime, nullable=True)
    first_fire_time = db.Column(db.DateTime, nullable=True)
    login_method = db.Column(db.String(20), default='rfid')  # rfid, web, auto_switch
    switched_from_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # If user switching occurred
    session_fire_count = db.Column(db.Integer, default=0)
    session_fire_time_ms = db.Column(db.BigInteger, default=0)
    session_table_cycles = db.Column(db.Integer, default=0)  # Track table cycles for performance
    performance_score = db.Column(db.Float, nullable=True)  # Enhanced performance score with cycles (higher is better)
    machine_id = db.Column(db.String(64), default='laser_room_1')
    card_id = db.Column(db.String(32), nullable=True)
    
    user = db.relationship('User', foreign_keys=[user_id], backref='sessions')
    switched_from_user = db.relationship('User', foreign_keys=[switched_from_user_id])
    
    def calculate_performance_score(self):
        """Calculate enhanced performance score that rewards efficiency
        
        Formula: (session_table_cycles * 100) - (session_fire_count * 10) - (session_duration_minutes * 2) + (optimal_fire_ratio * 50)
        
        - More table cycles = better (batch processing efficiency)
        - Fewer fires = better (precision/quality)
        - Less time = better (speed efficiency)
        - Optimal fire time ratio = better (skill/technique)
        
        Higher score is better (opposite of old system)
        """
        if self.logout_time and self.login_time:
            # Calculate total session time in minutes for more readable scoring
            session_duration = (self.logout_time - self.login_time).total_seconds() / 60.0
            
            # Convert fiber fire time from milliseconds to seconds
            fiber_fire_time_seconds = (self.session_fire_time_ms or 0) / 1000.0
            
            # Calculate optimal fire time ratio (sweet spot around 30-60 seconds per fire)
            fires = max(self.session_fire_count or 0, 1)  # Avoid division by zero
            avg_fire_time = fiber_fire_time_seconds / fires
            
            # Optimal fire time bonus (peak efficiency around 45 seconds per fire)
            optimal_fire_ratio = 1.0
            if 30 <= avg_fire_time <= 60:
                # Reward optimal fire times
                optimal_fire_ratio = 1.5 - abs(avg_fire_time - 45) / 30
            elif avg_fire_time < 30:
                # Penalize rushed fires (quality concern)
                optimal_fire_ratio = avg_fire_time / 30
            else:
                # Penalize overly long fires (efficiency concern)
                optimal_fire_ratio = max(0.2, 60 / avg_fire_time)
            
            # Enhanced performance formula (higher is better)
            table_cycles_score = (self.session_table_cycles or 0) * 100  # Major efficiency factor
            fire_count_penalty = (self.session_fire_count or 0) * 10      # Quality factor
            time_penalty = session_duration * 2                          # Speed factor
            technique_bonus = optimal_fire_ratio * 50                     # Skill factor
            
            self.performance_score = table_cycles_score - fire_count_penalty - time_penalty + technique_bonus
            return self.performance_score
        return None
    
    def to_dict(self):
        try:
            username = self.user.username if self.user else None
        except:
            # If user relationship is not accessible, try to get it directly
            try:
                from models import User
                user = User.query.get(self.user_id)
                username = user.username if user else None
            except:
                username = None
                
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': username,
            'login_time': self.login_time.isoformat() if self.login_time else None,
            'logout_time': self.logout_time.isoformat() if self.logout_time else None,
            'first_fire_time': self.first_fire_time.isoformat() if self.first_fire_time else None,
            'login_method': self.login_method,
            'switched_from_user_id': self.switched_from_user_id,
            'session_fire_count': self.session_fire_count,
            'session_fire_time_ms': self.session_fire_time_ms,
            'session_table_cycles': self.session_table_cycles,
            'performance_score': self.performance_score,
            'machine_id': self.machine_id,
            'card_id': self.card_id
        }
    
    def __repr__(self):
        try:
            username = self.user.username if self.user else "Unknown"
        except:
            username = f"User{self.user_id}" if self.user_id else "Unknown"
        return f'<UserSession {username} - {self.login_time}>'