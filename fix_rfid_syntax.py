#!/usr/bin/env python3
"""
Fix script for rfid_control.py
Cleans up syntax errors and removes duplicate code
"""
import os
import re

# Path to the file
file_path = 'rfid_control.py'

print(f"Fixing {file_path}...")

# Read the file content
with open(file_path, 'r') as file:
    content = file.read()

# Remove the copilot editing tag and everything after it
pattern = r'</copilot-edited-file>.*'
clean_content = re.sub(pattern, '', content, flags=re.DOTALL)

# Remove duplicate status_msg lines
pattern = r'(status_msg = "will be used but not required" if PROTOTYPE_MODE else "will not be used"\n)\s*status_msg = "will be used but not required" if PROTOTYPE_MODE else "will not be used"\n\s*status_msg = "will be used but not required" if PROTOTYPE_MODE else "will not be used"'
clean_content = re.sub(pattern, r'\1', clean_content)

# Write the fixed content back to the file
with open(file_path, 'w') as file:
    file.write(clean_content)

print(f"{file_path} has been fixed.")
