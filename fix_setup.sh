#!/bin/bash

# Fix script for LCleanerControler database binding and f-string errors
echo "Applying fixes to LCleanerControler..."

# Create a backup of the main files
cp main.py main.py.bak
cp rfid_control.py rfid_control.py.bak
echo "Backups created: main.py.bak and rfid_control.py.bak"

# Fix 1: Update main.py to handle SQLite bindings
cat > main.py.new << 'EOL'
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
EOL

# Append the rest of the original main.py file, skipping the first 60 lines
tail -n +60 main.py.bak >> main.py.new
mv main.py.new main.py
echo "Fixed main.py database bindings and indentation"

# Fix 2: Update rfid_control.py to fix f-string syntax error
sed -i 's/logging.info(f"Running in {OPERATION_MODE} mode - RFID hardware {"will be used but not required" if PROTOTYPE_MODE else "will not be used"}")/status_msg = "will be used but not required" if PROTOTYPE_MODE else "will not be used"\n    logging.info(f"Running in {OPERATION_MODE} mode - RFID hardware {status_msg}")/' rfid_control.py
echo "Fixed f-string syntax error in rfid_control.py"

# Fix 3: Add model changes for SQLite compatibility
sed -i 's/__bind_key__ = .core./# __bind_key__ is managed by application/' models.py
sed -i 's/__bind_key__ = .cleaner_controller./# __bind_key__ is managed by application/' models.py
echo "Updated models.py to make bind keys flexible"

echo "All fixes applied successfully!"
echo "You can now run: python3 test_run.py --prototype --debug"
