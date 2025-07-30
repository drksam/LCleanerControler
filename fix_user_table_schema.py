#!/usr/bin/env python3
"""
User Table Schema Fix
====================

Adds missing columns to the user table to match the application model:
- suite_user_id (from User model)
- external_id (from SuiteIntegrationMixin)
- last_synced (from SuiteIntegrationMixin)
- sync_status (from SuiteIntegrationMixin)
- source_app (from SuiteIntegrationMixin)

These columns are required for Shop Suite integration features.
"""

import sqlite3
import os
from datetime import datetime

def fix_user_table_schema():
    """Add missing columns to user table"""
    
    print("🔧 User Table Schema Fix")
    print("=" * 40)
    
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
        
        print("🔍 Checking current user table schema...")
        
        # Get current table structure
        cursor.execute("PRAGMA table_info(user)")
        current_columns = [row[1] for row in cursor.fetchall()]
        print(f"📊 Current columns: {current_columns}")
        
        # Define columns that need to be added
        missing_columns = [
            ("suite_user_id", "INTEGER"),
            ("external_id", "VARCHAR(100)"),
            ("last_synced", "DATETIME"),
            ("sync_status", "VARCHAR(20)", "pending"),
            ("source_app", "VARCHAR(50)", "cleaner_controller")
        ]
        
        # Check which columns are missing and add them
        columns_added = []
        
        for col_info in missing_columns:
            col_name = col_info[0]
            col_type = col_info[1]
            default_value = col_info[2] if len(col_info) > 2 else None
            
            if col_name not in current_columns:
                # Build ALTER TABLE statement
                if default_value:
                    alter_sql = f"ALTER TABLE user ADD COLUMN {col_name} {col_type} DEFAULT '{default_value}'"
                else:
                    alter_sql = f"ALTER TABLE user ADD COLUMN {col_name} {col_type}"
                
                print(f"➕ Adding column: {col_name} ({col_type})")
                cursor.execute(alter_sql)
                columns_added.append(col_name)
            else:
                print(f"✓ Column {col_name} already exists")
        
        if columns_added:
            print(f"🎉 Added {len(columns_added)} missing columns: {', '.join(columns_added)}")
        else:
            print("✅ All required columns already exist!")
        
        # Commit changes
        conn.commit()
        
        # Verify the updated schema
        print("\n🔍 Verifying updated user table schema...")
        cursor.execute("PRAGMA table_info(user)")
        updated_columns = [row[1] for row in cursor.fetchall()]
        print(f"📊 Updated columns: {updated_columns}")
        
        # Check for any users without the required sync status
        if 'sync_status' in columns_added:
            print("\n🔄 Updating existing users with default sync status...")
            cursor.execute("UPDATE user SET sync_status = 'pending' WHERE sync_status IS NULL")
            updated_rows = cursor.rowcount
            if updated_rows > 0:
                print(f"✅ Updated {updated_rows} users with default sync status")
            conn.commit()
        
        conn.close()
        
        print("\n✅ User table schema fix completed successfully!")
        print("\n🚀 Try running the application again:")
        print("  python test_run.py --production-db --hardware")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing user table schema: {e}")
        return False

if __name__ == '__main__':
    fix_user_table_schema()
