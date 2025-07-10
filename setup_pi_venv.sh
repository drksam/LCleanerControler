#!/bin/bash
# LCleaner Controller - Pi Setup Script
# Run this script on the Raspberry Pi after copying files manually

set -e  # Exit on any error

echo "========================================"
echo "LCleaner Controller - Pi Environment Setup"
echo "========================================"

# Check if running on Raspberry Pi
if [[ ! -f /proc/device-tree/model ]] || ! grep -q "Raspberry Pi" /proc/device-tree/model; then
    echo "⚠️  Warning: This doesn't appear to be a Raspberry Pi"
    echo "Continuing anyway..."
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📁 Working directory: $PWD"

# Check for required files
echo "🔍 Checking for required files..."
required_files=("requirements.txt" "app.py" "main.py" "config.py" "machine_config.json")
for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "❌ Missing required file: $file"
        echo "Please ensure all files were copied correctly."
        exit 1
    fi
done
echo "✅ All required files found"

# Check Python version
echo "🐍 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python3:"
    echo "   sudo apt update && sudo apt install -y python3 python3-pip python3-venv"
    exit 1
fi

python_version=$(python3 --version | cut -d' ' -f2)
echo "✅ Python version: $python_version"

# Create virtual environment
VENV_DIR="venv"
echo "🏗️  Setting up Python virtual environment..."

if [[ -d "$VENV_DIR" ]]; then
    echo "   Virtual environment already exists, removing old one..."
    rm -rf "$VENV_DIR"
fi

echo "   Creating new virtual environment..."
python3 -m venv "$VENV_DIR"

echo "   Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "   Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
echo "📦 Installing Python dependencies..."
if [[ -f "requirements.txt" ]]; then
    echo "   Installing from requirements.txt..."
    pip install -r requirements.txt
else
    echo "❌ requirements.txt not found!"
    exit 1
fi

# Install gpioesp custom library if present
echo "🔌 Installing custom GPIO ESP library..."
if [[ -d "gpioesp" ]]; then
    echo "   Installing gpioesp from local directory..."
    cd gpioesp
    pip install -e .
    cd ..
    echo "✅ gpioesp library installed"
else
    echo "⚠️  gpioesp directory not found - ESP32 control may not work"
fi

# Check system packages
echo "🔧 Checking system requirements..."

# Check if user is in required groups
current_user=$(whoami)
echo "   Current user: $current_user"

if ! groups "$current_user" | grep -q gpio; then
    echo "⚠️  User not in 'gpio' group. Adding..."
    sudo usermod -a -G gpio "$current_user"
    echo "   Added to gpio group (requires logout/login to take effect)"
fi

if ! groups "$current_user" | grep -q dialout; then
    echo "⚠️  User not in 'dialout' group. Adding..."
    sudo usermod -a -G dialout "$current_user"
    echo "   Added to dialout group (requires logout/login to take effect)"
fi

# Check for required system packages
echo "   Checking system packages..."
required_packages=("python3-gpiod" "python3-serial")
missing_packages=()

for package in "${required_packages[@]}"; do
    if ! dpkg -l | grep -q "^ii.*$package"; then
        missing_packages+=("$package")
    fi
done

if [[ ${#missing_packages[@]} -gt 0 ]]; then
    echo "⚠️  Missing system packages: ${missing_packages[*]}"
    echo "   Installing..."
    sudo apt update
    sudo apt install -y "${missing_packages[@]}"
fi

# Check interfaces (SPI, 1-Wire, etc.)
echo "🔌 Checking hardware interfaces..."

if ! grep -q "^spi=on" /boot/config.txt 2>/dev/null; then
    echo "⚠️  SPI interface not enabled. Enabling..."
    echo "spi=on" | sudo tee -a /boot/config.txt
    echo "   SPI enabled (requires reboot)"
    REBOOT_REQUIRED=true
fi

if ! grep -q "^dtoverlay=w1-gpio" /boot/config.txt 2>/dev/null; then
    echo "⚠️  1-Wire interface not enabled. Enabling..."
    echo "dtoverlay=w1-gpio" | sudo tee -a /boot/config.txt
    echo "   1-Wire enabled (requires reboot)"
    REBOOT_REQUIRED=true
fi

# Set executable permissions
echo "🔐 Setting executable permissions..."
chmod +x *.py 2>/dev/null || true
chmod +x *.sh 2>/dev/null || true

# Create systemd service
echo "⚙️  Creating systemd service..."
SERVICE_FILE="/etc/systemd/system/lcleaner.service"
cat > /tmp/lcleaner.service << EOF
[Unit]
Description=LCleaner Controller
After=network.target

[Service]
Type=simple
User=$current_user
WorkingDirectory=$PWD
Environment=PATH=$PWD/venv/bin
ExecStart=$PWD/venv/bin/python app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

if [[ -f "$SERVICE_FILE" ]]; then
    echo "   Updating existing service..."
    sudo cp /tmp/lcleaner.service "$SERVICE_FILE"
else
    echo "   Creating new service..."
    sudo mv /tmp/lcleaner.service "$SERVICE_FILE"
fi

sudo systemctl daemon-reload
echo "   Service created (use 'sudo systemctl enable lcleaner' to auto-start)"

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Run diagnostics: python3 diagnostic_hardware.py"
echo "   2. Test the application: python3 app.py"
echo "   3. Enable auto-start: sudo systemctl enable lcleaner"
echo ""

if [[ "$REBOOT_REQUIRED" == "true" ]]; then
    echo "⚠️  REBOOT REQUIRED to enable hardware interfaces!"
    echo "   Run: sudo reboot"
    echo ""
fi

echo "🎯 Quick test commands:"
echo "   source venv/bin/activate"
echo "   python3 diagnostic_hardware.py"
echo "   python3 analyze_pins.py"
echo ""
