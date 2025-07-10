# LCleaner Controller - Manual Deployment Guide

## 📋 Overview

This guide explains how to manually deploy the LCleaner Controller to your Raspberry Pi by copying files instead of using SSH scripts.

## 🎯 Deployment Process

### Step 1: Prepare Deployment Folder (on Development Machine)

1. **Run the preparation script** (Windows):
   ```batch
   prepare_deployment.bat
   ```

2. **Or manually copy files** if needed:
   - Copy all `.py`, `.txt`, `.json`, `.md`, `.service` files
   - Copy `templates/`, `static/`, `gpioesp/`, `instance/`, `tests/` folders
   - Copy deployment scripts from this folder

### Step 2: Copy Files to Raspberry Pi

Choose your preferred method to copy the `pi-deployment/LCleanerController/` folder to your Pi:

#### Option A: USB Drive
1. Copy the `LCleanerController` folder to a USB drive
2. Insert USB drive into Raspberry Pi
3. Copy folder to Pi home directory:
   ```bash
   cp -r /media/*/LCleanerController ~/
   ```

#### Option B: Network Share/SCP
1. **SCP (if SSH is available):**
   ```bash
   scp -r pi-deployment/LCleanerController/ pi@your-pi-ip:~/
   ```

2. **Network share:** Copy via file explorer to shared network folder

#### Option C: Cloud Storage
1. Upload `LCleanerController` folder to cloud storage (Google Drive, Dropbox, etc.)
2. Download on Pi using web browser or command line tools

### Step 3: Setup on Raspberry Pi

1. **SSH or use terminal on Pi:**
   ```bash
   cd ~/LCleanerController
   ```

2. **Make scripts executable:**
   ```bash
   chmod +x *.sh
   ```

3. **Run quick setup:**
   ```bash
   ./quick_start.sh
   ```

   **Or run setup manually:**
   ```bash
   ./setup_pi_venv.sh
   ```

## 🔧 What the Setup Scripts Do

### `setup_pi_venv.sh`
- ✅ Creates Python virtual environment
- ✅ Installs all dependencies from `requirements.txt`
- ✅ Installs custom `gpioesp` library for ESP32 control
- ✅ Adds user to required groups (`gpio`, `dialout`)
- ✅ Enables hardware interfaces (SPI, 1-Wire)
- ✅ Creates systemd service for auto-start
- ✅ Sets proper file permissions

### `quick_start.sh`
- 🚀 Runs `setup_pi_venv.sh`
- 🔍 Runs hardware diagnostics
- 📌 Verifies pin configuration
- 📋 Shows next steps

## 🏗️ Manual Setup Steps (if scripts fail)

### 1. Install System Requirements
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-gpiod python3-serial
```

### 2. Enable Hardware Interfaces
```bash
# Enable SPI and 1-Wire
sudo raspi-config
# Or manually edit /boot/config.txt:
echo "spi=on" | sudo tee -a /boot/config.txt
echo "dtoverlay=w1-gpio" | sudo tee -a /boot/config.txt
```

### 3. Add User to Groups
```bash
sudo usermod -a -G gpio,dialout $USER
# Logout and login again for groups to take effect
```

### 4. Create Virtual Environment
```bash
cd ~/LCleanerController
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Install Custom GPIO Library
```bash
cd gpioesp
pip install -e .
cd ..
```

## 🔍 Verification

### Run Diagnostics
```bash
source venv/bin/activate
python3 diagnostic_hardware.py
python3 analyze_pins.py
```

### Test Application
```bash
python3 app.py
```

### Enable Auto-Start
```bash
sudo systemctl enable lcleaner
sudo systemctl start lcleaner
```

## 📁 Deployment Folder Structure

```
pi-deployment/
└── LCleanerController/
    ├── setup_pi_venv.sh      # Main setup script
    ├── quick_start.sh        # One-command setup
    ├── DEPLOYMENT_GUIDE.md   # This file
    ├── app.py                # Main application
    ├── main.py               # Application entry point
    ├── config.py             # Configuration
    ├── machine_config.json   # Hardware config
    ├── requirements.txt      # Python dependencies
    ├── diagnostic_hardware.py # Hardware diagnostics
    ├── analyze_pins.py       # Pin verification
    ├── Default pinout.txt    # Pin reference
    ├── README.md             # Project documentation
    ├── gpioesp/              # Custom ESP32 library
    ├── templates/            # Web interface templates
    ├── static/               # Static web files
    ├── instance/             # Database files
    └── tests/                # Test files
```

## 🚨 Troubleshooting

### Permission Errors
```bash
# Fix file permissions
chmod +x *.sh
chmod +x *.py

# Check user groups
groups
# Should include: gpio, dialout
```

### Missing Dependencies
```bash
# Install system packages
sudo apt install -y python3-gpiod python3-serial

# Reinstall Python packages
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### Hardware Interface Issues
```bash
# Check enabled interfaces
sudo raspi-config
# Go to Interface Options → Enable SPI, 1-Wire

# Or check config file
grep -E "(spi|w1)" /boot/config.txt
```

### GPIO Access Issues
```bash
# Check GPIO chip access
ls -l /dev/gpiochip*

# Check current user groups
groups $USER

# Add to groups if missing
sudo usermod -a -G gpio,dialout $USER
```

## 🚨 Common GPIO Issues & Fixes

### Issue: GPIO Access Warnings During Diagnostics

If you see warnings like:
- GPIO API compatibility issues
- "will use simulation mode"
- gpiod version conflicts

**These are normal and don't prevent the application from working.**

### Why This Happens:
- Different gpiod library versions (v1.x vs v2.x) have different APIs
- The application automatically detects and handles this
- It gracefully falls back to simulation mode if needed
- Your application will still work correctly

### Simple Fix Process:
```bash
# If you need to update/fix anything:
# 1. On your development machine, run:
prepare_deployment.bat

# 2. Copy the updated pi-deployment/LCleanerController/ folder to Pi again
# 3. On the Pi, run setup again:
cd ~/LCleanerController
./setup_pi_venv.sh

# 4. Test again:
python3 diagnostic_hardware.py
```

### No Need for Complex Fix Scripts!
The beauty of manual deployment is: **just copy the files again** if you need to fix anything. All fixes go into the main codebase and get deployed together.

## ✅ Success Checklist

- [ ] Files copied to Pi successfully
- [ ] Setup script completed without errors
- [ ] User added to gpio and dialout groups
- [ ] Hardware interfaces enabled (SPI, 1-Wire)
- [ ] Virtual environment created and activated
- [ ] All dependencies installed
- [ ] Custom gpioesp library installed
- [ ] Diagnostic scripts run successfully
- [ ] Application starts without errors
- [ ] Systemd service created (optional)

## 📞 Need Help?

If you encounter issues:

1. **Check logs:** `journalctl -u lcleaner` (if using systemd service)
2. **Run diagnostics:** `python3 diagnostic_hardware.py`
3. **Verify setup:** `python3 analyze_pins.py`
4. **Check permissions:** `groups` and `ls -l /dev/gpiochip*`
5. **Review configuration:** Check `machine_config.json` and `config.py`

---

**Last Updated:** 2025-07-01
**Deployment Method:** Manual file copy with automated setup scripts
