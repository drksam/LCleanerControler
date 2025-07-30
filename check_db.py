#!/usr/bin/env python3
"""Check database tables and session data"""

import sqlite3
import os

db_path = 'instance/Shop_laser.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔍 Database Analysis")
    print("=" * 50)
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"\n📊 Tables found: {[t[0] for t in tables]}")
    
    # Check if user_session table exists
    if 'user_session' in [t[0] for t in tables]:
        print("\n✅ user_session table exists")
        
        # Get recent sessions
        try:
            cursor.execute("""
                SELECT u.username, us.login_time, us.session_fire_count, 
                       us.session_fire_time_ms, us.performance_score, us.login_method
                FROM user_session us 
                JOIN user u ON us.user_id = u.id 
                ORDER BY us.login_time DESC LIMIT 5
            """)
            rows = cursor.fetchall()
            
            print(f"\n📈 Recent sessions ({len(rows)} found):")
            for i, row in enumerate(rows, 1):
                username, login_time, fire_count, fire_time_ms, perf_score, login_method = row
                fire_time_sec = fire_time_ms / 1000.0 if fire_time_ms else 0
                print(f"  {i}. {username} | {login_time} | Fires: {fire_count} | Time: {fire_time_sec:.1f}s | Perf: {perf_score} | Method: {login_method}")
                
        except Exception as e:
            print(f"❌ Error querying sessions: {e}")
            
        # Check schema
        cursor.execute("PRAGMA table_info(user_session)")
        columns = cursor.fetchall()
        print(f"\n🗂️  user_session columns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
            
    else:
        print("❌ user_session table NOT found")
        
        # Check if there are any sessions in other tables
        for table_name in [t[0] for t in tables]:
            if 'session' in table_name.lower():
                print(f"Found session-related table: {table_name}")
    
    conn.close()
else:
    print(f"❌ Database not found at: {db_path}")
