#!/usr/bin/env python3
"""
Quick restart script for testing servo fixes
"""
import os
import sys
import subprocess

def restart_test():
    """Restart the test application with hardware debugging enabled"""
    
    print("Restarting LCleaner with SharedGPIOController...")
    print("="*50)
    
    # Kill any existing processes
    try:
        if os.name != 'nt':  # Linux/Unix
            subprocess.run(['pkill', '-f', 'test_run.py'], check=False)
            subprocess.run(['pkill', '-f', 'main.py'], check=False)
        else:  # Windows
            subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], check=False)
    except:
        pass
    
    print("Starting with hardware debugging...")
    
    # Start test_run with hardware and debug flags
    cmd = [sys.executable, 'test_run.py', '--hardware', '--debug']
    
    print(f"Running: {' '.join(cmd)}")
    print("="*50)
    print("Look for SharedGPIOController messages in the logs")
    print("Test the servo buttons - they should work without JSON errors")
    print("="*50)
    
    # Run the command
    subprocess.run(cmd)

if __name__ == "__main__":
    restart_test()
