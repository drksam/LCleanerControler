"""
Output control module for managing outputs (fan, red lights, table movement) using gpiod.
"""
import time
import logging
import os
import threading
from config import get_gpio_config, get_system_config, get_timing_config
from gpio_controller_wrapper import LocalGPIOWrapper

class OutputController:
    """
    Controller for fan, red lights, and table movement outputs with timeout functionality
    """
    
    def __init__(self):
        """Initialize the output controller"""
        logging.info(f"OutputController __init__ from file: {__file__}")
        logging.info("OutputController version: 2025-07-09 diagnostic logging patch")
        
        # Load configuration
        config = get_gpio_config()
        system_config = get_system_config()
        
        # Get operation mode from system config
        operation_mode = system_config.get('operation_mode', 'simulation')
        
        # Set simulation mode based on system configuration or environment
        self.simulation_mode = (operation_mode == 'simulation') or (os.environ.get('SIMULATION_MODE', 'False').lower() == 'true')
        
        # Check if we should force hardware mode (used in prototype mode)
        self.force_hardware = os.environ.get('FORCE_HARDWARE', 'False').lower() == 'true'
        
        logging.info(f"OutputController __init__: simulation_mode={self.simulation_mode}, operation_mode={operation_mode}")
        
        # GPIO pin assignments from config (with correct defaults matching Default pinout.txt)
        self.fan_pin = config.get('fan_pin', 26)
        self.red_lights_pin = config.get('red_lights_pin', 16)
        self.table_forward_pin = config.get('table_forward_pin', 13)
        self.table_backward_pin = config.get('table_backward_pin', 6)
        self.table_front_switch_pin = config.get('table_front_switch_pin', 21)
        self.table_back_switch_pin = config.get('table_back_switch_pin', 20)
        
        # Current state tracking
        self.fan_on = False
        self.red_lights_on = False
        self.table_moving_forward = False
        self.table_moving_backward = False
        self.table_at_front_limit = False
        self.table_at_back_limit = False
        
        # Mode tracking - manual or auto
        self.fan_mode = 'auto'  # Default to auto mode
        self.lights_mode = 'auto'  # Default to auto mode
        
        # Timing configuration - load from timing config
        timing_config = get_timing_config()
        self.fan_auto_on_duration = config.get('fan_auto_on_duration', 3000)  # ms
        self.fan_auto_off_timeout = timing_config.get('fan_off_delay', 5000)  # ms
        self.fan_last_trigger_time = 0
        self.red_lights_auto_off_timeout = timing_config.get('red_lights_off_delay', 3000)  # ms
        self.red_lights_last_trigger_time = 0
        
        # For thread safety - using RLock to allow reentrant calls
        self.lock = threading.RLock()
        self.update_thread = None
        self.update_thread_running = False
        
        if self.simulation_mode:
            logging.info("Output controller running in simulation mode")
            self.gpio = LocalGPIOWrapper(simulation_mode=True)
        else:
            # Initialize GPIO with gpiod
            try:
                logging.info("Attempting to initialize LocalGPIOWrapper for output controller")
                self.gpio = LocalGPIOWrapper(simulation_mode=False)
                
                # Set up output pins
                self.gpio.setup_output(self.fan_pin, 0)
                self.gpio.setup_output(self.red_lights_pin, 0)
                self.gpio.setup_output(self.table_forward_pin, 0)
                self.gpio.setup_output(self.table_backward_pin, 0)
                
                # Set up input pins for limit switches with pull-up resistors
                self.gpio.setup_input(self.table_front_switch_pin, pull_up=True)
                self.gpio.setup_input(self.table_back_switch_pin, pull_up=True)
                
                # Start a monitoring thread for limit switches
                self.start_monitor_thread()
                
                logging.info("Output controller initialized with gpiod")
            except Exception as e:
                logging.error(f"Failed to initialize output controller with gpiod: {e}")
                if self.force_hardware:
                    # In prototype mode with FORCE_HARDWARE, we should raise the exception
                    # rather than falling back to simulation mode
                    logging.error("FORCE_HARDWARE is set - cannot fall back to simulation mode")
                    raise
                else:
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
                front_limit = not bool(self.gpio.read(self.table_front_switch_pin))
                back_limit = not bool(self.gpio.read(self.table_back_switch_pin))
                
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
        logging.info(f"OutputController.set_fan called: state={state}")
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
        logging.info(f"OutputController.set_red_lights called: state={state}")
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
    
    def set_fan_mode(self, mode):
        """Set the fan control mode (manual or auto)"""
        logging.info(f"OutputController.set_fan_mode called: mode={mode}")
        with self.lock:
            self.fan_mode = mode
            if mode == 'manual':
                # In manual mode, stop any automatic behavior
                logging.debug("Fan set to manual mode")
            else:
                # In auto mode, the update loop will handle fan control
                logging.debug("Fan set to auto mode")
    
    def set_lights_mode(self, mode):
        """Set the lights control mode (manual or auto)"""
        logging.info(f"OutputController.set_lights_mode called: mode={mode}")
        with self.lock:
            self.lights_mode = mode
            if mode == 'manual':
                # In manual mode, stop any automatic behavior
                logging.debug("Lights set to manual mode")
            else:
                # In auto mode, the update loop will handle lights control
                logging.debug("Lights set to auto mode")
    
    def set_table_forward(self, state):
        logging.info(f"OutputController.set_table_forward called: state={state}")
        """
        Move the table forward (towards front limit switch)
        
        Safety: Won't allow forward movement if front limit switch is activated
        """
        logging.info(f"set_table_forward: attempting to acquire lock")
        with self.lock:
            logging.info(f"set_table_forward: lock acquired, checking safety")
            # Safety check - don't allow forward movement if at front limit
            if state and self.table_at_front_limit:
                logging.warning("Cannot move table forward: front limit switch activated")
                state = False
            
            # Safety check - ensure we don't drive in both directions
            if state and self.table_moving_backward:
                logging.info(f"set_table_forward: stopping backward movement first")
                # Stop backward movement directly instead of recursive call
                self.table_moving_backward = False
                if not self.simulation_mode:
                    try:
                        self.gpio.write(self.table_backward_pin, 0)
                        logging.info(f"set_table_forward: stopped backward movement (pin {self.table_backward_pin} = 0)")
                    except Exception as e:
                        logging.error(f"Error stopping backward movement: {e}")
            
            logging.info(f"set_table_forward: setting state to {state}")
            self.table_moving_forward = bool(state)
            if self.simulation_mode:
                logging.debug(f"Simulation: Table forward {'on' if self.table_moving_forward else 'off'}")
            else:
                try:
                    logging.info(f"set_table_forward: writing GPIO pin {self.table_forward_pin} = {1 if self.table_moving_forward else 0}")
                    self.gpio.write(self.table_forward_pin, 1 if self.table_moving_forward else 0)
                    logging.info(f"set_table_forward: GPIO write completed successfully")
                    logging.debug(f"Table forward {'on' if self.table_moving_forward else 'off'}")
                except Exception as e:
                    logging.error(f"Error setting table forward state: {e}")
        logging.info(f"set_table_forward: lock released, function complete")
    
    def set_table_backward(self, state):
        logging.info(f"OutputController.set_table_backward called: state={state}")
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
                logging.info(f"set_table_backward: stopping forward movement first")
                # Stop forward movement directly instead of recursive call
                self.table_moving_forward = False
                if not self.simulation_mode:
                    try:
                        self.gpio.write(self.table_forward_pin, 0)
                        logging.info(f"set_table_backward: stopped forward movement (pin {self.table_forward_pin} = 0)")
                    except Exception as e:
                        logging.error(f"Error stopping forward movement: {e}")
            
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
        # Stop forward movement for safety - use lock to avoid race conditions
        with self.lock:
            if self.table_moving_forward:
                logging.info("Front limit: stopping forward movement")
                self.table_moving_forward = False
                if not self.simulation_mode:
                    try:
                        self.gpio.write(self.table_forward_pin, 0)
                        logging.info(f"Front limit: stopped forward movement (pin {self.table_forward_pin} = 0)")
                    except Exception as e:
                        logging.error(f"Error stopping forward movement at front limit: {e}")
    
    def _on_table_back_limit(self):
        """Callback when table reaches back limit switch"""
        logging.info("Table reached back limit switch")
        # Stop backward movement for safety - use lock to avoid race conditions
        with self.lock:
            if self.table_moving_backward:
                logging.info("Back limit: stopping backward movement")
                self.table_moving_backward = False
                if not self.simulation_mode:
                    try:
                        self.gpio.write(self.table_backward_pin, 0)
                        logging.info(f"Back limit: stopped backward movement (pin {self.table_backward_pin} = 0)")
                    except Exception as e:
                        logging.error(f"Error stopping backward movement at back limit: {e}")
    
    def update(self, servo_position, normal_position):
        """
        Update the outputs based on timing and servo position
        
        Args:
            servo_position: Current servo position
            normal_position: Reference position for "normal" (non-fire) state
        """
        with self.lock:
            current_time = int(time.time() * 1000)  # Current time in ms
            
            # Fan auto control based on timing (only when in auto mode)
            if self.fan_mode == "auto":
                if servo_position != normal_position:
                    # Servo is in "fire" position, ensure fan is on and update trigger time
                    self.fan_last_trigger_time = current_time
                    if not self.fan_on:
                        self.set_fan(True)
                elif self.fan_on and (current_time - self.fan_last_trigger_time > self.fan_auto_off_timeout):
                    # Auto-off timeout expired, turn fan off
                    self.set_fan(False)
            
            # Red lights auto control based on timing (only when in auto mode)
            if self.lights_mode == "auto":
                if servo_position != normal_position:
                    # Servo is in "fire" position, ensure red lights are on
                    self.red_lights_last_trigger_time = current_time
                    if not self.red_lights_on:
                        self.set_red_lights(True)
                elif self.red_lights_on and (current_time - self.red_lights_last_trigger_time > self.red_lights_auto_off_timeout):
                    # Auto-off timeout expired, turn red lights off
                    self.set_red_lights(False)
    
    # --- Subsystem Independence ---
    # Table, stepper, and servo controls are independent.
    # Stopping the laser/servo does NOT stop the table, and vice versa.
    # Only stop_all_outputs() (E-Stop) stops everything at once.
    # Do NOT call stop_table() or stop_servo() from unrelated subsystem logic.
    #
    # update() only manages fan and red lights based on servo position.
    # Table movement is controlled solely by set_table_forward/backward and stop_table().
    #
    # If you add new stop logic for other subsystems (e.g., stepper, servo), ensure it does not interfere with table or other outputs.
    #
    # E-Stop (stop_all_outputs) is the only method that stops all outputs for safety.
    # -----------------------------------
    
    def stop_table(self):
        logging.info("OutputController.stop_table called")
        """Stop all table movement (for momentary button release or safety)"""
        with self.lock:
            self.set_table_forward(False)
            self.set_table_backward(False)
            self.table_moving_forward = False
            self.table_moving_backward = False
            logging.info("Table movement stopped (stop_table called)")

    def stop_all_outputs(self, servo=None):
        logging.info("OutputController.stop_all_outputs called")
        """Emergency stop: move servo to A, then turn off all outputs (fan, lights, table)"""
        with self.lock:
            if servo is not None:
                try:
                    servo.move_to_a()
                    logging.info("Servo moved to position A for E-Stop")
                except Exception as e:
                    logging.error(f"Error moving servo to position A during E-Stop: {e}")
            self.set_fan(False)
            self.set_red_lights(False)
            self.stop_table()
            logging.info("All outputs stopped (emergency stop)")
    
    def get_status(self):
        logging.info("OutputController.get_status called")
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
                "simulation_mode": self.simulation_mode,
                "table_moving": self.table_moving_forward or self.table_moving_backward
            }
    
    def cleanup(self):
        logging.info("OutputController.cleanup called")
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
    
    def move_table_forward(self):
        logging.info("move_table_forward called")
        try:
            self.set_table_forward(True)
            logging.info("move_table_forward: set_table_forward(True) called successfully")
        except Exception as e:
            logging.error(f"move_table_forward: Exception: {e}")
            raise

    def move_table_backward(self):
        logging.info("move_table_backward called")
        try:
            self.set_table_backward(True)
            logging.info("move_table_backward: set_table_backward(True) called successfully")
        except Exception as e:
            logging.error(f"move_table_backward: Exception: {e}")
            raise

    def update_timing_config(self):
        """Reload timing configuration from config file"""
        try:
            with self.lock:
                old_fan_timeout = getattr(self, 'fan_auto_off_timeout', None)
                old_lights_timeout = getattr(self, 'red_lights_auto_off_timeout', None)
                
                self.timing_config = get_timing_config()
                
                # Update timeout values from timing config
                # Convert from seconds to milliseconds for internal use
                self.fan_auto_off_timeout = self.timing_config.get('fan_off_delay', 5000)  # Already in ms
                self.red_lights_auto_off_timeout = self.timing_config.get('red_lights_off_delay', 3000)  # Already in ms
                
                logging.info(f"Timing configuration updated:")
                logging.info(f"  Fan delay: {old_fan_timeout}ms -> {self.fan_auto_off_timeout}ms")
                logging.info(f"  Red lights delay: {old_lights_timeout}ms -> {self.red_lights_auto_off_timeout}ms")
                logging.info(f"  Full timing config: {self.timing_config}")
        except Exception as e:
            logging.error(f"Error updating timing configuration: {e}")