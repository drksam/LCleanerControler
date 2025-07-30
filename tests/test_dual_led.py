#!/usr/bin/env python3
"""
Test script for dual LED placement guide functionality
Tests LED2 placement guide behavior with different states
"""

import time
import logging
from ws2812b_controller import WS2812BController, LEDState

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_dual_led_placement_guide():
    """Test the dual LED placement guide functionality"""
    
    print("Testing Dual LED Placement Guide")
    print("=" * 50)
    print("LED1 = Status LED (authentication states)")
    print("LED2 = Placement guide (shows where to scan card)")
    print()
    
    # Create LED controller
    led_controller = WS2812BController()
    
    try:
        # Start the controller
        led_controller.start()
        
        print("1. BOOTING - Both LEDs show blue rotating animation")
        led_controller.set_state(LEDState.BOOTING)
        time.sleep(8)
        
        print("\n2. IDLE - Both LEDs show blue breathing (card scanning area)")
        led_controller.set_state(LEDState.IDLE)
        time.sleep(8)
        
        print("\n3. LOGIN_SCREEN - LED1: blue, LED2: white (login screen active)")
        led_controller.set_state(LEDState.LOGIN_SCREEN)
        time.sleep(5)
        
        print("\n4. ACCESS_GRANTED - LED1: green solid, LED2: dim red (normal user logged in)")
        led_controller.set_state(LEDState.ACCESS_GRANTED)
        time.sleep(5)
        
        print("\n5. ADMIN_LOGGED_IN - LED1: purple solid, LED2: dim red (admin user logged in)")
        led_controller.set_state(LEDState.ADMIN_LOGGED_IN)
        time.sleep(5)
        
        print("\n6. ACCESS_DENIED - LED1: red flash, LED2: off (unauthorized)")
        led_controller.set_state(LEDState.ACCESS_DENIED)
        time.sleep(5)
        
        print("\n7. LOGGED_OUT - LED1: purple blink, LED2: off (logging out)")
        led_controller.set_state(LEDState.LOGGED_OUT)
        time.sleep(5)
        
        print("\n8. Back to LOGIN_SCREEN - LED1: blue, LED2: white")
        led_controller.set_state(LEDState.LOGIN_SCREEN)
        time.sleep(5)
        
        print("\n9. Testing login workflow:")
        print("   - LOGIN_SCREEN (white placement guide)")
        led_controller.set_login_screen_active()
        time.sleep(3)
        
        print("   - CARD_DETECTED (both blue flash)")
        led_controller.set_state(LEDState.CARD_DETECTED)
        time.sleep(2)
        
        print("   - NORMAL USER LOGIN (green + dim red)")
        led_controller.set_user_logged_in()
        time.sleep(3)
        
        print("   - LOGOUT (purple blink + off)")
        led_controller.set_state(LEDState.LOGGED_OUT)
        time.sleep(3)
        
        print("   - ADMIN LOGIN (purple + dim red)")
        led_controller.set_admin_logged_in()
        time.sleep(3)
        
        print("   - LOGOUT (purple blink + off)")
        led_controller.set_state(LEDState.LOGGED_OUT)
        time.sleep(3)
        
        print("   - Back to LOGIN_SCREEN (blue + white)")
        led_controller.set_login_screen_active()
        time.sleep(3)
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean shutdown
        print("\nStopping LED controller...")
        led_controller.stop()
        print("Test completed")

def test_individual_led_control():
    """Test individual LED control directly"""
    print("\nTesting Individual LED Control")
    print("=" * 40)
    
    led_controller = WS2812BController()
    
    try:
        led_controller.start()
        
        # Test individual LED control
        print("Setting LED0 to red...")
        led_controller._set_individual_led(0, 'red')
        time.sleep(2)
        
        print("Setting LED1 to blue...")
        led_controller._set_individual_led(1, 'blue')
        time.sleep(2)
        
        print("Setting LED0 to green, LED1 to white...")
        led_controller._set_individual_led(0, 'green')
        led_controller._set_individual_led(1, 'white')
        time.sleep(2)
        
        print("Setting LED1 to dim_red...")
        led_controller._set_individual_led(1, 'dim_red')
        time.sleep(2)
        
        print("Turning off both LEDs...")
        led_controller._set_individual_led(0, 'off')
        led_controller._set_individual_led(1, 'off')
        time.sleep(1)
        
    except Exception as e:
        print(f"Individual LED test error: {e}")
    finally:
        led_controller.stop()

if __name__ == "__main__":
    test_dual_led_placement_guide()
    test_individual_led_control()
