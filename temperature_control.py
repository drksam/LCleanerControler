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
            # Get the configured GPIO pin for 1-Wire
            w1_gpio_pin = self.temp_config.get('w1_gpio_pin', 2)
            
            # Use the specified GPIO pin for 1-Wire
            if w1_gpio_pin != 4:  # 4 is the default, so we only need to specify if it's different
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
            
            if not self.device_folder:
                logger.error("No DS18B20 temperature sensors found")
                return
            
            # Save the device file paths
            for folder in self.device_folder:
                device_file = folder + '/w1_slave'
                device_id = os.path.basename(folder)
                
                # Get device name from config if available
                device_name = self.temp_config.get('device_ids', {}).get(device_id, f"Sensor {device_id}")
                logger.debug(f"Initializing temperature sensor {device_id} with name: {device_name}")
                
                self.device_files.append(device_file)
                self.temperatures[device_id] = {
                    'temp': 0.0, 
                    'last_reading': datetime.now(),
                    'name': device_name
                }
            
            self.devices_loaded = True
            logger.info(f"Found {len(self.device_files)} DS18B20 temperature sensors")
            
        except Exception as e:
            logger.error(f"Error initializing temperature sensors: {e}")
            # Fall back to simulation mode
            self.devices_loaded = False
            
    def _read_temp_raw(self, device_file):
        """Read raw temperature data from sensor file"""
        try:
            with open(device_file, 'r') as f:
                lines = f.readlines()
            return lines
        except Exception as e:
            logger.error(f"Error reading temperature sensor {device_file}: {e}")
            return None
        
    def _read_temp(self, device_file):
        """Convert raw temperature data to Celsius"""
        # Simulate temperature reading if not on Raspberry Pi
        if os.environ.get('SIMULATION_MODE') == 'True':
            import random
            return round(25.0 + random.uniform(-2.0, 2.0), 1)  # Simulate around 25°C
        
        lines = self._read_temp_raw(device_file)
        if not lines:
            return None
        
        try:
            # Check if the CRC is valid (the last 3 characters should be 'YES')
            if lines[0].strip()[-3:] != 'YES':
                logger.warning(f"CRC check failed for sensor {device_file}")
                return None
            
            # Find the temperature reading (t=xxxxx)
            equals_pos = lines[1].find('t=')
            if equals_pos == -1:
                logger.warning(f"Temperature reading not found for sensor {device_file}")
                return None
            
            # Convert the temperature reading from millidegrees to degrees Celsius
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string) / 1000.0
            return temp_c
        
        except Exception as e:
            logger.error(f"Error processing temperature data from {device_file}: {e}")
            return None
        
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
        """Update temperature readings from sensors"""
        if os.environ.get('SIMULATION_MODE') == 'True':
            # Simulate temperature changes
            import random
            for device_id in self.temperatures:
                # Randomly adjust the simulated temperature
                current = self.temperatures[device_id]['temp']
                new_temp = current + random.uniform(-0.5, 0.5)
                
                # Keep within a reasonable range (20-35°C normally, unless testing high temp)
                if new_temp < 20:
                    new_temp = 20
                
                self.temperatures[device_id]['temp'] = round(new_temp, 1)
                self.temperatures[device_id]['last_reading'] = datetime.now()
            return True
                
        if not self.devices_loaded:
            return False
        
        try:
            for i, device_file in enumerate(self.device_files):
                device_id = os.path.basename(os.path.dirname(device_file))
                temp = self._read_temp(device_file)
                
                if temp is not None:
                    self.temperatures[device_id]['temp'] = temp
                    self.temperatures[device_id]['last_reading'] = datetime.now()
            
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
                'last_reading': data['last_reading'].strftime('%Y-%m-%d %H:%M:%S')
            }
        
        # Create the status dictionary
        status = {
            'sensors': sensors,
            'high_limit': self.temp_config.get('high_limit', 50.0),  # Global high limit
            'high_temp_condition': self.high_temp_condition,
            'monitoring_enabled': self.monitoring,
            'devices_found': len(self.temperatures),
            'sensor_limits': self.temp_config.get('sensor_limits', {}),
            'primary_sensor': self.temp_config.get('primary_sensor', None)
        }
        
        return status
    
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