"""
Output control module for managing outputs (fan, red lights, table movement).
"""
import time
import logging
import os
import threading
from gpiozero import DigitalOutputDevice, DigitalInputDevice
from config import get_gpio_config, get_timing_config

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
        
        # Check if we should force hardware mode (used in prototype mode)
        self.force_hardware = os.environ.get('FORCE_HARDWARE', 'False').lower() == 'true'
        
        if self.simulation_mode:
            logging.info("Output controller running in simulation mode")
            self.pins_initialized = False
        else:
            try:
                # Initialize output pins
                self.fan_pin = DigitalOutputDevice(self.gpio_config['fan_pin'])
                self.red_lights_pin = DigitalOutputDevice(self.gpio_config['red_lights_pin'])
                self.table_forward_pin = DigitalOutputDevice(self.gpio_config['table_forward_pin'])
                self.table_backward_pin = DigitalOutputDevice(self.gpio_config['table_backward_pin'])
                
                # Initialize input pins for table end switches
                self.table_front_switch = DigitalInputDevice(
                    self.gpio_config['table_front_switch_pin'],
                    pull_up=True,
                    bounce_time=self.timing_config['debounce_delay'] / 1000.0
                )
                self.table_back_switch = DigitalInputDevice(
                    self.gpio_config['table_back_switch_pin'], 
                    pull_up=True,
                    bounce_time=self.timing_config['debounce_delay'] / 1000.0
                )
                
                # Set up callbacks for end switches
                self.table_front_switch.when_activated = self._on_table_front_limit
                self.table_back_switch.when_activated = self._on_table_back_limit
                
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
                    self.pins_initialized = False
    
    def set_fan(self, state):
        """Set the fan output state"""
        with self.lock:
            self.fan_state = state
            if state:
                self.fan_delay_start = int(time.time() * 1000)  # Current time in ms
                logging.debug("Fan turned ON")
            
            # Apply the state to the GPIO if not in simulation mode
            if not self.simulation_mode and self.pins_initialized:
                self.fan_pin.value = 1 if state else 0
    
    def set_red_lights(self, state):
        """Set the red lights output state"""
        with self.lock:
            self.red_lights_state = state
            if state:
                self.red_lights_delay_start = int(time.time() * 1000)  # Current time in ms
                logging.debug("Red lights turned ON")
            
            # Apply the state to the GPIO if not in simulation mode
            if not self.simulation_mode and self.pins_initialized:
                self.red_lights_pin.value = 1 if state else 0
    
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
            # Apply the state to the GPIO if not in simulation mode
            if not self.simulation_mode and self.pins_initialized:
                self.table_backward_pin.value = 0
        
        self.table_forward_state = state
        if state:
            logging.debug("Table moving FORWARD")
        
        # Apply the state to the GPIO if not in simulation mode
        if not self.simulation_mode and self.pins_initialized:
            self.table_forward_pin.value = 1 if state else 0
        
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
            # Apply the state to the GPIO if not in simulation mode
            if not self.simulation_mode and self.pins_initialized:
                self.table_forward_pin.value = 0
        
        self.table_backward_state = state
        if state:
            logging.debug("Table moving BACKWARD")
        
        # Apply the state to the GPIO if not in simulation mode
        if not self.simulation_mode and self.pins_initialized:
            self.table_backward_pin.value = 1 if state else 0
        
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
        if not self.simulation_mode and self.pins_initialized:
            try:
                with self.lock:
                    # Turn off all outputs
                    self.fan_pin.off()
                    self.red_lights_pin.off()
                    self.table_forward_pin.off()
                    self.table_backward_pin.off()
                    
                    # Close all pins
                    self.fan_pin.close()
                    self.red_lights_pin.close()
                    self.table_forward_pin.close()
                    self.table_backward_pin.close()
                    self.table_front_switch.close()
                    self.table_back_switch.close()
                    
                    logging.info("Output pins cleaned up")
            except Exception as e:
                logging.error(f"Error during cleanup: {e}")