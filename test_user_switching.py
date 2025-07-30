#!/usr/bin/env python3
"""
Test script for user switching and performance tracking functionality
"""

import time
import sys
import os
from datetime import datetime

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_user_switching():
    """Test the user switching logic"""
    
    class MockUser:
        def __init__(self, user_id, username, access_level):
            self.id = user_id
            self.username = username
            self.access_level = access_level
            self.active = True
            
        def to_dict(self):
            return {
                'user_id': self.id,
                'username': self.username,
                'access_level': self.access_level
            }
    
    class MockRFIDCard:
        def __init__(self, card_id, user):
            self.card_id = card_id
            self.user = user
            self.user_id = user.id
            self.active = True
    
    class MockUserSession:
        def __init__(self, user_id, login_time=None, login_method='rfid', switched_from_user_id=None):
            self.id = len(sessions) + 1
            self.user_id = user_id
            self.login_time = login_time or datetime.utcnow()
            self.logout_time = None
            self.first_fire_time = None
            self.login_method = login_method
            self.switched_from_user_id = switched_from_user_id
            self.session_fire_count = 0
            self.session_fire_time_ms = 0
            self.performance_score = None
            sessions.append(self)
            
        def calculate_performance_score(self):
            if self.first_fire_time and self.login_time:
                delta = self.first_fire_time - self.login_time
                self.performance_score = delta.total_seconds()
                return self.performance_score
            return None
    
    class MockRFIDController:
        def __init__(self):
            self.authenticated_user = None
            self.current_session = None
            self.last_auth_time = 0
            self.login_consumed = False
            
        def _create_user_session(self, user_data, login_method='rfid', switched_from_user_id=None):
            # Close current session if exists
            if self.current_session:
                self.current_session.logout_time = datetime.utcnow()
                
            # Create new session
            session = MockUserSession(
                user_id=user_data.get('user_id'),
                login_method=login_method,
                switched_from_user_id=switched_from_user_id
            )
            
            self.current_session = session
            print(f"Created new session for {user_data.get('username')} (ID: {session.id})")
            
        def record_first_fire(self):
            if self.current_session and not self.current_session.first_fire_time:
                self.current_session.first_fire_time = datetime.now()  # Use local time
                self.current_session.calculate_performance_score()
                print(f"First fire recorded - Performance: {self.current_session.performance_score:.2f}s")
                
        def simulate_card_scan(self, card_id, users_db, cards_db):
            """Simulate scanning an RFID card"""
            # Check if this is a different user (user switching scenario)
            current_user_id = None
            if self.authenticated_user:
                current_user_id = self.authenticated_user.get('user_id')
                
            # Look up the new card
            if card_id in cards_db:
                card = cards_db[card_id]
                new_user_id = card.user_id
                
                if current_user_id and current_user_id != new_user_id:
                    # User switching
                    print(f"User switching detected: {self.authenticated_user.get('username')} -> {card.user.username}")
                    
                    old_user_id = current_user_id
                    self.authenticated_user = card.user.to_dict()
                    self.last_auth_time = time.time()
                    self.login_consumed = False
                    
                    # Create user session
                    self._create_user_session(self.authenticated_user, 'auto_switch', old_user_id)
                    
                elif not current_user_id:
                    # Initial login
                    print(f"Initial login: {card.user.username}")
                    
                    self.authenticated_user = card.user.to_dict()
                    self.last_auth_time = time.time()
                    self.login_consumed = False
                    
                    # Create user session
                    self._create_user_session(self.authenticated_user, 'rfid')
                    
                else:
                    # Same user re-scanned
                    print(f"Same user {card.user.username} re-scanned card")
                    self.last_auth_time = time.time()
                    self.login_consumed = False
                    
                return True
            else:
                print(f"Unknown card: {card_id}")
                return False
    
    # Create test data
    sessions = []
    
    # Create test users
    user1 = MockUser(1, 'john_doe', 'operator')
    user2 = MockUser(2, 'jane_smith', 'admin')
    user3 = MockUser(3, 'bob_jones', 'operator')
    
    # Create test cards
    users_db = {1: user1, 2: user2, 3: user3}
    cards_db = {
        'CARD001': MockRFIDCard('CARD001', user1),
        'CARD002': MockRFIDCard('CARD002', user2),
        'CARD003': MockRFIDCard('CARD003', user3)
    }
    
    # Create controller
    controller = MockRFIDController()
    
    print("=== User Switching and Performance Test ===\n")
    
    # Test case 1: Initial login
    print("1. Initial login - John")
    controller.simulate_card_scan('CARD001', users_db, cards_db)
    
    # Simulate some delay before first fire
    time.sleep(1)
    
    # Record first fire
    controller.record_first_fire()
    
    # Test case 2: User switching
    print("\n2. User switching - Jane takes over")
    controller.simulate_card_scan('CARD002', users_db, cards_db)
    
    # Simulate quick fire for good performance
    time.sleep(0.5)
    controller.record_first_fire()
    
    # Test case 3: Another user switch
    print("\n3. Another user switch - Bob takes over")
    controller.simulate_card_scan('CARD003', users_db, cards_db)
    
    # Simulate slow reaction for poor performance
    time.sleep(3)
    controller.record_first_fire()
    
    # Test case 4: Same user re-scans
    print("\n4. Same user re-scans card")
    controller.simulate_card_scan('CARD003', users_db, cards_db)
    
    # Display results
    print("\n=== Session Results ===")
    for i, session in enumerate(sessions, 1):
        user = users_db[session.user_id]
        print(f"Session {i}:")
        print(f"  User: {user.username}")
        print(f"  Login method: {session.login_method}")
        print(f"  Switched from user: {session.switched_from_user_id}")
        print(f"  Performance score: {session.performance_score:.2f}s" if session.performance_score else "  No fire recorded")
        print(f"  Login time: {session.login_time}")
        print(f"  Logout time: {session.logout_time}")
        print()
    
    print("=== Performance Ranking ===")
    completed_sessions = [s for s in sessions if s.performance_score is not None]
    completed_sessions.sort(key=lambda x: x.performance_score)
    
    for i, session in enumerate(completed_sessions, 1):
        user = users_db[session.user_id]
        print(f"{i}. {user.username}: {session.performance_score:.2f}s")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_user_switching()
