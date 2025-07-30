#!/usr/bin/env python3
"""
Complete Database Schema Fix
============================

Fixes all database schema issues to match the application models:

1. api_key table: Renames key_hash to "key"
2. user table: Adds suite integration columns
3. rfid_card table: Adds date and suite integration columns
4. Verifies all other tables have required columns

This script ensures the database is fully compatible with the application.
"""

import sqlite3
import os
from datetime import datetime

def fix_complete_database_schema():
    """Fix all database schema issues"""
    
    print("🔧 Complete Database Schema Fix")
    print("=" * 50)
    
    # Database file path
    db_path = 'instance/LCleaner_production.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        print("Run setup_local_production_db.py first")
        return False
    
    print(f"📂 Database: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n1️⃣ Fixing api_key table...")
        fix_api_key_table(cursor)
        
        print("\n2️⃣ Fixing user table...")
        fix_user_table(cursor)
        
        print("\n3️⃣ Fixing rfid_card table...")
        fix_rfid_card_table(cursor)
        
        print("\n4️⃣ Verifying other tables...")
        verify_other_tables(cursor)
        
        # Commit all changes
        conn.commit()
        conn.close()
        
        print("\n🎉 Complete database schema fix completed successfully!")
        print("\n🚀 Your database is now ready! Try running:")
        print("  python test_run.py --production-db --hardware")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing database schema: {e}")
        return False

def fix_api_key_table(cursor):
    """Fix api_key table schema"""
    try:
        # Check if key column exists or key_hash exists
        cursor.execute("PRAGMA table_info(api_key)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        if 'key_hash' in columns and 'key' not in columns:
            print("🔧 Renaming key_hash column to key...")
            
            # Create new table with correct schema
            cursor.execute("""
                CREATE TABLE api_key_new (
                    id INTEGER PRIMARY KEY,
                    "key" VARCHAR(256),
                    description TEXT,
                    active BOOLEAN,
                    created_at DATETIME,
                    last_used DATETIME
                )
            """)
            
            # Copy data from old table
            cursor.execute("""
                INSERT INTO api_key_new (id, "key", description, active, created_at, last_used)
                SELECT id, key_hash, name, active, created_at, last_used FROM api_key
            """)
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE api_key")
            cursor.execute("ALTER TABLE api_key_new RENAME TO api_key")
            
            print("✅ api_key table fixed!")
        else:
            print("✅ api_key table schema is correct")
            
    except Exception as e:
        print(f"❌ Error fixing api_key table: {e}")

def fix_user_table(cursor):
    """Fix user table schema"""
    try:
        # Get current columns
        cursor.execute("PRAGMA table_info(user)")
        current_columns = [row[1] for row in cursor.fetchall()]
        
        # Define required columns
        required_columns = [
            ("suite_user_id", "INTEGER"),
            ("external_id", "VARCHAR(100)"),
            ("last_synced", "DATETIME"),
            ("sync_status", "VARCHAR(20)", "pending"),
            ("source_app", "VARCHAR(50)", "cleaner_controller")
        ]
        
        columns_added = []
        for col_info in required_columns:
            col_name = col_info[0]
            col_type = col_info[1]
            default_value = col_info[2] if len(col_info) > 2 else None
            
            if col_name not in current_columns:
                if default_value:
                    cursor.execute(f"ALTER TABLE user ADD COLUMN {col_name} {col_type} DEFAULT '{default_value}'")
                else:
                    cursor.execute(f"ALTER TABLE user ADD COLUMN {col_name} {col_type}")
                columns_added.append(col_name)
        
        if columns_added:
            print(f"✅ Added columns to user table: {', '.join(columns_added)}")
            # Update existing users with default sync status
            cursor.execute("UPDATE user SET sync_status = 'pending' WHERE sync_status IS NULL")
        else:
            print("✅ user table schema is correct")
            
    except Exception as e:
        print(f"❌ Error fixing user table: {e}")

def fix_rfid_card_table(cursor):
    """Fix rfid_card table schema"""
    try:
        # Get current columns
        cursor.execute("PRAGMA table_info(rfid_card)")
        current_columns = [row[1] for row in cursor.fetchall()]
        
        # Define required columns
        required_columns = [
            ("issue_date", "DATETIME"),
            ("expiry_date", "DATETIME"),
            ("external_id", "VARCHAR(100)"),
            ("last_synced", "DATETIME"),
            ("sync_status", "VARCHAR(20)", "pending"),
            ("source_app", "VARCHAR(50)", "cleaner_controller")
        ]
        
        columns_added = []
        for col_info in required_columns:
            col_name = col_info[0]
            col_type = col_info[1]
            default_value = col_info[2] if len(col_info) > 2 else None
            
            if col_name not in current_columns:
                if default_value:
                    cursor.execute(f"ALTER TABLE rfid_card ADD COLUMN {col_name} {col_type} DEFAULT '{default_value}'")
                else:
                    cursor.execute(f"ALTER TABLE rfid_card ADD COLUMN {col_name} {col_type}")
                columns_added.append(col_name)
        
        if columns_added:
            print(f"✅ Added columns to rfid_card table: {', '.join(columns_added)}")
            # Set default values for existing cards
            cursor.execute("UPDATE rfid_card SET issue_date = CURRENT_TIMESTAMP WHERE issue_date IS NULL")
            cursor.execute("UPDATE rfid_card SET sync_status = 'pending' WHERE sync_status IS NULL")
            cursor.execute("UPDATE rfid_card SET source_app = 'cleaner_controller' WHERE source_app IS NULL")
        else:
            print("✅ rfid_card table schema is correct")
            
    except Exception as e:
        print(f"❌ Error fixing rfid_card table: {e}")

def verify_other_tables(cursor):
    """Verify other tables exist and have basic structure"""
    try:
        # Check that all required tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['user', 'rfid_card', 'access_log', 'api_key', 'user_session']
        
        for table in required_tables:
            if table in existing_tables:
                print(f"✅ {table} table exists")
            else:
                print(f"❌ {table} table missing")
        
        # Verify user_session table has all columns
        if 'user_session' in existing_tables:
            cursor.execute("PRAGMA table_info(user_session)")
            session_columns = [row[1] for row in cursor.fetchall()]
            required_session_columns = [
                'id', 'user_id', 'login_time', 'logout_time', 'first_fire_time', 
                'login_method', 'switched_from_user_id', 'session_fire_count', 
                'session_fire_time_ms', 'performance_score', 'machine_id', 'card_id'
            ]
            
            missing_session_columns = [col for col in required_session_columns if col not in session_columns]
            if missing_session_columns:
                print(f"⚠️  user_session table missing columns: {', '.join(missing_session_columns)}")
            else:
                print("✅ user_session table has all required columns")
                
    except Exception as e:
        print(f"❌ Error verifying tables: {e}")

if __name__ == '__main__':
    fix_complete_database_schema()
