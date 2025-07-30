#!/usr/bin/env python3
"""
Test script to verify LED flickering fix
This script tests the dual LED functionality without conflicts
"""

import time
import logging
from ws2812b_controller import WS2812BController, LEDState

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_led_states():
    """Test each LED state to verify no flickering or breathing interference"""
    print("Testing LED states - should show solid colors without flickering...")
    
    # Initialize LED controller
    led_controller = WS2812BController()
    led_controller.start()
    
    try:
        print("\n1. Testing LOGIN_SCREEN state (LED1: blue solid, LED2: white solid)")
        led_controller.set_login_screen_active()
        time.sleep(5)
        
        print("\n2. Testing ACCESS_GRANTED state (LED1: green solid, LED2: dim red solid)")
        led_controller.set_user_logged_in()
        time.sleep(5)
        
        print("\n3. Testing ADMIN_LOGGED_IN state (LED1: purple solid, LED2: dim red solid)")
        led_controller.set_admin_logged_in()
        time.sleep(5)
        
        print("\n4. Testing ACCESS_DENIED state (LED1: red flash, LED2: off)")
        led_controller.set_state(LEDState.ACCESS_DENIED)
        time.sleep(3)
        
        print("\n5. Back to LOGIN_SCREEN state")
        led_controller.set_login_screen_active()
        time.sleep(3)
        
        print("\n6. Testing LOGGED_OUT state (LED1: purple blink, LED2: off)")
        led_controller.set_state(LEDState.LOGGED_OUT)
        time.sleep(3)
        
        print("\n7. Final state: LOGIN_SCREEN")
        led_controller.set_login_screen_active()
        time.sleep(2)
        
        print("\nTest completed! LEDs should show solid colors without blue breathing interference.")
        
    finally:
        # Clean up
        led_controller.stop()
        led_controller.close()

if __name__ == "__main__":
    test_led_states()
