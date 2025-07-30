#!/usr/bin/env python3
"""
Quick test for dim_red color fix
"""

from ws2812b_controller import WS2812BController

# Test color parsing
controller = WS2812BController()

print("Testing color definitions:")
print(f"dim_red: {controller.colors['dim_red']}")
print(f"blue: {controller.colors['blue']}")
print(f"purple: {controller.colors['purple']}")

# Test color parsing logic
test_colors = ['dim_red', 'blue_rotating', 'purple']
for color in test_colors:
    if '_' in color and color not in controller.colors:
        parsed_color = color.split('_')[0]
        print(f"'{color}' -> '{parsed_color}' -> {controller.colors.get(parsed_color, 'NOT FOUND')}")
    else:
        print(f"'{color}' -> {controller.colors.get(color, 'NOT FOUND')}")
