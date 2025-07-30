#!/usr/bin/env python3
"""
Simple enable pin test to verify current behavior.
Use this to debug what's actually happening with the enable pin.
"""

import time
import logging
import sys
import config
from gpio_controller_wrapper import StepperWrapper

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def test_enable_pin_states():
    """Test and log enable pin states step by step."""
    logger.info("=== ENABLE PIN STATE TEST ===")
    
    # Get stepper configuration
    stepper_config = config.get_stepper_config()
    enable_pin = stepper_config.get('esp_enable_pin', 27)
    logger.info(f"Testing enable pin: {enable_pin}")
    
    try:
        stepper = StepperWrapper(
            step_pin=stepper_config['esp_step_pin'],
            dir_pin=stepper_config['esp_dir_pin'],
            enable_pin=enable_pin,
            simulation_mode=False,
            serial_port="/dev/ttyUSB0"  # Adjust for your setup
        )
        
        logger.info("StepperWrapper created")
        
        # Test sequence with detailed logging
        logger.info("\n1. ENABLING STEPPER (should set pin HIGH)")
        stepper.enable()
        logger.info("   Expected: Enable pin = HIGH (1)")
        input("   Press Enter after checking enable pin voltage...")
        
        logger.info("\n2. DISABLING STEPPER (should start timer, pin stays HIGH)")
        stepper.disable()
        logger.info("   Expected: Enable pin = HIGH (1) for 5 minutes")
        input("   Press Enter after checking enable pin voltage...")
        
        logger.info("\n3. ENABLING AGAIN (should cancel timer)")
        stepper.enable()
        logger.info("   Expected: Enable pin = HIGH (1), timer cancelled")
        input("   Press Enter after checking enable pin voltage...")
        
        logger.info("\n4. IMMEDIATE DISABLE (should set pin LOW)")
        stepper.disable(immediate_disable=True)
        logger.info("   Expected: Enable pin = LOW (0)")
        input("   Press Enter after checking enable pin voltage...")
        
        logger.info("\n5. ENABLE AGAIN")
        stepper.enable()
        logger.info("   Expected: Enable pin = HIGH (1)")
        input("   Press Enter after checking enable pin voltage...")
        
        # Cleanup
        stepper.close()
        logger.info("Test completed - stepper closed")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Enable Pin State Test")
    print("This will step through each state change and pause for voltage measurement")
    print("Use a multimeter to verify the actual pin voltage at each step")
    print("")
    
    test_enable_pin_states()
