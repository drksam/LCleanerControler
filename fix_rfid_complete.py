#!/usr/bin/env python3
"""
This script fixes multiple issues in rfid_control.py:
1. The f-string syntax error around line 31
2. The backtick syntax error around line 553
"""
import os
import re
import shutil

# Create a backup of the original file if it doesn't exist
if os.path.exists('rfid_control.py') and not os.path.exists('rfid_control.py.orig'):
    print("Creating original backup of rfid_control.py as rfid_control.py.orig")
    shutil.copy2('rfid_control.py', 'rfid_control.py.orig')

# If we already have a backup from a previous run, use that to start fresh
if os.path.exists('rfid_control.py.orig'):
    print("Restoring original file from rfid_control.py.orig")
    shutil.copy2('rfid_control.py.orig', 'rfid_control.py')

# Read the file
with open('rfid_control.py', 'r') as f:
    lines = f.readlines()

# Fix 1: The f-string syntax error
for i, line in enumerate(lines):
    if 'logging.info(f"Running in {OPERATION_MODE} mode - RFID hardware {' in line and '"will be used but not required"' in line:
        print(f"Found f-string syntax error at line {i+1}")
        lines[i] = '    status_msg = "will be used but not required" if PROTOTYPE_MODE else "will not be used"\n'
        lines.insert(i+1, '    logging.info(f"Running in {OPERATION_MODE} mode - RFID hardware {status_msg}")\n')
        print("Fixed f-string syntax error")
        break

# Fix 2: Remove any triple backticks from the file
backticks_found = False
for i, line in enumerate(lines):
    if '```' in line:
        print(f"Found backticks at line {i+1}: {line.strip()}")
        lines[i] = line.replace('```', '')
        backticks_found = True

if backticks_found:
    print("Removed backticks from file")
else:
    print("No backticks found in the file content")

# Check for any empty lines at the end that might contain hidden characters
for i in range(len(lines)-1, -1, -1):
    if lines[i].strip() == '':
        print(f"Found possibly problematic empty line at line {i+1}")
        # Keep the line but ensure it's just a clean newline
        lines[i] = '\n'
    else:
        # Stop once we find non-empty lines
        break

# Write back the fixed file
with open('rfid_control.py', 'w') as f:
    f.writelines(lines)

print("Fixed rfid_control.py successfully!")
print("If problems persist, try running: cat -A rfid_control.py | tail -n 10")
print("This will show any hidden/special characters at the end of the file.")
