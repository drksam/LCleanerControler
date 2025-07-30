#!/usr/bin/env python3
"""
Test script to verify both normal and inverted enable pin logic.
This will help diagnose which setting is needed for your stepper driver.
"""

import time
import logging
import sys
import json
from gpio_controller_wrapper import StepperWrapper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
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

def test_stepper_logic(invert_logic):
    """Test stepper with specified enable pin logic."""
    config = load_config()
    gpio_config = config.get('gpio', {})
    
    # Get pin configurations
    step_pin = gpio_config.get('esp_step_pin', 25)
    dir_pin = gpio_config.get('esp_dir_pin', 26)
    enable_pin = gpio_config.get('esp_enable_pin', 27)
    
    logic_type = "INVERTED" if invert_logic else "NORMAL"
    print(f"\n=== TESTING WITH {logic_type} LOGIC ===")
    print(f"Step Pin: {step_pin}, Dir Pin: {dir_pin}, Enable Pin: {enable_pin}")
    print(f"Enable logic: {'LOW=Enable, HIGH=Disable' if invert_logic else 'HIGH=Enable, LOW=Disable'}")
    
    try:
        # Initialize stepper with specified logic
        stepper = StepperWrapper(
            step_pin=step_pin,
            dir_pin=dir_pin,
            enable_pin=enable_pin,
            simulation_mode=False,
            invert_enable_logic=invert_logic,
            serial_port=serial_port
        )
        
        print("\nTest sequence:")
        
        # Step 1: Enable stepper
        print("\n1. ENABLING stepper...")
        stepper.enable()
        result = input("   Is the stepper motor enabled (can be moved manually)? (y/n): ").lower()
        enabled_works = result.startswith('y')
        
        # Step 2: Try to move stepper
        if enabled_works:
            print("\n2. Moving stepper 100 steps forward...")
            stepper.move_steps(100, 1)
            time.sleep(2)
            input("   Press Enter after observing movement...")
        
        # Step 3: Disable with timer
        print("\n3. DISABLING stepper (with 10-second timer)...")
        stepper._enable_timeout = 10  # Short timeout for testing
        stepper.disable()
        result = input("   Is the stepper still enabled (can be moved manually)? (y/n): ").lower()
        timer_works = result.startswith('y')
        
        # Step 4: Wait for timeout
        if timer_works:
            print("\n4. Waiting for 12 seconds for timer to expire...")
            time.sleep(12)
            result = input("   Is the stepper now disabled (cannot be moved manually)? (y/n): ").lower()
            timer_disable_works = result.startswith('y')
        else:
            timer_disable_works = False
        
        # Step 5: Immediate disable
        print("\n5. Re-enabling and then IMMEDIATE DISABLE...")
        stepper.enable()
        time.sleep(1)
        stepper.disable(immediate_disable=True)
        result = input("   Is the stepper now immediately disabled (cannot be moved manually)? (y/n): ").lower()
        immediate_disable_works = result.startswith('y')
        
        # Report results
        print("\n=== TEST RESULTS ===")
        print(f"Logic setting: {logic_type}")
        print(f"Enable works: {enabled_works}")
        print(f"Timer keeps enabled: {timer_works}")
        print(f"Timer disable works: {timer_disable_works}")
        print(f"Immediate disable works: {immediate_disable_works}")
        
        if enabled_works and timer_works and timer_disable_works and immediate_disable_works:
            print(f"\n✓ SUCCESS: {logic_type} logic works correctly for your stepper driver!")
            return True
        else:
            print(f"\n✗ FAILURE: {logic_type} logic does NOT work correctly for your stepper driver.")
            return False
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Stepper Enable Pin Logic Test")
    print("This test will verify if your stepper driver needs normal or inverted logic")
    print("You'll need to manually observe if the motor is enabled/disabled at each step")
    
    serial_port = input("\nEnter serial port (e.g., /dev/ttyUSB0 or COM3): ")
    
    print("\n=== TEST PLAN ===")
    print("1. First testing with NORMAL logic (HIGH=Enable, LOW=Disable)")
    print("2. Then testing with INVERTED logic (LOW=Enable, HIGH=Disable)")
    print("3. Results will show which one works correctly")
    input("\nPress Enter to begin testing...")
    
    # Test with normal logic
    normal_result = test_stepper_logic(invert_logic=False)
    
    # Test with inverted logic
    inverted_result = test_stepper_logic(invert_logic=True)
    
    # Final summary
    print("\n=== FINAL SUMMARY ===")
    if normal_result and not inverted_result:
        print("Your stepper driver uses NORMAL logic (HIGH=Enable, LOW=Disable)")
        print("This is the default in the code.")
        recommended = "invert_enable_logic=False"
    elif inverted_result and not normal_result:
        print("Your stepper driver uses INVERTED logic (LOW=Enable, HIGH=Disable)")
        print("You need to modify the code to use inverted logic.")
        recommended = "invert_enable_logic=True"
    elif normal_result and inverted_result:
        print("Both logic settings seem to work. This is unusual.")
        print("Recommend sticking with the default normal logic.")
        recommended = "invert_enable_logic=False"
    else:
        print("Neither logic setting worked. There may be a hardware issue.")
        print("Check your connections and try again.")
        recommended = "unknown"
    
    print(f"\nRecommended setting: {recommended}")
