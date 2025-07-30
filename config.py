"""
Configuration module for machine parameters and settings.
All configurable values should be stored here for easy access and modification.
"""
import os
import json
import logging
from pathlib import Path

# Default configuration parameters
DEFAULT_CONFIG = {
    # System mode settings
    'system': {
        'operation_mode': 'simulation',    # One of: 'simulation', 'prototype', 'normal'
        'debug_level': 'info',             # Logging level: 'debug', 'info', 'warning', 'error'
        'bypass_safety': False,            # Bypass safety checks in prototype mode
    },
    
    # Stepper motor parameters
    'stepper': {
        'max_speed': 3500,                # Maximum speed in steps/sec
        'acceleration': 2000,             # Acceleration in steps/sec^2
        'index_distance': 15842,          # X distance for indexing (steps)
        'jog_speed': 500,                 # Jog speed in steps/sec
        'jog_step_size': 20,              # Steps to move when jogging
        'invert_enable_logic': False,     # Set to True if your driver needs LOW=Enable, HIGH=Disable
    },
    
    # Servo parameters
    'servo': {
        'position_normal': 75,            # Servo position in normal state (degrees)
        'detach_delay': 0.5,              # Time to wait before detaching servo (seconds)
        'sequence_delay': 500,            # Delay between steps in sequence mode (ms)
    },
    
    # Timing parameters
    'timing': {
        'fan_off_delay': 600000,          # Fan off delay (ms)
        'red_lights_off_delay': 60000,    # Red lights off delay (ms)
        'debounce_delay': 200,            # Button debounce delay (ms)
        'laser_fire_threshold': 2000,     # Time threshold to count a laser firing (ms)
        'estop_confirmation_timeout': 5000, # E-Stop auto-confirm timeout (ms)
    },
    
    # Temperature sensor parameters
    'temperature': {
        'sensor1_name': 'Laser Head',    # Name for temperature sensor 1
        'sensor2_name': 'Control Box',   # Name for temperature sensor 2
        'sensor1_high_limit': 40.0,      # High temperature limit for sensor 1 (°C)
        'sensor2_high_limit': 50.0,      # High temperature limit for sensor 2 (°C)
        'auto_stop_enabled': False,      # Auto-stop on high temperature
        'update_interval': 2.0           # Temperature reading update interval (seconds)
    },
    
    # RFID access control parameters
    'rfid': {
        'server_url': 'https://Shopmachinemonitor.replit.app/api/auth', # Authentication server URL
        'api_key': '',                   # API key for server authentication
        'machine_id': 'laser_room_1',    # Machine ID for this device
        'session_hours': 8,              # Session duration in hours
        'access_control_enabled': True,  # Enable/disable access control
        'offline_mode': True             # Allow offline authentication using local database
    },
    
    # Statistics tracking
    'statistics': {
        'laser_fire_count': 0,            # Count of laser firings (>2 seconds)
        'total_laser_fire_time': 0,       # Total time laser has been fired (ms)
    },
    
    # LED status light settings
    'led_status': {
        'enabled': True,                  # Enable WS2812B LED status indicator
        'num_leds': 2,                    # Number of LEDs in the chain (updated for dual LED setup)
        'brightness': 50,                 # LED brightness (0-100)
        'idle_color': 'blue',             # Color when machine is idle
        'authorized_color': 'green',      # Color when user is authorized
        'denied_color': 'red',            # Color when access is denied
        'logout_color': 'purple',         # Color during logout transition
        'warning_color': 'yellow',        # Warning state color
        'error_color': 'red_sos',         # Error state color pattern
    },
    
    # Sequences for automated operations
    'sequences': {
        # Default example sequence
        'example_sequence': {
            'name': 'Example Sequence',
            'description': 'A simple example sequence',
            'steps': [
                {'action': 'stepper_move', 'direction': 'in', 'steps': 1000, 'delay_after': 500},
                {'action': 'fire', 'duration': 2000},
                {'action': 'stepper_move', 'direction': 'out', 'steps': 1000, 'delay_after': 500},
                {'action': 'wait', 'duration': 1000},
                {'action': 'stop_fire'}
            ]
        }
    },
    
        # GPIO pin configuration
    'gpio': {
        # Raspberry Pi GPIO pins
        'fan_pin': 26,                    # Fan relay pin (BCM 26)
        'red_lights_pin': 16,             # Red lights relay pin (BCM 16)
        'in_switch_pin': 5,               # IN switch pin (BCM 5, Pull-Up, LOW=Active)
        'out_switch_pin': 25,             # OUT switch pin (BCM 25, Pull-Up, LOW=Active)
        'fire_switch_pin': 22,            # FIRE switch pin (BCM 22, Pull-Up, LOW=Active)
        'invert_switch_pin': 12,          # INVERT switch pin (BCM 12, Pull-Up, LOW=Active)
        'estop_pin': 17,                  # Emergency stop pin (BCM 17, Pull-Up, LOW=Active)
        'table_forward_pin': 13,          # Table forward movement relay pin (BCM 13)
        'table_backward_pin': 6,          # Table backward movement relay pin (BCM 6)
        'table_front_switch_pin': 21,     # Table front end switch pin (BCM 21, Pull-Up, LOW=Active)
        'table_back_switch_pin': 20,      # Table back end switch pin (BCM 20, Pull-Up, LOW=Active)

        # RFID pins
        'rfid_mosi_pin': 10,              # RFID MOSI pin (BCM 10)
        'rfid_miso_pin': 9,               # RFID MISO pin (BCM 9)
        'rfid_sclk_pin': 11,              # RFID SCLK pin (BCM 11)
        'rfid_ce0_pin': 8,                # RFID CE0 pin (BCM 8)

        # ESP32 control pins (do not use on Pi)
        'esp_step_pin': 25,               # ESP32 Stepper STEP (GPIO 25)
        'esp_dir_pin': 26,                # ESP32 Stepper DIR (GPIO 26)
        'esp_enable_pin': 27,             # ESP32 Stepper EN (GPIO 27, HIGH=Enable, normal logic)
        'esp_limit_a_pin': 18,            # ESP32 Stepper Limit A (GPIO 18, Pull-Up, LOW=Active) - CW limit
        'esp_limit_b_pin': 19,            # ESP32 Stepper Limit B (GPIO 19, Pull-Up, LOW=Active) - CCW limit
        'esp_home_pin': 21,               # ESP32 Stepper Home (GPIO 21, Pull-Up, LOW=Active)
        'esp_servo_pwm_pin': 12,          # ESP32 Servo PWM (GPIO 12)
        'esp_ws2812b_pin': 23,            # ESP32 WS2812B LED Data (GPIO 23)
    }
}

