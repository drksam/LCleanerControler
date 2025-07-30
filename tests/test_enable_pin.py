#!/usr/bin/env python3
"""
Test script for enable pin behavior and timer functionality.
This script helps debug the enable pin logic and 5-minute timer.

ENABLE PIN LOGIC (NORMAL):
- HIGH = Motor Enabled (can move)  
- LOW = Motor Disabled (cannot move)
"""

import time
import logging
import sys
import config
from gpio_controller_wrapper import StepperWrapper

# Configure logging to see all debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def test_enable_pin_logic():
    """Test the enable pin logic and timer functionality."""
    logger.info("=== ENABLE PIN TEST ===")
    
    # Get stepper configuration
    stepper_config = config.get_stepper_config()
    logger.info(f"Stepper config: {stepper_config}")
    
    # Initialize stepper wrapper
    try:
        stepper = StepperWrapper(
            step_pin=stepper_config['esp_step_pin'],
            dir_pin=stepper_config['esp_dir_pin'],
            enable_pin=stepper_config['esp_enable_pin'],
            simulation_mode=False,  # Use real hardware on Pi
            serial_port="/dev/ttyUSB0"  # Adjust for your Pi
        )
        logger.info("StepperWrapper initialized successfully")
        
        # Test 1: Enable stepper
        logger.info("\n--- Test 1: Enable Stepper ---")
        result = stepper.enable()
        logger.info(f"Enable result: {result}")
        time.sleep(2)
        
        # Test 2: Move stepper (should restart timer)
        logger.info("\n--- Test 2: Move Stepper ---")
        result = stepper.move_steps(100, 1, wait=False)
        logger.info(f"Move result: {result}")
        time.sleep(2)
        
        # Test 3: Another move (should restart timer again)
        logger.info("\n--- Test 3: Another Move ---")
        result = stepper.move_steps(100, 0, wait=False)
        logger.info(f"Move result: {result}")
        time.sleep(2)
        
        # Test 4: Disable stepper (should start 5-minute timer)
        logger.info("\n--- Test 4: Disable Stepper (with timer) ---")
        result = stepper.disable()
        logger.info(f"Disable result: {result}")
        logger.info("Timer should be running for 5 minutes...")
        
        # Test 5: Enable again (should cancel timer)
        logger.info("\n--- Test 5: Enable Again (should cancel timer) ---")
        time.sleep(5)  # Wait a bit
        result = stepper.enable()
        logger.info(f"Enable result: {result}")
        
        # Test 6: Immediate disable
        logger.info("\n--- Test 6: Immediate Disable ---")
        result = stepper.disable(immediate_disable=True)
        logger.info(f"Immediate disable result: {result}")
        
        # Cleanup
        logger.info("\n--- Cleanup ---")
        stepper.close()
        logger.info("Test completed successfully")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

def test_timer_only():
    """Test just the timer functionality with a short timeout."""
    logger.info("=== TIMER ONLY TEST ===")
    
    # Get stepper configuration
    stepper_config = config.get_stepper_config()
    
    # Initialize stepper wrapper
    try:
        stepper = StepperWrapper(
            step_pin=stepper_config['esp_step_pin'],
            dir_pin=stepper_config['esp_dir_pin'],
            enable_pin=stepper_config['esp_enable_pin'],
            simulation_mode=False,
            serial_port="/dev/ttyUSB0"
        )
        
        # Temporarily set shorter timeout for testing
        stepper._enable_timeout = 10  # 10 seconds instead of 5 minutes
        logger.info("Set timeout to 10 seconds for testing")
        
        # Enable and start timer
        stepper.enable()
        stepper.disable()  # This should start the 10-second timer
        
        logger.info("Waiting for 10-second timer to expire...")
        time.sleep(12)  # Wait a bit longer than timeout
        
        stepper.close()
        logger.info("Timer test completed")
        
    except Exception as e:
        logger.error(f"Timer test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Enable Pin Test Script")
    print("1. Full test")
    print("2. Timer only test (10 seconds)")
    
    choice = input("Choose test (1 or 2): ").strip()
    
    if choice == "1":
        test_enable_pin_logic()
    elif choice == "2":
        test_timer_only()
    else:
        print("Invalid choice")
