#!/usr/bin/env python3
"""
Test script to simulate the home button functionality on Windows
This helps us verify the logic without actual hardware
"""

import os
import sys
import time
import logging

# Set simulation mode BEFORE importing any modules
os.environ['SIMULATION_MODE'] = 'True'

# Update the machine config to force simulation mode
import json
config_path = 'machine_config.json'
with open(config_path, 'r') as f:
    config = json.load(f)
    
# Backup current operation mode
original_mode = config.get('operation_mode', 'hardware')

# Set to simulation mode for testing
config['operation_mode'] = 'simulation'

# Write updated config
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print(f"Changed operation_mode from '{original_mode}' to 'simulation' for testing")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_home_simulation():
    """Test the home button functionality in simulation mode"""
    
    print("=" * 60)
    print("Testing Home Button Functionality (Simulation Mode)")
    print("=" * 60)
    
    try:
        # Import our modules
        from stepper_control_gpioctrl import StepperMotor
        
        print("✓ Successfully imported StepperMotor")
        
        # Create stepper instance
        stepper = StepperMotor()
        print("✓ Successfully created StepperMotor instance")
        
        # Test initial state
        print(f"Initial position: {stepper.get_position()}")
        print(f"Is moving: {stepper.is_moving()}")
        
        # Test home function
        print("\n--- Testing Home Function ---")
        print("Calling stepper.home(wait=False)...")
        
        result = stepper.home(wait=False)
        print(f"Home function returned: {result}")
        
        # Check if moving
        time.sleep(0.1)  # Small delay
        print(f"Is moving after home call: {stepper.is_moving()}")
        
        # Wait a bit and check again
        time.sleep(1.0)
        print(f"Position after 1 second: {stepper.get_position()}")
        print(f"Is moving after 1 second: {stepper.is_moving()}")
        
        # Test stopping during homing
        if stepper.is_moving():
            print("\n--- Testing Stop During Homing ---")
            stepper.stop()
            print("Called stepper.stop()")
            time.sleep(0.1)
            print(f"Is moving after stop: {stepper.is_moving()}")
        
        print("\n--- Test Completed ---")
        
        # Restore original operation mode
        config['operation_mode'] = original_mode
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Restored operation_mode to '{original_mode}'")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        
        # Restore original operation mode even on error
        try:
            config['operation_mode'] = original_mode
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"Restored operation_mode to '{original_mode}' after error")
        except:
            print("Failed to restore original operation_mode")

if __name__ == "__main__":
    test_home_simulation()
