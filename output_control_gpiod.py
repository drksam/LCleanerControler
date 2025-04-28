"""
Output control module for managing outputs (fan, red lights, table movement) using gpiod.
"""
import time
import logging
import threading
from config import get_gpio_config, get_system_config
from gpio_controller_wrapper import LocalGPIOWrapper

class OutputController:
    """
    Controller for fan, red lights, and table movement outputs with timeout functionality
    """
    
    def __init__(self):
        """Initialize the output controller"""
        # Load configuration
        config = get_gpio_config()
        system_config = get_system_config()
        
        # Get operation mode from system config
        operation_mode = system_config.get('operation_mode', 'simulation')
        
        # Set simulation mode based on system configuration
        self.simulation_mode = operation_mode == 'simulation'
        
        # GPIO pin assignments
        self.fan_pin = config.get('fan_pin', 17)
        self.red_lights_pin = config.get('red_lights_pin', 27)
        self.table_forward_pin = config.get('table_forward_pin', 22)
        self.table_backward_pin = config.get('table_backward_pin', 23)
        self.table_front_limit_pin = config.get('table_front_limit_pin', 24)
        self.table_back_limit_pin = config.get('table_back_limit_pin', 25)
        
        # Current state tracking
        self.fan_on = False
        self.red_lights_on = False
        self.table_moving_forward = False
        self.table_moving_backward = False
        self.table_at_front_limit = False
        self.table_at_back_limit = False
        
        # Timing configuration
        self.fan_auto_on_duration = config.get('fan_auto_on_duration', 3000)  # ms
        self.fan_auto_off_timeout = config.get('fan_auto_off_timeout', 5000)  # ms
        self.fan_last_trigger_time = 0
        self.red_lights_auto_on_duration = config.get('red_lights_auto_on_duration', 1000)  # ms
        self.red_lights_last_trigger_time = 0
        
        # For thread safety
        self.lock = threading.Lock()
        self.update_thread = None
        self.update_thread_running = False
        
        if self.simulation_mode:
            logging.info("Output controller running in simulation mode")
            self.gpio = LocalGPIOWrapper(simulation_mode=True)
        else:
            # Initialize GPIO with gpiod
            try:
                self.gpio = LocalGPIOWrapper(simulation_mode=False)
                
                # Set up output pins
                self.gpio.setup_output(self.fan_pin, 0)
                self.gpio.setup_output(self.red_lights_pin, 0)
                self.gpio.setup_output(self.table_forward_pin, 0)
                self.gpio.setup_output(self.table_backward_pin, 0)
                
                # Set up input pins for limit switches with pull-up resistors
                self.gpio.setup_input(self.table_front_limit_pin, pull_up=True)
                self.gpio.setup_input(self.table_back_limit_pin, pull_up=True)
                
                # Start a monitoring thread for limit switches
                self.start_monitor_thread()
                
                logging.info("Output controller initialized with gpiod")
            except Exception as e:
                logging.error(f"Failed to initialize output controller with gpiod: {e}")
                self.simulation_mode = True
                self.gpio = LocalGPIOWrapper(simulation_mode=True)
                logging.info("Falling back to simulation mode for output controller")
    
    def start_monitor_thread(self):
        """Start a background thread to monitor limit switches"""
        if self.simulation_mode:
            return
        
        self.update_thread_running = True
        self.update_thread = threading.Thread(target=self._monitor_limit_switches)
        self.update_thread.daemon = True
        self.update_thread.start()
    
    def _monitor_limit_switches(self):
        """Background thread to monitor limit switches"""
        while self.update_thread_running:
            try:
                # Read limit switch inputs (inverted logic with pull-up resistors)
                front_limit = not bool(self.gpio.read(self.table_front_limit_pin))
                back_limit = not bool(self.gpio.read(self.table_back_limit_pin))
                
                # Handle state changes
                if front_limit != self.table_at_front_limit:
                    self.table_at_front_limit = front_limit
                    if front_limit:
                        self._on_table_front_limit()
                
                if back_limit != self.table_at_back_limit:
                    self.table_at_back_limit = back_limit
                    if back_limit:
                        self._on_table_back_limit()
            except Exception as e:
                logging.error(f"Error monitoring limit switches: {e}")
            
            # Check every 100ms
            time.sleep(0.1)
    
    def set_fan(self, state):
        """Set the fan output state"""
        with self.lock:
            self.fan_on = bool(state)
            if self.simulation_mode:
                logging.debug(f"Simulation: Fan {'on' if self.fan_on else 'off'}")
            else:
                try:
                    self.gpio.write(self.fan_pin, 1 if self.fan_on else 0)
                    logging.debug(f"Fan {'on' if self.fan_on else 'off'}")
                except Exception as e:
                    logging.error(f"Error setting fan state: {e}")
    
    def set_red_lights(self, state):
        """Set the red lights output state"""
        with self.lock:
            self.red_lights_on = bool(state)
            if self.simulation_mode:
                logging.debug(f"Simulation: Red lights {'on' if self.red_lights_on else 'off'}")
            else:
                try:
                    self.gpio.write(self.red_lights_pin, 1 if self.red_lights_on else 0)
                    logging.debug(f"Red lights {'on' if self.red_lights_on else 'off'}")
                except Exception as e:
                    logging.error(f"Error setting red lights state: {e}")
    
    def set_table_forward(self, state):
        """
        Move the table forward (towards front limit switch)
        
        Safety: Won't allow forward movement if front limit switch is activated
        """
        with self.lock:
            # Safety check - don't allow forward movement if at front limit
            if state and self.table_at_front_limit:
                logging.warning("Cannot move table forward: front limit switch activated")
                state = False
            
            # Safety check - ensure we don't drive in both directions
            if state and self.table_moving_backward:
                self.set_table_backward(False)
            
            self.table_moving_forward = bool(state)
            if self.simulation_mode:
                logging.debug(f"Simulation: Table forward {'on' if self.table_moving_forward else 'off'}")
            else:
                try:
                    self.gpio.write(self.table_forward_pin, 1 if self.table_moving_forward else 0)
                    logging.debug(f"Table forward {'on' if self.table_moving_forward else 'off'}")
                except Exception as e:
                    logging.error(f"Error setting table forward state: {e}")
    
    def set_table_backward(self, state):
        """
        Move the table backward (towards back limit switch)
        
        Safety: Won't allow backward movement if back limit switch is activated
        """
        with self.lock:
            # Safety check - don't allow backward movement if at back limit
            if state and self.table_at_back_limit:
                logging.warning("Cannot move table backward: back limit switch activated")
                state = False
            
            # Safety check - ensure we don't drive in both directions
            if state and self.table_moving_forward:
                self.set_table_forward(False)
            
            self.table_moving_backward = bool(state)
            if self.simulation_mode:
                logging.debug(f"Simulation: Table backward {'on' if self.table_moving_backward else 'off'}")
            else:
                try:
                    self.gpio.write(self.table_backward_pin, 1 if self.table_moving_backward else 0)
                    logging.debug(f"Table backward {'on' if self.table_moving_backward else 'off'}")
                except Exception as e:
                    logging.error(f"Error setting table backward state: {e}")
    
    def _on_table_front_limit(self):
        """Callback when table reaches front limit switch"""
        logging.info("Table reached front limit switch")
        # Stop forward movement for safety
        self.set_table_forward(False)
    
    def _on_table_back_limit(self):
        """Callback when table reaches back limit switch"""
        logging.info("Table reached back limit switch")
        # Stop backward movement for safety
        self.set_table_backward(False)
    
    def update(self, servo_position, normal_position):
        """
        Update the outputs based on timing and servo position
        
        Args:
            servo_position: Current servo position
            normal_position: Reference position for "normal" (non-fire) state
        """
        with self.lock:
            current_time = int(time.time() * 1000)  # Current time in ms
            
            # Fan auto control based on timing
            if servo_position != normal_position:
                # Servo is in "fire" position, ensure fan is on and update trigger time
                self.fan_last_trigger_time = current_time
                if not self.fan_on:
                    self.set_fan(True)
            elif self.fan_on and (current_time - self.fan_last_trigger_time > self.fan_auto_off_timeout):
                # Auto-off timeout expired, turn fan off
                self.set_fan(False)
            
            # Red lights auto control based on timing
            if servo_position != normal_position:
                # Servo is in "fire" position, ensure red lights are on
                self.red_lights_last_trigger_time = current_time
                if not self.red_lights_on:
                    self.set_red_lights(True)
            elif self.red_lights_on and (current_time - self.red_lights_last_trigger_time > self.red_lights_auto_on_duration):
                # Auto-off timeout expired, turn red lights off
                self.set_red_lights(False)
    
    def get_status(self):
        """Get the current status of outputs"""
        with self.lock:
            # Return in the format expected by app.py
            return {
                "fan_state": self.fan_on,
                "red_lights_state": self.red_lights_on,
                "table_forward": self.table_moving_forward,
                "table_backward": self.table_moving_backward,
                "table_at_front_limit": self.table_at_front_limit,
                "table_at_back_limit": self.table_at_back_limit,
                "fan_time_remaining": 0,  # Placeholder value
                "red_lights_time_remaining": 0,  # Placeholder value
                "simulation_mode": self.simulation_mode
            }
    
    def cleanup(self):
        """Clean up GPIO pins"""
        # Stop all outputs for safety
        self.set_fan(False)
        self.set_red_lights(False)
        self.set_table_forward(False)
        self.set_table_backward(False)
        
        # Stop the monitor thread
        self.update_thread_running = False
        if self.update_thread:
            self.update_thread.join(timeout=1.0)
        
        # Clean up GPIO resources
        if not self.simulation_mode and self.gpio:
            self.gpio.cleanup()
            logging.info("Output controller GPIO cleaned up")