#!/usr/bin/env python
"""
Test Runner for LCleanerController

This script executes the test suite for the LCleanerController project.
It can run all tests or specific categories of tests.

Usage:
    python tests/run_tests.py [category]

Categories:
    all         Run all tests (default)
    unit        Run unit tests only
    hardware    Run hardware tests only
    sequences   Run sequence tests only
    integration Run integration tests only
    api         Run API tests only
"""
import os
import sys
import unittest
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_runner')

# Add project root directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_tests(category='all'):
    """
    Run tests in the specified category
    
    Args:
        category: Test category to run ('all', 'unit', 'hardware', 'sequences', 'integration', 'api')
        
    Returns:
        bool: True if all tests pass, False otherwise
    """
    logger.info(f"Running {category} tests...")
    
    # Determine test directories based on category
    if category == 'all':
        test_dirs = [
            'tests/unit',
            'tests/hardware',
            'tests/sequences',
            'tests/integration'
        ]
    elif category == 'api':
        # API tests are in a single file
        test_dirs = []
        api_test_path = Path(__file__).parent.parent / 'api_tests.py'
        if api_test_path.exists():
            # Import and run the API tests
            sys.path.insert(0, str(api_test_path.parent))
            spec = importlib.util.spec_from_file_location("api_tests", api_test_path)
            api_tests = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(api_tests)
            return api_tests.run_all_tests()
        else:
            logger.error(f"API test file not found: {api_test_path}")
            return False
    else:
        test_dirs = [f'tests/{category}']
    
    # Find and load test modules
    test_suite = unittest.TestSuite()
    
    for test_dir in test_dirs:
        dir_path = Path(test_dir)
        
        if not dir_path.exists() or not dir_path.is_dir():
            logger.warning(f"Test directory not found: {test_dir}")
            continue
            
        # Find all test files
        test_files = list(dir_path.glob("test_*.py"))
        
        if not test_files:
            logger.warning(f"No test files found in {test_dir}")
            continue
            
        # Add tests to suite
        for test_file in test_files:
            module_name = test_file.stem
            module_path = f"{test_dir.replace('/', '.')}.{module_name}"
            
            try:
                logger.info(f"Loading tests from {module_path}")
                tests = unittest.defaultTestLoader.loadTestsFromName(module_path)
                test_suite.addTests(tests)
            except Exception as e:
                logger.error(f"Error loading tests from {module_path}: {e}")
    
    # Run the tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Return True if all tests passed
    return result.wasSuccessful()

if __name__ == '__main__':
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run LCleanerController tests')
    parser.add_argument('category', nargs='?', default='all',
                        choices=['all', 'unit', 'hardware', 'sequences', 'integration', 'api'],
                        help='Test category to run (default: all)')
    args = parser.parse_args()
    
    # Add import here to avoid circular import issues
    import importlib.util
    
    # Run tests and exit with appropriate code
    success = run_tests(args.category)
    sys.exit(0 if success else 1)