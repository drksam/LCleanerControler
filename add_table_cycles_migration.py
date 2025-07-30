#!/usr/bin/env python3
"""
Database migration to add table cycles tracking to user sessions
"""

import os
import sys
import logging
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def add_table_cycles_column():
    """Add session_table_cycles column to user_session table"""
    try:
        from main import app, db
        from models import UserSession, is_using_postgres
        
        with app.app_context():
            print("🗄️  Adding table cycles column to user sessions...")
            
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = inspector.get_columns('user_session')
            column_names = [col['name'] for col in columns]
            
            if 'session_table_cycles' in column_names:
                print("✅ session_table_cycles column already exists")
                return True
            
            # Add the column based on database type
            if is_using_postgres():
                # PostgreSQL syntax
                sql = "ALTER TABLE user_session ADD COLUMN session_table_cycles INTEGER DEFAULT 0"
            else:
                # SQLite syntax
                sql = "ALTER TABLE user_session ADD COLUMN session_table_cycles INTEGER DEFAULT 0"
            
            print(f"Executing: {sql}")
            db.session.execute(db.text(sql))
            db.session.commit()
            
            print("✅ Successfully added session_table_cycles column")
            
            # Update any existing sessions to have 0 table cycles
            result = db.session.execute(db.text("""
                UPDATE user_session 
                SET session_table_cycles = 0 
                WHERE session_table_cycles IS NULL
            """))
            db.session.commit()
            
            print(f"✅ Updated {result.rowcount} existing sessions with default table cycles")
            
            return True
            
    except Exception as e:
        print(f"❌ Error adding table cycles column: {e}")
        logging.error(f"Migration error: {e}")
        return False

def verify_migration():
    """Verify the migration was successful"""
    try:
        from main import app, db
        from models import UserSession
        
        with app.app_context():
            # Try to query the new column
            result = db.session.execute(db.text("""
                SELECT COUNT(*) as count, 
                       COALESCE(SUM(session_table_cycles), 0) as total_cycles
                FROM user_session
            """)).fetchone()
            
            print(f"✅ Migration verification successful:")
            print(f"   - Total sessions: {result.count}")
            print(f"   - Total table cycles tracked: {result.total_cycles}")
            
            return True
            
    except Exception as e:
        print(f"❌ Migration verification failed: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Starting table cycles migration...")
    print("="*50)
    
    if add_table_cycles_column():
        if verify_migration():
            print("="*50)
            print("✅ Table cycles migration completed successfully!")
            print("📈 Performance tracking now includes table cycle efficiency")
        else:
            print("⚠️  Migration completed but verification failed")
            sys.exit(1)
    else:
        print("❌ Migration failed")
        sys.exit(1)
