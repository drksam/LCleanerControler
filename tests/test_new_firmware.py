#!/usr/bin/env python3
"""
Test script to validate new ESP32 firmware functionality with updated pin assignments
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stepper_control_gpioctrl import StepperMotor
import logging
import time

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_new_firmware():
    """Test new ESP32 firmware with updated pin assignments and switch detection."""
    print("=== New ESP32 Firmware Validation Test ===")
    print("Pin assignments:")
    print("  Limit A (CW): Pin 18")
    print("  Limit B (CCW): Pin 19") 
    print("  Home: Pin 21")
    print()
    
    try:
        # Initialize stepper controller
        stepper = StepperMotor()
        
        print("✅ Stepper initialized successfully")
        
        if not stepper.stepper or not stepper.stepper._controller:
            print("❌ No stepper controller available - cannot test")
            return
            
        controller = stepper.stepper._controller
        
        # Test 1: Test new get_pin_states command
        print("\n--- Test 1: New get_pin_states Command ---")
        try:
            if hasattr(controller, 'get_pin_states'):
                pin_states = controller.get_pin_states(0)
                print(f"✅ get_pin_states response: {pin_states}")
            else:
                print("❌ get_pin_states method not found - GPIO controller needs update")
        except Exception as e:
            print(f"❌ get_pin_states failed: {e}")
        
        # Test 2: Test updated get_status response
        print("\n--- Test 2: Updated get_status Response ---")
        try:
            status = controller.get_status()
            print(f"get_status response: {status}")
            
            # Check for new format
            if isinstance(status.get('status'), dict) and 'stepper_0' in status.get('status', {}):
                stepper_status = status['status']['stepper_0']
                print(f"✅ New firmware format detected:")
                print(f"  Limit A: {stepper_status.get('limit_a', 'N/A')}")
                print(f"  Limit B: {stepper_status.get('limit_b', 'N/A')}")
                print(f"  Home: {stepper_status.get('home', 'N/A')}")
                print(f"  Moving: {stepper_status.get('moving', 'N/A')}")
                print(f"  Position: {stepper_status.get('position', 'N/A')}")
            else:
                print(f"⚠️  Old firmware format detected: {status}")
                
        except Exception as e:
            print(f"❌ get_status failed: {e}")
        
        # Test 3: Test switch detection through stepper wrapper
        print("\n--- Test 3: Switch Detection via Stepper Wrapper ---")
        print("Testing switch states (manually trigger switches during this test)...")
        
        for i in range(20):  # 10 seconds of testing
            stepper.stepper.update_limit_states()
            
            limit_a = stepper.stepper._limit_a_triggered
            limit_b = stepper.stepper._limit_b_triggered 
            home = stepper.stepper._home_triggered
            
            # Also test high-level methods
            is_at_home = stepper.is_at_home()
            
            print(f"Switches: Limit A={limit_a} | Limit B={limit_b} | Home={home} | is_at_home()={is_at_home}    ", end='\r')
            time.sleep(0.5)
        
        print(f"\n✅ Switch monitoring completed")
        
        # Test 4: Test pin assignments match config
        print("\n--- Test 4: Pin Assignment Verification ---")
        print(f"Stepper wrapper pin assignments:")
        print(f"  Limit A pin: {stepper.stepper.limit_a_pin} (should be 18)")
        print(f"  Limit B pin: {stepper.stepper.limit_b_pin} (should be 19)")
        print(f"  Home pin: {stepper.stepper.home_pin} (should be 21)")
        
        # Verify pin assignments
        if (stepper.stepper.limit_a_pin == 18 and 
            stepper.stepper.limit_b_pin == 19 and 
            stepper.stepper.home_pin == 21):
            print("✅ Pin assignments correct")
        else:
            print("❌ Pin assignments incorrect - check machine_config.json")
            
        print("\n--- Test Summary ---")
        print("✅ Firmware validation completed")
        print("Manual verification needed:")
        print("  1. Trigger Limit A (pin 18) and verify 'limit_a': true")
        print("  2. Trigger Limit B (pin 19) and verify 'limit_b': true") 
        print("  3. Trigger Home (pin 21) and verify 'home': true")
        print("  4. Test homing movement with 'python -c \"from stepper_control_gpioctrl import StepperMotor; s=StepperMotor(); s.home()\"'")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_new_firmware()
