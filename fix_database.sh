#!/bin/bash
# Database migration script for Raspberry Pi

echo "🗄️  LCleaner Database Migration"
echo "=" * 50

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run this script from the LCleanerController directory."
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not detected. Activating..."
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo "✅ Virtual environment activated"
    else
        echo "❌ Virtual environment not found. Please create one first:"
        echo "  python -m venv venv"
        echo "  source venv/bin/activate"
        exit 1
    fi
fi

echo "🔄 Stopping laser service (if running)..."
sudo systemctl stop nooyen-laser.service 2>/dev/null || echo "  (Service not running or not found)"

echo "🔄 Running database migration..."
python migrate_database.py

if [ $? -eq 0 ]; then
    echo "✅ Migration completed successfully!"
    
    echo "🔄 Starting laser service..."
    sudo systemctl start nooyen-laser.service
    
    echo "🎉 All done! The laser system should now track sessions properly."
    echo ""
    echo "🧪 Test the fixes:"
    echo "  1. Access the web interface"
    echo "  2. Log in with RFID"
    echo "  3. Go to Performance page"
    echo "  4. Perform some firing operations"
    echo "  5. Check that session data appears"
else
    echo "❌ Migration failed!"
    echo "  Check the error messages above for details."
fi
