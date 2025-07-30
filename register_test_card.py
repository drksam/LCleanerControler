#!/usr/bin/env python3
"""
Quick script to register the test RFID card (2667607583) for authentication testing
"""
import sys
import os
import sqlite3
from datetime import datetime

def register_test_card():
    """Register the test RFID card directly in the database"""
    card_id = "2667607583"
    
    # Database path
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'Shop_laser.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if card already exists
        cursor.execute("SELECT * FROM rfid_card WHERE card_id = ?", (card_id,))
        existing_card = cursor.fetchone()
        
        if existing_card:
            print(f"Card {card_id} is already registered!")
            print(f"Card details: {existing_card}")
            conn.close()
            return
        
        # Find the admin user
        cursor.execute("SELECT id, username, access_level FROM user WHERE username = 'admin'")
        admin_user = cursor.fetchone()
        
        if not admin_user:
            print("Error: Admin user not found!")
            print("Available users:")
            cursor.execute("SELECT id, username, access_level FROM user")
            users = cursor.fetchall()
            for user in users:
                print(f"  ID: {user[0]}, Username: {user[1]}, Access: {user[2]}")
            conn.close()
            return
        
        admin_id, admin_username, admin_access = admin_user
        
        # Create new RFID card entry
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT INTO rfid_card (card_id, user_id, active, issue_date)
            VALUES (?, ?, ?, ?)
        """, (card_id, admin_id, True, now))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Card {card_id} successfully registered to user: {admin_username}")
        print(f"   Access level: {admin_access}")
        print(f"   Issue date: {now}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    register_test_card()
