"""
Input control module for handling GPIO inputs for remote control using gpiod.
This module handles the physical buttons and switches for controlling
the machine remotely without using the web interface.
"""
import time
import logging
import threading
from config import get_gpio_config, get_system_config
from gpio_controller_wrapper import LocalGPIOWrapper

class InputController:
    """
    Controller for GPIO inputs that trigger stepper and servo actions
    """
    
    def __init__(self, stepper_handler=None, servo_handler=None):
        """
        Initialize the input controller with callbacks
        
        Args:
            stepper_handler: Callback function for stepper motor actions
                  Signature: stepper_handler(action, **kwargs)
            servo_handler: Callback function for servo actions
                  Signature: servo_handler(action, **kwargs)
        """
        # Load configuration
        config = get_gpio_config()
        system_config = get_system_config()
        
        # Get operation mode from system config
        operation_mode = system_config.get('operation_mode', 'simulation')
        
        # Set simulation mode based on system configuration
        self.simulation_mode = operation_mode == 'simulation'
        
        logging.info(f"InputController __init__: simulation_mode={self.simulation_mode}, operation_mode={operation_mode}")
        
        # GPIO pin assignments
        self.in_button_pin = config.get('in_button_pin', 5)
        self.out_button_pin = config.get('out_button_pin', 6)
        self.fire_button_pin = config.get('fire_button_pin', 13)
        self.servo_invert_switch_pin = config.get('servo_invert_switch_pin', 19)
        
        # Input state tracking
        self.in_button_pressed = False
        self.out_button_pressed = False
        self.fire_button_pressed = False
        self.servo_inverted = False
        
        # Multi-press handling
        self.in_button_press_count = 0
        self.in_button_last_press_time = 0
        self.out_button_press_count = 0
        self.out_button_last_press_time = 0
        self.button_multi_press_timeout = 500  # ms
        
        # Long press handling
        self.in_button_press_start_time = 0
        self.out_button_press_start_time = 0
        self.fire_button_press_start_time = 0
        self.button_long_press_threshold = 1000  # ms
        
        # Callbacks
        self.stepper_handler = stepper_handler
        self.servo_handler = servo_handler
        
        # For thread safety
        self.lock = threading.Lock()
        self.monitor_thread = None
        self.monitor_thread_running = False
        
        if self.simulation_mode:
            logging.info("Input controller running in simulation mode")
            self.gpio = LocalGPIOWrapper(simulation_mode=True)
        else:
            # Initialize GPIO with gpiod
            try:
                logging.info("Attempting to initialize LocalGPIOWrapper for input controller")
                self.gpio = LocalGPIOWrapper(simulation_mode=False)
                logging.info("Input controller initialized with gpiod")
                
                # Set up input pins with pull-up resistors
                self.gpio.setup_input(self.in_button_pin, pull_up=True)
                self.gpio.setup_input(self.out_button_pin, pull_up=True)
                self.gpio.setup_input(self.fire_button_pin, pull_up=True)
                self.gpio.setup_input(self.servo_invert_switch_pin, pull_up=True)
                
                # Start a monitoring thread for inputs
                self.setup_event_handlers()
                
                logging.info("Input controller initialized with gpiod")
            except Exception as e:
                logging.error(f"Failed to initialize input controller with gpiod: {e}")
                self.simulation_mode = True
                self.gpio = LocalGPIOWrapper(simulation_mode=True)
                logging.info("Falling back to simulation mode for input controller")
    
    def setup_event_handlers(self):
        """Set up button event handlers"""
        if self.simulation_mode:
            return
        
        # Start a monitoring thread for inputs
        self.monitor_thread_running = True
        self.monitor_thread = threading.Thread(target=self._button_monitor)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def _on_in_button_pressed(self):
        """Handle in button press event"""
        with self.lock:
            self.in_button_pressed = True
            
            # Record press time for multi-press detection
            current_time = int(time.time() * 1000)
            if current_time - self.in_button_last_press_time < self.button_multi_press_timeout:
                self.in_button_press_count += 1
            else:
                self.in_button_press_count = 1
            
            self.in_button_last_press_time = current_time
            self.in_button_press_start_time = current_time
            
            # Single press triggers stepper movement
            if self.stepper_handler:
                self.stepper_handler("jog", direction=0)  # In direction
                logging.debug("IN button pressed - jogging stepper in")
    
    def _on_in_button_released(self):
        """Handle in button release event"""
        with self.lock:
            if not self.in_button_pressed:
                return
                
            self.in_button_pressed = False
            
            # Check for long press
            current_time = int(time.time() * 1000)
            press_duration = current_time - self.in_button_press_start_time
            
            if press_duration >= self.button_long_press_threshold:
                # Long press - home stepper
                if self.stepper_handler:
                    self.stepper_handler("home")
                    logging.debug("IN button long press - homing stepper")
            else:
                # Check for double press
                if self.in_button_press_count >= 2:
                    # Double press - move to saved position 1
                    if self.stepper_handler:
                        self.stepper_handler("move_to_preset", preset=1)
                        logging.debug("IN button double press - moving to preset 1")
                # Else was just a short single press, already handled on press
            
            # Always stop motion on release for safety
            if self.stepper_handler:
                self.stepper_handler("stop")
    
    def _on_out_button_pressed(self):
        """Handle out button press event"""
        with self.lock:
            self.out_button_pressed = True
            
            # Record press time for multi-press detection
            current_time = int(time.time() * 1000)
            if current_time - self.out_button_last_press_time < self.button_multi_press_timeout:
                self.out_button_press_count += 1
            else:
                self.out_button_press_count = 1
            
            self.out_button_last_press_time = current_time
            self.out_button_press_start_time = current_time
            
            # Single press triggers stepper movement
            if self.stepper_handler:
                self.stepper_handler("jog", direction=1)  # Out direction
                logging.debug("OUT button pressed - jogging stepper out")
    
    def _on_out_button_released(self):
        """Handle out button release event"""
        with self.lock:
            if not self.out_button_pressed:
                return
                
            self.out_button_pressed = False
            
            # Check for long press
            current_time = int(time.time() * 1000)
            press_duration = current_time - self.out_button_press_start_time
            
            if press_duration >= self.button_long_press_threshold:
                # Long press - move stepper all the way out
                if self.stepper_handler:
                    self.stepper_handler("move_to_max")
                    logging.debug("OUT button long press - moving stepper to max")
            else:
                # Check for double press
                if self.out_button_press_count >= 2:
                    # Double press - move to saved position 2
                    if self.stepper_handler:
                        self.stepper_handler("move_to_preset", preset=2)
                        logging.debug("OUT button double press - moving to preset 2")
                # Else was just a short single press, already handled on press
            
            # Always stop motion on release for safety
            if self.stepper_handler:
                self.stepper_handler("stop")
    
    def _on_fire_button_pressed(self):
        """Handle fire button press event"""
        with self.lock:
            self.fire_button_pressed = True
            self.fire_button_press_start_time = int(time.time() * 1000)
            
            # Fire the laser
            if self.servo_handler:
                self.servo_handler("fire")
                logging.debug("FIRE button pressed - firing laser")
    
    def _on_fire_button_released(self):
        """Handle fire button release event"""
        with self.lock:
            if not self.fire_button_pressed:
                return
                
            self.fire_button_pressed = False
            
            # Check for long press
            current_time = int(time.time() * 1000)
            press_duration = current_time - self.fire_button_press_start_time
            
            # Stop firing
            if self.servo_handler:
                self.servo_handler("stop_fire")
                
                # If was a long press, start fiber sequence
                if press_duration >= self.button_long_press_threshold:
                    self.servo_handler("start_sequence")
                    logging.debug("FIRE button long press - starting fiber sequence")
                else:
                    logging.debug("FIRE button released - stopping fire")
    
    def _on_servo_invert_enabled(self):
        """Handle servo invert switch enabled"""
        with self.lock:
            self.servo_inverted = True
            
            # Update servo configuration
            if self.servo_handler:
                self.servo_handler("set_inverted", inverted=True)
                logging.debug("Servo invert switch enabled")
    
    def _on_servo_invert_disabled(self):
        """Handle servo invert switch disabled"""
        with self.lock:
            self.servo_inverted = False
            
            # Update servo configuration
            if self.servo_handler:
                self.servo_handler("set_inverted", inverted=False)
                logging.debug("Servo invert switch disabled")
    
    def _button_monitor(self):
        """Monitor button states for multi-press and held actions"""
        previous_in_button = False
        previous_out_button = False
        previous_fire_button = False
        previous_servo_invert = False
        
        while self.monitor_thread_running:
            try:
                # Read button inputs (inverted logic with pull-up resistors)
                in_button = not bool(self.gpio.read(self.in_button_pin))
                out_button = not bool(self.gpio.read(self.out_button_pin))
                fire_button = not bool(self.gpio.read(self.fire_button_pin))
                servo_invert = not bool(self.gpio.read(self.servo_invert_switch_pin))
                
                # Detect edge changes
                if in_button != previous_in_button:
                    if in_button:
                        self._on_in_button_pressed()
                    else:
                        self._on_in_button_released()
                    previous_in_button = in_button
                
                if out_button != previous_out_button:
                    if out_button:
                        self._on_out_button_pressed()
                    else:
                        self._on_out_button_released()
                    previous_out_button = out_button
                
                if fire_button != previous_fire_button:
                    if fire_button:
                        self._on_fire_button_pressed()
                    else:
                        self._on_fire_button_released()
                    previous_fire_button = fire_button
                
                if servo_invert != previous_servo_invert:
                    if servo_invert:
                        self._on_servo_invert_enabled()
                    else:
                        self._on_servo_invert_disabled()
                    previous_servo_invert = servo_invert
            except Exception as e:
                logging.error(f"Error monitoring buttons: {e}")
            
            # Check every 20ms for responsive button handling
            time.sleep(0.02)
    
    def cleanup(self):
        """Clean up resources"""
        # Stop the monitor thread
        self.monitor_thread_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        
        # Clean up GPIO resources
        if not self.simulation_mode and self.gpio:
            self.gpio.cleanup()
            logging.info("Input controller GPIO cleaned up")