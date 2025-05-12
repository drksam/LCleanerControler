#!/usr/bin/env python
"""
Authentication Integration Tests

This module tests the RFID authentication system and permission checks.
"""
import unittest
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.test_base import BaseTestCase
from tests.test_config import TEST_USERS

# Import from application
import models
from rfid_control import RFIDController

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_authentication')

class MockRFIDReader:
    """Mock implementation of RFID reader for testing"""
    
    def __init__(self):
        """Initialize mock RFID reader"""
        self.next_card_id = None
        self.read_count = 0
        
    def read(self):
        """Read a card ID from the reader"""
        if self.next_card_id:
            card_id = self.next_card_id
            self.read_count += 1
            return card_id
        return None
        
    def set_next_card(self, card_id):
        """Set the next card ID to be read"""
        self.next_card_id = card_id
        
    def reset(self):
        """Reset the mock reader"""
        self.next_card_id = None
        self.read_count = 0

class MockDatabase:
    """Mock database for testing authentication"""
    
    def __init__(self):
        """Initialize with test users"""
        self.users = {
            TEST_USERS["admin"]["card_id"]: self._create_user(TEST_USERS["admin"]),
            TEST_USERS["operator"]["card_id"]: self._create_user(TEST_USERS["operator"]),
            TEST_USERS["invalid"]["card_id"]: self._create_user(TEST_USERS["invalid"])
        }
        
    def _create_user(self, user_data):
        """Create a User object from test data"""
        user = models.User(
            id=user_data["id"],
            username=user_data["username"],
            card_id=user_data["card_id"]
        )
        user.permissions = user_data["permissions"]
        return user
        
    def get_user_by_card(self, card_id):
        """Get a user by card ID"""
        return self.users.get(card_id)

class MockRFIDController(RFIDController):
    """Mock RFID controller for testing"""
    
    def __init__(self):
        """Initialize with mock reader and database"""
        self.reader = MockRFIDReader()
        self.db = MockDatabase()
        self.current_user = None
        self.last_result = None
        
    def authenticate(self, card_id=None):
        """
        Authenticate a user by card ID
        
        Args:
            card_id: Card ID to authenticate (if None, read from reader)
            
        Returns:
            tuple: (success, user, message)
        """
        # If no card_id provided, read from reader
        if card_id is None:
            card_id = self.reader.read()
            
        if not card_id:
            self.last_result = (False, None, "No card detected")
            return self.last_result
            
        # Look up user in database
        user = self.db.get_user_by_card(card_id)
        
        if not user:
            self.last_result = (False, None, f"No user found with card ID: {card_id}")
            return self.last_result
            
        # User found, set as current user
        self.current_user = user
        self.last_result = (True, user, f"User {user.username} authenticated successfully")
        return self.last_result
        
    def check_permission(self, permission):
        """
        Check if current user has a specific permission
        
        Args:
            permission: Permission to check
            
        Returns:
            bool: True if user has permission
        """
        if not self.current_user:
            return False
            
        return permission in self.current_user.permissions
        
    def logout(self):
        """Log out the current user"""
        self.current_user = None
        return True

class AuthenticationTest(BaseTestCase):
    """Test case for authentication system"""
    
    def setUp(self):
        """Set up test fixtures before each test"""
        super().setUp()
        self.controller = MockRFIDController()
        
    def test_valid_user_authentication(self):
        """Test authentication with valid card ID"""
        # Set up mock reader
        card_id = TEST_USERS["admin"]["card_id"]
        self.controller.reader.set_next_card(card_id)
        
        # Authenticate
        success, user, message = self.controller.authenticate()
        
        # Verify authentication was successful
        self.assertTrue(success)
        self.assertIsNotNone(user)
        self.assertEqual(TEST_USERS["admin"]["username"], user.username)
        
    def test_invalid_user_authentication(self):
        """Test authentication with invalid card ID"""
        # Try non-existent card ID
        card_id = "nonexistent_card"
        self.controller.reader.set_next_card(card_id)
        
        # Authenticate
        success, user, message = self.controller.authenticate()
        
        # Verify authentication failed
        self.assertFalse(success)
        self.assertIsNone(user)
        
    def test_permission_check(self):
        """Test permission checking"""
        # Authenticate admin user
        self.controller.authenticate(TEST_USERS["admin"]["card_id"])
        
        # Check permissions
        self.assertTrue(self.controller.check_permission("admin"))
        self.assertTrue(self.controller.check_permission("laser_operate"))
        self.assertTrue(self.controller.check_permission("machine_monitor"))
        self.assertFalse(self.controller.check_permission("nonexistent_permission"))
        
        # Authenticate operator user
        self.controller.authenticate(TEST_USERS["operator"]["card_id"])
        
        # Check permissions
        self.assertFalse(self.controller.check_permission("admin"))
        self.assertTrue(self.controller.check_permission("laser_operate"))
        self.assertFalse(self.controller.check_permission("machine_monitor"))
        
    def test_logout(self):
        """Test user logout"""
        # Authenticate
        self.controller.authenticate(TEST_USERS["admin"]["card_id"])
        self.assertIsNotNone(self.controller.current_user)
        
        # Logout
        self.controller.logout()
        self.assertIsNone(self.controller.current_user)
        
        # Verify permissions fail after logout
        self.assertFalse(self.controller.check_permission("admin"))

if __name__ == '__main__':
    unittest.main()