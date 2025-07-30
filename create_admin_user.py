#!/usr/bin/env python3
"""
Create default admin user for LCleanerController
Run this script to add the default admin user to the database
"""

import sys
import os

# Add the parent directory to the path so we can import the application modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from models import db, User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin_user():
    """Create the default admin user"""
    with app.app_context():
        try:
            # Check if admin user already exists
            existing_admin = User.query.filter_by(username='admin').first()
            if existing_admin:
                logger.info("Admin user already exists")
                logger.info(f"Username: {existing_admin.username}")
                logger.info(f"Access Level: {existing_admin.access_level}")
                logger.info(f"Active: {existing_admin.active}")
                return

            # Create the admin user
            admin_user = User(
                username="admin",
                full_name="Default Administrator", 
                email="admin@laser.local",
                department="System Administration",
                access_level="admin",
                active=True
            )
            admin_user.set_password("pigfloors")
            
            # Add to database
            db.session.add(admin_user)
            db.session.commit()
            
            logger.info("✅ Successfully created default admin user!")
            logger.info("Username: admin")
            logger.info("Password: pigfloors")
            logger.info("Access Level: admin")
            
        except Exception as e:
            logger.error(f"❌ Error creating admin user: {e}")
            db.session.rollback()

if __name__ == "__main__":
    print("Creating default admin user for LCleanerController...")
    create_admin_user()
    print("Done!")
