#!/usr/bin/env python
"""
Base Test Class for LCleanerController

This module provides a base class for all tests, including common setup
and teardown operations.
"""
import os
import sys
import unittest
import logging
import json
import time
from pathlib import Path

# Import from test_config
from tests.test_config import (
    TEST_ENVIRONMENT, 
    TEST_API_URL, 
    TEST_API_KEY, 
    HARDWARE_SIMULATION,
    SAMPLE_SEQUENCES,
    HARDWARE_TEST_CONFIG
)

# Configure logging
logging.basicConfig(
    level=logging.INFO if TEST_ENVIRONMENT == 'development' else logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('tests')

class BaseTestCase(unittest.TestCase):
    """Base test case for LCleanerController tests"""
    
    @classmethod
    def setUpClass(cls):
        """Set up class-level test fixtures"""
        logger.info(f"Setting up test class: {cls.__name__}")
        cls.test_start_time = time.time()
        
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests in this class have run"""
        elapsed = time.time() - cls.test_start_time
        logger.info(f"Tearing down test class: {cls.__name__}")
        logger.info(f"Tests completed in {elapsed:.2f} seconds")
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        logger.info(f"Setting up test: {self._testMethodName}")
        self.test_start_time = time.time()
        
        # Initialize any common test resources here
        # This could include database connections, hardware interfaces, etc.
        
    def tearDown(self):
        """Clean up after each test method"""
        elapsed = time.time() - self.test_start_time
        logger.info(f"Tearing down test: {self._testMethodName}")
        logger.info(f"Test completed in {elapsed:.2f} seconds")
        
        # Clean up any resources here
        # This could include closing connections, resetting hardware, etc.
        
    def create_test_sequence(self, sequence_type="basic_sequence"):
        """Create a test sequence from templates in test_config"""
        if sequence_type not in SAMPLE_SEQUENCES:
            raise ValueError(f"Unknown sequence type: {sequence_type}")
            
        # Return a copy of the sequence to avoid modifying the template
        return json.loads(json.dumps(SAMPLE_SEQUENCES[sequence_type]))
    
    def assert_hardware_state(self, expected_state, actual_state, msg=None):
        """
        Assert that hardware state matches the expected state
        
        Args:
            expected_state: Dictionary of expected hardware state values
            actual_state: Dictionary of actual hardware state values
            msg: Optional message to display on failure
        """
        for key, expected_value in expected_state.items():
            self.assertIn(key, actual_state, f"Key '{key}' not found in hardware state")
            self.assertEqual(expected_value, actual_state[key], 
                             msg or f"Hardware state mismatch for {key}")
    
    def simulate_hardware_failure(self, component, error_type="hardware_failure"):
        """
        Simulate a hardware failure for testing error recovery
        
        Args:
            component: Name of component to simulate failure for (e.g., "stepper", "laser")
            error_type: Type of error to simulate
        """
        # Implementation depends on how your hardware simulation is structured
        # This is a placeholder that should be overridden in specific test cases
        logger.info(f"Simulating {error_type} for {component}")
        
    def wait_for_operation(self, operation_name, timeout=5.0, check_interval=0.1):
        """
        Wait for an operation to complete, with timeout
        
        Args:
            operation_name: Name of operation to wait for
            timeout: Maximum time to wait in seconds
            check_interval: How often to check status in seconds
            
        Returns:
            bool: True if operation completed, False if timed out
        """
        start_time = time.time()
        elapsed = 0
        
        logger.info(f"Waiting for operation: {operation_name}")
        
        while elapsed < timeout:
            # Check if operation is complete - this is a placeholder
            # Actual implementation depends on how operations are tracked
            if self._check_operation_status(operation_name):
                logger.info(f"Operation completed: {operation_name}")
                return True
                
            time.sleep(check_interval)
            elapsed = time.time() - start_time
            
        logger.warning(f"Timeout waiting for operation: {operation_name}")
        return False
        
    def _check_operation_status(self, operation_name):
        """
        Check if an operation has completed - placeholder method
        
        Args:
            operation_name: Name of operation to check
            
        Returns:
            bool: True if operation is complete
        """
        # This is a placeholder that should be overridden in specific test cases
        return False