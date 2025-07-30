#!/usr/bin/env python3
"""Create missing user_session table and update database schema"""

import sqlite3
import os
from datetime import datetime

def create_user_session_table():
    """Create the user_session table that's missing from the database"""
    
    db_path = 'instance/Shop_laser.db'
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔧 Creating user_session table...")
        
        # Create the user_session table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_session (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                logout_time DATETIME,
                first_fire_time DATETIME,
                login_method VARCHAR(20) DEFAULT 'rfid',
                switched_from_user_id INTEGER,
                session_fire_count INTEGER DEFAULT 0,
                session_fire_time_ms BIGINT DEFAULT 0,
                performance_score FLOAT,
                machine_id VARCHAR(64) DEFAULT 'laser_room_1',
                card_id VARCHAR(32),
                FOREIGN KEY (user_id) REFERENCES user (id),
                FOREIGN KEY (switched_from_user_id) REFERENCES user (id)
            )
        """)
        
        # Commit the changes
        conn.commit()
        print("✅ user_session table created successfully!")
        
        # Verify the table was created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_session'")
        result = cursor.fetchone()
        
        if result:
            print("✅ Table verified in database")
            
            # Show the table structure
            cursor.execute("PRAGMA table_info(user_session)")
            columns = cursor.fetchall()
            print("\n📋 user_session table structure:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]}) {col[3] if col[3] else ''}")
                
            return True
        else:
            print("❌ Table creation verification failed")
            return False
            
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return False
    finally:
        if conn:
            conn.close()

def check_and_create_indexes():
    """Create useful indexes for the user_session table"""
    
    db_path = 'instance/Shop_laser.db'
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n🔍 Creating indexes for better performance...")
        
        # Index on user_id for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_session_user_id 
            ON user_session(user_id)
        """)
        
        # Index on login_time for faster date-based queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_session_login_time 
            ON user_session(login_time)
        """)
        
        # Index for finding active sessions (no logout_time)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_session_active 
            ON user_session(logout_time) 
            WHERE logout_time IS NULL
        """)
        
        conn.commit()
        print("✅ Indexes created successfully!")
        
    except Exception as e:
        print(f"⚠️  Warning creating indexes: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🗄️  Database Schema Update")
    print("=" * 50)
    
    success = create_user_session_table()
    
    if success:
        check_and_create_indexes()
        print("\n🎉 Database update completed!")
        print("\n📝 Next steps:")
        print("  1. Restart the application: sudo systemctl restart your-laser-service")
        print("  2. Log in with RFID to create your first session")
        print("  3. Perform some firing operations")
        print("  4. Check the performance page for session data")
    else:
        print("\n❌ Database update failed!")
        print("  - Check file permissions")
        print("  - Ensure the application is not running")
        print("  - Try running with sudo if needed")
