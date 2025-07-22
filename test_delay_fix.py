#!/usr/bin/env python3
"""
Test script to verify delay timer functionality
"""
import requests
import json
import time

# Configuration
BASE_URL = "http://10.4.2.33:5000"

def test_delay_routes():
    """Test the delay setting routes"""
    print("Testing delay setting routes...")
    
    # Test fan delay setting
    print("\n1. Testing fan off delay setting...")
    fan_data = {"delay_seconds": 120}  # 2 minutes
    
    try:
        response = requests.post(f"{BASE_URL}/settings/fan_off_delay", 
                               json=fan_data,
                               headers={'Content-Type': 'application/json'})
        print(f"Fan delay response: {response.status_code}")
        print(f"Fan delay data: {response.json()}")
    except Exception as e:
        print(f"Error testing fan delay: {e}")
    
    # Test red lights delay setting
    print("\n2. Testing red lights off delay setting...")
    lights_data = {"delay_seconds": 30}  # 30 seconds
    
    try:
        response = requests.post(f"{BASE_URL}/settings/red_lights_off_delay", 
                               json=lights_data,
                               headers={'Content-Type': 'application/json'})
        print(f"Red lights delay response: {response.status_code}")
        print(f"Red lights delay data: {response.json()}")
    except Exception as e:
        print(f"Error testing red lights delay: {e}")

def test_servo_routes():
    """Test the servo control routes"""
    print("\n\nTesting servo control routes...")
    
    routes = [
        ("/servo/move_to_a", "Move to Position A"),
        ("/servo/move_to_b", "Move to Position B"),
        ("/servo/detach", "Detach Servo"),
        ("/servo/reattach", "Reattach Servo")
    ]
    
    for route, description in routes:
        print(f"\n3. Testing {description}...")
        try:
            response = requests.post(f"{BASE_URL}{route}", 
                                   headers={'Content-Type': 'application/json'})
            print(f"{description} response: {response.status_code}")
            if response.status_code == 200:
                print(f"{description} data: {response.json()}")
            else:
                print(f"{description} error: {response.text}")
            time.sleep(1)  # Small delay between tests
        except Exception as e:
            print(f"Error testing {description}: {e}")

def test_angle_control():
    """Test direct angle control"""
    print("\n\n4. Testing direct angle control...")
    angle_data = {"angle": 90}  # 90 degrees
    
    try:
        response = requests.post(f"{BASE_URL}/servo/move_to_angle", 
                               json=angle_data,
                               headers={'Content-Type': 'application/json'})
        print(f"Angle control response: {response.status_code}")
        print(f"Angle control data: {response.json()}")
    except Exception as e:
        print(f"Error testing angle control: {e}")

def test_fire_routes():
    """Test firing functionality routes"""
    print("\n\n5. Testing Fire Routes...")
    
    # Test fire endpoint
    print("\n   Testing fire route...")
    try:
        response = requests.post(f"{BASE_URL}/fire", timeout=10)
        print(f"Fire response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Fire data: {data}")
        else:
            print(f"Fire error: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Fire route failed: {e}")
    
    # Test stop firing endpoint  
    print("\n   Testing stop firing route...")
    try:
        response = requests.post(f"{BASE_URL}/stop_firing", timeout=10)
        print(f"Stop firing response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Stop firing data: {data}")
        else:
            print(f"Stop firing error: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Stop firing route failed: {e}")
    
    # Test fire fiber endpoint
    print("\n   Testing fire fiber route...")
    try:
        response = requests.post(f"{BASE_URL}/fire_fiber", timeout=10)
        print(f"Fire fiber response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Fire fiber data: {data}")
        else:
            print(f"Fire fiber error: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Fire fiber route failed: {e}")

if __name__ == "__main__":
    print("LCleaner Controller - Delay Timer Fix Test")
    print("=" * 50)
    
    test_delay_routes()
    test_servo_routes()
    test_angle_control()
    test_fire_routes()
    
    print("\n" + "=" * 50)
    print("Test completed!")
