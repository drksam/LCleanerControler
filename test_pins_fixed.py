#!/usr/bin/env python3
"""
Quick test to verify pin assignments are correct after config fix
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stepper_control_gpioctrl import StepperMotor
from config import get_stepper_config

print("=== Pin Assignment Verification (Updated) ===")

# Test 1: Check config values
print("\n--- Config Values ---")
config = get_stepper_config()
print(f"Config esp_limit_a_pin: {config.get('esp_limit_a_pin')}")
print(f"Config esp_limit_b_pin: {config.get('esp_limit_b_pin')}")
print(f"Config esp_home_pin: {config.get('esp_home_pin')}")

print(f"\nAll stepper config keys: {list(config.keys())}")

# Test 2: Check stepper motor values
print("\n--- Stepper Motor Values ---")
try:
    stepper = StepperMotor()
    print(f"Stepper limit_a_pin: {stepper.limit_a_pin}")
    print(f"Stepper limit_b_pin: {stepper.limit_b_pin}")
    print(f"Stepper home_pin: {stepper.home_pin}")
    
    # Expected values
    expected = {
        'limit_a': 18,
        'limit_b': 19, 
        'home': 21
    }
    
    # Verify
    if (stepper.limit_a_pin == expected['limit_a'] and
        stepper.limit_b_pin == expected['limit_b'] and
        stepper.home_pin == expected['home']):
        print("✅ Pin assignments are correct!")
        
        # Test switch detection
        print("\n--- Testing Switch Detection ---")
        if stepper.stepper and stepper.stepper._controller:
            print("Getting ESP32 status...")
            stepper.stepper.update_limit_states()
            print(f"Limit A triggered: {stepper.stepper._limit_a_triggered}")
            print(f"Limit B triggered: {stepper.stepper._limit_b_triggered}")
            print(f"Home triggered: {stepper.stepper._home_triggered}")
        else:
            print("No stepper controller available")
            
    else:
        print("❌ Pin assignments are still incorrect!")
        print(f"Expected: Limit A={expected['limit_a']}, Limit B={expected['limit_b']}, Home={expected['home']}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
