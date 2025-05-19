#!/usr/bin/env python3
"""
Main fix script for LCleanerControler
Runs the individual fix scripts in sequence
"""
import os
import subprocess
import sys

def run_script(script_name):
    print(f"\n=== Running {script_name} ===")
    result = subprocess.run([sys.executable, script_name])
    if result.returncode != 0:
        print(f"Error running {script_name}. Please check the script and try again.")
        return False
    return True

def main():
    print("Starting LCleanerControler fixes...")
    
    # Check for the enhanced RFID fixer first
    if os.path.exists('fix_rfid_complete.py'):
        # Use the enhanced RFID fixer instead of the basic one
        required_scripts = ['fix_main.py', 'fix_rfid_complete.py', 'fix_models.py']
    else:
        required_scripts = ['fix_main.py', 'fix_rfid.py', 'fix_models.py']
    
    # Check that all required scripts exist
    for script in required_scripts:
        if not os.path.exists(script):
            print(f"Error: Required script {script} not found!")
            return False
    
    # Make scripts executable
    for script in required_scripts:
        os.chmod(script, 0o755)
    
    # Run each fix script in sequence
    success = True
    for script in required_scripts:
        if not run_script(script):
            success = False
            break
    
    if success:
        print("\n=== All fixes applied successfully! ===")
        print("You can now run: python3 test_run.py --prototype --debug")
        
        # Check if the check_rfid.py script exists and suggest using it for verification
        if os.path.exists('check_rfid.py'):
            print("\nFor additional verification of rfid_control.py, you can run:")
            print("  python3 check_rfid.py")
    else:
        print("\n=== Fix process encountered errors ===")
        print("Please check the error messages above.")
    
    return success

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