# Path to store configuration file
CONFIG_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / 'machine_config.json'

def load_config():
    """Load configuration from file or create with defaults if not exists"""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                logging.info(f"Configuration loaded from {CONFIG_PATH}")
                return config
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            logging.info("Using default configuration")
            return DEFAULT_CONFIG
    else:
        # Create default configuration file
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

def save_config(config):
    """Save configuration to file"""
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)
            logging.info(f"Configuration saved to {CONFIG_PATH}")
        return True
    except Exception as e:
        logging.error(f"Error saving configuration: {e}")
        return False

# Load the configuration
config = load_config()

# Helper functions to get configuration values
def get_system_config():
    """Get system mode and debug level settings"""
    # Make sure all expected keys exist
    system_config = config.get('system', {})
    if 'operation_mode' not in system_config:
        system_config['operation_mode'] = DEFAULT_CONFIG['system']['operation_mode']
    if 'debug_level' not in system_config:
        system_config['debug_level'] = DEFAULT_CONFIG['system']['debug_level']
    if 'bypass_safety' not in system_config:
        system_config['bypass_safety'] = DEFAULT_CONFIG['system']['bypass_safety']
        
    return system_config

def get_stepper_config():
    """Get stepper configuration including ESP32 pin assignments from GPIO section."""
    stepper_config = config['stepper'].copy()
    gpio_config = config['gpio']
    
    # Add ESP32 pin configurations from GPIO section
    esp_pins = {
        'esp_step_pin': gpio_config.get('esp_step_pin'),
        'esp_dir_pin': gpio_config.get('esp_dir_pin'),
        'esp_enable_pin': gpio_config.get('esp_enable_pin'),
        'esp_limit_a_pin': gpio_config.get('esp_limit_a_pin'),
        'esp_limit_b_pin': gpio_config.get('esp_limit_b_pin'),
        'esp_home_pin': gpio_config.get('esp_home_pin'),
        'esp_servo_pwm_pin': gpio_config.get('esp_servo_pwm_pin'),
    }
    
    # Only add pins that have values (not None)
    for pin_name, pin_value in esp_pins.items():
        if pin_value is not None:
            stepper_config[pin_name] = pin_value
    
    return stepper_config

def get_servo_config():
    return config['servo']

def get_timing_config():
    return config['timing']

