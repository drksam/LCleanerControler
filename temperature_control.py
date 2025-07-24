"""
Temperature control module for DS18B20 sensors.
This module provides functionality to read temperatures from DS18B20 sensors
and monitor them for high temperature conditions.
"""
import os
import glob
import time
import logging
import threading
import subprocess
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class TemperatureController:
    """Controller for DS18B20 temperature sensors with high limit monitoring"""

    def __init__(self, temp_config=None, stop_callback=None):
        """
        Initialize the temperature controller
        
        Args:
            temp_config (dict): Configuration for temperature sensors
            stop_callback (function): Callback to stop all operations on high temp
        """
        self.device_folder = None
        self.device_files = []
        self.devices_loaded = False
        self.temperatures = {}  # {device_id: {'temp': float, 'last_reading': timestamp}}
        self.monitoring = False
        self.monitoring_thread = None
        
        # Default configuration
        self.temp_config = temp_config or {
            'high_limit': 50.0,         # Default high temp limit in Celsius
            'sampling_interval': 5.0,   # Seconds between temperature readings
            'enabled': True,            # Temperature monitoring enabled by default
            'device_ids': {},           # Empty device ID mapping
            'w1_gpio_pin': 2           # Default GPIO pin (BCM) for 1-Wire interface
        }
        
        # Register stop callback
        self.stop_callback = stop_callback
        
        # Flag to track if high temp condition is active
        self.high_temp_condition = False
        
        # Try to initialize temperature sensors
        self._initialize_sensors()
        
        # Start monitoring thread if enabled
        if self.temp_config.get('enabled', True) and self.devices_loaded:
            self._start_monitoring()
    
    def _initialize_sensors(self):
        """Initialize DS18B20 temperature sensors"""
        logger.debug("_initialize_sensors called. SIMULATION_MODE=%s", os.environ.get('SIMULATION_MODE'))
        # Check if we're in simulation mode
        if os.environ.get('SIMULATION_MODE') == 'True':
            logger.info("Temperature sensors in simulation mode")
            self.devices_loaded = True
            
            # Get sensor limits from config if available
            sensor_limits = self.temp_config.get('sensor_limits', {})
            global_limit = self.temp_config.get('high_limit', 50.0)
            
            # Get custom sensor names from device_ids config if available
            device_ids = self.temp_config.get('device_ids', {})
            
            # Create fake device IDs for simulation with custom names if defined
            self.temperatures = {
                'simulator1': {
                    'temp': 25.0, 
                    'last_reading': datetime.now(), 
                    'name': device_ids.get('simulator1', 'Control Sensor'),
                    'high_limit': sensor_limits.get('simulator1', global_limit)
                },
                'simulator2': {
                    'temp': 30.0, 
                    'last_reading': datetime.now(), 
                    'name': device_ids.get('simulator2', 'Output Sensor'),
                    'high_limit': sensor_limits.get('simulator2', global_limit)
                }
            }
            
            logger.debug(f"Initialized simulator sensors with names from config: {device_ids}")
            return

        # Try to load the kernel modules needed for 1-Wire (w1) communication on Raspberry Pi
        try:
            w1_gpio_pin = self.temp_config.get('w1_gpio_pin', 2)
            logger.debug(f"Attempting to load w1-gpio on pin {w1_gpio_pin}")
            if w1_gpio_pin != 4:
                subprocess.run(["modprobe", "w1-gpio", f"gpiopin={w1_gpio_pin}"], check=True)
            else:
                subprocess.run(["modprobe", "w1-gpio"], check=True)
            subprocess.run(["modprobe", "w1-therm"], check=True)
            logger.info(f"Loaded 1-Wire modules using GPIO pin {w1_gpio_pin}")
        except Exception as e:
            logger.warning(f"Could not load w1 kernel modules (normal if not on Raspberry Pi): {e}")
        # Try to find DS18B20 sensors
        try:
            base_dir = '/sys/bus/w1/devices/'
            self.device_folder = glob.glob(base_dir + '28*')
            logger.debug(f"Sensor search in {base_dir}: found {self.device_folder}")
            if not self.device_folder:
                logger.error("No DS18B20 temperature sensors found")
                return
            for folder in self.device_folder:
                device_file = folder + '/w1_slave'
                device_id = os.path.basename(folder)
                device_name = self.temp_config.get('device_ids', {}).get(device_id, f"Sensor {device_id}")
                logger.info(f"Initializing temperature sensor {device_id} with name: {device_name}, file: {device_file}")
                self.device_files.append(device_file)
                self.temperatures[device_id] = {
                    'temp': 0.0, 
                    'last_reading': datetime.now(),
                    'name': device_name
                }
            self.devices_loaded = True
            logger.info(f"Found {len(self.device_files)} DS18B20 temperature sensors: {list(self.temperatures.keys())}")
        except Exception as e:
            logger.error(f"Error initializing temperature sensors: {e}")
            self.devices_loaded = False

    def _read_temp_raw(self, device_file):
        """Read raw temperature data from sensor file"""
        try:
            logger.debug(f"Reading raw temperature from {device_file}")
            
            # Check if file exists
            if not os.path.exists(device_file):
                logger.error(f"Temperature sensor file does not exist: {device_file}")
                return None
            
            # Check file permissions
            if not os.access(device_file, os.R_OK):
                logger.error(f"Cannot read temperature sensor file (permissions): {device_file}")
                return None
            
            with open(device_file, 'r') as f:
                lines = f.readlines()
            
            logger.debug(f"Raw lines from {device_file}: {lines}")
            
            # Check if we got any data
            if not lines:
                logger.warning(f"Temperature sensor file is empty: {device_file}")
                return None
                
            return lines
        except Exception as e:
            logger.error(f"Error reading temperature sensor {device_file}: {e}")
            return None

    def _read_temp(self, device_file):
        """Convert raw temperature data to Celsius"""
        if os.environ.get('SIMULATION_MODE') == 'True':
            import random
            return round(25.0 + random.uniform(-2.0, 2.0), 1)
        lines = self._read_temp_raw(device_file)
        if not lines:
            logger.warning(f"No lines read from {device_file}")
            # Try to diagnose the issue
            self._diagnose_sensor_issue(device_file)
            return None
        try:
            if lines[0].strip()[-3:] != 'YES':
                logger.warning(f"CRC check failed for sensor {device_file}: {lines[0].strip()}")
                return None
            equals_pos = lines[1].find('t=')
            if equals_pos == -1:
                logger.warning(f"Temperature reading not found for sensor {device_file}: {lines[1]}")
                return None
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string) / 1000.0
            # logger.info(f"Read temperature {temp_c:.2f}C from {device_file}")  # Commented out to reduce log noise
            return temp_c
        except Exception as e:
            logger.error(f"Error processing temperature data from {device_file}: {e}")
            return None

    def _diagnose_sensor_issue(self, device_file):
        """Diagnose why sensor reading failed"""
        try:
            device_dir = os.path.dirname(device_file)
            device_id = os.path.basename(device_dir)
            
            logger.info(f"Diagnosing sensor issue for {device_id}")
            
            # Check if device directory exists
            if os.path.exists(device_dir):
                logger.info(f"Device directory exists: {device_dir}")
                
                # List files in device directory
                files = os.listdir(device_dir)
                logger.info(f"Files in device directory: {files}")
                
                # Check if w1_slave file exists
                if os.path.exists(device_file):
                    # Get file size
                    file_size = os.path.getsize(device_file)
                    logger.info(f"w1_slave file size: {file_size} bytes")
                    
                    # Try to read file with different method
                    try:
                        with open(device_file, 'rb') as f:
                            raw_data = f.read()
                        logger.info(f"Raw file content (bytes): {raw_data}")
                        logger.info(f"Raw file content (string): {raw_data.decode('utf-8', errors='ignore')}")
                    except Exception as read_error:
                        logger.error(f"Failed to read file with binary mode: {read_error}")
                else:
                    logger.error(f"w1_slave file does not exist: {device_file}")
            else:
                logger.error(f"Device directory does not exist: {device_dir}")
                
            # Check 1-Wire master status
            master_dir = "/sys/bus/w1/devices/w1_bus_master1"
            if os.path.exists(master_dir):
                try:
                    with open(f"{master_dir}/w1_master_slaves", 'r') as f:
                        slaves = f.read().strip()
                    logger.info(f"1-Wire master slaves: {slaves}")
                except Exception as e:
                    logger.error(f"Could not read 1-Wire master slaves: {e}")
            else:
                logger.error("1-Wire master directory not found")
                
        except Exception as e:
            logger.error(f"Error during sensor diagnosis: {e}")

    def _monitor_temperatures(self):
        """Background thread to monitor temperatures"""
        logger.info("Temperature monitoring thread started")
        
        while self.monitoring:
            try:
                self.update_temperatures()
                
                # Check for high temperature condition
                high_temp_detected = False
                high_temp_sensors = []
                
                for device_id, data in self.temperatures.items():
                    # Get sensor-specific limit or fallback to global limit
                    sensor_limits = self.temp_config.get('sensor_limits', {})
                    sensor_high_limit = sensor_limits.get(device_id, self.temp_config.get('high_limit', 50.0))
                    
                    # Store sensor limit in the temperature data for display
                    data['high_limit'] = sensor_high_limit
                    
                    # Check if temperature exceeds the limit
                    if data['temp'] > sensor_high_limit:
                        high_temp_detected = True
                        data['high_temp'] = True
                        high_temp_sensors.append(f"{data['name']} ({data['temp']}°C)")
                    else:
                        data['high_temp'] = False
                
                # Take action if high temperature is detected
                if high_temp_detected and not self.high_temp_condition:
                    self.high_temp_condition = True
                    logger.warning(f"HIGH TEMPERATURE ALERT: {', '.join(high_temp_sensors)}")
                    
                    # Call the stop callback if provided
                    if self.stop_callback:
                        self.stop_callback()
                
                # Reset high temp condition if all temps are now below the limit
                elif not high_temp_detected and self.high_temp_condition:
                    self.high_temp_condition = False
                    logger.info("Temperature returned to normal range")
                
            except Exception as e:
                logger.error(f"Error in temperature monitoring thread: {e}")
            
            # Wait for the next sampling interval
            time.sleep(self.temp_config.get('sampling_interval', 5.0))
    
    def _start_monitoring(self):
        """Start the temperature monitoring thread"""
        if not self.monitoring and self.devices_loaded:
            self.monitoring = True
            self.monitoring_thread = threading.Thread(target=self._monitor_temperatures)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            logger.info("Temperature monitoring started")
            return True
        return False
    
    def _stop_monitoring(self):
        """Stop the temperature monitoring thread"""
        if self.monitoring:
            self.monitoring = False
            # The thread will end on its next iteration
            logger.info("Temperature monitoring stopped")
            return True
        return False
    
    def update_temperatures(self):
        logger.debug("update_temperatures called. devices_loaded=%s", self.devices_loaded)
        if os.environ.get('SIMULATION_MODE') == 'True':
            import random
            for device_id in self.temperatures:
                current = self.temperatures[device_id]['temp']
                new_temp = current + random.uniform(-0.5, 0.5)
                if new_temp < 20:
                    new_temp = 20
                self.temperatures[device_id]['temp'] = round(new_temp, 1)
                self.temperatures[device_id]['last_reading'] = datetime.now()
                logger.debug(f"Simulated temp for {device_id}: {self.temperatures[device_id]['temp']}")
            return True
        if not self.devices_loaded:
            logger.warning("update_temperatures called but devices_loaded is False")
            return False
        try:
            for i, device_file in enumerate(self.device_files):
                device_id = os.path.basename(os.path.dirname(device_file))
                temp = self._read_temp(device_file)
                if temp is not None:
                    self.temperatures[device_id]['temp'] = temp
                    self.temperatures[device_id]['last_reading'] = datetime.now()
                    # logger.info(f"Updated temperature for {device_id}: {temp}")  # Commented out to reduce log noise
                else:
                    logger.warning(f"Failed to update temperature for {device_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating temperatures: {e}")
            return False
    
    def get_status(self):
        """Get current temperature status"""
        # Update temperatures before returning status
        self.update_temperatures()
        
        # For API compatibility, create a sensors dictionary with device_id as key
        sensors = {}
        for device_id, data in self.temperatures.items():
            # Get sensor-specific high limit or fall back to global limit
            sensor_limits = self.temp_config.get('sensor_limits', {})
            high_limit = sensor_limits.get(device_id, self.temp_config.get('high_limit', 50.0))
            
            sensors[device_id] = {
                'temperature': data['temp'],
                'name': data['name'],
                'high_limit': high_limit,
                'high_temp': data.get('high_temp', False),
                'temp': data['temp'],  # Include both for compatibility
                'last_reading': data['last_reading'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(data['last_reading'], datetime) else str(data['last_reading'])
            }
        
        return {
            'sensors': sensors,
            'temperatures': self.temperatures,  # Include original format for compatibility
            'high_limit': self.temp_config.get('high_limit', 50.0),
            'monitoring_interval': self.temp_config.get('sampling_interval', 5.0),
            'high_temp_condition': self.high_temp_condition,
            'monitoring_enabled': self.monitoring,
            'devices_found': len(self.temperatures),
            'sensor_limits': self.temp_config.get('sensor_limits', {}),
            'simulated': False,
            'primary_sensor': self.temp_config.get('primary_sensor', None)
        }

    def get_status_cached(self):
        """Get current temperature status without forcing an update"""
        # Return cached values without calling update_temperatures()
        # For API compatibility, create a sensors dictionary with device_id as key
        sensors = {}
        for device_id, data in self.temperatures.items():
            # Get sensor-specific high limit or fall back to global limit
            sensor_limits = self.temp_config.get('sensor_limits', {})
            high_limit = sensor_limits.get(device_id, self.temp_config.get('high_limit', 50.0))
            
            sensors[device_id] = {
                'temperature': data['temp'],
                'name': data['name'],
                'high_limit': high_limit,
                'high_temp': data.get('high_temp', False),
                'temp': data['temp'],  # Include both for compatibility
                'last_reading': data['last_reading'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(data['last_reading'], datetime) else str(data['last_reading'])
            }
        
        return {
            'sensors': sensors,
            'temperatures': self.temperatures,  # Include original format for compatibility
            'high_limit': self.temp_config.get('high_limit', 50.0),
            'monitoring_interval': self.temp_config.get('sampling_interval', 5.0),
            'high_temp_condition': self.high_temp_condition,
            'monitoring_enabled': self.monitoring,
            'devices_found': len(self.temperatures),
            'sensor_limits': self.temp_config.get('sensor_limits', {}),
            'simulated': False,
            'primary_sensor': self.temp_config.get('primary_sensor', None)
        }
    
    def diagnose_sensors(self):
        """Public method to diagnose all sensor issues"""
        logger.info("=== Temperature Sensor Diagnosis ===")
        
        # Check if 1-Wire modules are loaded
        try:
            result = subprocess.run(['lsmod'], capture_output=True, text=True)
            w1_modules = [line for line in result.stdout.split('\n') if 'w1' in line]
            if w1_modules:
                logger.info(f"1-Wire modules loaded: {w1_modules}")
            else:
                logger.warning("No 1-Wire modules found in lsmod output")
        except Exception as e:
            logger.error(f"Could not check loaded modules: {e}")
        
        # Check base 1-Wire directory
        base_dir = '/sys/bus/w1/devices/'
        if os.path.exists(base_dir):
            logger.info(f"1-Wire base directory exists: {base_dir}")
            try:
                devices = os.listdir(base_dir)
                logger.info(f"Devices in 1-Wire directory: {devices}")
                
                # Look for temperature sensors (28-*)
                temp_sensors = [d for d in devices if d.startswith('28-')]
                logger.info(f"Temperature sensors found: {temp_sensors}")
                
                # Diagnose each sensor
                for sensor in temp_sensors:
                    device_file = os.path.join(base_dir, sensor, 'w1_slave')
                    self._diagnose_sensor_issue(device_file)
                    
            except Exception as e:
                logger.error(f"Could not list 1-Wire devices: {e}")
        else:
            logger.error(f"1-Wire base directory does not exist: {base_dir}")
            
        logger.info("=== End Temperature Sensor Diagnosis ===")
        
        return {"status": "diagnosis_complete", "check_logs": True}
        # The background monitoring thread keeps these values fresh
        
        # For API compatibility, create a sensors dictionary with device_id as key
        sensors = {}
        for device_id, data in self.temperatures.items():
            # Get sensor-specific high limit or fall back to global limit
            sensor_limits = self.temp_config.get('sensor_limits', {})
            high_limit = sensor_limits.get(device_id, self.temp_config.get('high_limit', 50.0))
            
            sensors[device_id] = {
                'temperature': data['temp'],
                'name': data['name'],
                'high_limit': high_limit,
                'high_temp': data.get('high_temp', False),
                'temp': data['temp'],  # Include both for compatibility
                'last_reading': data['last_reading'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(data['last_reading'], datetime) else str(data['last_reading'])
            }
        
        return {
            'sensors': sensors,
            'temperatures': self.temperatures,  # Include original format for compatibility
            'high_limit': self.temp_config.get('high_limit', 50.0),
            'monitoring_interval': self.temp_config.get('sampling_interval', 5.0),
            'high_temp_condition': self.high_temp_condition,
            'monitoring_enabled': self.monitoring,
            'devices_found': len(self.temperatures),
            'sensor_limits': self.temp_config.get('sensor_limits', {}),
            'simulated': False,
            'primary_sensor': self.temp_config.get('primary_sensor', None)
        }
    
    def update_config(self, new_config):
        """Update temperature sensor configuration"""
        if new_config:
            # Update configuration values
            for key, value in new_config.items():
                self.temp_config[key] = value
            
            # Handle enable/disable monitoring
            if 'enabled' in new_config:
                if new_config['enabled'] and not self.monitoring:
                    self._start_monitoring()
                elif not new_config['enabled'] and self.monitoring:
                    self._stop_monitoring()
            
            # Update sensor names from device_ids if present
            if 'device_ids' in new_config:
                logger.debug(f"Updating sensor names from device_ids: {new_config['device_ids']}")
                device_ids = new_config['device_ids']
                
                # Update names in temperature data
                for device_id, name in device_ids.items():
                    if device_id in self.temperatures:
                        self.temperatures[device_id]['name'] = name
                        logger.debug(f"Updated sensor {device_id} name to: {name}")
            
            return True
        return False
    
    def cleanup(self):
        """Clean up resources"""
        self._stop_monitoring()
        logger.info("Temperature controller cleaned up")