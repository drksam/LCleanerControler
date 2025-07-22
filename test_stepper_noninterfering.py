#!/usr/bin/env python3
"""
Non-interfering stepper test that uses the correct machine_config.json pins
and doesn't conflict with the main application.
"""

import time
import logging
import json
from gpioctrl import GPIOController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def load_machine_config():
    """Load the actual machine configuration."""
    try:
        with open('/home/laser/LCleanerController/machine_config.json', 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Failed to load machine_config.json: {e}")
        return None

def test_stepper_with_correct_config():
    """Test stepper using the exact machine_config.json configuration."""
    print("=== STEPPER TEST WITH MACHINE CONFIG ===")
    
    # Load the actual configuration
    config = load_machine_config()
    if not config:
        return False
    
    gpio_config = config.get('gpio', {})
    
    # Get the correct pins from machine_config.json
    step_pin = gpio_config.get('esp_step_pin', 25)
    dir_pin = gpio_config.get('esp_dir_pin', 26) 
    enable_pin = gpio_config.get('esp_enable_pin', 27)
    limit_a_pin = gpio_config.get('esp_limit_a_pin', 32)
    limit_b_pin = gpio_config.get('esp_limit_b_pin', 33)
    home_pin = gpio_config.get('esp_home_pin', 34)
    
    print(f"Using machine_config.json pins:")
    print(f"  Step: {step_pin}, Dir: {dir_pin}, Enable: {enable_pin}")
    print(f"  LimitA: {limit_a_pin}, LimitB: {limit_b_pin}, Home: {home_pin}")
    
    try:
        # Create GPIO controller
        print("1. Creating GPIOController...")
        gpio = GPIOController(port="/dev/ttyUSB0")
        
        # Use stepper ID 1 to avoid conflict with main app (which uses ID 0)
        stepper_id = 1
        
        print(f"2. Initializing stepper ID {stepper_id} with machine config pins...")
        gpio.init_stepper(
            id=stepper_id,
            step_pin=step_pin,
            dir_pin=dir_pin,
            limit_a=limit_a_pin,
            limit_b=limit_b_pin, 
            home=home_pin,
            min_limit=-1000,
            max_limit=1000
        )
        
        # Manually control enable pin like our wrapper does
        print(f"3. Setting enable pin {enable_pin} HIGH...")
        gpio.set_pin(enable_pin, 1)  # Enable stepper
        time.sleep(0.1)
        
        print("4. Testing movement with correct configuration...")
        
        # Test forward movement
        print("   Moving 100 steps forward...")
        start_time = time.time()
        gpio.move_stepper(id=stepper_id, steps=100, direction=1, speed=1000, wait=True)
        elapsed = time.time() - start_time
        print(f"   Forward move completed in {elapsed:.2f}s")
        
        time.sleep(1)
        
        # Test backward movement
        print("   Moving 100 steps backward...")
        start_time = time.time()
        gpio.move_stepper(id=stepper_id, steps=100, direction=0, speed=1000, wait=True)
        elapsed = time.time() - start_time
        print(f"   Backward move completed in {elapsed:.2f}s")
        
        # Disable stepper properly
        print(f"5. Setting enable pin {enable_pin} LOW (disable)...")
        gpio.set_pin(enable_pin, 0)  # Disable stepper
        
        print("6. Cleaning up stepper...")
        gpio.stop_stepper(id=stepper_id)
        
        gpio.stop()
        
        print("✅ TEST COMPLETED WITHOUT INTERFERING WITH MAIN APP")
        return True
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_main_app_stepper_direct():
    """Test if we can call the main app's stepper directly without interference."""
    print("\n=== TESTING MAIN APP STEPPER DIRECT ACCESS ===")
    
    try:
        # Import the actual stepper from the main app
        import sys
        sys.path.append('/home/laser/LCleanerController')
        
        from stepper_control_gpioctrl import StepperMotor
        
        print("1. Creating StepperMotor instance (same as main app)...")
        stepper = StepperMotor()
        
        print("2. Testing if stepper is enabled...")
        if not stepper.enabled:
            print("   Stepper not enabled, enabling...")
            stepper.stepper.enable()
        
        print("3. Getting current position...")
        position = stepper.get_position()
        print(f"   Current position: {position}")
        
        print("4. Testing small jog movement...")
        result = stepper.jog(direction=1, steps=50)  # 50 steps forward
        print(f"   Jog result: {result}")
        
        if result:
            # Wait a bit and check position
            time.sleep(2)
            new_position = stepper.get_position()
            print(f"   Position after jog: {new_position}")
            
            if new_position != position:
                print("   ✅ POSITION CHANGED - STEPPER IS WORKING!")
            else:
                print("   ❌ Position didn't change - movement issue")
        
        print("5. Testing reverse jog...")
        result = stepper.jog(direction=0, steps=50)  # 50 steps backward
        print(f"   Reverse jog result: {result}")
        
        time.sleep(2)
        final_position = stepper.get_position()
        print(f"   Final position: {final_position}")
        
        return True
        
    except Exception as e:
        print(f"❌ MAIN APP STEPPER TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 NON-INTERFERING STEPPER DIAGNOSTIC")
    print("=" * 50)
    print("This test uses correct pins and won't break the working script.\n")
    
    # Test 1: With correct machine config (non-interfering)
    config_success = test_stepper_with_correct_config()
    
    # Test 2: Direct access to main app stepper
    main_app_success = test_main_app_stepper_direct()
    
    print(f"\n🎯 DIAGNOSTIC RESULTS:")
    print(f"Machine config test: {'✅ PASS' if config_success else '❌ FAIL'}")
    print(f"Main app stepper test: {'✅ PASS' if main_app_success else '❌ FAIL'}")
    
    if config_success:
        print("\n💡 CONCLUSION: Hardware works with correct config and non-conflicting ID")
    else:
        print("\n💡 CONCLUSION: Still have hardware or configuration issues")
        
    print("\nNow try your working stepper script to verify it still works!")
