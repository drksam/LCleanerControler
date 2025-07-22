"""
Output control module for managing outputs (fan, red lights, table movement).
"""
import time
import logging
import os
import threading
from config import get_gpio_config, get_timing_config, get_system_config
from gpio_controller_wrapper import LocalGPIOWrapper

class OutputController:
    """
    Controller for fan, red lights, and table movement outputs with timeout functionality
    """
    
    def __init__(self):
        """Initialize the output controller"""
        self.gpio_config = get_gpio_config()
        self.timing_config = get_timing_config()
        
        # State tracking
        self.fan_state = False
        self.red_lights_state = False
        self.table_forward_state = False
        self.table_backward_state = False
        
        # End switch states
        self.table_front_switch_state = False
        self.table_back_switch_state = False
        
        # Timing variables
        self.fan_delay_start = 0
        self.fan_delay_end = 0
        self.red_lights_delay_start = 0
        self.red_lights_delay_end = 0
        
        # Threading lock for thread safety
        self.lock = threading.Lock()
        
        # Check if running in simulation mode
        self.simulation_mode = os.environ.get('SIMULATION_MODE', 'False').lower() == 'true'
        
        # Get operation mode from system config if available
        try:
            system_config = get_system_config()
            operation_mode = system_config.get('operation_mode', 'normal')
            if operation_mode == 'simulation':
                self.simulation_mode = True
        except Exception:
            pass
        
        # Check if we should force hardware mode (used in prototype mode)
        self.force_hardware = os.environ.get('FORCE_HARDWARE', 'False').lower() == 'true'
        
        if self.simulation_mode:
            logging.info("Output controller running in simulation mode")
            self.gpio = LocalGPIOWrapper(simulation_mode=True)
            self.pins_initialized = True
        else:
            try:
                # Initialize GPIO wrapper for hardware access
                self.gpio = LocalGPIOWrapper(simulation_mode=False)
                
                # Initialize output pins
                self.gpio.setup_output(self.gpio_config['fan_pin'], 0)
                self.gpio.setup_output(self.gpio_config['red_lights_pin'], 0)
                self.gpio.setup_output(self.gpio_config['table_forward_pin'], 0)
                self.gpio.setup_output(self.gpio_config['table_backward_pin'], 0)
                
                # Initialize input pins for table end switches with pull-up
                self.gpio.setup_input(self.gpio_config['table_front_limit_pin'], pull_up=True)
                self.gpio.setup_input(self.gpio_config['table_back_limit_pin'], pull_up=True)
                
                # Start monitor thread for limit switches
                self.update_thread_running = True
                self.update_thread = threading.Thread(target=self._monitor_limit_switches)
                self.update_thread.daemon = True
                self.update_thread.start()
                
                logging.info("Output pins initialized successfully")
                self.pins_initialized = True
            except Exception as e:
                if self.force_hardware:
                    # In prototype mode with FORCE_HARDWARE, we should raise the exception
                    # rather than falling back to simulation mode
                    logging.error(f"Failed to initialize output pins with FORCE_HARDWARE enabled: {e}")
                    raise
                else:
                    logging.error(f"Failed to initialize output pins: {e}")
                    logging.info("Falling back to simulation mode")
                    self.simulation_mode = True
                    self.gpio = LocalGPIOWrapper(simulation_mode=True)
                    self.pins_initialized = True
    
    def _monitor_limit_switches(self):
        """Background thread to monitor limit switches"""
        while self.update_thread_running:
            try:
                # Read limit switch inputs (inverted logic with pull-up resistors)
                front_limit = not bool(self.gpio.read(self.gpio_config['table_front_limit_pin']))
                back_limit = not bool(self.gpio.read(self.gpio_config['table_back_limit_pin']))
                
                # Handle state changes
                if front_limit != self.table_front_switch_state:
                    self.table_front_switch_state = front_limit
                    if front_limit:
                        self._on_table_front_limit()
                
                if back_limit != self.table_back_switch_state:
                    self.table_back_switch_state = back_limit
                    if back_limit:
                        self._on_table_back_limit()
            except Exception as e:
                logging.error(f"Error monitoring limit switches: {e}")
            
            # Check every 100ms
            time.sleep(0.1)
    
    def set_fan(self, state):
        """Set the fan output state"""
        with self.lock:
            self.fan_state = state
            if state:
                self.fan_delay_start = int(time.time() * 1000)  # Current time in ms
                logging.debug("Fan turned ON")
            
            # Apply the state to the GPIO
            if self.pins_initialized:
                self.gpio.write(self.gpio_config['fan_pin'], 1 if state else 0)
    
    def set_red_lights(self, state):
        """Set the red lights output state"""
        with self.lock:
            self.red_lights_state = state
            if state:
                self.red_lights_delay_start = int(time.time() * 1000)  # Current time in ms
                logging.debug("Red lights turned ON")
            
            # Apply the state to the GPIO
            if self.pins_initialized:
                self.gpio.write(self.gpio_config['red_lights_pin'], 1 if state else 0)
    
    def set_table_forward(self, state):
        """
        Move the table forward (towards front limit switch)
        
        Safety: Won't allow forward movement if front limit switch is activated
        """
        # We'll avoid using the lock to prevent gunicorn worker timeout
        # Only allow forward movement if not at front limit
        if state and self.table_front_switch_state:
            logging.warning("Table at front limit - cannot move forward")
            return False
        
        # Don't allow both directions at the same time
        if state and self.table_backward_state:
            self.table_backward_state = False
            # Apply the state to the GPIO
            if self.pins_initialized:
                self.gpio.write(self.gpio_config['table_backward_pin'], 0)
        
        self.table_forward_state = state
        if state:
            logging.debug("Table moving FORWARD")
        
        # Apply the state to the GPIO
        if self.pins_initialized:
            self.gpio.write(self.gpio_config['table_forward_pin'], 1 if state else 0)
        
        return True
    
    def set_table_backward(self, state):
        """
        Move the table backward (towards back limit switch)
        
        Safety: Won't allow backward movement if back limit switch is activated
        """
        # We'll avoid using the lock to prevent gunicorn worker timeout
        # Only allow backward movement if not at back limit
        if state and self.table_back_switch_state:
            logging.warning("Table at back limit - cannot move backward")
            return False
        
        # Don't allow both directions at the same time
        if state and self.table_forward_state:
            self.table_forward_state = False
            # Apply the state to the GPIO
            if self.pins_initialized:
                self.gpio.write(self.gpio_config['table_forward_pin'], 0)
        
        self.table_backward_state = state
        if state:
            logging.debug("Table moving BACKWARD")
        
        # Apply the state to the GPIO
        if self.pins_initialized:
            self.gpio.write(self.gpio_config['table_backward_pin'], 1 if state else 0)
        
        return True
    
    def _on_table_front_limit(self):
        """Callback when table reaches front limit switch"""
        self.table_front_switch_state = True
        logging.info("Table reached FRONT limit")
        self.set_table_forward(False)  # Stop forward movement
    
    def _on_table_back_limit(self):
        """Callback when table reaches back limit switch"""
        self.table_back_switch_state = True
        logging.info("Table reached BACK limit")
        self.set_table_backward(False)  # Stop backward movement
    
    def update(self, servo_position, normal_position):
        """
        Update the outputs based on timing and servo position
        
        Args:
            servo_position: Current servo position
            normal_position: Reference position for "normal" (non-fire) state
        """
        current_time = int(time.time() * 1000)  # Current time in ms
        
        with self.lock:
            # If servo is in fire position (not in normal position), activate outputs
            if servo_position != normal_position:
                self.set_fan(True)
                self.set_red_lights(True)
            else:
                # Calculate when to turn off outputs
                if self.fan_state:
                    fan_off_delay = self.timing_config['fan_off_delay']
                    self.fan_delay_end = self.fan_delay_start + fan_off_delay
                    
                    # Turn off fan if delay time has passed
                    if current_time > self.fan_delay_end:
                        self.set_fan(False)
                
                if self.red_lights_state:
                    red_lights_off_delay = self.timing_config['red_lights_off_delay']
                    self.red_lights_delay_end = self.red_lights_delay_start + red_lights_off_delay
                    
                    # Turn off red lights if delay time has passed
                    if current_time > self.red_lights_delay_end:
                        self.set_red_lights(False)
    
    def get_status(self):
        """Get the current status of outputs"""
        # We only need to read data, so we'll avoid using the lock
        # to prevent issues with gunicorn worker timeouts
        current_time = int(time.time() * 1000)
        return {
            "fan_state": self.fan_state,
            "red_lights_state": self.red_lights_state,
            "table_forward_state": self.table_forward_state,
            "table_backward_state": self.table_backward_state,
            "table_front_switch_state": self.table_front_switch_state,
            "table_back_switch_state": self.table_back_switch_state,
            "fan_time_remaining": max(0, self.fan_delay_end - current_time) if self.fan_state else 0,
            "red_lights_time_remaining": max(0, self.red_lights_delay_end - current_time) if self.red_lights_state else 0
        }
    
    def cleanup(self):
        """Clean up GPIO pins"""
        if self.pins_initialized:
            try:
                with self.lock:
                    # Turn off all outputs
                    if hasattr(self, 'gpio_config'):
                        self.gpio.write(self.gpio_config['fan_pin'], 0)
                        self.gpio.write(self.gpio_config['red_lights_pin'], 0)
                        self.gpio.write(self.gpio_config['table_forward_pin'], 0)
                        self.gpio.write(self.gpio_config['table_backward_pin'], 0)
                    
                    # Stop the monitor thread if it exists
                    if hasattr(self, 'update_thread_running'):
                        self.update_thread_running = False
                        if hasattr(self, 'update_thread') and self.update_thread:
                            self.update_thread.join(timeout=1.0)
                    
                    # Clean up GPIO resources
                    if hasattr(self, 'gpio'):
                        self.gpio.cleanup()
                    
                    logging.info("Output pins cleaned up")
            except Exception as e:
                logging.error(f"Error during cleanup: {e}")
    
    def update_timing_config(self):
        """Reload timing configuration from config file"""
        try:
            with self.lock:
                self.timing_config = get_timing_config()
                logging.info("Timing configuration updated successfully")
        except Exception as e:
            logging.error(f"Error updating timing configuration: {e}")