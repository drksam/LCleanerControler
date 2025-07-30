#!/usr/bin/env python3
"""
Quick fix to create user_session table in production database
"""

import os
import sqlite3

def fix_production_database():
    """Create user_session table in the production database"""
    
    # Look for the main production database
    production_db_paths = [
        'instance/Shop_laser.db',
        '/home/laser/LCleanerController/instance/Shop_laser.db'
    ]
    
    for db_path in production_db_paths:
        if os.path.exists(db_path):
            print(f"📍 Found production database: {db_path}")
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Check if user_session table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_session';")
                if cursor.fetchone():
                    print("✅ user_session table already exists!")
                    conn.close()
                    return True
                
                print("🔧 Creating user_session table...")
                
                # Create user_session table
                cursor.execute('''
                    CREATE TABLE user_session (
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
                        FOREIGN KEY (user_id) REFERENCES user (id)
                    )
                ''')
                
                # Create indexes
                cursor.execute('CREATE INDEX idx_user_session_user_id ON user_session(user_id)')
                cursor.execute('CREATE INDEX idx_user_session_login_time ON user_session(login_time)')
                
                conn.commit()
                conn.close()
                
                print("✅ user_session table created successfully!")
                print("\n🎉 Production database fixed!")
                print("\nNow you can:")
                print("1. Start the production application (without test_run.py)")
                print("2. Or run: python test_run.py --temp-db=False")
                return True
                
            except Exception as e:
                print(f"❌ Error fixing database {db_path}: {e}")
                
    print("❌ Production database not found!")
    print("Try creating instance directory: mkdir -p instance")
    return False

if __name__ == "__main__":
    print("🗄️  Quick Production Database Fix")
    print("=" * 40)
    fix_production_database()
