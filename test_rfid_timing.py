#!/usr/bin/env python3
"""
Test script to verify RFID authentication timing mechanism
"""

import time
import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_timing_mechanism():
    """Test the authentication timing logic"""
    
    class MockRFIDController:
        def __init__(self):
            self.authenticated_user = None
            self.last_auth_time = 0
            self.login_consumed = False
            
        def authenticate_user(self, user_data):
            """Simulate user authentication"""
            self.authenticated_user = user_data
            self.last_auth_time = time.time()
            self.login_consumed = False
            print(f"User authenticated: {user_data['username']} at {self.last_auth_time}")
            
        def is_authenticated(self):
            return self.authenticated_user is not None
            
        def get_authenticated_user(self):
            return self.authenticated_user
            
        def check_fresh_auth(self, max_age=5):
            """Check if authentication is fresh and not consumed"""
            if not self.is_authenticated():
                return False
                
            current_time = time.time()
            time_since_auth = current_time - self.last_auth_time
            
            is_fresh = time_since_auth <= max_age and not self.login_consumed
            print(f"Auth check: age={time_since_auth:.1f}s, consumed={self.login_consumed}, fresh={is_fresh}")
            return is_fresh
            
        def consume_login(self):
            """Mark login as consumed"""
            self.login_consumed = True
            print("Login marked as consumed")
    
    # Create mock controller
    controller = MockRFIDController()
    
    # Test case 1: Fresh authentication
    print("\n=== Test Case 1: Fresh Authentication ===")
    user_data = {'username': 'test_user', 'user_id': 1}
    controller.authenticate_user(user_data)
    
    # Should be fresh
    if controller.check_fresh_auth():
        print("✓ Fresh authentication detected correctly")
        controller.consume_login()
    else:
        print("✗ Fresh authentication not detected")
    
    # Should not be fresh after consumption
    if not controller.check_fresh_auth():
        print("✓ Consumed authentication correctly rejected")
    else:
        print("✗ Consumed authentication incorrectly accepted")
    
    # Test case 2: Old authentication
    print("\n=== Test Case 2: Old Authentication ===")
    controller.last_auth_time = time.time() - 10  # 10 seconds ago
    controller.login_consumed = False
    
    if not controller.check_fresh_auth():
        print("✓ Old authentication correctly rejected")
    else:
        print("✗ Old authentication incorrectly accepted")
    
    # Test case 3: Multiple login attempts
    print("\n=== Test Case 3: Multiple Login Attempts ===")
    controller.authenticate_user(user_data)
    
    # First attempt should work
    if controller.check_fresh_auth():
        print("✓ First login attempt successful")
        controller.consume_login()
    
    # Second attempt should fail
    if not controller.check_fresh_auth():
        print("✓ Second login attempt correctly rejected")
    else:
        print("✗ Second login attempt incorrectly accepted")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_timing_mechanism()
