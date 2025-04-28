import time
import logging
import os
import random

# Check if we're running on a Raspberry Pi or in a simulation environment
if os.environ.get('SIMULATION_MODE') == 'True' or not os.path.exists('/proc/device-tree/model'):
    # For development/testing on non-Raspberry Pi systems
    logging.warning("RPi.GPIO not available. Using mock GPIO.")
    
    class MockGPIO:
        # Constants
        BCM = 11
        BOARD = 10
        OUT = 0
        IN = 1
        LOW = 0
        HIGH = 1
        PUD_UP = 22
        PUD_DOWN = 21
        
        # Keep track of pin states and configuration
        _pin_states = {}
        _pin_modes = {}  # To track if a pin is input or output
        _setup_pins = set()  # To track pins that have been set up
        
        @classmethod
        def setmode(cls, mode):
            cls.current_mode = mode
            logging.debug(f"GPIO mode set to {'BCM' if mode == cls.BCM else 'BOARD'}")
        
        @classmethod
        def setup(cls, channel, direction, pull_up_down=None, initial=None):
            # Can be a single pin or list of pins
            if isinstance(channel, list):
                for pin in channel:
                    cls._setup_pin(pin, direction, pull_up_down, initial)
            else:
                cls._setup_pin(channel, direction, pull_up_down, initial)
        
        @classmethod
        def _setup_pin(cls, pin, direction, pull_up_down, initial):
            cls._setup_pins.add(pin)
            cls._pin_modes[pin] = direction
            
            # Set initial state for output pins
            if direction == cls.OUT and initial is not None:
                cls._pin_states[pin] = initial
            elif direction == cls.IN:
                # For input pins, simulate different states
                if pin not in cls._pin_states:
                    cls._pin_states[pin] = cls.HIGH  # Default state
            
            logging.debug(f"Pin {pin} set up as {'output' if direction == cls.OUT else 'input'}")
        
        @classmethod
        def input(cls, channel):
            if channel not in cls._setup_pins:
                logging.warning(f"Reading from pin {channel} which was not set up")
                return cls.HIGH
                
            # For simulation purposes, the home switch will eventually trigger
            # after some random steps
            if channel in cls._pin_states:
                # For home switch, simulate random triggering after 10-30 calls
                if random.random() < 0.1:  # 10% chance of triggering on each call
                    cls._pin_states[channel] = cls.LOW
                
                return cls._pin_states[channel]
            return cls.HIGH
        
        @classmethod
        def output(cls, channel, state):
            if channel not in cls._setup_pins:
                logging.warning(f"Writing to pin {channel} which was not set up")
                
            # Can be a single pin or list of pins
            if isinstance(channel, list):
                for pin in channel:
                    cls._pin_states[pin] = state
            else:
                cls._pin_states[channel] = state
            
            logging.debug(f"Set pin {channel} to {'HIGH' if state == cls.HIGH else 'LOW'}")
        
        @classmethod
        def cleanup(cls, channel=None):
            if channel is None:
                # Clean up all pins
                cls._pin_states.clear()
                cls._pin_modes.clear()
                cls._setup_pins.clear()
                logging.debug("Cleaned up all GPIO pins")
            else:
                # Clean up specified pins
                if isinstance(channel, list):
                    for pin in channel:
                        if pin in cls._setup_pins:
                            cls._setup_pins.remove(pin)
                            cls._pin_modes.pop(pin, None)
                            cls._pin_states.pop(pin, None)
                else:
                    if channel in cls._setup_pins:
                        cls._setup_pins.remove(channel)
                        cls._pin_modes.pop(channel, None)
                        cls._pin_states.pop(channel, None)
                        
                logging.debug(f"Cleaned up GPIO pin(s): {channel}")
    
    GPIO = MockGPIO()
else:
    # We're on a Raspberry Pi, use the actual GPIO library
    import RPi.GPIO as GPIO

