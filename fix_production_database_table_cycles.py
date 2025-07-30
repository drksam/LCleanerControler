#!/usr/bin/env python3
"""
Production database migration to add table cycles tracking to user sessions
"""

import os
import sys
import sqlite3
import logging

def add_table_cycles_column_direct():
    """Add session_table_cycles column directly to the production database"""
    try:
        # Use the production database path from the logs
        db_path = '/home/laser/LCleanerController/instance/LCleaner_production.db'
        
        if not os.path.exists(db_path):
            print(f"❌ Production database not found at {db_path}")
            return False
        
        print(f"🗄️  Migrating production database: {db_path}")
        
        # Connect directly to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(user_session)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📋 Current user_session columns: {column_names}")
        
        if 'session_table_cycles' in column_names:
            print("✅ session_table_cycles column already exists")
            conn.close()
            return True
        
        # Add the column
        print("🔧 Adding session_table_cycles column...")
        cursor.execute("ALTER TABLE user_session ADD COLUMN session_table_cycles INTEGER DEFAULT 0")
        
        # Update existing sessions to have 0 table cycles
        cursor.execute("UPDATE user_session SET session_table_cycles = 0 WHERE session_table_cycles IS NULL")
        affected_rows = cursor.rowcount
        
        # Commit changes
        conn.commit()
        
        print("✅ Successfully added session_table_cycles column")
        print(f"✅ Updated {affected_rows} existing sessions with default table cycles")
        
        # Verify the migration
        cursor.execute("SELECT COUNT(*) FROM user_session")
        total_sessions = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(session_table_cycles) FROM user_session")
        total_cycles = cursor.fetchone()[0] or 0
        
        print(f"✅ Verification successful:")
        print(f"   - Total sessions: {total_sessions}")
        print(f"   - Total table cycles tracked: {total_cycles}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error in direct migration: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Starting production database migration...")
    print("="*60)
    
    if add_table_cycles_column_direct():
        print("="*60)
        print("✅ Production database migration completed successfully!")
        print("📈 Performance tracking now includes table cycle efficiency")
        print("🔄 Please restart the Flask application to use the new schema")
    else:
        print("❌ Migration failed")
        sys.exit(1)
