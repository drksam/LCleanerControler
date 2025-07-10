"""
GPIO Controller Wrapper for ShopLaserRoom application.
This module provides wrapper classes for GPIOController library to replace gpiozero.
"""
import os
import time
import logging
import threading
import platform
import importlib.util
from typing import Optional, Callable, Dict, Any

# Determine default serial port based on platform
if platform.system() == 'Windows':
    DEFAULT_SERIAL_PORT = "COM3"  # Default Windows port, adjust as needed
else:
    DEFAULT_SERIAL_PORT = "/dev/ttyUSB0"  # Default Linux port

# Check if FORCE_HARDWARE flag is set
FORCE_HARDWARE = os.environ.get('FORCE_HARDWARE', 'False').lower() == 'true'

# Determine if we're in simulation mode based on the existence of sim.txt and system platform
IS_WINDOWS = platform.system() == 'Windows'
SIM_FILE_EXISTS = os.path.exists(os.path.join(os.path.dirname(__file__), 'sim.txt'))
DEFAULT_SIMULATION_MODE = IS_WINDOWS or SIM_FILE_EXISTS

# Conditional import for GPIOController
try:
    from gpioctrl import GPIOController
    GPIOCTRL_AVAILABLE = True
except ImportError:
    GPIOCTRL_AVAILABLE = False
    logging.warning("GPIOController library not available. Simulation mode will be used.")
    if FORCE_HARDWARE:
        logging.error("FORCE_HARDWARE is set but GPIOController library is not available!")
        raise ImportError("GPIOController library is required when FORCE_HARDWARE is enabled")

# Conditional import for local GPIO control via gpiod - using dynamic import to avoid editor warnings
GPIOD_AVAILABLE = False
gpiod = None

if not IS_WINDOWS:  # Only try to import gpiod on non-Windows platforms
    # Use dynamic import to avoid editor warnings
    gpiod_spec = importlib.util.find_spec('gpiod')
    if gpiod_spec:
        try:
            gpiod = importlib.util.module_from_spec(gpiod_spec)
            gpiod_spec.loader.exec_module(gpiod)
            GPIOD_AVAILABLE = True
        except ImportError:
            GPIOD_AVAILABLE = False
            logging.warning("gpiod library not available. Local GPIO will use simulation mode.")
            if FORCE_HARDWARE:
                logging.error("FORCE_HARDWARE is set but gpiod library is not available!")
                raise ImportError("gpiod library is required when FORCE_HARDWARE is enabled")
else:
    # On Windows, create a mock gpiod module for development purposes
    class MockGpiod:
        """Mock implementation for gpiod on Windows"""
        class chip:
            def __init__(self, chip_name):
                self.name = chip_name
                logging.debug(f"MockGpiod: Created chip {chip_name}")
                
            def get_line(self, pin_offset):
                return MockGpiod.line(pin_offset)
                
            def close(self):
                logging.debug(f"MockGpiod: Closed chip {self.name}")
        
        class line:
            def __init__(self, pin_offset):
                self.pin = pin_offset
                self.value = 0
                
            def request(self, config):
                logging.debug(f"MockGpiod: Requested line {self.pin}")
                
            def set_value(self, value):
                self.value = value
                logging.debug(f"MockGpiod: Set line {self.pin} to {value}")
                
            def get_value(self):
                # Return random value to simulate actual hardware
                import random
                return random.choice([0, 1])
                
            def release(self):
                logging.debug(f"MockGpiod: Released line {self.pin}")
        
        class line_request:
            DIRECTION_OUTPUT = 1
            DIRECTION_INPUT = 2
            FLAG_BIAS_PULL_UP = 4
            
            def __init__(self):
                self.consumer = ""
                self.request_type = 0
                self.flags = 0
    
    gpiod = MockGpiod()
    logging.info("Using mock gpiod implementation on Windows")

