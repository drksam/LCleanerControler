#!/usr/bin/env python3
"""
Check user session data to verify performance tracking is working
"""

import sqlite3
import os
from datetime import datetime

def check_session_data():
    """Check the user_session table for actual data"""
    
    # Use the production database path
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'Shop_laser.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return
    
    print("🔍 Session Data Analysis")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check all user sessions
        cursor.execute("""
            SELECT 
                id,
                user_id,
                login_time,
                logout_time,
                first_fire_time,
                login_method,
                session_fire_count,
                session_fire_time_ms,
                performance_score,
                card_id
            FROM user_session 
            ORDER BY login_time DESC
            LIMIT 10
        """)
        
        sessions = cursor.fetchall()
        
        if sessions:
            print(f"📊 Found {len(sessions)} session(s):")
            print()
            
            for session in sessions:
                id, user_id, login_time, logout_time, first_fire_time, login_method, fire_count, fire_time_ms, score, card_id = session
                
                print(f"Session ID: {id}")
                print(f"  User ID: {user_id}")
                print(f"  Login Time: {login_time}")
                print(f"  Logout Time: {logout_time or 'Still active'}")
                print(f"  First Fire: {first_fire_time or 'No firing yet'}")
                print(f"  Login Method: {login_method}")
                print(f"  Fire Count: {fire_count or 0}")
                print(f"  Fire Time: {fire_time_ms or 0}ms ({(fire_time_ms or 0) / 1000:.1f}s)")
                print(f"  Performance Score: {score or 'Not calculated'}")
                print(f"  Card ID: {card_id}")
                print("-" * 30)
        else:
            print("❌ No session data found")
        
        # Check user table for reference
        cursor.execute("SELECT id, username, full_name FROM user")
        users = cursor.fetchall()
        
        print("\n👥 Users in database:")
        for user in users:
            print(f"  ID {user[0]}: {user[1]} ({user[2]})")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking session data: {e}")

if __name__ == "__main__":
    check_session_data()
