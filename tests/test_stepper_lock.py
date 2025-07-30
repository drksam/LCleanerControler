#!/usr/bin/env python3
"""
Simple lock debugging test to identify stepper lock contention issues.
"""

import time
import logging
import threading
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_stepper_lock_state():
    """Test if the stepper is in a locked state."""
    print("=== STEPPER LOCK STATE TEST ===")
    
    try:
        # Import stepper
        sys.path.append('/home/laser/LCleanerController')
        from stepper_control_gpioctrl import StepperMotor
        
        print("1. Creating StepperMotor instance...")
        stepper = StepperMotor()
        
        print("2. Testing lock acquisition with timeout...")
        
        def test_lock():
            print("   Attempting to acquire stepper lock...")
            acquired = stepper.lock.acquire(blocking=False)  # Non-blocking acquire
            if acquired:
                print("   ✅ Lock acquired successfully")
                stepper.lock.release()
                return True
            else:
                print("   ❌ Lock is currently held by another thread")
                return False
        
        # Test lock state
        lock_available = test_lock()
        
        if not lock_available:
            print("3. Lock is held - investigating...")
            
            # Try to find what's holding the lock
            print("   Checking for background threads...")
            for thread in threading.enumerate():
                print(f"   Active thread: {thread.name} - {thread}")
            
            print("   Waiting 5 seconds to see if lock is released...")
            time.sleep(5)
            
            # Test again
            lock_available = test_lock()
            
            if not lock_available:
                print("   ❌ Lock still held after 5 seconds - likely deadlock")
                return False
        
        print("4. Testing simple stepper operations...")
        
        # Test basic operations that don't require movement
        try:
            position = stepper.get_position()
            print(f"   Current position: {position}")
            
            enabled = stepper.enabled
            print(f"   Stepper enabled: {enabled}")
            
            moving = stepper.moving
            print(f"   Stepper moving: {moving}")
            
        except Exception as e:
            print(f"   ❌ Basic operations failed: {e}")
            return False
        
        print("5. Testing JOG operation (this is where it hangs)...")
        
        def test_jog_with_timeout():
            try:
                print("   About to call stepper.jog(1, 50)...")
                result = stepper.jog(1, 50)  # This is the exact call that hangs
                print(f"   Jog result: {result}")
                return result
            except Exception as e:
                print(f"   Jog failed with exception: {e}")
                return False
        
        # Test jog with a timeout to prevent hanging
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Jog operation timed out")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(15)  # 15 second timeout
        
        try:
            jog_result = test_jog_with_timeout()
            signal.alarm(0)  # Cancel timeout
            
            if jog_result:
                print("   ✅ Jog operation completed successfully")
            else:
                print("   ❌ Jog operation failed")
            
        except TimeoutError:
            signal.alarm(0)
            print("   ❌ JOG OPERATION TIMED OUT - This confirms the hanging issue!")
            return False
        except Exception as e:
            signal.alarm(0)
            print(f"   ❌ Jog operation failed with exception: {e}")
            return False
        
        print("✅ STEPPER LOCK TEST COMPLETED")
        return True
        
    except Exception as e:
        print(f"❌ STEPPER LOCK TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def force_stepper_reset():
    """Force reset the stepper to clear any stuck state."""
    print("\n=== FORCE STEPPER RESET ===")
    
    try:
        sys.path.append('/home/laser/LCleanerController')
        from stepper_control_gpioctrl import StepperMotor
        
        print("1. Creating new StepperMotor instance...")
        stepper = StepperMotor()
        
        print("2. Force stopping any movement...")
        try:
            stepper.stop()
            print("   Stop command sent")
        except Exception as e:
            print(f"   Stop failed: {e}")
        
        print("3. Resetting stepper state...")
        try:
            stepper.moving = False
            stepper.position = 0
            stepper.target_position = 0
            print("   State reset")
        except Exception as e:
            print(f"   State reset failed: {e}")
        
        print("4. Testing basic movement with timeout...")
        
        def test_with_timeout():
            try:
                # Test with a very simple operation
                result = stepper.jog(1, 10)  # 10 steps forward
                return result
            except Exception as e:
                print(f"   Jog failed: {e}")
                return False
        
        # Run test with timeout
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Test timed out")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)  # 10 second timeout
        
        try:
            result = test_with_timeout()
            signal.alarm(0)
            
            if result:
                print("   ✅ Basic movement test passed")
            else:
                print("   ❌ Basic movement test failed")
            
            return result
            
        except TimeoutError:
            signal.alarm(0)
            print("   ❌ Basic movement test timed out")
            return False
        
    except Exception as e:
        print(f"❌ FORCE RESET FAILED: {e}")
        return False

if __name__ == "__main__":
    print("🔧 STEPPER LOCK DEBUGGING")
    print("=" * 50)
    
    # Test 1: Check lock state
    lock_success = test_stepper_lock_state()
    
    if not lock_success:
        print("\n🔄 ATTEMPTING FORCE RESET...")
        reset_success = force_stepper_reset()
        
        print(f"\n🎯 RESULTS:")
        print(f"Lock test: {'✅ PASS' if lock_success else '❌ FAIL'}")
        print(f"Force reset: {'✅ PASS' if reset_success else '❌ FAIL'}")
        
        if not reset_success:
            print("\n💡 RECOMMENDATION: Restart the Flask app to clear stuck stepper state")
    else:
        print(f"\n🎯 RESULT: Lock test ✅ PASS")
        print("💡 Lock is available - the hang might be elsewhere")
