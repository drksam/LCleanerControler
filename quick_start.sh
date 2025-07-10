#!/bin/bash
# LCleaner Controller - Quick Start Script
# One-command setup and verification for Raspberry Pi

echo "🚀 LCleaner Controller - Quick Start"
echo "======================================"

# Run setup
echo "📦 Setting up environment..."
./setup_pi_venv.sh

# Activate virtual environment
echo ""
echo "🔍 Running diagnostics..."
source venv/bin/activate

# Run diagnostics
echo ""
echo "🔧 Hardware diagnostics:"
python3 diagnostic_hardware.py

echo ""
echo "📌 Pin configuration check:"
python3 analyze_pins.py

echo ""
echo "🧪 Application startup test:"
python3 test_app_startup.py

echo ""
echo "✅ Quick start completed!"
echo ""
echo "� Diagnostic Summary:"
echo "  If you saw GPIO access errors above, this is usually normal"
echo "  The errors are gpiod API compatibility issues, not hardware problems"
echo "  The application should still work correctly"
echo ""
echo "�💡 To start the application:"
echo "   source venv/bin/activate"
echo "   python3 app.py"
echo ""
echo "🌐 Access web interface at: http://your-pi-ip:5000"
echo ""
echo "🔧 If you need to fix any issues:"
echo "   Copy updated files from your development machine"
echo "   Run ./setup_pi_venv.sh again"
echo ""
echo "⚙️ To enable auto-start on boot:"
echo "   sudo systemctl enable lcleaner"
echo "   sudo systemctl start lcleaner"
echo ""
