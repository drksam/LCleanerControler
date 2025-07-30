#!/usr/bin/env python3
"""
Test script to verify performance page data and fire count tracking
"""

import requests
import json
import sqlite3
import os
from datetime import datetime

def test_performance_api():
    """Test the performance API endpoints"""
    
    print("🔥 Performance API Test")
    print("=" * 50)
    
    base_url = "http://localhost:5000"  # Change if different
    
    try:
        # Test current session endpoint
        print("1. Testing /api/sessions/current")
        response = requests.get(f"{base_url}/api/sessions/current")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status: {response.status_code}")
            if data.get('success'):
                session = data.get('session', {})
                print(f"   User: {session.get('username', 'None')}")
                print(f"   Fire Count: {session.get('session_fire_count', 0)}")
                print(f"   Fire Time: {session.get('session_fire_time_ms', 0)}ms")
                print(f"   Performance: {session.get('live_performance_score', 'N/A')}")
            else:
                print(f"   ❌ No active session")
        else:
            print(f"   ❌ Error: {response.status_code}")
        
        print()
        
        # Test performance stats endpoint
        print("2. Testing /api/sessions/performance")
        response = requests.get(f"{base_url}/api/sessions/performance")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status: {response.status_code}")
            if data.get('success'):
                performance_data = data.get('performance_data', [])
                print(f"   Users with performance data: {len(performance_data)}")
                
                for user in performance_data[:3]:  # Show first 3 users
                    print(f"   • {user.get('username')}: {len(user.get('sessions', []))} sessions, "
                          f"{user.get('total_fire_count', 0)} fires, "
                          f"{user.get('total_fire_time_ms', 0)}ms fire time")
            else:
                print(f"   ❌ No performance data")
        else:
            print(f"   ❌ Error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure the application is running.")
    except Exception as e:
        print(f"❌ Error testing API: {e}")
    
    print()
    
    # Check database directly
    print("3. Checking database directly")
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'Shop_laser.db')
    
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check for active sessions with fire data
            cursor.execute("""
                SELECT 
                    us.id,
                    u.username,
                    us.session_fire_count,
                    us.session_fire_time_ms,
                    us.login_time,
                    us.logout_time
                FROM user_session us
                LEFT JOIN user u ON us.user_id = u.id
                WHERE us.logout_time IS NULL
                ORDER BY us.login_time DESC
                LIMIT 5
            """)
            
            active_sessions = cursor.fetchall()
            
            if active_sessions:
                print(f"   ✅ Found {len(active_sessions)} active session(s):")
                for session in active_sessions:
                    id, username, fire_count, fire_time_ms, login_time, logout_time = session
                    print(f"   • Session {id} - {username}: {fire_count or 0} fires, {fire_time_ms or 0}ms")
            else:
                print("   ⚠️  No active sessions found")
            
            conn.close()
            
        except Exception as e:
            print(f"   ❌ Database error: {e}")
    else:
        print(f"   ❌ Database not found at: {db_path}")

def test_recommendations():
    """Provide testing recommendations"""
    print("\n🎯 Testing Recommendations:")
    print("=" * 50)
    print("1. Make sure the laser application is running")
    print("2. Login with RFID card to create an active session")
    print("3. Perform 2-3 firing operations")
    print("4. Visit the performance page to see live data")
    print("5. Check for these elements:")
    print("   • Fire Count should increment with each firing")
    print("   • Fire Time should accumulate laser operation time")
    print("   • Performance page should show session statistics")
    print("   • Leaderboard should display fire count and fire time columns")

if __name__ == "__main__":
    test_performance_api()
    test_recommendations()
