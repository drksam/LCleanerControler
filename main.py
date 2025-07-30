import os
import logging
import sys
import secrets
from flask import Flask
# --- CHANGES: Use extensions.py for db and login_manager ---
from extensions import db, login_manager

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

# --- CHANGES: Initialize db and login_manager with app here ---
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'main_bp.login'

from models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize Shop Suite integration and webhook system
with app.app_context():
    # First import models to create tables
    from models import User, RFIDCard, AccessLog, ApiKey, SuiteUser, SuitePermission, SyncEvent, UserSession
    
    # For SQLite mode, dynamically adjust the model bindings
    if 'sqlite' in database_url:
        for model in [SuiteUser, SuitePermission, SyncEvent, User, RFIDCard, AccessLog, ApiKey, UserSession]:
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
    
    # Initialize WS2812B LED status indicator - DISABLED (handled by Flask app)
    # The LED is now managed by the Flask application in app.py
    try:
        logger.info("WS2812B LED management delegated to Flask application")
        # Old LED initialization code disabled to prevent conflicts
        # from ws2812bFlash import status_led
        
        # if status_led.initialize():
        #     logger.info("WS2812B LED status indicator initialized")
        #     
        #     # Set initial boot state
        #     status_led.set_booting()
        #     
        #     # Schedule transition to idle state after 5 seconds
        #     import threading
        #     threading.Timer(5.0, lambda: status_led.set_idle()).start()
        # else:
        #     logger.warning("Failed to initialize WS2812B LED status indicator")
            
    except Exception as e:
        logger.error(f"Error initializing WS2812B LED status indicator: {e}")
        logger.error(f"Error setting up webhook system: {e}")
        logger.warning("Continuing without webhook integration")

    # Create API keys if none exist (for first run)
    from models import ApiKey
    if ApiKey.query.count() == 0:
        import uuid
        first_key = ApiKey(
            key=uuid.uuid4().hex + uuid.uuid4().hex,
            description="Default API key generated on first run"
        )
        db.session.add(first_key)
        db.session.commit()
        logger.info(f"Created default API key: {first_key.key}")

    # Create default admin user if none exist (for first run)
    from models import User
    if User.query.filter_by(access_level='admin').count() == 0:
        default_admin = User(
            username="admin",
            full_name="Default Administrator",
            email="admin@laser.local",
            department="System Administration",
            access_level="admin",
            active=True
        )
        default_admin.set_password("pigfloors")
        db.session.add(default_admin)
        db.session.commit()
        logger.info("Created default admin user: admin / pigfloors")

    # Create default operator user if none exist (for first run)
    if User.query.filter_by(username='laser').count() == 0:
        default_operator = User(
            username="laser",
            full_name="Default Operator",
            email="operator@laser.local",
            department="Operations",
            access_level="operator",
            active=True
        )
        default_operator.set_password("piglaser")
        db.session.add(default_operator)
        db.session.commit()
        logger.info("Created default operator user: laser / piglaser")

    # Create default RFID cards if they don't exist
    admin_user = User.query.filter_by(username='admin').first()
    laser_user = User.query.filter_by(username='laser').first()
    
    if admin_user and not RFIDCard.query.filter_by(card_id='2667607583').first():
        admin_card = RFIDCard(
            card_id='2667607583',
            user_id=admin_user.id,
            active=True
        )
        db.session.add(admin_card)
        logger.info("Created default admin RFID card: 2667607583")
    
    if laser_user and not RFIDCard.query.filter_by(card_id='3743073564').first():
        laser_card = RFIDCard(
            card_id='3743073564',
            user_id=laser_user.id,
            active=True
        )
        db.session.add(laser_card)
        logger.info("Created default laser RFID card: 3743073564")
    
    # Commit any new RFID cards
    db.session.commit()

# Import and register blueprints and routes
from api_routes import register_api_routes
register_api_routes(app)
logger.info("API routes registered successfully")

# Register main app routes blueprint
from app import main_bp, init_controllers, inject_globals, page_not_found, server_error

app.register_blueprint(main_bp)

# Register context processor and error handlers
app.context_processor(inject_globals)
app.register_error_handler(404, page_not_found)
app.register_error_handler(500, server_error)

init_controllers(app)
