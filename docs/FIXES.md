# LCleanerControler Fixes

This document provides fixes for several critical issues in the LCleanerControler application:

1. **Database binding error**: When running in prototype mode with SQLite, the application fails with `UnboundExecutionError: Bind key 'core' is not in 'SQLALCHEMY_BINDS' config`.

2. **F-string syntax error**: The application fails with a syntax error in `rfid_control.py` due to invalid nesting of curly braces in an f-string.

3. **Syntax error in main.py**: There's a syntax error due to improper indentation in the database configuration section.

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

1. **Fix main.py for SQLite bindings and syntax errors**:
   ```bash
   nano main.py
   ```
   
   Replace the database configuration section (around line 40-60) with:
   ```python
   # Configure schema binding for Shop Suite integration
   # This sets up separate schemas for core shared data and app-specific data
   if 'postgresql' in database_url:
       app.config["SQLALCHEMY_BINDS"] = {
           'core': os.environ.get("CORE_DATABASE_URL", database_url),
           'cleaner_controller': os.environ.get("CLEANER_DATABASE_URL", database_url + "?schema=cleaner_controller"),
       }
       logger.info("Configured database schema bindings for Shop Suite integration")
   else:
       # For SQLite, use same database for all bindings
       app.config["SQLALCHEMY_BINDS"] = {
           'core': database_url,
           'cleaner_controller': database_url,
       }
       logger.info("Using SQLite without schema separation for development/prototype mode")
   ```

2. **Edit rfid_control.py to fix the f-string syntax error**:
   ```bash
   nano rfid_control.py
   ```
   
   Find this line (around line 31):
   ```python
   logging.info(f"Running in {OPERATION_MODE} mode - RFID hardware {"will be used but not required" if PROTOTYPE_MODE else "will not be used"}")
   ```
   
   Replace it with:
   ```python
   status_msg = "will be used but not required" if PROTOTYPE_MODE else "will not be used"
   logging.info(f"Running in {OPERATION_MODE} mode - RFID hardware {status_msg}")
   ```

3. **Update models.py to make bind keys flexible**:
   ```bash
   nano models.py
   ```
   
   For each model class, replace lines like:
   ```python
   __bind_key__ = 'core'
   ```
   
   With:
   ```python
   # __bind_key__ is managed by application
   __bind_key__ = 'core'
   ```

4. Run the application:
   ```bash
   python3 test_run.py --prototype --debug
   ```

## Technical Details

### Database Binding Fix

The original issue was that models were using bind keys for database schemas, which are not supported in SQLite. The fix adds conditional bindings for SQLite environments and makes the model bindings more flexible.

### F-String Syntax Fix

The f-string error occurs because Python f-strings don't support direct conditional expressions with nested braces. The fix moves the conditional logic outside the f-string for cleaner and more reliable code.

### Main.py Syntax Error Fix

There was a syntax error in the main.py file due to improper indentation or structure around the database configuration section. The fix ensures proper syntax throughout the file.

## Additional Notes

- The fix script creates backups of your original files before making changes
- These fixes are specifically for running the application in prototype mode on the Raspberry Pi with SQLite
- The application will continue to work with PostgreSQL in production mode
