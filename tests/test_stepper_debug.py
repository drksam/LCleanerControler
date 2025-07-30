#!/usr/bin/env python3
"""
Test stepper initialization and movement with enhanced debugging
"""
import sys
import os
import time

# Add the gpioesp directory to the path
sys.path.insert(0, '/home/laser/LCleanerController/gpioesp')

try:
    from gpioctrl import GPIOController
    print("✓ Successfully imported GPIOController")
except ImportError as e:
    print(f"✗ Failed to import GPIOController: {e}")
    sys.exit(1)

def test_stepper():
    """Test stepper initialization and movement"""
    print("\n" + "="*60)
    print("Enhanced Stepper Test")
    print("="*60)
    
    try:
        # Initialize controller
        print("1. Creating GPIOController...")
        gpio = GPIOController(port="/dev/ttyUSB0")
        print("✓ Controller created")
        
        # Wait for initialization
        print("2. Waiting 3 seconds for initialization...")
        time.sleep(3)
        
        # Check initial feedback
        print("3. Checking initial feedback...")
        feedback = gpio.get_feedback()
        print(f"   Initial feedback: {feedback}")
        print(f"   Feedback type: {type(feedback)}")
        
        # Initialize stepper
        print("4. Initializing stepper...")
        gpio.init_stepper(
            id=0,
            step_pin=25,     # From machine config
            dir_pin=26,      # From machine config
            limit_a=0,       # Dummy pin
            limit_b=0,       # Dummy pin  
            home=0,          # Dummy pin
            min_limit=-1000,
            max_limit=1000,
            enable_pin=27    # From machine config
        )
        print("✓ Stepper init command sent")
        
        # Wait and check feedback
        print("5. Waiting 2 seconds after stepper init...")
        time.sleep(2)
        
        feedback = gpio.get_feedback()
        print(f"   Post-init feedback: {feedback}")
        print(f"   Feedback type: {type(feedback)}")
        
        # Test small movement
        print("6. Testing small stepper movement (10 steps forward)...")
        gpio.move_stepper(id=0, steps=10, direction=1, speed=500, wait=False)
        print("✓ Movement command sent")
        
        # Monitor feedback for 5 seconds
        print("7. Monitoring feedback for 5 seconds...")
        start_time = time.time()
        last_feedback = None
        
        while time.time() - start_time < 5:
            feedback = gpio.get_feedback()
            if feedback != last_feedback:
                elapsed = time.time() - start_time
                print(f"   {elapsed:.1f}s: {feedback}")
                last_feedback = feedback
            time.sleep(0.1)
        
        # Test movement in opposite direction
        print("8. Testing movement in opposite direction (10 steps backward)...")
        gpio.move_stepper(id=0, steps=10, direction=0, speed=500, wait=False)
        print("✓ Reverse movement command sent")
        
        # Monitor for another 3 seconds
        print("9. Monitoring for 3 more seconds...")
        start_time = time.time()
        
        while time.time() - start_time < 3:
            feedback = gpio.get_feedback()
            if feedback != last_feedback:
                elapsed = time.time() - start_time
                print(f"   {elapsed:.1f}s: {feedback}")
                last_feedback = feedback
            time.sleep(0.1)
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            print("10. Stopping controller...")
            gpio.stop()
            print("✓ Controller stopped")
        except:
            pass

if __name__ == "__main__":
    test_stepper()