def get_gpio_config():
    # Get the GPIO config from the config file
    gpio_config = config['gpio']
    
    # Map the pin names in the config file to the names expected by the pinout template
    # This ensures backward compatibility if pin naming has changed
    pin_mapping = {
        # ESP32 mappings (these stay the same)
        'esp_step_pin': 'esp_step_pin',
        'esp_dir_pin': 'esp_dir_pin',
        'esp_enable_pin': 'esp_enable_pin',
        'esp_limit_a_pin': 'esp_limit_a_pin',
        'esp_limit_b_pin': 'esp_limit_b_pin',
        'esp_home_pin': 'esp_home_pin',
        'esp_servo_pwm_pin': 'esp_servo_pwm_pin',
    }
    mapped_config = gpio_config.copy()
    for old_name, new_name in pin_mapping.items():
        if old_name in gpio_config:
            mapped_config[new_name] = gpio_config[old_name]
    return mapped_config

def get_statistics():
    """Get statistics data, ensuring it exists with defaults"""
    if 'statistics' not in config:
        # Initialize statistics if it doesn't exist
        config['statistics'] = {
            'laser_fire_count': 0,
            'total_laser_fire_time': 0
        }
        save_config(config)
    
    return config['statistics']

def get_temperature_config():
    # Ensure default temperature configuration includes primary_sensor
    temp_config = config.get('temperature', {})
    
    # Add primary_sensor field if it doesn't exist
    if 'primary_sensor' not in temp_config:
        temp_config['primary_sensor'] = None
        
    return temp_config

def get_rfid_config():
    """Get RFID access control configuration"""
    return config.get('rfid', {})

def get_sequences():
    """Get all saved sequences"""
    return config.get('sequences', {})

def get_sequence(sequence_id):
    """Get a specific sequence by ID"""
    sequences = get_sequences()
    return sequences.get(sequence_id)

def save_sequence(sequence_id, sequence_data):
    """Save a sequence"""
    if 'sequences' not in config:
        config['sequences'] = {}
    
    config['sequences'][sequence_id] = sequence_data
    return save_config(config)

def delete_sequence(sequence_id):
    """Delete a sequence"""
    if 'sequences' in config and sequence_id in config['sequences']:
        del config['sequences'][sequence_id]
        return save_config(config)
    return False

def update_config(section, key, value):
    """Update a specific configuration value"""
    # Create the section if it doesn't exist
    if section not in config:
        config[section] = {}
        
    # Update the value
    config[section][key] = value
    save_config(config)
    return True

def increment_laser_counter():
    """Increment the laser fire counter"""
    if 'statistics' in config and 'laser_fire_count' in config['statistics']:
        config['statistics']['laser_fire_count'] += 1
        save_config(config)
        
        # Log the increment for debugging
        import logging
        logging.info(f"Global laser fire counter incremented to {config['statistics']['laser_fire_count']}")
        
        return config['statistics']['laser_fire_count']
    return 0

def add_laser_fire_time(time_ms):
    """Add time to the total laser firing time (in milliseconds)"""
    if 'statistics' in config and 'total_laser_fire_time' in config['statistics']:
        config['statistics']['total_laser_fire_time'] += time_ms
        save_config(config)
        
        # Also update the current user session stats if RFID is available
        try:
            # Import here to avoid circular imports
            import sys
            
            # Try to get rfid_controller from app module where it's actually initialized
            if 'app' in sys.modules:
                app_module = sys.modules['app']
                rfid_controller = getattr(app_module, 'rfid_controller', None)
                if rfid_controller and hasattr(rfid_controller, 'current_session_id') and rfid_controller.current_session_id:
                    rfid_controller.update_session_stats(fire_count_increment=1, fire_time_increment_ms=time_ms)
                    import logging
                    logging.info(f"Session stats updated: +1 fire, +{time_ms}ms firing time")
                else:
                    import logging
                    logging.debug(f"RFID controller not available or no active session for session stats update")
        except Exception as e:
            import logging
            logging.warning(f"Could not update session stats: {e}")
        
        return config['statistics']['total_laser_fire_time']
    return 0

def reset_statistics(reset_type='all'):
    """Reset the laser fire statistics to zero
    
    Args:
        reset_type (str): Type of reset - 'counter', 'timer', or 'all'
    """
    if 'statistics' not in config:
        return False
        
    try:
        if reset_type == 'counter':
            config['statistics']['laser_fire_count'] = 0
        elif reset_type == 'timer':
            config['statistics']['total_laser_fire_time'] = 0
        elif reset_type == 'all':
            config['statistics']['laser_fire_count'] = 0
            config['statistics']['total_laser_fire_time'] = 0
        else:
            return False
            
        save_config(config)
        return True
    except Exception:
        return False