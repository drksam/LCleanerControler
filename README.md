# ShopLaserRoom Control System v2.0.2

## 🚀 Quick Start - Manual Deployment

**This folder is ready for manual deployment to your Raspberry Pi.**

### 1. Copy this entire folder to your Pi:
- **USB Drive**: Copy folder to USB → Insert in Pi → Copy to Pi home directory
- **Network Share**: Copy via file explorer
- **SCP**: `scp -r LCleanerController/ pi@your-pi:~/`
- **Cloud Storage**: Upload to cloud → Download on Pi

### 2. One-command setup on Pi:
```bash
cd ~/LCleanerController
chmod +x *.sh
./quick_start.sh
```

### 3. Verify and test:
```bash
# Check hardware
python3 diagnostic_hardware.py

# Start application  
python3 app.py
```

**📖 For detailed instructions, see `DEPLOYMENT_GUIDE.md`**

---

## Overview
This is a sophisticated Raspberry Pi 5 control system for the ShopLaserRoom laser cleaning machine. 
It provides a touchscreen web-based GUI for controlling the cleaning head movement, trigger servo for firing the laser, 
and various auxiliary functions such as fan control, red lights, and table movement.

## Key Features
- Full control of stepper motor for cleaning head positioning
- Servo control for laser trigger activation
- Fan and warning light control
- Safety temperature monitoring system
- RFID access control integration
- Comprehensive statistics tracking
- Sequence programming for automated operations
- Detailed GPIO pinout reference

## New in Version 2.0.2
- Completely removed gpiozero dependency, replaced with gpiod and custom GPIO wrapper
- Enhanced compatibility with Raspberry Pi 5 GPIO architecture
- Fixed JavaScript syntax errors in the web interface
- Improved error handling and robustness in GPIO access
- Consolidated GPIO control methods for better maintainability
- Added support for running in testing/development environments

## New in Version 2.0.0
- Added support for GPIOController-based implementations, resolving Raspberry Pi 5 GPIO issues
- Updated stepper control to support both GPIOController and fallback implementations
- Updated servo control to support both implementations with enhanced features
- Fixed various issues with output status reporting
- Added safety measures to prevent application crashes
- Improved simulation mode for GPIOController fallback
- Enhanced robustness of system with conditional code paths

## Hardware Requirements
- Raspberry Pi 5 (recommended) or Raspberry Pi 4B
- Stepper motor for cleaning head movement
- Servo motor for laser trigger
- Optional: MFRC522 RFID reader for access control
- Optional: DS18B20 temperature sensors

## Project Structure

```
LCleanerController/
├── 📁 deploy/                    # SSH-based deployment tools (optional)
│   ├── deploy_to_pi.ps1/.sh     # Automated deployment scripts
│   ├── verify_pi_setup.py       # Pi readiness verification
│   ├── diagnostic_hardware.py   # Hardware testing and diagnostics
│   └── README.md                # SSH deployment guide
├── 📁 pi-deployment/             # Complete deployable package (recommended)
│   ├── All application files    # Ready-to-copy folder with everything
│   ├── setup_pi_venv.sh         # Virtual environment setup
│   ├── quick_start.sh           # One-command setup and start
│   ├── gpioesp/                 # ESP32 communication package
│   └── DEPLOYMENT_GUIDE.md      # Manual deployment instructions
├── 📁 Archive/                   # Archived files and backups
├── 📁 docs/                      # Documentation
├── 📁 static/                    # Web interface assets
├── 📁 templates/                 # Web interface templates
├── 📁 instance/                  # Database files
├── app.py                       # Main Flask application
├── config.py                    # Configuration management
├── models.py                    # Database models
├── machine_config.json          # Hardware configuration
├── Default pinout.txt           # GPIO pin reference
├── requirements.txt             # Python dependencies
├── prepare_deployment.bat       # Updates pi-deployment folder
└── README.md                    # This file
```

## Quick Start for Deployment

### 🚀 Manual Deployment (Recommended)

The easiest and most reliable deployment method:

1. **Prepare deployment folder:**
   ```bash
   # Windows:
   prepare_deployment.bat
   
   # This creates/updates the pi-deployment folder with all necessary files
   ```

2. **Copy to Raspberry Pi:**
   - Copy the entire `pi-deployment` folder to your Pi using any method:
     - USB drive (most reliable)
     - Network file share
     - SCP/FTP if you have basic file access
     - Cloud storage (upload from PC, download on Pi)

