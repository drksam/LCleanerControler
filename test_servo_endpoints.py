#!/usr/bin/env python3
"""
Quick test script to verify servo button fix
"""
import requests
import time
import json

def test_servo_endpoints():
    """Test the servo endpoints that were failing"""
    base_url = "http://localhost:5000"
    
    print("Testing servo endpoints...")
    print("="*50)
    
    # Test servo_status
    print("1. Testing /servo_status...")
    try:
        response = requests.get(f"{base_url}/servo_status")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    print()
    
    # Test fire toggle
    print("2. Testing /fire (toggle mode)...")
    try:
        response = requests.post(f"{base_url}/fire", 
                               json={"mode": "toggle"},
                               headers={"Content-Type": "application/json"})
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    print()
    
    # Test stop_firing
    print("3. Testing /stop_firing...")
    try:
        response = requests.post(f"{base_url}/stop_firing")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    print()
    
    # Test fire_fiber toggle
    print("4. Testing /fire_fiber (toggle mode)...")
    try:
        response = requests.post(f"{base_url}/fire_fiber", 
                               json={"mode": "toggle"},
                               headers={"Content-Type": "application/json"})
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    print()
    
    # Test estop
    print("5. Testing /estop...")
    try:
        response = requests.post(f"{base_url}/estop")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    print()
    print("Test completed!")

if __name__ == "__main__":
    test_servo_endpoints()
