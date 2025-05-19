#!/usr/bin/env python3
"""
This script examines rfid_control.py to find syntax errors
"""
import os

# Check if the file exists
if not os.path.exists('rfid_control.py'):
    print("Error: rfid_control.py not found!")
    exit(1)

# Read the entire file
with open('rfid_control.py', 'r') as f:
    lines = f.readlines()

# Print last 30 lines with line numbers for inspection
print(f"Total lines in file: {len(lines)}")
print("\nLast 30 lines:")
for i, line in enumerate(lines[-30:], start=len(lines)-29):
    print(f"{i}: {line.rstrip()}")

# Look for backticks in the file
print("\nSearching for backticks (```) in the file...")
backticks_found = False
for i, line in enumerate(lines, start=1):
    if "```" in line:
        print(f"Found backticks at line {i}: {line.strip()}")
        backticks_found = True

if not backticks_found:
    print("No backticks found in the file.")

# Check specifically around line 553
target_line = 553
start_line = max(1, target_line - 5)
end_line = min(len(lines), target_line + 5)
print(f"\nLines {start_line}-{end_line} (around line {target_line}):")
for i in range(start_line-1, end_line):
    if i < len(lines):
        print(f"{i+1}: {lines[i].rstrip()}")
    else:
        print(f"{i+1}: <beyond end of file>")

# Write a fixed version without any backticks or markdown
print("\nCreating clean version of the file...")
with open('rfid_control.py.clean', 'w') as f:
    for line in lines:
        # Remove any markdown backticks
        clean_line = line.replace('```', '')
        f.write(clean_line)

print("Clean version saved as rfid_control.py.clean")
print("To apply the fix, run: mv rfid_control.py.clean rfid_control.py")
