#!/usr/bin/env python3
"""
Test script to verify fiber fire count tracking is working properly
"""

import sqlite3
import os
import json
from datetime import datetime

def test_fire_tracking():
    """Test the fire tracking functionality"""
    
    print("🔥 Fire Tracking Test")
    print("=" * 50)
    
    # Check database
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'Shop_laser.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check recent sessions with fire data
        cursor.execute("""
            SELECT 
                us.id,
                u.username,
                us.login_time,
                us.first_fire_time,
                us.session_fire_count,
                us.session_fire_time_ms,
                us.performance_score
            FROM user_session us
            LEFT JOIN user u ON us.user_id = u.id
            WHERE us.login_time >= datetime('now', '-1 day')
            ORDER BY us.login_time DESC
            LIMIT 5
        """)
        
        sessions = cursor.fetchall()
        
        if sessions:
            print(f"📊 Recent sessions with fire data:")
            print()
            
            for session in sessions:
                id, username, login_time, first_fire_time, fire_count, fire_time_ms, performance_score = session
                
                print(f"Session {id} - {username or 'Unknown'}:")
                print(f"  Login: {login_time}")
                print(f"  First Fire: {first_fire_time or 'None'}")
                print(f"  Fire Count: {fire_count or 0}")
                print(f"  Fire Time: {fire_time_ms or 0}ms ({(fire_time_ms or 0) / 1000:.1f}s)")
                print(f"  Performance: {performance_score or 'Not calculated'}")
                print("-" * 30)
        else:
            print("❌ No recent sessions found")
        
        # Check machine config for global stats
        config_path = os.path.join(os.path.dirname(__file__), 'machine_config.json')
        if os.path.exists(config_path):
            print("\n🔧 Global Statistics (machine_config.json):")
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            stats = config.get('statistics', {})
            print(f"  Global fire count: {stats.get('laser_fire_count', 0)}")
            print(f"  Total fire time: {stats.get('total_laser_fire_time', 0)}ms")
        
        conn.close()
        
        # Test recommendations
        print("\n✅ Testing Recommendations:")
        print("1. Login with RFID card")
        print("2. Perform a few firing operations")
        print("3. Check performance page for updated stats")
        print("4. Run this script again to verify data updates")
        
    except Exception as e:
        print(f"❌ Error testing fire tracking: {e}")

if __name__ == "__main__":
    test_fire_tracking()
