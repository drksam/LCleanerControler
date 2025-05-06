# NooyenLaserRoom Control System v2.0.1

## Overview
This is a sophisticated Raspberry Pi 5 control system for the NooyenLaserRoom laser cleaning machine. 
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
sudo pip3 install requests==2.31.0 gpiozero==2.0 gpiod==1.5.3 mfrc522==0.0.7
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
   sudo -u postgres psql -c "CREATE USER nooyen WITH PASSWORD 'your_secure_password';"
   sudo -u postgres psql -c "CREATE DATABASE nooyenlaser OWNER nooyen;"
   sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE nooyenlaser TO nooyen;"
   ```

### 4. Application Installation
1. Unzip the NooyenLaserRoom package to /opt:
   ```
   sudo mkdir -p /opt/nooyenlaser
   sudo unzip nooyenlaser_v2.0.0.zip -d /opt/nooyenlaser
   cd /opt/nooyenlaser
   ```
2. Set proper permissions:
   ```
   sudo chown -R pi:pi /opt/nooyenlaser  # Use appropriate username instead of 'pi'
   ```
3. Configure the database connection in machine_config.json:
   ```json
   "database": {
     "url": "postgresql://nooyen:your_secure_password@localhost/nooyenlaser"
   }
   ```

### 5. Setup SystemD Service
1. Install the service file:
   ```
   sudo cp nooyen-laser.service /etc/systemd/system/
   sudo systemctl daemon-reload
   ```
2. Enable and start the service:
   ```
   sudo systemctl enable nooyen-laser.service
   sudo systemctl start nooyen-laser.service
   ```
3. Check service status:
   ```
   sudo systemctl status nooyen-laser.service
   ```

### 6. Configure Nginx as Reverse Proxy (Optional, recommended for production)
1. Install Nginx:
   ```
   sudo apt install -y nginx
   ```
2. Create a configuration file:
   ```
   sudo nano /etc/nginx/sites-available/nooyenlaser
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
   sudo ln -s /etc/nginx/sites-available/nooyenlaser /etc/nginx/sites-enabled
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

## Integration with NooyenMachineMonitor
This system is designed to integrate with the NooyenMachineMonitor central monitoring server for:
- User authentication
- Machine access control
- Operation logging
- Maintenance scheduling

To configure integration, update the RFID section in machine_config.json with the appropriate authentication server URL.

## Troubleshooting
### GPIO Access Issues
If you encounter GPIO access issues:
1. Ensure your user is in the gpio group: `sudo usermod -a -G gpio,spi,i2c your_username`
2. For Raspberry Pi 5 specifically, use the provided GPIOController approach in Settings
3. Check connections and pin numbers in machine_config.json
4. For persistent issues, set "simulation_mode": true in the respective component sections for testing

### Database Connection Issues
If database connection fails:
1. Verify PostgreSQL is running: `sudo systemctl status postgresql`
2. Check connection details in machine_config.json
3. Test connection manually: `psql -U nooyen -W nooyenlaser`
4. Check logs for specific errors: `journalctl -u nooyen-laser.service`

## Support
For support or more information, contact the project team through the NooyenUSATracker portal.
