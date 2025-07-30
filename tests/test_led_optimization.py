#!/usr/bin/env python3
"""
Test script for LED controller optimization
Tests the state tracking and command reduction functionality
"""

import time
import logging
from ws2812b_controller import WS2812BController, LEDState

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_led_optimization():
    """Test the LED controller with optimization"""
    
    print("Testing LED Controller Optimization")
    print("=" * 50)
    
    # Create LED controller
    led_controller = WS2812BController()
    
    try:
        # Start the controller
        led_controller.start()
        
        print("\n1. Testing state changes (should see minimal command spam)")
        
        # Test IDLE state (breathing blue)
        print("Setting IDLE state (breathing blue)...")
        led_controller.set_state(LEDState.IDLE)
        time.sleep(5)
        
        # Test ACCESS_GRANTED state (solid green) 
        print("Setting ACCESS_GRANTED state (solid green)...")
        led_controller.set_state(LEDState.ACCESS_GRANTED)
        time.sleep(3)
        
        # Test ACCESS_DENIED state (flashing red)
        print("Setting ACCESS_DENIED state (flashing red)...")
        led_controller.set_state(LEDState.ACCESS_DENIED)
        time.sleep(3)
        
        # Test LOGGED_OUT state (blinking purple)
        print("Setting LOGGED_OUT state (blinking purple)...")
        led_controller.set_state(LEDState.LOGGED_OUT)
        time.sleep(3)
        
        # Test repeated state changes (should not spam commands)
        print("\n2. Testing repeated state changes (should not send redundant commands)")
        for i in range(3):
            print(f"Setting ACCESS_GRANTED again ({i+1}/3)...")
            led_controller.set_state(LEDState.ACCESS_GRANTED)
            time.sleep(1)
        
        print("\n3. Testing breathing animation for reduced command frequency")
        print("Setting IDLE state for breathing animation test...")
        led_controller.set_state(LEDState.IDLE)
        time.sleep(10)  # Watch for command frequency in logs
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        # Clean shutdown
        print("\nStopping LED controller...")
        led_controller.stop()
        print("Test completed")

if __name__ == "__main__":
    test_led_optimization()