class ServoWrapper:
    """
    Wrapper for GPIOController servo functionality to replace gpiozero.AngularServo.
    Implements compatible functionality while using GPIOController under the hood.
    """
    
    def __init__(self, 
                 pin, 
                 initial_angle=0,
                 min_angle=-90, 
                 max_angle=90, 
                 min_pulse_width=0.5/1000, 
                 max_pulse_width=2.5/1000,
                 frame_width=20/1000,
                 simulation_mode=False,
                 serial_port=None):
        """
        Initialize the servo wrapper.
        
        Args:
            pin: GPIO pin number for the servo
            initial_angle: Initial angle to set
            min_angle: Minimum allowed angle
            max_angle: Maximum allowed angle
            min_pulse_width: Minimum pulse width (for compatibility, not used)
            max_pulse_width: Maximum pulse width (for compatibility, not used)
            frame_width: Frame width (for compatibility, not used)
            simulation_mode: Whether to run in simulation mode
            serial_port: Serial port for the GPIOController
        """
        self.pin = pin
        self.min_angle = min_angle
        self.max_angle = max_angle
        self._angle = initial_angle
        self.simulation_mode = simulation_mode
        self.serial_port = serial_port or DEFAULT_SERIAL_PORT
        self._controller = None
        
        logging.info(f"ServoWrapper __init__: simulation_mode={simulation_mode}, FORCE_HARDWARE={os.environ.get('FORCE_HARDWARE')}, GPIOCTRL_AVAILABLE={GPIOCTRL_AVAILABLE}")
        # Initialize controller if not in simulation mode
        if not simulation_mode and GPIOCTRL_AVAILABLE:
            try:
                logging.info(f"Attempting to initialize GPIOController for servo on port {self.serial_port}")
                self._controller = GPIOController(port=self.serial_port)
                logging.info(f"GPIOController initialized for servo")
                # Set initial angle
                self._controller.set_servo(pin=pin, angle=initial_angle)
                logging.info(f"Initialized ServoWrapper with GPIOController on pin {pin}")
            except Exception as e:
                logging.error(f"Failed to initialize GPIOController for servo: {e}")
                if FORCE_HARDWARE:
                    logging.error("FORCE_HARDWARE is set - cannot fall back to simulation mode")
                    raise
                logging.info("Falling back to simulation mode for ServoWrapper")
        else:
            if FORCE_HARDWARE and not GPIOCTRL_AVAILABLE:
                logging.error("FORCE_HARDWARE is set but GPIOController library is not available!")
                raise ImportError("GPIOController library is required when FORCE_HARDWARE is enabled")
            
            self.simulation_mode = True
            logging.info(f"ServoWrapper initialized in simulation mode (reason: simulation_mode={simulation_mode}, GPIOCTRL_AVAILABLE={GPIOCTRL_AVAILABLE})")
    
    @property
    def angle(self):
        """Get the current angle."""
        return self._angle
    
    @angle.setter
    def angle(self, value):
        """Set the servo angle."""
        # Clamp value to min/max
        if value < self.min_angle:
            value = self.min_angle
        elif value > self.max_angle:
            value = self.max_angle
            
        self._angle = value
        
        if not self.simulation_mode and self._controller:
            try:
                self._controller.set_servo(pin=self.pin, angle=value)
                logging.debug(f"Set servo on pin {self.pin} to {value} degrees")
            except Exception as e:
                logging.error(f"Failed to set servo angle: {e}")
        else:
            logging.debug(f"Simulation: Set servo on pin {self.pin} to {value} degrees")
    
    def close(self):
        """Close and cleanup the servo."""
        if not self.simulation_mode and self._controller:
            try:
                # Set servo to middle position to minimize power consumption
                middle_position = (self.min_angle + self.max_angle) / 2
                self._controller.set_servo(pin=self.pin, angle=middle_position)
                time.sleep(0.5)  # Give servo time to move
                # No explicit detach method in GPIOController, but stop will clean up
                self._controller.stop()
                logging.info(f"Closed servo on pin {self.pin}")
            except Exception as e:
                logging.error(f"Error closing servo: {e}")
        else:
            logging.debug(f"Simulation: Closed servo on pin {self.pin}")