3. **Setup on the Pi:**
   ```bash
   cd /path/to/pi-deployment  # wherever you copied the folder
   ./quick_start.sh           # One command setup and start
   ```

### 🎯 Alternative: Automated SSH Deployment

If you prefer automated deployment and have SSH working:

```bash
cd deploy/
# For Windows:
.\deploy_to_pi.ps1 your-username@your-pi-ip
# For Linux/Mac:
./deploy_to_pi.sh your-username@your-pi-ip
```

Then on the Pi:
```bash
cd ~/LCleanerController
./setup_pi_venv.sh
source ~/lcleaner-env/bin/activate
python3 verify_pi_setup.py
python3 diagnostic_hardware.py
python3 app.py
```

### ⚡ Key Dependencies

- **Custom gpioctrl package**: Essential for ESP32 stepper/servo control (auto-installed from `gpioesp/`)
- **Virtual environment**: Required for modern Pi OS PEP 668 compliance
- **Hardware interfaces**: SPI (RFID), 1-Wire (temperature), GPIO (local control)

## Detailed Installation Instructions

### 1. Basic System Setup
1. Start with a fresh installation of Raspberry Pi OS Bookworm or newer
2. Update your system:
   ```
   sudo apt update
   sudo apt upgrade -y
   ```
3. Install required system dependencies:
   ```
   sudo apt install -y python3-pip python3-dev postgresql libpq-dev nginx
   ```

### 2. Install Python Dependencies
Install the required Python packages:
```
sudo pip3 install flask==2.3.3 flask-login==0.6.2 flask-sqlalchemy==3.1.1 flask-wtf==1.2.1 
sudo pip3 install gunicorn==21.2.0 psycopg2-binary==2.9.9 werkzeug==2.3.7 email-validator==2.1.0
sudo pip3 install requests==2.31.0 gpiod==1.5.3 mfrc522==0.0.7
```

### 3. Prepare PostgreSQL Database
1. Install and configure PostgreSQL:
   ```
   sudo apt install -y postgresql postgresql-contrib
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```
2. Create a database and user:
   ```
   sudo -u postgres psql -c "CREATE USER Shop WITH PASSWORD 'your_secure_password';"
   sudo -u postgres psql -c "CREATE DATABASE Shoplaser OWNER Shop;"
   sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE Shoplaser TO Shop;"
   ```

### 4. Application Installation
1. Unzip the ShopLaserRoom package to /opt:
   ```
   sudo mkdir -p /opt/Shoplaser
   sudo unzip Shoplaser_v2.0.0.zip -d /opt/Shoplaser
   cd /opt/Shoplaser
   ```
2. Set proper permissions:
   ```
   sudo chown -R pi:pi /opt/Shoplaser  # Use appropriate username instead of 'pi'
   ```
3. Configure the database connection in machine_config.json:
   ```json
   "database": {
     "url": "postgresql://Shop:your_secure_password@localhost/Shoplaser"
   }
   ```

### 5. Setup SystemD Service
1. Install the service file:
   ```
   sudo cp Shop-laser.service /etc/systemd/system/
   sudo systemctl daemon-reload
   ```
2. Enable and start the service:
   ```
   sudo systemctl enable Shop-laser.service
   sudo systemctl start Shop-laser.service
   ```
3. Check service status:
   ```
   sudo systemctl status Shop-laser.service
   ```

### 6. Configure Nginx as Reverse Proxy (Optional, recommended for production)
1. Install Nginx:
   ```
   sudo apt install -y nginx
   ```
2. Create a configuration file:
   ```
   sudo nano /etc/nginx/sites-available/Shoplaser
   ```
3. Add the following configuration:
   ```
   server {
       listen 80;
       server_name your_server_name_or_ip;
   
       location / {
           proxy_pass http://localhost:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```
4. Enable the site and restart Nginx:
   ```
   sudo ln -s /etc/nginx/sites-available/Shoplaser /etc/nginx/sites-enabled
   sudo nginx -t
   sudo systemctl restart nginx
   ```

### 7. Hardware Connection Setup
1. Stepper Motor Connection:
   - Connect stepper driver STEP pin to GPIO pin specified in machine_config.json (default GPIO 17)
   - Connect stepper driver DIR pin to GPIO pin specified in machine_config.json (default GPIO 18)
   - Connect stepper driver ENABLE pin to GPIO pin specified in machine_config.json (default GPIO 4)

