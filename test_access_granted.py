#!/usr/bin/env python3
"""
Test to check LED states when ACCESS_GRANTED is set
"""

import time
import logging
from ws2812b_controller import WS2812BController, LEDState

# Set up logging to see what's happening
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

print("Testing ACCESS_GRANTED LED state...")

controller = WS2812BController()
print(f"State colors: {controller.state_colors}")
print(f"LED2 colors: {controller.led2_placement_colors}")

controller.start()

print(f"\nInitial state: {controller.current_state}")
print("Setting ACCESS_GRANTED state...")

controller.set_state(LEDState.ACCESS_GRANTED)

print(f"Current state after setting: {controller.current_state}")
print(f"LED1 should be: {controller.state_colors[LEDState.ACCESS_GRANTED]}")
print(f"LED2 should be: {controller.led2_placement_colors[LEDState.ACCESS_GRANTED]}")

# Wait to see the LED colors
print("\nWaiting 10 seconds to observe LED colors...")
print("LED1 should be GREEN, LED2 should be DIM RED")
time.sleep(10)

controller.stop()
controller.close()
print("Test completed.")
