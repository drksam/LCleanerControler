#!/usr/bin/env python3
"""
RFID Card Table Schema Fix
==========================

Adds missing columns to the rfid_card table to match the application model:
- issue_date (from RFIDCard model)
- expiry_date (from RFIDCard model)  
- external_id (from SuiteIntegrationMixin)
- last_synced (from SuiteIntegrationMixin)
- sync_status (from SuiteIntegrationMixin)
- source_app (from SuiteIntegrationMixin)

These columns are required for RFID card management and Shop Suite integration.
"""

import sqlite3
import os
from datetime import datetime

def fix_rfid_card_table_schema():
    """Add missing columns to rfid_card table"""
    
    print("🔧 RFID Card Table Schema Fix")
    print("=" * 45)
    
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
        
        print("🔍 Checking current rfid_card table schema...")
        
        # Get current table structure
        cursor.execute("PRAGMA table_info(rfid_card)")
        current_columns = [row[1] for row in cursor.fetchall()]
        print(f"📊 Current columns: {current_columns}")
        
        # Define columns that need to be added
        missing_columns = [
            ("issue_date", "DATETIME"),
            ("expiry_date", "DATETIME"),
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
                    alter_sql = f"ALTER TABLE rfid_card ADD COLUMN {col_name} {col_type} DEFAULT '{default_value}'"
                else:
                    alter_sql = f"ALTER TABLE rfid_card ADD COLUMN {col_name} {col_type}"
                
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
        print("\n🔍 Verifying updated rfid_card table schema...")
        cursor.execute("PRAGMA table_info(rfid_card)")
        updated_columns = [row[1] for row in cursor.fetchall()]
        print(f"📊 Updated columns: {updated_columns}")
        
        # Update existing RFID cards with default values
        updates_made = False
        
        # Set issue_date for cards that don't have one
        if 'issue_date' in columns_added:
            print("\n🔄 Setting default issue_date for existing cards...")
            cursor.execute("UPDATE rfid_card SET issue_date = CURRENT_TIMESTAMP WHERE issue_date IS NULL")
            updated_rows = cursor.rowcount
            if updated_rows > 0:
                print(f"✅ Set issue_date for {updated_rows} existing cards")
                updates_made = True
        
        # Set sync_status for cards that don't have it
        if 'sync_status' in columns_added:
            print("🔄 Setting default sync_status for existing cards...")
            cursor.execute("UPDATE rfid_card SET sync_status = 'pending' WHERE sync_status IS NULL")
            updated_rows = cursor.rowcount
            if updated_rows > 0:
                print(f"✅ Set sync_status for {updated_rows} existing cards")
                updates_made = True
        
        # Set source_app for cards that don't have it  
        if 'source_app' in columns_added:
            print("🔄 Setting default source_app for existing cards...")
            cursor.execute("UPDATE rfid_card SET source_app = 'cleaner_controller' WHERE source_app IS NULL")
            updated_rows = cursor.rowcount
            if updated_rows > 0:
                print(f"✅ Set source_app for {updated_rows} existing cards")
                updates_made = True
        
        if updates_made:
            conn.commit()
        
        conn.close()
        
        print("\n✅ RFID card table schema fix completed successfully!")
        print("\n🚀 Try running the application again:")
        print("  python test_run.py --production-db --hardware")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing rfid_card table schema: {e}")
        return False

if __name__ == '__main__':
    fix_rfid_card_table_schema()