2. Servo Connection:
   - Connect servo signal pin to GPIO pin specified in machine_config.json (default GPIO 12)
   - Connect servo power to 5V (NOT from Raspberry Pi for high-torque servos)
   - Connect servo ground to Raspberry Pi ground

3. Temperature Sensors:
   - Connect DS18B20 sensors to GPIO4
   - Enable 1-Wire interface using raspi-config: `sudo raspi-config` → Interfaces → 1-Wire → Enable

4. RFID Reader Connection:
   - Connect MFRC522 module to SPI pins:
     - MFRC522 SDA → GPIO8 (SPI CE0)
     - MFRC522 SCK → GPIO11 (SPI SCLK)
     - MFRC522 MOSI → GPIO10 (SPI MOSI)
     - MFRC522 MISO → GPIO9 (SPI MISO)
     - MFRC522 RST → GPIO25 (configurable)
     - MFRC522 GND → GND
     - MFRC522 3.3V → 3.3V

## Running in Different Operational Modes
The system can operate in three modes, selectable in the Settings page:

### Simulation Mode
- No physical hardware needed
- All operations simulated for development and testing
- Enable by setting "operation_mode": "simulation" in machine_config.json

### Prototype/Debug Mode
- All hardware operations enabled with enhanced logging
- Enable by setting "operation_mode": "prototype" in machine_config.json
- Set "debug_level": "debug" for maximum logging detail

### Normal Production Mode
- Optimized performance with minimal logging
- Enable by setting "operation_mode": "normal" in machine_config.json
- Set "debug_level": "info" for standard operational logging

## Integration with ShopMachineMonitor
This system is designed to integrate with the ShopMachineMonitor central monitoring server for:
- User authentication
- Machine access control
- Operation logging
- Maintenance scheduling

To configure integration, update the RFID section in machine_config.json with the appropriate authentication server URL.

## Testing and Development

### Setting Up a Virtual Environment for Testing
To test the system without affecting your system-wide Python environment:

1. Create a virtual environment:
   ```
   python -m venv venv
   ```

2. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On Linux/macOS:
     ```
     source venv/bin/activate
     ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

### Running test_run.py
The `test_run.py` script allows you to test various components of the system in isolation:

1. Activate your virtual environment (if not already activated).

2. Run the test script:
   ```
   python test_run.py
   ```

3. Follow the on-screen menu to select which component to test:
   - Stepper motor
   - Servo control
   - GPIO outputs (fan, lights, table control)
   - Temperature sensors
   - RFID reader

4. The test script will run in simulation mode by default if no hardware is detected.

5. To force hardware mode (when hardware is present):
   ```
   FORCE_HARDWARE=true python test_run.py
   ```

### Development in Windows Environment
For development on Windows where Raspberry Pi hardware is not available:

1. Set up the virtual environment as described above.

2. Run in simulation mode:
   ```
   SIMULATION_MODE=true python app.py
   ```

3. Access the web interface at http://localhost:5000

## Troubleshooting
### GPIO Access Issues
If you encounter GPIO access issues:
1. Ensure your user is in the gpio group: `sudo usermod -a -G gpio,spi,i2c your_username`
2. For Raspberry Pi 5 specifically, the system now uses gpiod library instead of gpiozero
3. Check connections and pin numbers in machine_config.json
4. For persistent issues, set "simulation_mode": true in the respective component sections for testing
5. If you need to test on Windows or non-Pi Linux systems, use the simulation mode

### Database Connection Issues
If database connection fails:
1. Verify PostgreSQL is running: `sudo systemctl status postgresql`
2. Check connection details in machine_config.json
3. Test connection manually: `psql -U Shop -W Shoplaser`
4. Check logs for specific errors: `journalctl -u Shop-laser.service`

## Support
For support or more information, contact the project team through the ShopTracker portal or submit an issue on GitHub.

---

## Redeployment Instructions

### 4. Need to fix anything? Just redeploy:
```bash
# On development machine:
prepare_deployment.bat

# Copy updated LCleanerController folder to Pi again
# Then on Pi, run setup again:
cd ~/LCleanerController
./setup_pi_venv.sh
```

**💡 No complex fix scripts needed - just copy files again!**
