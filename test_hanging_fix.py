#!/usr/bin/env python3
"""
Test script to verify the hanging issue fixes for stepper motor operations.
"""

import logging
import time
import requests
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask server URL
BASE_URL = "http://10.4.2.33:5000"

def test_jog_operations():
    """Test jog operations that were previously hanging."""
    logger.info("=== Testing Jog Operations ===")
    
    # Test backward jog (this was working)
    logger.info("Testing backward jog...")
    try:
        response = requests.post(f"{BASE_URL}/jog", 
                               json={"direction": "backward", "steps": 10},
                               timeout=5)
        logger.info(f"Backward jog response: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Backward jog failed: {e}")
    
    time.sleep(2)  # Wait between operations
    
    # Test forward jog (this was hanging)
    logger.info("Testing forward jog...")
    try:
        response = requests.post(f"{BASE_URL}/jog", 
                               json={"direction": "forward", "steps": 10},
                               timeout=5)
        logger.info(f"Forward jog response: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Forward jog failed: {e}")
    
    time.sleep(2)  # Wait between operations
    
    # Test another backward jog to see if system still responds
    logger.info("Testing second backward jog...")
    try:
        response = requests.post(f"{BASE_URL}/jog", 
                               json={"direction": "backward", "steps": 10},
                               timeout=5)
        logger.info(f"Second backward jog response: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Second backward jog failed: {e}")

def test_index_operations():
    """Test index operations that were previously hanging."""
    logger.info("\n=== Testing Index Operations ===")
    
    # Test forward index
    logger.info("Testing forward index...")
    try:
        response = requests.post(f"{BASE_URL}/index_move", 
                               json={"direction": "forward"},
                               timeout=10)  # Index moves take longer
        logger.info(f"Forward index response: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Forward index failed: {e}")
    
    time.sleep(3)  # Wait for movement to complete
    
    # Test backward index
    logger.info("Testing backward index...")
    try:
        response = requests.post(f"{BASE_URL}/index_move", 
                               json={"direction": "backward"},
                               timeout=10)
        logger.info(f"Backward index response: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Backward index failed: {e}")
    
    time.sleep(3)  # Wait for movement to complete
    
    # Test another forward index to see if system still responds
    logger.info("Testing second forward index...")
    try:
        response = requests.post(f"{BASE_URL}/index_move", 
                               json={"direction": "forward"},
                               timeout=10)
        logger.info(f"Second forward index response: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Second forward index failed: {e}")

def test_rapid_operations():
    """Test rapid consecutive operations to stress test the fixes."""
    logger.info("\n=== Testing Rapid Operations ===")
    
    operations = [
        ("jog", {"direction": "forward", "steps": 5}),
        ("jog", {"direction": "backward", "steps": 5}),
        ("jog", {"direction": "forward", "steps": 5}),
        ("jog", {"direction": "backward", "steps": 5}),
    ]
    
    for i, (endpoint, data) in enumerate(operations):
        logger.info(f"Rapid test {i+1}: {endpoint} {data}")
        try:
            response = requests.post(f"{BASE_URL}/{endpoint}", 
                                   json=data,
                                   timeout=5)
            logger.info(f"Rapid test {i+1} response: {response.status_code} - {response.json()}")
        except Exception as e:
            logger.error(f"Rapid test {i+1} failed: {e}")
        time.sleep(0.5)  # Very short wait between operations

def check_server_status():
    """Check if the Flask server is responding."""
    logger.info("=== Checking Server Status ===")
    try:
        response = requests.get(f"{BASE_URL}/api/system/mode", timeout=5)
        logger.info(f"Server status: {response.status_code} - {response.text}")
        return True
    except Exception as e:
        logger.error(f"Server not responding: {e}")
        return False

def main():
    """Run all tests to verify hanging issue fixes."""
    logger.info("Starting hanging issue fix verification tests...")
    
    if not check_server_status():
        logger.error("Flask server is not responding. Please start the server first.")
        return
    
    logger.info("Server is responding. Starting tests...")
    
    # Run the tests
    test_jog_operations()
    test_index_operations()
    test_rapid_operations()
    
    # Final status check
    logger.info("\n=== Final Status Check ===")
    if check_server_status():
        logger.info("✓ All tests completed - server is still responding!")
    else:
        logger.error("✗ Server is no longer responding after tests")
    
    logger.info("Test completed. Check the Flask server logs for detailed operation logs.")

if __name__ == "__main__":
    main()
