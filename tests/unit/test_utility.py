#!/usr/bin/env python
"""
Unit Tests for Utility Functions

This module tests the utility functions used throughout the application.
"""
import unittest
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.test_base import BaseTestCase

# Import utility modules to test
import utility

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_utility')

class UtilityFunctionTest(BaseTestCase):
    """Test case for utility functions"""
    
    def test_error_handling(self):
        """Test error handling functionality"""
        # Test basic error handling functions if they exist
        if hasattr(utility, 'format_error_message'):
            result = utility.format_error_message("Test Error", "Test error details")
            self.assertIn("Test Error", result)
            self.assertIn("Test error details", result)
        
    def test_simulation_mode(self):
        """Test simulation mode utilities"""
        # Test simulation mode detection if it exists
        if hasattr(utility, 'is_simulation_mode'):
            # We can't know the expected result, but can at least verify it runs
            result = utility.is_simulation_mode()
            self.assertIsInstance(result, bool)
            
    def test_string_utilities(self):
        """Test string manipulation utilities"""
        # Test any string utilities if they exist
        if hasattr(utility, 'sanitize_filename'):
            safe_name = utility.sanitize_filename("test/file:name?.txt")
            self.assertNotIn("/", safe_name)
            self.assertNotIn(":", safe_name)
            self.assertNotIn("?", safe_name)
            
    def test_logging_utilities(self):
        """Test logging utilities"""
        # Test log helper functions if they exist
        if hasattr(utility, 'log_error'):
            # This should not raise an exception
            utility.log_error("Test error")
            
    def test_conversion_functions(self):
        """Test unit conversion functions"""
        # Test any conversion utilities if they exist
        if hasattr(utility, 'convert_temperature'):
            celsius = 25.0
            fahrenheit = utility.convert_temperature(celsius, 'C', 'F')
            self.assertAlmostEqual(77.0, fahrenheit)
            
            kelvin = utility.convert_temperature(celsius, 'C', 'K')
            self.assertAlmostEqual(298.15, kelvin)

if __name__ == '__main__':
    unittest.main()