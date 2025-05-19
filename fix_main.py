#!/usr/bin/env python3
"""
This script fixes the main.py file by rewriting it with proper indentation
and correctly setting up SQLAlchemy bindings for both PostgreSQL and SQLite.
"""
import os
import shutil

# Create a backup of the original file
if os.path.exists('main.py'):
    print("Creating backup of main.py as main.py.bak")
    shutil.copy2('main.py', 'main.py.bak')

# Rewrite the file with proper indentation
with open('main.py', 'w') as f:
    f.write('''import os
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

# Import and register blueprints and routes
from api_routes import register_api_routes
register_api_routes(app)
logger.info("API routes registered successfully")

# Import app routes last to avoid circular imports
from app import *
''')

print("Fixed main.py successfully!")
