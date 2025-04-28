"""
Input control module for handling GPIO inputs for remote control.
This module handles the physical buttons and switches for controlling
the machine remotely without using the web interface.
"""
import time
import logging
import threading
import os
from gpiozero import Button
from config import get_gpio_config

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
        self.gpio_config = get_gpio_config()
        self.stepper_handler = stepper_handler
        self.servo_handler = servo_handler
        
        # Check if running in simulation mode
        self.simulation_mode = os.environ.get('SIMULATION_MODE', 'False').lower() == 'true'
        
        if self.simulation_mode:
            logging.info("Input controller running in simulation mode")
            self.inputs_initialized = False
            return
            
        try:
            # Initialize input pins with pull-up resistors (buttons/switches connect to ground)
            self.button_in = Button(
                self.gpio_config['button_in_pin'],
                pull_up=True,  # Use pull-up resistor (button connects to ground)
                bounce_time=0.1  # Debounce time in seconds
            )
            
            self.button_out = Button(
                self.gpio_config['button_out_pin'],
                pull_up=True,
                bounce_time=0.1
            )
            
            self.fire_button = Button(
                self.gpio_config['fire_button_pin'],
                pull_up=True,
                bounce_time=0.1
            )
            
            self.servo_invert_switch = Button(
                self.gpio_config['servo_invert_switch_pin'],
                pull_up=True,
                bounce_time=0.1
            )
            
            # Set up button press and release event handlers
            self.setup_event_handlers()
            
            # Tracking variables for button state
            self.in_button_held = False
            self.out_button_held = False
            self.in_button_press_time = 0
            self.out_button_press_time = 0
            self.in_button_press_count = 0
            self.out_button_press_count = 0
            self.last_press_time = 0
            
            # Constants
            self.multi_press_timeout = 1.0  # seconds
            self.hold_threshold = 1.0  # seconds
            
            # Start button monitoring thread
            self.running = True
            self.button_monitor_thread = threading.Thread(target=self._button_monitor, daemon=True)
            self.button_monitor_thread.start()
            
            logging.info("Input pins initialized successfully")
            self.inputs_initialized = True
            
        except Exception as e:
            logging.error(f"Failed to initialize input pins: {e}")
            logging.info("Falling back to simulation mode")
            self.simulation_mode = True
            self.inputs_initialized = False
    
    def setup_event_handlers(self):
        """Set up button event handlers"""
        # Single press handlers
        self.button_in.when_pressed = self._on_in_button_pressed
        self.button_in.when_released = self._on_in_button_released
        
        self.button_out.when_pressed = self._on_out_button_pressed
        self.button_out.when_released = self._on_out_button_released
        
        self.fire_button.when_pressed = self._on_fire_button_pressed
        self.fire_button.when_released = self._on_fire_button_released
        
        # Switch state change
        self.servo_invert_switch.when_pressed = self._on_servo_invert_enabled
        self.servo_invert_switch.when_released = self._on_servo_invert_disabled
    
    def _on_in_button_pressed(self):
        logging.debug("IN button pressed")
        self.in_button_press_time = time.time()
        self.in_button_press_count += 1
        self.last_press_time = time.time()
    
    def _on_in_button_released(self):
        logging.debug("IN button released")
        press_duration = time.time() - self.in_button_press_time
        self.in_button_held = False
        
        # If held for jogging, do nothing more (jog stops on release)
        if press_duration >= self.hold_threshold:
            if self.stepper_handler:
                self.stepper_handler('jog_stop')
            return
    
    def _on_out_button_pressed(self):
        logging.debug("OUT button pressed")
        self.out_button_press_time = time.time()
        self.out_button_press_count += 1
        self.last_press_time = time.time()
    
    def _on_out_button_released(self):
        logging.debug("OUT button released")
        press_duration = time.time() - self.out_button_press_time
        self.out_button_held = False
        
        # If held for jogging, do nothing more (jog stops on release)
        if press_duration >= self.hold_threshold:
            if self.stepper_handler:
                self.stepper_handler('jog_stop')
            return
    
    def _on_fire_button_pressed(self):
        logging.debug("Fire button pressed")
        if self.servo_handler:
            self.servo_handler('fire')
    
    def _on_fire_button_released(self):
        logging.debug("Fire button released")
        if self.servo_handler:
            self.servo_handler('reset')
    
    def _on_servo_invert_enabled(self):
        logging.debug("Servo invert enabled")
        if self.servo_handler:
            self.servo_handler('set_inverted', inverted=True)
    
    def _on_servo_invert_disabled(self):
        logging.debug("Servo invert disabled")
        if self.servo_handler:
            self.servo_handler('set_inverted', inverted=False)
    
    def _button_monitor(self):
        """Monitor button states for multi-press and held actions"""
        while self.running:
            current_time = time.time()
            
            # Check for IN button held state for jogging
            if (not self.in_button_held and 
                self.in_button_press_time > 0 and 
                current_time - self.in_button_press_time >= self.hold_threshold and
                self.button_in.is_pressed):
                
                logging.debug("IN button held - start jogging")
                self.in_button_held = True
                if self.stepper_handler:
                    self.stepper_handler('jog', direction='backward')
            
            # Check for OUT button held state for jogging
            if (not self.out_button_held and 
                self.out_button_press_time > 0 and 
                current_time - self.out_button_press_time >= self.hold_threshold and
                self.button_out.is_pressed):
                
                logging.debug("OUT button held - start jogging")
                self.out_button_held = True
                if self.stepper_handler:
                    self.stepper_handler('jog', direction='forward')
            
            # Check for multi-press sequences that have timed out
            if (self.in_button_press_count > 0 and 
                current_time - self.last_press_time >= self.multi_press_timeout and
                not self.button_in.is_pressed):
                
                # Handle IN button multi-press actions
                if self.in_button_press_count == 1:
                    # Single press - small backward jog
                    if self.stepper_handler:
                        self.stepper_handler('jog_step', direction='backward')
                elif self.in_button_press_count == 2:
                    # Double press - index movement backward
                    if self.stepper_handler:
                        self.stepper_handler('index', direction='backward')
                elif self.in_button_press_count == 3:
                    # Triple press - home the stepper
                    if self.stepper_handler:
                        self.stepper_handler('home')
                
                # Reset press count
                self.in_button_press_count = 0
            
            # Check for OUT button multi-press sequences that have timed out
            if (self.out_button_press_count > 0 and 
                current_time - self.last_press_time >= self.multi_press_timeout and
                not self.button_out.is_pressed):
                
                # Handle OUT button multi-press actions
                if self.out_button_press_count == 1:
                    # Single press - small forward jog
                    if self.stepper_handler:
                        self.stepper_handler('jog_step', direction='forward')
                elif self.out_button_press_count == 2:
                    # Double press - index movement forward
                    if self.stepper_handler:
                        self.stepper_handler('index', direction='forward')
                
                # Reset press count
                self.out_button_press_count = 0
            
            # Sleep to reduce CPU usage
            time.sleep(0.05)
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        if self.inputs_initialized and not self.simulation_mode:
            # Wait for monitoring thread to end
            if hasattr(self, 'button_monitor_thread') and self.button_monitor_thread.is_alive():
                self.button_monitor_thread.join(timeout=1.0)
            
            # Close button objects
            if hasattr(self, 'button_in'):
                self.button_in.close()
            if hasattr(self, 'button_out'):
                self.button_out.close()
            if hasattr(self, 'fire_button'):
                self.fire_button.close()
            if hasattr(self, 'servo_invert_switch'):
                self.servo_invert_switch.close()
            
            logging.info("Input pins cleaned up")