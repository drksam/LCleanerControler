#!/usr/bin/env python3
"""
Debug script to check LED state when user is logged in
"""

import time
from ws2812b_controller import WS2812BController, LEDState

print("Testing user logged in state...")

controller = WS2812BController()
controller.start()

print(f"Initial state: {controller.current_state}")
print(f"ACCESS_GRANTED color mapping: {controller.state_colors[LEDState.ACCESS_GRANTED]}")
print(f"ACCESS_GRANTED LED2 mapping: {controller.led2_placement_colors[LEDState.ACCESS_GRANTED]}")

print("\nSetting user logged in state...")
controller.set_user_logged_in()

time.sleep(2)

print(f"Current state after set_user_logged_in(): {controller.current_state}")
print(f"Current animation: {controller.current_animation}")

# Also test direct state setting
print("\nTesting direct ACCESS_GRANTED state...")
controller.set_state(LEDState.ACCESS_GRANTED)

time.sleep(2)

print(f"Current state after direct set: {controller.current_state}")
print(f"LED1 color should be: {controller.state_colors[LEDState.ACCESS_GRANTED]}")
print(f"LED2 color should be: {controller.led2_placement_colors[LEDState.ACCESS_GRANTED]}")

controller.stop()
controller.close()
