#!/usr/bin/env python3
"""
Simple stepper test using the exact configuration from the working script.
This bypasses all our wrapper complexity and tests raw hardware functionality.
"""

import time
import logging
from gpioctrl import GPIOController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_raw_stepper():
    """Test stepper motor using the exact working configuration."""
    print("=== RAW STEPPER HARDWARE TEST ===")
    print("Using the exact configuration from the working script...")
    
    try:
        # Create GPIO controller - same as working script
        print("1. Creating GPIOController...")
        gpio = GPIOController(port="/dev/ttyUSB0")
        
        # Initialize stepper - EXACT same as working script
        print("2. Initializing stepper with working configuration...")
        gpio.init_stepper(
            id=0,
            step_pin=25,      # Same as working script
            dir_pin=26,       # Same as working script  
            limit_a=0,        # Same as working script (dummy)
            limit_b=0,        # Same as working script (dummy)
            home=0,           # Same as working script (dummy)
            min_limit=-50,    # Same as working script
            max_limit=250     # Same as working script
        )
        
        print("3. Testing small movements...")
        
        # Test small movements like the working script
        for i in range(3):
            print(f"   Move {i+1}/3: 50 steps forward...")
            start_time = time.time()
            
            # Exact same call as working script
            gpio.move_stepper(id=0, steps=50, direction=1, speed=1000)
            
            elapsed = time.time() - start_time
            print(f"   Move completed in {elapsed:.2f}s")
            
            time.sleep(0.5)  # Short pause between moves
            
            print(f"   Move {i+1}/3: 50 steps backward...")
            start_time = time.time()
            
            gpio.move_stepper(id=0, steps=50, direction=0, speed=1000)
            
            elapsed = time.time() - start_time
            print(f"   Reverse completed in {elapsed:.2f}s")
            
            time.sleep(0.5)
        
        print("\n4. Testing larger movement...")
        print("   Moving 200 steps forward...")
        gpio.move_stepper(id=0, steps=200, direction=1, speed=1000)
        
        time.sleep(1)
        
        print("   Moving 200 steps backward...")
        gpio.move_stepper(id=0, steps=200, direction=0, speed=1000)
        
        print("\n✅ RAW HARDWARE TEST COMPLETED")
        print("   If you see/hear the stepper moving, hardware is working!")
        print("   If no movement, there may be wiring or power issues.")
        
        gpio.stop()
        return True
        
    except Exception as e:
        print(f"❌ RAW HARDWARE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_enable_pin():
    """Test if adding enable pin control helps."""
    print("\n=== TESTING WITH ENABLE PIN CONTROL ===")
    
    try:
        gpio = GPIOController(port="/dev/ttyUSB0")
        
        # Initialize stepper same as before
        gpio.init_stepper(
            id=0,
            step_pin=25,
            dir_pin=26,
            limit_a=0,
            limit_b=0,
            home=0,
            min_limit=-50,
            max_limit=250
        )
        
        # Manually control enable pin (ESP32 pin 27 from machine_config.json)
        print("1. Setting enable pin HIGH (enable stepper)...")
        gpio.set_pin(27, 1)  # Enable pin HIGH
        time.sleep(0.1)
        
        print("2. Testing movement with enable pin controlled...")
        gpio.move_stepper(id=0, steps=100, direction=1, speed=1000)
        
        time.sleep(1)
        
        print("3. Setting enable pin LOW (disable stepper)...")
        gpio.set_pin(27, 0)  # Enable pin LOW
        
        gpio.stop()
        return True
        
    except Exception as e:
        print(f"❌ ENABLE PIN TEST FAILED: {e}")
        return False

if __name__ == "__main__":
    print("🔧 STEPPER HARDWARE DIAGNOSTIC")
    print("=" * 50)
    print("This test uses the exact working configuration to verify stepper hardware.")
    print("Listen/watch for stepper movement during the test.\n")
    
    # Test 1: Raw hardware (working script config)
    raw_success = test_raw_stepper()
    
    # Test 2: With enable pin control
    enable_success = test_with_enable_pin()
    
    print(f"\n🎯 DIAGNOSTIC RESULTS:")
    print(f"Raw hardware test: {'✅ PASS' if raw_success else '❌ FAIL'}")
    print(f"Enable pin test: {'✅ PASS' if enable_success else '❌ FAIL'}")
    
    if raw_success:
        print("\n💡 CONCLUSION: Stepper hardware works with working script config")
        print("   The issue is in our wrapper's pin configuration or position tracking")
    else:
        print("\n💡 CONCLUSION: Stepper hardware issue - check wiring/power/connections")