class StepperWrapper:
    """
    Wrapper for GPIOController stepper functionality to replace our current implementation.
    """
    
    def __init__(self, 
                 step_pin, 
                 dir_pin, 
                 enable_pin=None,
                 limit_a_pin=0,
                 limit_b_pin=0,
                 home_pin=0,
                 min_position=-1000, 
                 max_position=1000,
                 simulation_mode=False,
                 serial_port=None):
        """
        Initialize the stepper wrapper.
        Args:
            step_pin: ESP32 Step pin number
            dir_pin: ESP32 Direction pin number
            enable_pin: ESP32 Enable pin number (optional)
            limit_a_pin: ESP32 Minimum/lower limit switch pin number
            limit_b_pin: ESP32 Maximum/upper limit switch pin number
            home_pin: ESP32 Home position switch pin number
            min_position: Minimum allowed position (soft limit)
            max_position: Maximum allowed position (soft limit)
            simulation_mode: Whether to run in simulation mode
            serial_port: Serial port for the GPIOController
        """
        self.step_pin = step_pin
        self.dir_pin = dir_pin
        self.enable_pin = enable_pin if enable_pin else 0
        self.limit_a_pin = limit_a_pin if limit_a_pin else 0
        self.limit_b_pin = limit_b_pin if limit_b_pin else 0
        self.home_pin = home_pin if home_pin else 0
        self.min_position = min_position
        self.max_position = max_position
        self.simulation_mode = simulation_mode
        self.serial_port = serial_port or DEFAULT_SERIAL_PORT
        self._controller = None
        self._position = 0
        self._stepper_id = 0  # Default stepper ID
        self._enabled = False
        self.lock = threading.Lock()
        self._moving = False
        self._speed = 1000  # Default speed
        self._limit_a_triggered = False
        self._limit_b_triggered = False
        self._home_triggered = False
        
        logging.info(f"StepperWrapper __init__: simulation_mode={simulation_mode}, FORCE_HARDWARE={os.environ.get('FORCE_HARDWARE')}, GPIOCTRL_AVAILABLE={GPIOCTRL_AVAILABLE}")
        # Initialize controller if not in simulation mode
        if not simulation_mode and GPIOCTRL_AVAILABLE:
            try:
                logging.info(f"Attempting to initialize GPIOController for stepper on port {self.serial_port}")
                self._controller = GPIOController(port=self.serial_port)
                logging.info(f"GPIOController initialized for stepper")
                # Initialize stepper with ESP32 pins only
                self._controller.init_stepper(
                    id=self._stepper_id,
                    step_pin=step_pin,
                    dir_pin=dir_pin,
                    limit_a=self.limit_a_pin,
                    limit_b=self.limit_b_pin,
                    home=self.home_pin,
                    min_limit=min_position,
                    max_limit=max_position,
                    enable_pin=self.enable_pin
                )
                logging.info(f"Initialized StepperWrapper with GPIOController (ESP32 pins)")
            except Exception as e:
                logging.error(f"Failed to initialize GPIOController for stepper: {e}")
                if FORCE_HARDWARE:
                    logging.error("FORCE_HARDWARE is set - cannot fall back to simulation mode")
                    raise
                logging.info("Falling back to simulation mode for StepperWrapper")
        else:
            if FORCE_HARDWARE and not GPIOCTRL_AVAILABLE:
                logging.error("FORCE_HARDWARE is set but GPIOController library is not available!")
                raise ImportError("GPIOController library is required when FORCE_HARDWARE is enabled")
            
            self.simulation_mode = True
            logging.info(f"StepperWrapper initialized in simulation mode (reason: simulation_mode={simulation_mode}, GPIOCTRL_AVAILABLE={GPIOCTRL_AVAILABLE})")
    
    def enable(self):
        logging.info("StepperWrapper.enable called")
        """Enable the stepper motor."""
        with self.lock:
            if self.simulation_mode:
                logging.debug("Simulation: Stepper motor enabled")
                self._enabled = True
                return True
            
            if self._controller:
                try:
                    # Explicitly set EN pin LOW (active low) if defined
                    if self.enable_pin:
                        self._controller.set_pin(self.enable_pin, 0)  # LOW=Enable
                        logging.info(f"Set EN pin {self.enable_pin} LOW (enable)")
                    self._enabled = True
                    logging.info("Stepper motor enabled")
                    return True
                except Exception as e:
                    logging.error(f"Failed to enable stepper motor: {e}")
                    return False
            return False

    def disable(self):
        logging.info("StepperWrapper.disable called")
        """Disable the stepper motor."""
        with self.lock:
            if self.simulation_mode:
                logging.debug("Simulation: Stepper motor disabled")
                self._enabled = False
                return True
            
            if self._controller:
                try:
                    # Explicitly set EN pin HIGH (active low) if defined
                    if self.enable_pin:
                        self._controller.set_pin(self.enable_pin, 1)  # HIGH=Disable
                        logging.info(f"Set EN pin {self.enable_pin} HIGH (disable)")
                    # Stop the stepper which should release it
                    self._controller.stop_stepper(id=self._stepper_id)
                    self._enabled = False
                    logging.info("Stepper motor disabled")
                    return True
                except Exception as e:
                    logging.error(f"Failed to disable stepper motor: {e}")
                    return False
            return False
    
    def move_steps(self, steps, direction, wait=False):
        logging.info(f"StepperWrapper.move_steps called: steps={steps}, direction={direction}, wait={wait}, enabled={self._enabled}, sim={self.simulation_mode}")
        """
        Move the stepper a specified number of steps in the given direction.
        
        Args:
            steps: Number of steps to move
            direction: 1 for forward, 0 for backward
            wait: Whether to wait for the movement to complete
        
        Returns:
            True if the movement was started successfully, False otherwise
        """
        with self.lock:
            if not self._enabled:
                logging.warning("Cannot move: Stepper motor is disabled")
                return False
            
            # Check limit switches before moving
            self.update_limit_states()
            
            # Don't allow movement past hard limits
            if direction == 0 and self._limit_a_triggered:  # Moving backward and at min limit
                logging.warning("Cannot move backward: Minimum limit switch triggered")
                return False
            if direction == 1 and self._limit_b_triggered:  # Moving forward and at max limit
                logging.warning("Cannot move forward: Maximum limit switch triggered")
                return False
            
            if self.simulation_mode:
                logging.info(f"Sim mode: moving {steps} steps {'forward' if direction==1 else 'backward'} from {self._position}")
                # Update position in simulation mode
                step_change = steps * (1 if direction == 1 else -1)
                new_position = self._position + step_change
                
                # Check position limits
                if new_position < self.min_position:
                    new_position = self.min_position
                    logging.warning(f"Simulation: Stepper hit minimum limit at {self.min_position}")
                elif new_position > self.max_position:
                    new_position = self.max_position
                    logging.warning(f"Simulation: Stepper hit maximum limit at {self.max_position}")
                
                # Simulate movement time based on steps and speed
                self._moving = True
                move_time = steps / self._speed  # Simple estimation
                
                def simulate_move():
                    logging.debug(f"Sim move: sleeping {move_time}s for {steps} steps")
                    time.sleep(move_time)
                    with self.lock:
                        self._position = new_position
                        self._moving = False
                    logging.info(f"Sim move complete: new position {new_position}")
                
                if wait:
                    simulate_move()
                else:
                    threading.Thread(target=simulate_move, daemon=True).start()
                
                return True
            
            if self._controller:
                try:
                    logging.info(f"HW move: {steps} steps {'forward' if direction==1 else 'backward'} from {self._position} to {new_position} (adj={adjusted_steps}) speed={self._speed}")
                    # Calculate actual steps to move based on limits
                    step_change = steps * (1 if direction == 1 else -1)
                    new_position = self._position + step_change
                    
                    # Check position limits and adjust steps if needed
                    if new_position < self.min_position:
                        adjusted_steps = abs(self._position - self.min_position)
                        new_position = self.min_position
                        logging.warning(f"Adjusting steps to {adjusted_steps} due to min limit")
                    elif new_position > self.max_position:
                        adjusted_steps = abs(self.max_position - self._position)
                        new_position = self.max_position
                        logging.warning(f"Adjusting steps to {adjusted_steps} due to max limit")
                    else:
                        adjusted_steps = steps
                    
                    # If no steps to move after adjustment, return early
                    if adjusted_steps == 0:
                        return True
                    
                    self._moving = True
                    
                    def move_and_update():
                        try:
                            logging.info(f"Calling GPIOController.move_stepper(id={self._stepper_id}, steps={adjusted_steps}, direction={direction}, speed={self._speed}, wait=True)")
                            self._controller.move_stepper(
                                id=self._stepper_id,
                                steps=adjusted_steps,
                                direction=direction,
                                speed=self._speed,
                                wait=True
                            )
                            
                            # Update position after movement is complete
                            with self.lock:
                                self._position = new_position
                                self._moving = False
                                
                            logging.info(f"HW move complete: new position {new_position}")
                        except Exception as e:
                            logging.error(f"Error during stepper movement: {e}")
                            with self.lock:
                                self._moving = False
                    
                    if wait:
                        move_and_update()
                    else:
                        threading.Thread(target=move_and_update, daemon=True).start()
                    
                    return True
                except Exception as e:
                    logging.error(f"Failed to move stepper: {e}")
                    self._moving = False
                    return False
            
            return False
    
    def stop(self):
        logging.info("StepperWrapper.stop called")
        """Stop any ongoing movement."""
        with self.lock:
            if self.simulation_mode:
                logging.debug("Simulation: Stepper movement stopped")
                self._moving = False
                return True
                
            if self._controller:
                try:
                    self._controller.stop_stepper(id=self._stepper_id)
                    self._moving = False
                    logging.info("Stepper movement stopped")
                    return True
                except Exception as e:
                    logging.error(f"Failed to stop stepper movement: {e}")
                    return False
            return False
    
    def home(self, speed=None, wait=True):
        """
        Home the stepper motor.
        
        Args:
            speed: Homing speed (optional)
            wait: Whether to wait for homing to complete
        
        Returns:
            True if homing was started successfully, False otherwise
        """
        with self.lock:
            if not self._enabled:
                    return False
            
            return False
    
    def set_speed(self, speed):
        logging.info(f"StepperWrapper.set_speed called: speed={speed}")
        """Set the stepper speed."""
        self._speed = speed
        logging.debug(f"Stepper speed set to {speed}")
        return True
    
    def get_position(self):
        logging.info(f"StepperWrapper.get_position called, returning {self._position}")
        """Get the current position."""
        return self._position
    
    def set_position(self, position):
        logging.info(f"StepperWrapper.set_position called: position={position}")
        """
        Set the current position (without moving) for tracking purposes.
        
        This doesn't physically move the stepper, just updates the internal position counter.
        """
        with self.lock:
            self._position = position
            logging.debug(f"Stepper position set to {position} (no movement)")
            return True
    
    def is_moving(self):
        logging.info(f"StepperWrapper.is_moving called, returning {self._moving}")
        """Check if the stepper is currently moving."""
        return self._moving
    
    def update_limit_states(self):
        logging.info("StepperWrapper.update_limit_states called")
        """Update the state of limit switches from the controller feedback.
        
        Returns:
            dict: Dictionary with the state of all limit switches
        """
        if self.simulation_mode:
            # In simulation mode, pretend switches are never triggered
            return {
                'limit_a': False,
                'limit_b': False,
                'home': False
            }
            
        if self._controller:
            try:
                # Get feedback from the controller
                feedback = self._controller.get_feedback()
                status = feedback.get("status", {})
                
                # Update limit switch states
                self._limit_a_triggered = status.get(f"limit_a_{self._stepper_id}", False)
                self._limit_b_triggered = status.get(f"limit_b_{self._stepper_id}", False)
                self._home_triggered = status.get(f"home_{self._stepper_id}", False)
                
                return {
                    'limit_a': self._limit_a_triggered,
                    'limit_b': self._limit_b_triggered,
                    'home': self._home_triggered
                }
            except Exception as e:
                logging.error(f"Failed to update limit switch states: {e}")
                
        return {
            'limit_a': False,
            'limit_b': False,
            'home': False
        }
    
    def get_limit_a_state(self):
        logging.info(f"StepperWrapper.get_limit_a_state called, returning {self._limit_a_triggered}")
        """Get the current state of the minimum limit switch."""
        self.update_limit_states()
        return self._limit_a_triggered
        
    def get_limit_b_state(self):
        logging.info(f"StepperWrapper.get_limit_b_state called, returning {self._limit_b_triggered}")
        """Get the current state of the maximum limit switch."""
        self.update_limit_states()
        return self._limit_b_triggered
        
    def get_home_state(self):
        logging.info(f"StepperWrapper.get_home_state called, returning {self._home_triggered}")
        """Get the current state of the home switch."""
        self.update_limit_states()
        return self._home_triggered

    def close(self):
        logging.info("StepperWrapper.close called")
        """Clean up resources."""
        self.stop()
        self.disable()
        if self._controller:
            try:
                self._controller.stop()
                logging.info("Stepper controller closed")
            except Exception as e:
                logging.error(f"Error closing stepper controller: {e}")


