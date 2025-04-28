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
# Check if DATABASE_URL is set, otherwise use a SQLite database as fallback
if os.environ.get("DATABASE_URL"):
    database_url = os.environ.get("DATABASE_URL")
    logger.info("Using PostgreSQL database from DATABASE_URL environment variable")
else:
    # Fallback to SQLite if DATABASE_URL is not set
    database_url = "sqlite:///nooyen_laser.db"
    logger.warning("DATABASE_URL environment variable not set! Using SQLite database as fallback.")
    logger.warning("For production use, please set DATABASE_URL environment variable to your PostgreSQL connection string.")
    logger.warning("Example: export DATABASE_URL='postgresql://username:password@localhost/nooyen_laser'")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Configure login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import models to create tables
with app.app_context():
    from models import User, RFIDCard, AccessLog, ApiKey
    db.create_all()
    
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
        
    db.session.commit()

# Import app logic after initializing database
from app import *

# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)