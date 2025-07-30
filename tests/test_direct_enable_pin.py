#!/usr/bin/env python3
"""
Direct test of the enable pin using the GPIOController class.
This script bypasses all the wrapper code and directly sends commands to the ESP32.
"""

import time
import sys
import json
import logging
from gpioctrl.gpio_controller import GPIOController

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def load_config():
    """Load machine configuration from file."""
    try:
        with open('machine_config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}

def direct_pin_test():
    """Test enable pin behavior directly using GPIOController."""
    logger.info("=== DIRECT ENABLE PIN TEST ===")
    
    # Load configuration
    config = load_config()
    gpio_config = config.get('gpio', {})
    enable_pin = gpio_config.get('esp_enable_pin', 27)
    
    logger.info(f"Testing enable pin {enable_pin}")
    
    # Get serial port from user
    port = input(f"Enter serial port (e.g., /dev/ttyUSB0 or COM3): ")
    
    try:
        # Initialize controller
        logger.info(f"Initializing GPIOController on {port}...")
        gpio = GPIOController(port=port, baudrate=115200)
        logger.info("GPIOController initialized")
        
        # Test sequence
        print("\n=== ENABLE PIN TEST SEQUENCE ===")
        
        # Initial state measurement
        input("\nSTEP 1: Initial state check. Press Enter after measuring pin voltage...")
        
        # Set HIGH
        print("\nSTEP 2: Setting pin HIGH...")
        gpio.set_pin(enable_pin, 1)
        print(f"Command sent: set_pin({enable_pin}, 1)")
        time.sleep(0.5)
        input("Measure pin voltage and note if motor is ENABLED or DISABLED. Press Enter...")
        
        # Set LOW
        print("\nSTEP 3: Setting pin LOW...")
        gpio.set_pin(enable_pin, 0)
        print(f"Command sent: set_pin({enable_pin}, 0)")
        time.sleep(0.5)
        input("Measure pin voltage and note if motor is ENABLED or DISABLED. Press Enter...")
        
        # Ask user for observations
        print("\n=== OBSERVATIONS ===")
        high_state = input("When pin was HIGH (1), was the motor: [E]nabled or [D]isabled? ").upper().strip()
        low_state = input("When pin was LOW (0), was the motor: [E]nabled or [D]isabled? ").upper().strip()
        
        # Analyze the results
        print("\n=== ANALYSIS ===")
        if high_state.startswith('E') and low_state.startswith('D'):
            print("Your driver uses NORMAL logic (HIGH=Enable, LOW=Disable)")
            print("Current code logic matches this behavior.")
        elif high_state.startswith('D') and low_state.startswith('E'):
            print("Your driver uses INVERTED logic (LOW=Enable, HIGH=Disable)")
            print("Your code should be modified to invert the enable pin logic.")
        else:
            print("Results unclear. Please retry the test.")
        
        # Final state
        desired_state = input("\nDo you want to leave the motor [E]nabled or [D]isabled? ").upper().strip()
        
        if desired_state.startswith('E'):
            if high_state.startswith('E'):
                gpio.set_pin(enable_pin, 1)
                print(f"Set pin HIGH to enable motor")
            else:
                gpio.set_pin(enable_pin, 0)
                print(f"Set pin LOW to enable motor")
        else:
            if high_state.startswith('D'):
                gpio.set_pin(enable_pin, 1)
                print(f"Set pin HIGH to disable motor")
            else:
                gpio.set_pin(enable_pin, 0)
                print(f"Set pin LOW to disable motor")
        
        print("\nTest complete.")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Direct Enable Pin Test")
    print("This test will directly control the enable pin using GPIOController")
    print("You'll need a multimeter to check the pin voltage at each step")
    print("")
    
    direct_pin_test()
