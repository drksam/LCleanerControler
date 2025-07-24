#!/usr/bin/env python3
"""
Test script to test the Flask /home endpoint functionality
"""

import os
import requests
import time
import threading
import logging

# Set up environment for testing
os.environ['SIMULATION_MODE'] = 'True'

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_flask_home_endpoint():
    """Test the Flask /home endpoint"""
    
    print("=" * 60)
    print("Testing Flask /home Endpoint")
    print("=" * 60)
    
    # Start Flask app in background
    def start_flask():
        try:
            from main import app
            app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
        except Exception as e:
            print(f"Error starting Flask: {e}")
    
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    
    # Wait for Flask to start
    print("Starting Flask application...")
    time.sleep(3)
    
    try:
        # Test the /home endpoint
        print("\n--- Testing /home endpoint ---")
        url = "http://127.0.0.1:5000/home"
        
        print(f"Making POST request to: {url}")
        response = requests.post(url, json={}, timeout=10)
        
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success! Response data: {data}")
            
            # Check if it's simulated
            if data.get('simulated'):
                print("✓ Homing was properly simulated")
            else:
                print("ℹ Homing was performed on hardware")
                
            # Check position
            position = data.get('position')
            print(f"✓ Final position: {position}")
            
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n--- Test Completed ---")

if __name__ == "__main__":
    test_flask_home_endpoint()
