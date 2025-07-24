#!/usr/bin/env python3
"""
Test script to verify stepper motor fixes for ESP32 communication.
Tests jog and index functionality with improved error handling.
"""
import os
import sys
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set environment for hardware mode
os.environ['FORCE_HARDWARE'] = 'true'

try:
    from stepper_control_gpioctrl import StepperMotor
    from gpio_controller_wrapper import StepperWrapper
    
    def test_stepper_jog():
        """Test stepper jog functionality with error handling."""
        print("=" * 50)
        print("Testing Stepper Jog Functionality")
        print("=" * 50)
        
        # Initialize stepper motor
        print("Initializing stepper motor...")
        stepper = StepperMotor()
        
        # Test enabling
        print("Enabling stepper motor...")
        enable_result = stepper.enable()
        print(f"Enable result: {enable_result}")
        
        # Get initial position
        try:
            initial_pos = stepper.get_position()
            print(f"Initial position: {initial_pos}")
        except Exception as e:
            print(f"Error getting initial position: {e}")
            initial_pos = 0
        
        # Test forward jog
        print("\nTesting forward jog (10 steps)...")
        try:
            jog_result = stepper.jog(1, 10)  # direction=1 (forward), steps=10
            print(f"Forward jog result: {jog_result}")
            time.sleep(2)  # Allow movement to complete
            
            try:
                new_pos = stepper.get_position()
                print(f"Position after forward jog: {new_pos}")
            except Exception as e:
                print(f"Error getting position after forward jog: {e}")
                
        except Exception as e:
            print(f"Error during forward jog: {e}")
        
        # Test backward jog
        print("\nTesting backward jog (10 steps)...")
        try:
            jog_result = stepper.jog(0, 10)  # direction=0 (backward), steps=10
            print(f"Backward jog result: {jog_result}")
            time.sleep(2)  # Allow movement to complete
            
            try:
                new_pos = stepper.get_position()
                print(f"Position after backward jog: {new_pos}")
            except Exception as e:
                print(f"Error getting position after backward jog: {e}")
                
        except Exception as e:
            print(f"Error during backward jog: {e}")
        
        return stepper
    
    def test_stepper_index(stepper):
        """Test stepper index functionality with error handling."""
        print("\n" + "=" * 50)
        print("Testing Stepper Index Functionality")
        print("=" * 50)
        
        # Get initial position
        try:
            initial_pos = stepper.get_position()
            print(f"Initial position: {initial_pos}")
        except Exception as e:
            print(f"Error getting initial position: {e}")
            initial_pos = 0
        
        # Test forward index
        print("\nTesting forward index move...")
        try:
            index_result = stepper.move_index(1)  # direction=1 (forward)
            print(f"Forward index result: {index_result}")
            time.sleep(3)  # Allow movement to complete
            
            try:
                new_pos = stepper.get_position()
                print(f"Position after forward index: {new_pos}")
            except Exception as e:
                print(f"Error getting position after forward index: {e}")
                
        except Exception as e:
            print(f"Error during forward index: {e}")
        
        # Test backward index
        print("\nTesting backward index move...")
        try:
            index_result = stepper.move_index(-1)  # direction=-1 (backward)
            print(f"Backward index result: {index_result}")
            time.sleep(3)  # Allow movement to complete
            
            try:
                new_pos = stepper.get_position()
                print(f"Position after backward index: {new_pos}")
            except Exception as e:
                print(f"Error getting position after backward index: {e}")
                
        except Exception as e:
            print(f"Error during backward index: {e}")
    
    def test_esp32_communication():
        """Test ESP32 communication directly."""
        print("\n" + "=" * 50)
        print("Testing ESP32 Communication")
        print("=" * 50)
        
        try:
            from gpioctrl import GPIOController
            
            print("Creating GPIOController...")
            controller = GPIOController()
            time.sleep(2)  # Allow initialization
            
            print("Getting status...")
            try:
                status = controller.get_status()
                print(f"Status: {status}")
                print(f"Status type: {type(status)}")
            except Exception as e:
                print(f"Error getting status: {e}")
            
            print("Getting feedback...")
            try:
                feedback = controller.get_feedback()
                print(f"Feedback: {feedback}")
                print(f"Feedback type: {type(feedback)}")
            except Exception as e:
                print(f"Error getting feedback: {e}")
            
            print("Stopping controller...")
            controller.stop()
            
        except Exception as e:
            print(f"Error in ESP32 communication test: {e}")
    
    def main():
        """Main test function."""
        print("Starting Stepper Motor Fix Tests")
        print("This will test the fixes for ESP32 string response handling")
        
        # Test ESP32 communication first
        test_esp32_communication()
        
        # Test stepper functionality
        stepper = test_stepper_jog()
        test_stepper_index(stepper)
        
        print("\n" + "=" * 50)
        print("Test completed!")
        print("Check the logs above for any errors or warnings.")
        print("=" * 50)
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this on the Raspberry Pi with the gpioctrl library installed.")
except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()
