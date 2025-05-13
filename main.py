import os
import logging
import sys
import secrets
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   stream=sys.stdout)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", secrets.token_hex(32))

# Configure database
# Check for DATABASE_URL, otherwise fallback to SQLite for development
if os.environ.get("DATABASE_URL"):
    database_url = os.environ.get("DATABASE_URL")
    logger.info("Using production database from DATABASE_URL environment variable")
else:
    # Fallback to SQLite if DATABASE_URL is not set (development mode)
    database_url = "sqlite:///Shop_laser.db"
    logger.warning("DATABASE_URL environment variable not set! Using SQLite database as fallback.")
    logger.warning("For production use, please set DATABASE_URL environment variable to your PostgreSQL connection string.")
    logger.warning("Example: export DATABASE_URL='postgresql://username:password@localhost/shop_suite_db'")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure connection pooling for multi-app access
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 10,
    "max_overflow": 20,
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Configure schema binding for Shop Suite integration
# This sets up separate schemas for core shared data and app-specific data
if 'postgresql' in database_url:
    app.config["SQLALCHEMY_BINDS"] = {
        'core': os.environ.get("CORE_DATABASE_URL", database_url),
        'cleaner_controller': os.environ.get("CLEANER_DATABASE_URL", database_url + "?schema=cleaner_controller"),
    }
    logger.info("Configured database schema bindings for Shop Suite integration")
else:
    # For SQLite, use same database for all bindings
    app.config["SQLALCHEMY_BINDS"] = {
        'core': database_url,
        'cleaner_controller': database_url,
    }
    logger.info("Using SQLite without schema separation for development/prototype mode")

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Configure login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize Shop Suite integration and webhook system
with app.app_context():
    # First import models to create tables
    from models import User, RFIDCard, AccessLog, ApiKey, SuiteUser, SuitePermission, SyncEvent
    
    # For SQLite mode, dynamically adjust the model bindings
    if 'sqlite' in database_url:
        for model in [SuiteUser, SuitePermission, SyncEvent, User, RFIDCard, AccessLog, ApiKey]:
            try:
                # Reset any bind keys for SQLite to use main database
                if hasattr(model, '__bind_key__'):
                    model.__bind_key__ = None
            except:
                pass
    
    # Create all tables
    db.create_all()
    # Initialize sync handler for Shop Suite integration
    try:
        from sync_handler import SyncHandler, register_sync_tasks
        
        # Initialize database schemas and structures for Shop Suite
        SyncHandler.initialize_sync()
        
        # Register sync tasks for regular data synchronization
        sync_scheduler = register_sync_tasks(app)
        if sync_scheduler:
            logger.info("Shop Suite synchronization tasks scheduled")
            
        # Perform initial user synchronization if in PostgreSQL mode
        if 'postgresql' in database_url:
            SyncHandler.sync_users()
            logger.info("Initial user synchronization completed")
            
    except Exception as e:
        logger.error(f"Error setting up Shop Suite integration: {e}")
        logger.warning("Continuing without Shop Suite integration")
    
    # Initialize webhook system for real-time event notifications
    try:
        from webhook_handler import webhook_handler, register_webhook_tasks
        
        # Register webhook tasks for retry handling
        webhook_scheduler = register_webhook_tasks(app)
        if webhook_scheduler:
            logger.info("Webhook retry tasks scheduled")
            
        # Send a node status event to indicate the application is starting up
        webhook_handler.send_node_status_event("starting", {"message": "LCleanerController starting up"})
        
    except Exception as e:
        logger.error(f"Error setting up webhook system: {e}")
        logger.warning("Continuing without webhook integration")
    
    # Create default users if they don't exist
    from werkzeug.security import generate_password_hash
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            full_name='Administrator',
            access_level='admin',
            active=True
        )
        admin_user.password_hash = generate_password_hash('Pigfloors')
        db.session.add(admin_user)
        
    laser_user = User.query.filter_by(username='laser').first()
    if not laser_user:
        laser_user = User(
            username='laser',
            full_name='Laser Operator',
            access_level='operator',
            active=True
        )
        laser_user.password_hash = generate_password_hash('Piglaser')
        db.session.add(laser_user)
        
    # Create default API key for authentication if none exists
    default_api_key = ApiKey.query.filter_by(description='Default API Key').first()
    if not default_api_key:
        from secrets import token_hex
        api_key = token_hex(32)  # Generate a secure 64-character API key
        default_api_key = ApiKey(
            key=api_key,
            description='Default API Key',
            active=True
        )
        db.session.add(default_api_key)
        logger.info(f"Created default API key: {api_key}")
        
    db.session.commit()
    
    # Register API routes
    from api_routes import register_api_routes
    register_api_routes(app)
    logger.info("API routes registered successfully")
    
# Import app logic after initializing database
from app import *

# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    # Try to load from local User model first
    user = User.query.get(int(user_id))
    
    # If not found, try suite user (if in PostgreSQL mode)
    if user is None and 'core' in app.config.get("SQLALCHEMY_BINDS", {}):
        try:
            # Check if this might be a suite user ID
            suite_user = SuiteUser.query.get(int(user_id))
            if suite_user:
                # Look up or create the corresponding local user
                user = User.sync_from_suite_user(suite_user)
                db.session.commit()
        except Exception as e:
            logger.error(f"Error looking up suite user: {e}")
    
    return user

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)