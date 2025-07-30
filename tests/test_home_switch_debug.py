#!/usr/bin/env python3
"""
Test script to debug home switch detection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stepper_control_gpioctrl import StepperMotor
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_home_switch_detection():
    """Test home switch detection and feedback parsing."""
    print("=== Home Switch Detection Test ===")
    
    try:
        # Initialize stepper controller
        stepper = StepperMotor()
        
        print("Stepper initialized successfully")
        
        # Test current home switch state
        print("\n--- Current Home Switch State ---")
        home_state = stepper.is_at_home()
        print(f"Home switch state: {home_state}")
        
        # Get raw feedback from ESP32
        print("\n--- Raw ESP32 Feedback ---")
        if stepper.stepper and stepper.stepper._controller:
            try:
                feedback = stepper.stepper._controller.get_feedback()
                print(f"Raw feedback: {feedback}")
                print(f"Feedback type: {type(feedback)}")
                
                if isinstance(feedback, dict):
                    status = feedback.get("status", {})
                    print(f"Status: {status}")
                    print(f"Status type: {type(status)}")
                    
                    # Show all keys
                    if isinstance(status, dict):
                        print("Status keys:")
                        for key in status.keys():
                            print(f"  {key}: {status[key]}")
                    else:
                        print("Status is not a dictionary")
                        
                    # Check stepper wrapper internal states
                    print(f"\nStepper wrapper states:")
                    print(f"  _home_triggered: {stepper.stepper._home_triggered}")
                    print(f"  _limit_a_triggered: {stepper.stepper._limit_a_triggered}")
                    print(f"  _limit_b_triggered: {stepper.stepper._limit_b_triggered}")
                    print(f"  home_pin: {stepper.stepper.home_pin}")
                    print(f"  _stepper_id: {stepper.stepper._stepper_id}")
                else:
                    print("Feedback is not a dictionary - this might be the issue")
                    
            except Exception as e:
                print(f"Error getting feedback: {e}")
                import traceback
                traceback.print_exc()
        
        # Test home switch state in a loop
        print("\n--- Home Switch Monitoring (15 seconds) ---")
        print("Manually trigger the home switch during this time...")
        start_time = time.time()
        while time.time() - start_time < 15:
            home_state = stepper.is_at_home()
            # Force update to see real-time changes
            if stepper.stepper:
                stepper.stepper.update_limit_states()
                raw_home = stepper.stepper._home_triggered
                print(f"Home switch: {home_state} | Raw: {raw_home}         ", end='\r')
            else:
                print(f"Home switch: {home_state}                    ", end='\r')
            time.sleep(0.2)
        
        print("\nTest completed")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_home_switch_detection()
