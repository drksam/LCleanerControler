# extensions.py
# Holds shared Flask extensions to break circular imports

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