class StepperMotor:
    """
    Class to control a stepper motor using a stepper driver 
    (like A4988, DRV8825, etc.) connected to Raspberry Pi GPIO pins
    """
    
    def __init__(self, dir_pin, step_pin, enable_pin=None, home_switch_pin=None, 
                 step_delay=0.005, max_steps=2000):
        """
        Initialize the stepper motor controller
        
        Args:
            dir_pin (int): BCM pin number connected to the direction pin of the driver
            step_pin (int): BCM pin number connected to the step pin of the driver
            enable_pin (int, optional): BCM pin number connected to the enable pin of the driver
            home_switch_pin (int, optional): BCM pin number connected to the home limit switch
            step_delay (float, optional): Delay between steps in seconds
            max_steps (int, optional): Maximum number of steps allowed in one direction
        """
        self.dir_pin = dir_pin
        self.step_pin = step_pin
        self.enable_pin = enable_pin
        self.home_switch_pin = home_switch_pin
        self.step_delay = step_delay
        self.max_steps = max_steps
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.dir_pin, GPIO.OUT)
        GPIO.setup(self.step_pin, GPIO.OUT)
        
        if self.enable_pin is not None:
            GPIO.setup(self.enable_pin, GPIO.OUT)
            # Enable the motor by default (active low)
            GPIO.output(self.enable_pin, GPIO.LOW)
            
        if self.home_switch_pin is not None:
            # Setup home switch with pull-up resistor
            GPIO.setup(self.home_switch_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
        # Set initial direction
        GPIO.output(self.dir_pin, GPIO.HIGH)
        
        self.is_enabled = True
        logging.info("Stepper motor initialized on pins: DIR=%d, STEP=%d, ENABLE=%s, HOME=%s", 
                    dir_pin, step_pin, 
                    enable_pin if enable_pin is not None else "None",
                    home_switch_pin if home_switch_pin is not None else "None")
    
    def enable(self):
        """Enable the motor driver"""
        if self.enable_pin is not None:
            GPIO.output(self.enable_pin, GPIO.LOW)  # Active low
            self.is_enabled = True
            logging.debug("Motor enabled")
    
    def disable(self):
        """Disable the motor driver to save power and allow manual movement"""
        if self.enable_pin is not None:
            GPIO.output(self.enable_pin, GPIO.HIGH)  # Active low
            self.is_enabled = False
            logging.debug("Motor disabled")
    
    def step(self, steps):
        """
        Move the motor a specified number of steps
        
        Args:
            steps (int): Number of steps to move (positive = forward, negative = backward)
        
        Returns:
            int: Actual number of steps moved
        """
        if not self.is_enabled and self.enable_pin is not None:
            self.enable()
            
        # Ensure within limits
        if abs(steps) > self.max_steps:
            logging.warning(f"Step count limited to {self.max_steps}")
            steps = self.max_steps if steps > 0 else -self.max_steps
            
        # Set direction
        if steps >= 0:
            GPIO.output(self.dir_pin, GPIO.HIGH)  # Forward
            num_steps = steps
        else:
            GPIO.output(self.dir_pin, GPIO.LOW)   # Backward
            num_steps = abs(steps)
            
        logging.debug(f"Moving {'forward' if steps >= 0 else 'backward'} by {num_steps} steps")
        
        # Perform stepping
        for _ in range(num_steps):
            GPIO.output(self.step_pin, GPIO.HIGH)
            time.sleep(self.step_delay)
            GPIO.output(self.step_pin, GPIO.LOW)
            time.sleep(self.step_delay)
            
        return steps
    
    def find_home(self):
        """
        Home the motor by moving it until the home switch is triggered
        
        Returns:
            bool: True if homing was successful, False otherwise
        """
        if self.home_switch_pin is None:
            logging.error("Cannot home motor: No home switch configured")
            return False
            
        if not self.is_enabled and self.enable_pin is not None:
            self.enable()
            
        logging.info("Starting homing sequence")
        
        # First check if we're already at home
        if GPIO.input(self.home_switch_pin) == GPIO.LOW:
            logging.info("Already at home position")
            # Move away from home switch a bit
            self.step(50)
            
        # Move backward until we hit the home switch
        logging.info("Moving to find home switch...")
        GPIO.output(self.dir_pin, GPIO.LOW)  # Set direction to backward
        
        # Step until home switch is activated or max steps reached
        steps_taken = 0
        while GPIO.input(self.home_switch_pin) == GPIO.HIGH:
            GPIO.output(self.step_pin, GPIO.HIGH)
            time.sleep(self.step_delay)
            GPIO.output(self.step_pin, GPIO.LOW)
            time.sleep(self.step_delay)
            
            steps_taken += 1
            if steps_taken >= self.max_steps:
                logging.error("Homing failed: Reached maximum steps without finding home")
                return False
                
        logging.info(f"Home switch found after {steps_taken} steps")
        
        # Back off slightly from the switch
        self.step(10)  # Move forward a bit
        
        # Approach home switch slowly for precision
        GPIO.output(self.dir_pin, GPIO.LOW)  # Set direction back to backward
        while GPIO.input(self.home_switch_pin) == GPIO.HIGH:
            GPIO.output(self.step_pin, GPIO.HIGH)
            time.sleep(self.step_delay * 2)  # Slower approach
            GPIO.output(self.step_pin, GPIO.LOW)
            time.sleep(self.step_delay * 2)
            
        logging.info("Homing completed successfully")
        return True
        
    def cleanup(self):
        """Clean up GPIO pins"""
        if self.enable_pin is not None:
            self.disable()
            
        # Create a list of valid pins to clean up
        pins_to_cleanup = [self.dir_pin, self.step_pin]
        if self.enable_pin is not None:
            pins_to_cleanup.append(self.enable_pin)
        if self.home_switch_pin is not None:
            pins_to_cleanup.append(self.home_switch_pin)
            
        GPIO.cleanup(pins_to_cleanup)
        logging.info("Stepper motor GPIO cleaned up")
