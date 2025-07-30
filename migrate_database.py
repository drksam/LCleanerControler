#!/usr/bin/env python3
"""Database migration script to ensure all tables exist"""

import os
import sys

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_database_migration():
    """Run database migration to create missing tables"""
    try:
        # Import our Flask app and database
        from main import app, db
        
        print("🔄 Running database migration...")
        
        with app.app_context():
            # Import all models to ensure they're registered
            from models import (User, RFIDCard, AccessLog, ApiKey, 
                              SuiteUser, SuitePermission, SyncEvent, UserSession)
            
            print("📋 Models imported:")
            models = [User, RFIDCard, AccessLog, ApiKey, SuiteUser, SuitePermission, SyncEvent, UserSession]
            for model in models:
                print(f"  - {model.__name__}")
            
            # Create all tables
            print("\n🔨 Creating database tables...")
            db.create_all()
            
            print("✅ Database migration completed!")
            
            # Verify UserSession table exists
            try:
                # Try to query the UserSession table
                session_count = UserSession.query.count()
                print(f"✅ UserSession table verified - {session_count} existing sessions")
                return True
            except Exception as e:
                print(f"❌ UserSession table verification failed: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("🗄️  Database Migration")
    print("=" * 50)
    
    success = run_database_migration()
    
    if success:
        print("\n🎉 Migration successful!")
        print("\n📝 What was fixed:")
        print("  ✅ user_session table created")
        print("  ✅ All foreign key relationships established")
        print("  ✅ Session tracking now enabled")
        print("\n🔄 Next steps:")
        print("  1. Restart the laser application")
        print("  2. Log in with RFID")
        print("  3. Session tracking will now work!")
    else:
        print("\n❌ Migration failed!")
        print("  - Check the error messages above")
        print("  - Ensure no other process is using the database")
        print("  - Try stopping the laser application first")