class LocalGPIOWrapper:
    """
    Wrapper for local GPIO control using gpiod v2.x API.
    Provides a simple interface for controlling digital outputs.
    """
    
    def __init__(self, simulation_mode=False):
        """
        Initialize the local GPIO wrapper.
        
        Args:
            simulation_mode: Whether to run in simulation mode
        """
        self.simulation_mode = simulation_mode
        self._chip_name = 'gpiochip0'
        self._chip_instances = {}
        self._lines = {}
        logging.info(f"LocalGPIOWrapper initialized with chip_name={self._chip_name}, simulation_mode={self.simulation_mode}")

    def _get_chip_for_pin(self, pin):
        """
        Get a chip instance for a specific pin, creating it if needed.
        """
        if self._chip_name not in self._chip_instances:
            logging.info(f"Creating new gpiod Chip instance for {self._chip_name}")
            self._chip_instances[self._chip_name] = gpiod.Chip(self._chip_name)
        else:
            logging.debug(f"Using cached gpiod Chip instance for {self._chip_name}")
        return self._chip_instances[self._chip_name]

    def setup_output(self, pin, initial_value=0):
        logging.info(f"LocalGPIOWrapper.setup_output called: pin={pin}, initial_value={initial_value}")
        """
        Set up a GPIO pin as an output.
        """
        if self.simulation_mode:
            logging.debug(f"Simulation: Set up GPIO pin {pin} as output with value {initial_value}")
            return True
        try:
            pin_offset = int(pin)
            logging.info(f"Setting up GPIO pin {pin} (offset {pin_offset}) as output on chip {self._chip_name}")
            if pin in self._lines:
                self.cleanup(pin)
            chip = self._get_chip_for_pin(pin)
            line = chip.get_line(pin_offset)
            if line is None:
                logging.error(f"gpiod.Chip.get_line({pin_offset}) returned None for chip {self._chip_name}")
                return False
            line.request(consumer="ShopLaserRoom", type=gpiod.LINE_REQ_DIR_OUT)
            line.set_value(initial_value)
            self._lines[pin] = {"line": line, "chip": chip}
            logging.info(f"Successfully set up GPIO pin {pin} as output (initial value {initial_value})")
            return True
        except Exception as e:
            logging.error(f"Failed to set up GPIO pin {pin} as output: {e}")
            return False

    def setup_input(self, pin, pull_up=False):
        logging.info(f"LocalGPIOWrapper.setup_input called: pin={pin}, pull_up={pull_up}")
        """
        Set up a GPIO pin as an input.
        """
        if self.simulation_mode:
            logging.debug(f"Simulation: Set up GPIO pin {pin} as input")
            return True
        try:
            pin_offset = int(pin)
            logging.info(f"Setting up GPIO pin {pin} (offset {pin_offset}) as input on chip {self._chip_name}")
            if pin in self._lines:
                self.cleanup(pin)
            chip = self._get_chip_for_pin(pin)
            line = chip.get_line(pin_offset)
            if line is None:
                logging.error(f"gpiod.Chip.get_line({pin_offset}) returned None for chip {self._chip_name}")
                return False
            flags = 0
            if pull_up:
                # Use bias pull-up if available (gpiod v2.x)
                try:
                    flags = gpiod.LINE_REQ_FLAG_BIAS_PULL_UP
                except AttributeError:
                    logging.warning("gpiod.LINE_REQ_FLAG_BIAS_PULL_UP not available; ensure hardware pull-up is present")
            line.request(consumer="ShopLaserRoom", type=gpiod.LINE_REQ_DIR_IN, flags=flags)
            self._lines[pin] = {"line": line, "chip": chip}
            logging.info(f"Successfully set up GPIO pin {pin} as input (pull_up={pull_up})")
            return True
        except Exception as e:
            logging.error(f"Failed to set up GPIO pin {pin} as input: {e}")
            return False
    
    def write(self, pin, value):
        logging.info(f"LocalGPIOWrapper.write called: pin={pin}, value={value}")
        """
        Write a value to a GPIO pin.
        
        Args:
            pin: GPIO pin number
            value: Pin value (0 or 1)
        
        Returns:
            True if successful, False otherwise
        """
        if self.simulation_mode:
            logging.debug(f"Simulation: Set GPIO pin {pin} to {value}")
            return True
            
        if pin in self._lines:
            try:
                self._lines[pin]["line"].set_value(value)
                logging.debug(f"Set GPIO pin {pin} to {value}")
                return True
            except Exception as e:
                logging.error(f"Failed to write to GPIO pin {pin}: {e}")
                return False
        
        return False
    
    def read(self, pin):
        logging.debug(f"LocalGPIOWrapper.read called: pin={pin}")
        """
        Read a value from a GPIO pin.
        
        Args:
            pin: GPIO pin number
        
        Returns:
            Pin value (0 or 1) or None if error
        """
        if self.simulation_mode:
            # In simulation mode, randomly return 0 or 1 for inputs
            import random
            value = random.choice([0, 1])
            logging.debug(f"Simulation: Read GPIO pin {pin} as {value}")
            return value
            
        if pin in self._lines:
            try:
                value = self._lines[pin]["line"].get_value()
                logging.debug(f"Read GPIO pin {pin} as {value}")
                return value
            except Exception as e:
                logging.error(f"Failed to read from GPIO pin {pin}: {e}")
                return None
        
        return None
    
    def cleanup(self, pin=None):
        logging.info(f"LocalGPIOWrapper.cleanup called: pin={pin}")
        """
        Clean up GPIO resources.
        
        Args:
            pin: Specific pin to clean up, or None for all
        """
        if self.simulation_mode:
            logging.debug("Simulation: GPIO cleanup")
            return
            
        if pin is not None:
            # Clean up a specific pin
            if pin in self._lines:
                try:
                    self._lines[pin]["line"].release()
                    logging.debug(f"Released GPIO pin {pin}")
                    del self._lines[pin]
                except Exception as e:
                    logging.error(f"Error releasing GPIO pin {pin}: {e}")
        else:
            # Clean up all pins first
            for pin, data in list(self._lines.items()):
                try:
                    data["line"].release()
                    logging.debug(f"Released GPIO pin {pin}")
                except Exception as e:
                    logging.error(f"Error releasing GPIO pin {pin}: {e}")
            
            # Clear lines dictionary
            self._lines.clear()
            
            # Close all chip instances
            for chip_name, chip in list(self._chip_instances.items()):
                try:
                    chip.close()
                    logging.debug(f"Closed chip {chip_name}")
                except Exception as e:
                    logging.error(f"Error closing chip {chip_name}: {e}")
            
            # Clear chip instances dictionary
            self._chip_instances.clear()