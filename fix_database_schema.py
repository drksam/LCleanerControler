#!/usr/bin/env python3
"""
Fix Database Schema - Update api_key table column name
"""

import os
import sqlite3

def fix_api_key_table():
    """Fix the api_key table schema to match application expectations"""
    
    db_path = 'instance/LCleaner_production.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False
    
    try:
        print("🔧 Fixing database schema...")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if api_key table exists and what columns it has
        cursor.execute("PRAGMA table_info(api_key)")
        columns = cursor.fetchall()
        
        print("📊 Current api_key table columns:")
        for col in columns:
            print(f"  • {col[1]} ({col[2]})")
        
        # Check if we need to fix the column name
        column_names = [col[1] for col in columns]
        
        if 'key_hash' in column_names and 'key' not in column_names:
            print("🔧 Renaming key_hash column to key...")
            
            # SQLite doesn't support RENAME COLUMN directly in older versions
            # So we'll recreate the table
            
            # 1. Create new table with correct schema
            cursor.execute('''
                CREATE TABLE api_key_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    "key" VARCHAR(256) UNIQUE NOT NULL,
                    description TEXT,
                    active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_used DATETIME
                )
            ''')
            
            # 2. Copy data from old table (map key_hash to key, name to description)
            cursor.execute('''
                INSERT INTO api_key_new (id, "key", description, active, created_at, last_used)
                SELECT id, key_hash, name, active, created_at, last_used
                FROM api_key
            ''')
            
            # 3. Drop old table
            cursor.execute('DROP TABLE api_key')
            
            # 4. Rename new table
            cursor.execute('ALTER TABLE api_key_new RENAME TO api_key')
            
            print("✅ api_key table schema fixed!")
            
        elif 'key' in column_names:
            print("✅ api_key table already has correct schema!")
        else:
            print("🔧 Creating api_key table with correct schema...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_key (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    "key" VARCHAR(256) UNIQUE NOT NULL,
                    description TEXT,
                    active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_used DATETIME
                )
            ''')
            print("✅ api_key table created!")
        
        # Verify the fix
        cursor.execute("PRAGMA table_info(api_key)")
        columns = cursor.fetchall()
        
        print("\n📊 Updated api_key table columns:")
        for col in columns:
            print(f"  • {col[1]} ({col[2]})")
        
        conn.commit()
        conn.close()
        
        print("\n🎉 Database schema fix completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        return False

def check_other_tables():
    """Check if other tables need fixes"""
    
    db_path = 'instance/LCleaner_production.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n🔍 Checking other table schemas...")
        
        # Check user table
        cursor.execute("PRAGMA table_info(user)")
        user_columns = [col[1] for col in cursor.fetchall()]
        print(f"✓ user table columns: {user_columns}")
        
        # Check user_session table
        cursor.execute("PRAGMA table_info(user_session)")
        session_columns = [col[1] for col in cursor.fetchall()]
        print(f"✓ user_session table columns: {session_columns}")
        
        # Verify user_session has all required columns
        required_session_columns = [
            'id', 'user_id', 'login_time', 'logout_time', 'first_fire_time',
            'login_method', 'switched_from_user_id', 'session_fire_count',
            'session_fire_time_ms', 'performance_score', 'machine_id', 'card_id'
        ]
        
        missing_columns = [col for col in required_session_columns if col not in session_columns]
        if missing_columns:
            print(f"⚠️  Missing user_session columns: {missing_columns}")
        else:
            print("✅ user_session table has all required columns!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking tables: {e}")

if __name__ == "__main__":
    print("🗄️  Database Schema Fix")
    print("=" * 30)
    
    if fix_api_key_table():
        check_other_tables()
        print("\n✅ Database is ready for application startup!")
        print("\nTry running the application again:")
        print("  python test_run.py --production-db --hardware")
    else:
        print("\n❌ Schema fix failed!")
