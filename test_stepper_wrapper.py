#!/usr/bin/env python3
"""
Simple test script to isolate stepper wrapper issues.
This will test each layer of the stepper system independently using the ACTUAL interfaces.
"""

import time
import logging
import threading
from gpio_controller_wrapper import StepperWrapper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_stepper_wrapper_actual():
    """Test the StepperWrapper using the exact same parameters as StepperMotor class."""
    print("=== STEPPER WRAPPER TEST (ACTUAL INTERFACE) ===")
    
    try:
        # Use the same configuration as in stepper_control_gpioctrl.py
        print("1. Creating StepperWrapper with actual configuration...")
        stepper = StepperWrapper(
            step_pin=2,      # From machine_config.json
            dir_pin=3,       # From machine_config.json  
            enable_pin=4,    # From machine_config.json
            min_position=-1000,
            max_position=1000,
            limit_a_pin=0,
            limit_b_pin=0,
            home_pin=0,
            simulation_mode=False,  # Force hardware mode to test real issue
            serial_port="/dev/ttyUSB0"
        )
        
        print("2. Setting stepper speed...")
        stepper.set_speed(10)  # Default speed from StepperMotor
        
        print("3. Testing stepper enable...")
        enable_result = stepper.enable()
        print(f"   Enable result: {enable_result}")
        
        if not enable_result:
            print("   FAILED: Stepper enable failed")
            return False
        
        print("4. Testing position reading...")
        position = stepper.get_position()
        print(f"   Current position: {position}")
        
        print("5. Testing is_moving status...")
        moving_status = stepper.is_moving()
        print(f"   Is moving: {moving_status}")
        
        # Test the exact call that's hanging in the logs
        print("6. Testing move_steps call (the one that hangs)...")
        print("   This is the exact call that StepperMotor.move_to makes...")
        
        start_time = time.time()
        
        # Create a timeout mechanism to catch hanging
        result_container = {}
        timeout_occurred = False
        
        def move_with_timeout():
            try:
                print("   Calling stepper.move_steps(10, 1, False)...")
                result = stepper.move_steps(10, 1, False)  # Same as in StepperMotor.move_to
                result_container['result'] = result
                result_container['completed'] = True
                print(f"   move_steps returned: {result}")
            except Exception as e:
                result_container['error'] = str(e)
                result_container['completed'] = True
                print(f"   move_steps raised exception: {e}")
        
        # Start the movement in a thread with timeout
        move_thread = threading.Thread(target=move_with_timeout, daemon=True)
        move_thread.start()
        
        # Wait up to 8 seconds (our timeout limit)
        timeout = 8.0
        while time.time() - start_time < timeout:
            if 'completed' in result_container:
                break
            elapsed = time.time() - start_time
            if elapsed > 1.0 and int(elapsed) % 2 == 0:  # Print every 2 seconds
                print(f"   Still waiting... {elapsed:.1f}s")
            time.sleep(0.1)
        
        elapsed = time.time() - start_time
        
        if 'completed' in result_container:
            if 'result' in result_container:
                print(f"   ✓ move_steps completed: {result_container['result']} (took {elapsed:.1f}s)")
                success = True
            else:
                print(f"   ✗ move_steps failed: {result_container.get('error', 'Unknown error')} (took {elapsed:.1f}s)")
                success = False
        else:
            print(f"   ✗ TIMEOUT: move_steps call hung for {elapsed:.1f}s")
            print("   This confirms the hanging issue is in StepperWrapper.move_steps!")
            timeout_occurred = True
            success = False
        
        # Test actual movement verification if the first move succeeded
        if success and 'result' in result_container and result_container['result']:
            print("\n7. Testing movement verification and position tracking...")
            
            # Wait a bit for movement to complete
            print("   Waiting for movement to complete...")
            time.sleep(2.0)
            
            # Check if stepper is still moving
            moving_status = stepper.is_moving()
            print(f"   Is still moving: {moving_status}")
            
            # Check position after first movement
            position_after_move1 = stepper.get_position()
            print(f"   Position after first move: {position_after_move1}")
            
            # Test reverse movement
            print("\n8. Testing reverse movement (10 steps backward)...")
            start_time = time.time()
            
            try:
                result2 = stepper.move_steps(10, 0, False)  # 10 steps backward
                elapsed = time.time() - start_time
                print(f"   Reverse move result: {result2} (took {elapsed:.1f}s)")
                
                if result2:
                    # Wait for second movement
                    time.sleep(2.0)
                    
                    position_after_move2 = stepper.get_position()
                    print(f"   Position after reverse move: {position_after_move2}")
                    
                    # Calculate expected positions
                    expected_pos1 = 10  # Started at 0, moved 10 forward
                    expected_pos2 = 0   # Then moved 10 backward
                    
                    print(f"\n   📊 MOVEMENT ANALYSIS:")
                    print(f"   Initial position: 0")
                    print(f"   After +10 steps: {position_after_move1} (expected: {expected_pos1})")
                    print(f"   After -10 steps: {position_after_move2} (expected: {expected_pos2})")
                    
                    # Check if positions changed as expected
                    if position_after_move1 != 0:
                        print("   ✓ First movement changed position - STEPPER IS MOVING!")
                    else:
                        print("   ✗ Position didn't change - stepper may not be moving")
                        
                    if abs(position_after_move2 - 0) <= 1:  # Allow 1 step tolerance
                        print("   ✓ Reverse movement returned close to start - BIDIRECTIONAL WORKS!")
                    else:
                        print("   ⚠ Reverse movement didn't return to start position")
                        
            except Exception as e:
                print(f"   ✗ Reverse movement failed: {e}")
                
        # Test multiple small movements
        print("\n9. Testing multiple small movements...")
        for i in range(3):
            try:
                print(f"   Small move {i+1}/3: 5 steps forward...")
                result = stepper.move_steps(5, 1, False)
                time.sleep(1.0)  # Wait between moves
                pos = stepper.get_position()
                print(f"   Move {i+1} result: {result}, position: {pos}")
            except Exception as e:
                print(f"   Small move {i+1} failed: {e}")
                break
        
        # Test cleanup
        print("\n10. Testing stepper disable...")
        try:
            disable_result = stepper.disable()
            print(f"   Disable result: {disable_result}")
        except Exception as e:
            print(f"   Disable failed: {e}")
        
        if timeout_occurred:
            print("\n   🔍 DIAGNOSIS: The hang occurs in StepperWrapper.move_steps()")
            print("   This means the issue is in the GPIOController hardware communication.")
            
        return success
        
    except Exception as e:
        print(f"=== TEST FAILED WITH EXCEPTION ===")
        print(f"Error during wrapper creation or setup: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_stepper_simulation_mode():
    """Test if the issue occurs in simulation mode too."""
    print("\n=== STEPPER SIMULATION MODE TEST ===")
    
    try:
        print("1. Creating StepperWrapper in simulation mode...")
        stepper = StepperWrapper(
            step_pin=2,
            dir_pin=3,  
            enable_pin=4,
            min_position=-1000,
            max_position=1000,
            limit_a_pin=0,
            limit_b_pin=0,
            home_pin=0,
            simulation_mode=True,  # Force simulation mode
            serial_port="/dev/ttyUSB0"
        )
        
        print("2. Testing simulation mode operations...")
        stepper.set_speed(10)
        enable_result = stepper.enable()
        print(f"   Enable result: {enable_result}")
        
        print("3. Testing move_steps in simulation mode...")
        start_time = time.time()
        result = stepper.move_steps(10, 1, False)
        elapsed = time.time() - start_time
        print(f"   Simulation move result: {result} (took {elapsed:.1f}s)")
        
        stepper.disable()
        
        if elapsed < 1.0:
            print("   ✓ Simulation mode works quickly - issue is hardware-specific")
            return True
        else:
            print("   ✗ Even simulation mode is slow - issue may be in wrapper logic")
            return False
            
    except Exception as e:
        print(f"   Simulation test failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting stepper wrapper diagnostic tests...")
    print("This will help identify where the hanging issue occurs.\n")
    
    # Test 1: Simulation mode first (safe)
    sim_success = test_stepper_simulation_mode()
    
    # Test 2: Hardware mode (this may hang)
    if sim_success:
        print("\nSimulation mode works, now testing hardware mode...")
        hw_success = test_stepper_wrapper_actual()
    else:
        print("\nSkipping hardware test since simulation failed.")
        hw_success = False
    
    print(f"\n=== FINAL RESULTS ===")
    print(f"Simulation mode test: {'PASS' if sim_success else 'FAIL'}")
    print(f"Hardware mode test: {'PASS' if hw_success else 'FAIL'}")
    
    if sim_success and not hw_success:
        print("\n🎯 CONCLUSION: Issue is in hardware communication layer (GPIOController)")
        print("   The StepperWrapper logic works, but hardware calls are hanging.")
    elif not sim_success:
        print("\n🎯 CONCLUSION: Issue is in StepperWrapper logic itself")
    else:
        print("\n🎯 CONCLUSION: No hanging detected - issue may be elsewhere")
