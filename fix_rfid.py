#!/usr/bin/env python3
"""
This script fixes the f-string syntax error in rfid_control.py
"""
import os
import re
import shutil

# Create a backup of the original file
if os.path.exists('rfid_control.py'):
    print("Creating backup of rfid_control.py as rfid_control.py.bak")
    shutil.copy2('rfid_control.py', 'rfid_control.py.bak')

# Read the file content
with open('rfid_control.py', 'r') as file:
    content = file.read()

# Fix the problematic f-string
pattern = r'logging\.info\(f"Running in \{OPERATION_MODE\} mode - RFID hardware \{\"will be used but not required\" if PROTOTYPE_MODE else \"will not be used\"\}"\)'
replacement = 'status_msg = "will be used but not required" if PROTOTYPE_MODE else "will not be used"\n    logging.info(f"Running in {OPERATION_MODE} mode - RFID hardware {status_msg}")'
    
# Use regex to find and replace the problematic line
new_content = re.sub(pattern, replacement, content)

# If nothing changed, try a more flexible pattern
if new_content == content:
    print("Using alternative pattern matching for f-string fix...")
    
    # Read the file line by line
    with open('rfid_control.py', 'r') as file:
        lines = file.readlines()
    
    # Scan for the problematic line and replace it
    for i, line in enumerate(lines):
        if 'logging.info(f"Running in {OPERATION_MODE} mode - RFID hardware {' in line:
            # Split into multiple lines for clarity
            lines[i] = '    status_msg = "will be used but not required" if PROTOTYPE_MODE else "will not be used"\n'
            lines.insert(i + 1, '    logging.info(f"Running in {OPERATION_MODE} mode - RFID hardware {status_msg}")\n')
            break
    
    # Rebuild the content
    new_content = ''.join(lines)

# Write the modified content back to the file
with open('rfid_control.py', 'w') as file:
    file.write(new_content)

print("Fixed rfid_control.py successfully!")
