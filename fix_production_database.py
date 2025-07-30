#!/usr/bin/env python3
"""
Find and fix the production database - create missing user_session table
"""

import os
import sqlite3
import json

def find_production_database():
    """Find the actual database being used by the production application"""
    
    print("🔍 Finding Production Database")
    print("=" * 50)
    
    # Check common database locations
    possible_locations = [
        'instance/Shop_laser.db',
        '/home/laser/LCleanerController/instance/Shop_laser.db',
        'Shop_laser.db',
        '/home/laser/Shop_laser.db',
        '/home/laser/LCleanerController/Shop_laser.db'
    ]
    
    # Check environment variables or config files
    config_file = 'machine_config.json'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                db_path = config.get('database_path')
                if db_path:
                    possible_locations.insert(0, db_path)
                    print(f"📝 Found database path in config: {db_path}")
        except Exception as e:
            print(f"⚠️  Could not read config file: {e}")
    
    # Check for DATABASE_URL environment variable (Flask style)
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
        possible_locations.insert(0, db_path)
        print(f"📝 Found DATABASE_URL: {db_path}")
    
    print("\n📂 Checking possible database locations:")
    
    existing_dbs = []
    for location in possible_locations:
        abs_path = os.path.abspath(location)
        if os.path.exists(abs_path):
            size = os.path.getsize(abs_path)
            print(f"   ✅ {abs_path} ({size} bytes)")
            existing_dbs.append(abs_path)
        else:
            print(f"   ❌ {abs_path} (not found)")
    
    return existing_dbs

def check_database_tables(db_path):
    """Check what tables exist in a database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\n📊 Tables in {db_path}:")
        for table in sorted(tables):
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   • {table}: {count} records")
        
        conn.close()
        return tables
        
    except Exception as e:
        print(f"❌ Error checking {db_path}: {e}")
        return []

def create_user_session_table(db_path):
    """Create the user_session table in the specified database"""
    try:
        print(f"\n🔧 Creating user_session table in {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create user_session table with all required columns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_session (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                login_time DATETIME NOT NULL,
                logout_time DATETIME,
                first_fire_time DATETIME,
                login_method VARCHAR(20) DEFAULT 'unknown',
                switched_from_user_id INTEGER,
                session_fire_count INTEGER DEFAULT 0,
                session_fire_time_ms BIGINT DEFAULT 0,
                performance_score FLOAT,
                machine_id VARCHAR(64),
                card_id VARCHAR(32),
                FOREIGN KEY (user_id) REFERENCES user (id),
                FOREIGN KEY (switched_from_user_id) REFERENCES user (id)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_session_user_id ON user_session(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_session_login_time ON user_session(login_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_session_logout_time ON user_session(logout_time)')
        
        conn.commit()
        
        # Verify the table was created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_session';")
        if cursor.fetchone():
            print("   ✅ user_session table created successfully!")
            
            # Show table structure
            cursor.execute("PRAGMA table_info(user_session)")
            columns = cursor.fetchall()
            print("\n📋 Table structure:")
            for col in columns:
                print(f"   • {col[1]} ({col[2]})")
        else:
            print("   ❌ Failed to create user_session table")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating table in {db_path}: {e}")
        return False

def main():
    print("🗄️  Production Database Repair")
    print("=" * 50)
    
    # Find all existing databases
    databases = find_production_database()
    
    if not databases:
        print("\n❌ No databases found!")
        print("   The application may not have created a database yet.")
        print("   Try starting the application first.")
        return
    
    # Check each database for tables
    production_db = None
    for db_path in databases:
        print(f"\n🔍 Examining {db_path}:")
        tables = check_database_tables(db_path)
        
        # Look for typical Flask app tables
        if 'user' in tables and 'rfid_card' in tables:
            print(f"   ✅ This looks like the production database!")
            production_db = db_path
            
            if 'user_session' not in tables:
                print(f"   ⚠️  Missing user_session table")
                create_user_session_table(db_path)
            else:
                print(f"   ✅ user_session table already exists")
            break
    
    if not production_db:
        print("\n⚠️  Could not identify the production database.")
        print("   Creating user_session table in the largest database...")
        if databases:
            # Use the largest database as it's likely the production one
            largest_db = max(databases, key=os.path.getsize)
            create_user_session_table(largest_db)
    
    print("\n🎉 Database repair completed!")
    print("\nNext steps:")
    print("1. Restart the laser application")
    print("2. Login with RFID to create a session")
    print("3. Test the performance page")

if __name__ == "__main__":
    main()
