#!/usr/bin/env python3
"""
This script modifies models.py to make bindings more flexible for SQLite support
"""
import os
import re
import shutil

# Create a backup of the original file
if os.path.exists('models.py'):
    print("Creating backup of models.py as models.py.bak")
    shutil.copy2('models.py', 'models.py.bak')

# Read the file content
with open('models.py', 'r') as file:
    content = file.read()

# Update all bind keys to be more flexible
patterns = [
    (r'__bind_key__ = \'core\'', '# Bind key is managed by application\n    __bind_key__ = \'core\''),
    (r'__bind_key__ = \'cleaner_controller\'', '# Bind key is managed by application\n    __bind_key__ = \'cleaner_controller\''),
]

# Apply all replacements
for pattern, replacement in patterns:
    content = re.sub(pattern, replacement, content)

# Write the modified content back
with open('models.py', 'w') as file:
    file.write(content)

print("Fixed models.py successfully!")
