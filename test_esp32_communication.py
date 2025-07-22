#!/usr/bin/env python3
"""
Test script to check ESP32 communication and diagnose JSON parsing issues
"""
import sys
import os
import time
import json

# Add the current directory to path to import gpioctrl
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'gpioesp'))

try:
    from gpioctrl import GPIOController
    
    print("Testing ESP32 communication...")
    print("Creating GPIOController...")
    
    # Create controller with debug output
    gpio = GPIOController(port="/dev/ttyUSB0")
    
    print("Controller created. Waiting 2 seconds for initialization...")
    time.sleep(2)
    
    print("Testing servo command...")
    gpio.set_servo(pin=12, angle=45)
    
    print("Waiting 1 second...")
    time.sleep(1)
    
    print("Getting status...")
    status = gpio.get_status()
    print(f"Status: {status}")
    
    print("Getting feedback...")
    feedback = gpio.get_feedback()
    print(f"Feedback: {feedback}")
    
    print("Testing second servo command...")
    gpio.set_servo(pin=12, angle=90)
    time.sleep(1)
    
    print("Final status...")
    final_status = gpio.get_status()
    print(f"Final status: {final_status}")
    
    print("Stopping controller...")
    gpio.stop()
    print("Test completed successfully!")
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure gpioctrl is installed and available")
except Exception as e:
    print(f"Error during test: {e}")
    import traceback
    traceback.print_exc()
