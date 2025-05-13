#!/bin/bash

# Fix script for LCleanerControler database binding and f-string errors
echo "Applying fixes to LCleanerControler..."

# Fix 1: Update main.py to handle SQLite bindings
sed -i '/if .*postgresql.* in database_url:/,/logger.info("Configured database schema bindings for Shop Suite integration")/ c\
# Configure schema binding for Shop Suite integration\
# This sets up separate schemas for core shared data and app-specific data\
if '"'"'postgresql'"'"' in database_url:\
    app.config["SQLALCHEMY_BINDS"] = {\
        '"'"'core'"'"': os.environ.get("CORE_DATABASE_URL", database_url),\
        '"'"'cleaner_controller'"'"': os.environ.get("CLEANER_DATABASE_URL", database_url + "?schema=cleaner_controller"),\
    }\
    logger.info("Configured database schema bindings for Shop Suite integration")\
else:\
    # For SQLite, use same database for all bindings\
    app.config["SQLALCHEMY_BINDS"] = {\
        '"'"'core'"'"': database_url,\
        '"'"'cleaner_controller'"'"': database_url,\
    }\
    logger.info("Using SQLite without schema separation for development/prototype mode")' main.py

# Fix 2: Update rfid_control.py to fix f-string syntax error
sed -i 's/logging.info(f"Running in {OPERATION_MODE} mode - RFID hardware {"will be used but not required" if PROTOTYPE_MODE else "will not be used"}")/status_msg = "will be used but not required" if PROTOTYPE_MODE else "will not be used"\n    logging.info(f"Running in {OPERATION_MODE} mode - RFID hardware {status_msg}")/' rfid_control.py

echo "Fixes applied successfully!"
echo "You can now run: python3 test_run.py --prototype --debug"
