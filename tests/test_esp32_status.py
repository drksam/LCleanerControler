#!/usr/bin/env python3
"""
Test script to request status from ESP32 and debug home switch detection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stepper_control_gpioctrl import StepperMotor
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_esp32_status_request():
    """Test ESP32 status request and switch detection."""
    print("=== ESP32 Status Request Test ===")
    
    try:
        # Initialize stepper controller
        stepper = StepperMotor()
        
        print("Stepper initialized successfully")
        
        if not stepper.stepper or not stepper.stepper._controller:
            print("No stepper controller available - cannot test")
            return
            
        controller = stepper.stepper._controller
        
        # Test 1: Get current feedback (passive)
        print("\n--- Test 1: Current Feedback (Passive) ---")
        feedback = controller.get_feedback()
        print(f"Current feedback: {feedback}")
        
        # Test 2: Request status actively
        print("\n--- Test 2: Request Status (Active) ---")
        try:
            status = controller.get_status()
            print(f"Requested status: {status}")
        except Exception as e:
            print(f"Error requesting status: {e}")
        
        # Test 3: Send custom pin read command
        print("\n--- Test 3: Custom Pin Read Commands ---")
        try:
            # Try to read pin 34 (home switch)
            controller._send_cmd({"cmd": "read_pin", "pin": 34})
            time.sleep(0.1)  # Give ESP32 time to respond
            feedback = controller.get_feedback()
            print(f"Pin 34 read response: {feedback}")
            
            # Try to read pin status
            controller._send_cmd({"cmd": "pin_status"})
            time.sleep(0.1)
            feedback = controller.get_feedback()
            print(f"Pin status response: {feedback}")
            
            # Try get_pins command
            controller._send_cmd({"cmd": "get_pins"})
            time.sleep(0.1)
            feedback = controller.get_feedback()
            print(f"Get pins response: {feedback}")
            
        except Exception as e:
            print(f"Error with custom commands: {e}")
        
        # Test 4: Monitor for any ESP32 responses
        print("\n--- Test 4: Monitor ESP32 Responses (10 seconds) ---")
        print("Press home switch during this time...")
        
        start_time = time.time()
        last_feedback = None
        
        while time.time() - start_time < 10:
            # Request status periodically
            if int(time.time() - start_time) % 2 == 0:  # Every 2 seconds
                try:
                    controller.get_status()
                except:
                    pass
            
            # Check for any new feedback
            current_feedback = controller.get_feedback()
            if current_feedback != last_feedback:
                print(f"\nNew feedback received: {current_feedback}")
                last_feedback = current_feedback
            
            # Also check stepper wrapper state
            stepper.stepper.update_limit_states()
            home_state = stepper.stepper._home_triggered
            print(f"Home: {home_state}  ", end='\r')
            
            time.sleep(0.2)
        
        print("\nTest completed")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_esp32_status_request()
