# LCleanerControler Fixes

This document provides fixes for two critical issues in the LCleanerControler application:

1. **Database binding error**: When running in prototype mode with SQLite, the application fails with `UnboundExecutionError: Bind key 'core' is not in 'SQLALCHEMY_BINDS' config`.

2. **F-string syntax error**: The application fails with a syntax error in `rfid_control.py` due to invalid nesting of curly braces in an f-string.

## How to Apply the Fixes

### Option 1: Using the Fix Script (Recommended)

1. Transfer the `fix_setup.sh` script to your Raspberry Pi:
   ```bash
   scp fix_setup.sh laser@raspberrypi:~/Downloads/LCleanerControler-main/
   ```

2. Connect to your Raspberry Pi via SSH:
   ```bash
   ssh laser@raspberrypi
   ```

3. Navigate to the project directory:
   ```bash
   cd ~/Downloads/LCleanerControler-main/
   ```

4. Make the script executable and run it:
   ```bash
   chmod +x fix_setup.sh
   ./fix_setup.sh
   ```

5. Run the application:
   ```bash
   python3 test_run.py --prototype --debug
   ```

### Option 2: Manual Fixes

If you prefer to make changes manually, follow these steps:

1. Edit `main.py` to add SQLite bindings:
   ```bash
   nano main.py
   ```
   Find the section with PostgreSQL bindings and add the SQLite bindings as shown in the fix script.

2. Edit `rfid_control.py` to fix the f-string syntax error:
   ```bash
   nano rfid_control.py
   ```
   Find the problematic f-string (around line 31) and replace it with:
   ```python
   status_msg = "will be used but not required" if PROTOTYPE_MODE else "will not be used"
   logging.info(f"Running in {OPERATION_MODE} mode - RFID hardware {status_msg}")
   ```

3. Save the files and run the application:
   ```bash
   python3 test_run.py --prototype --debug
   ```

## Technical Details

### Database Binding Fix

The original issue was that models were using bind keys for database schemas, which are not supported in SQLite. The fix adds conditional bindings for SQLite environments.

### F-String Syntax Fix

The f-string error occurs because Python f-strings don't support direct conditional expressions with nested braces. The fix moves the conditional logic outside the f-string for cleaner and more reliable code.

## Additional Notes

- These fixes are specifically for running the application in prototype mode on the Raspberry Pi with SQLite
- The application will continue to work with PostgreSQL in production mode
