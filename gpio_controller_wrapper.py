"""
GPIO Controller Wrapper for NooyenLaserRoom application.
This module provides wrapper classes for GPIOController library to replace gpiozero.
"""
import os
import time
import logging
import threading
import platform
from typing import Optional, Callable, Dict, Any

# Determine default serial port based on platform
if platform.system() == 'Windows':
    DEFAULT_SERIAL_PORT = "COM3"  # Default Windows port, adjust as needed
else:
    DEFAULT_SERIAL_PORT = "/dev/ttyUSB0"  # Default Linux port

# Check if FORCE_HARDWARE flag is set
FORCE_HARDWARE = os.environ.get('FORCE_HARDWARE', 'False').lower() == 'true'

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

# Conditional import for local GPIO control via gpiod
try:
    import gpiod
    GPIOD_AVAILABLE = True
except ImportError:
    GPIOD_AVAILABLE = False
    logging.warning("gpiod library not available. Local GPIO will use simulation mode.")
    if FORCE_HARDWARE:
        logging.error("FORCE_HARDWARE is set but gpiod library is not available!")
        raise ImportError("gpiod library is required when FORCE_HARDWARE is enabled")

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
        
        # Initialize controller if not in simulation mode
        if not simulation_mode and GPIOCTRL_AVAILABLE:
            try:
                self._controller = GPIOController(port=self.serial_port)
                # Set initial angle
                self._controller.set_servo(pin=pin, angle=initial_angle)
                logging.info(f"Initialized ServoWrapper with GPIOController on pin {pin}")
            except Exception as e:
                logging.error(f"Failed to initialize GPIOController: {e}")
                if FORCE_HARDWARE:
                    logging.error("FORCE_HARDWARE is set - cannot fall back to simulation mode")
                    raise
                self.simulation_mode = True
                logging.info("Falling back to simulation mode")
        else:
            if FORCE_HARDWARE and not GPIOCTRL_AVAILABLE:
                logging.error("FORCE_HARDWARE is set but GPIOController library is not available!")
                raise ImportError("GPIOController library is required when FORCE_HARDWARE is enabled")
            
            self.simulation_mode = True
            logging.info(f"ServoWrapper initialized in simulation mode")
    
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
                 min_position=-1000, 
                 max_position=1000,
                 simulation_mode=False,
                 serial_port=None):
        """
        Initialize the stepper wrapper.
        
        Args:
            step_pin: Step pin number
            dir_pin: Direction pin number
            enable_pin: Enable pin number (optional)
            min_position: Minimum allowed position
            max_position: Maximum allowed position
            simulation_mode: Whether to run in simulation mode
            serial_port: Serial port for the GPIOController
        """
        self.step_pin = step_pin
        self.dir_pin = dir_pin
        self.enable_pin = enable_pin if enable_pin else 0
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
        
        # Initialize controller if not in simulation mode
        if not simulation_mode and GPIOCTRL_AVAILABLE:
            try:
                self._controller = GPIOController(port=self.serial_port)
                # Initialize stepper
                self._controller.init_stepper(
                    id=self._stepper_id,
                    step_pin=step_pin,
                    dir_pin=dir_pin,
                    limit_a=0,  # Not using limit switches via GPIOController
                    limit_b=0,  # Not using limit switches via GPIOController
                    home=0,     # Not using home switch via GPIOController
                    min_limit=min_position,
                    max_limit=max_position,
                    enable_pin=self.enable_pin
                )
                logging.info(f"Initialized StepperWrapper with GPIOController")
            except Exception as e:
                logging.error(f"Failed to initialize GPIOController for stepper: {e}")
                if FORCE_HARDWARE:
                    logging.error("FORCE_HARDWARE is set - cannot fall back to simulation mode")
                    raise
                self.simulation_mode = True
                logging.info("Falling back to simulation mode")
        else:
            if FORCE_HARDWARE and not GPIOCTRL_AVAILABLE:
                logging.error("FORCE_HARDWARE is set but GPIOController library is not available!")
                raise ImportError("GPIOController library is required when FORCE_HARDWARE is enabled")
            
            self.simulation_mode = True
            logging.info(f"StepperWrapper initialized in simulation mode")
    
    def enable(self):
        """Enable the stepper motor."""
        with self.lock:
            if self.simulation_mode:
                logging.debug("Simulation: Stepper motor enabled")
                self._enabled = True
                return True
                
            if self._controller:
                try:
                    # GPIOController doesn't have a dedicated enable method,
                    # but we can use move_stepper with 0 steps to enable
                    self._controller.move_stepper(
                        id=self._stepper_id, 
                        steps=0, 
                        direction=1, 
                        speed=self._speed
                    )
                    self._enabled = True
                    logging.info("Stepper motor enabled")
                    return True
                except Exception as e:
                    logging.error(f"Failed to enable stepper motor: {e}")
                    return False
            return False
    
    def disable(self):
        """Disable the stepper motor."""
        with self.lock:
            if self.simulation_mode:
                logging.debug("Simulation: Stepper motor disabled")
                self._enabled = False
                return True
                
            if self._controller:
                try:
                    # GPIOController doesn't have a dedicated disable method,
                    # but we can stop the stepper which should release it
                    self._controller.stop_stepper(id=self._stepper_id)
                    self._enabled = False
                    logging.info("Stepper motor disabled")
                    return True
                except Exception as e:
                    logging.error(f"Failed to disable stepper motor: {e}")
                    return False
            return False
    
    def move_steps(self, steps, direction, wait=False):
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
            
            if self.simulation_mode:
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
                    time.sleep(move_time)
                    with self.lock:
                        self._position = new_position
                        self._moving = False
                    logging.debug(f"Simulation: Stepper moved to position {new_position}")
                
                if wait:
                    simulate_move()
                else:
                    threading.Thread(target=simulate_move, daemon=True).start()
                
                return True
            
            if self._controller:
                try:
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
                                
                            logging.debug(f"Stepper moved to position {new_position}")
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
                logging.warning("Cannot home: Stepper motor is disabled")
                return False
            
            if self.simulation_mode:
                # Simulate homing in simulation mode
                self._moving = True
                
                def simulate_home():
                    # Simulate movement time for homing
                    home_time = abs(self._position) / (speed or self._speed)
                    time.sleep(home_time)
                    with self.lock:
                        self._position = 0
                        self._moving = False
                    logging.debug("Simulation: Stepper homed to position 0")
                
                if wait:
                    simulate_home()
                else:
                    threading.Thread(target=simulate_home, daemon=True).start()
                
                return True
            
            if self._controller:
                try:
                    self._moving = True
                    
                    def home_and_update():
                        try:
                            self._controller.home_stepper(
                                id=self._stepper_id,
                                wait=True
                            )
                            
                            # Update position after homing is complete
                            with self.lock:
                                self._position = 0
                                self._moving = False
                                
                            logging.debug("Stepper homed to position 0")
                        except Exception as e:
                            logging.error(f"Error during stepper homing: {e}")
                            with self.lock:
                                self._moving = False
                    
                    if wait:
                        home_and_update()
                    else:
                        threading.Thread(target=home_and_update, daemon=True).start()
                    
                    return True
                except Exception as e:
                    logging.error(f"Failed to home stepper: {e}")
                    self._moving = False
                    return False
            
            return False
    
    def set_speed(self, speed):
        """Set the stepper speed."""
        self._speed = speed
        logging.debug(f"Stepper speed set to {speed}")
        return True
    
    def get_position(self):
        """Get the current position."""
        return self._position
    
    def set_position(self, position):
        """
        Set the current position (without moving) for tracking purposes.
        
        This doesn't physically move the stepper, just updates the internal position counter.
        """
        with self.lock:
            self._position = position
            logging.debug(f"Stepper position set to {position} (no movement)")
            return True
    
    def is_moving(self):
        """Check if the stepper is currently moving."""
        return self._moving
    
    def close(self):
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
    Wrapper for local GPIO control using gpiod library.
    Provides a simple interface for controlling digital outputs.
    Compatible with both old (v1.x) and new (v2.x) gpiod API.
    """
    
    def __init__(self, simulation_mode=False):
        """
        Initialize the local GPIO wrapper.
        
        Args:
            simulation_mode: Whether to run in simulation mode
        """
        self.simulation_mode = simulation_mode
        self._chip = None
        self._lines = {}
        self._gpiod_v2 = False  # Flag to track which gpiod API version we're using
        
        # Initialize gpiod if not in simulation mode
        if not simulation_mode and GPIOD_AVAILABLE:
            try:
                # Check which version of gpiod we're using by looking at available functions/attributes
                # gpiod v2.x has chip() function while v1.x has Chip class
                if hasattr(gpiod, 'chip'):
                    # New API (v2.x)
                    self._gpiod_v2 = True
                    # In v2, chips are accessed differently
                    self._chip = 'gpiochip4'  # Just store the name for now
                    logging.info("LocalGPIOWrapper initialized with gpiod v2.x API")
                elif hasattr(gpiod, 'Chip'):
                    # Old API (v1.x)
                    self._gpiod_v2 = False
                    # For Raspberry Pi 5, GPIO pins are typically on gpiochip4
                    self._chip = gpiod.Chip('gpiochip4')
                    logging.info("LocalGPIOWrapper initialized with gpiod v1.x API")
                else:
                    raise ImportError("Could not detect gpiod API version")
            except Exception as e:
                logging.error(f"Failed to initialize gpiod: {e}")
                if FORCE_HARDWARE:
                    logging.error("FORCE_HARDWARE is set - cannot fall back to simulation mode")
                    raise
                self.simulation_mode = True
                logging.info("Falling back to simulation mode")
        else:
            if FORCE_HARDWARE and not GPIOD_AVAILABLE and not simulation_mode:
                logging.error("FORCE_HARDWARE is set but gpiod library is not available!")
                raise ImportError("gpiod library is required when FORCE_HARDWARE is enabled")
                
            self.simulation_mode = True
            logging.info("LocalGPIOWrapper initialized in simulation mode")
    
    def setup_output(self, pin, initial_value=0):
        """
        Set up a GPIO pin as an output.
        
        Args:
            pin: GPIO pin number
            initial_value: Initial pin value (0 or 1)
        
        Returns:
            True if successful, False otherwise
        """
        if self.simulation_mode:
            logging.debug(f"Simulation: Set up GPIO pin {pin} as output with value {initial_value}")
            return True
            
        try:
            if self._gpiod_v2:
                # New gpiod v2.x API - completely revised approach
                chip = gpiod.chip(self._chip)
                
                # In v2.x, we need to use line_request() differently
                request = gpiod.line_request()
                request.consumer = "NooyenLaserRoom"
                request.request_type = gpiod.line_request.DIRECTION_OUTPUT
                
                # Get the line offset for this pin
                offset = int(pin)
                
                # Request the line
                line = chip.get_lines([offset])
                line.request(request)
                
                # Set initial value
                values = [initial_value]
                line.set_values(values)
                
                # Store both chip and line for cleanup
                self._lines[pin] = {"line": line, "chip": chip}
            else:
                # Old gpiod v1.x API
                line = self._chip.get_line(pin)
                line.request(consumer="NooyenLaserRoom", type=gpiod.LINE_REQ_DIR_OUT)
                line.set_value(initial_value)
                self._lines[pin] = line
                
            logging.debug(f"Set up GPIO pin {pin} as output with value {initial_value}")
            return True
        except Exception as e:
            logging.error(f"Failed to set up GPIO pin {pin}: {e}")
            return False
            
    def setup_input(self, pin, pull_up=False):
        """
        Set up a GPIO pin as an input.
        
        Args:
            pin: GPIO pin number
            pull_up: Whether to use pull-up resistor
        
        Returns:
            True if successful, False otherwise
        """
        if self.simulation_mode:
            logging.debug(f"Simulation: Set up GPIO pin {pin} as input")
            return True
            
        try:
            if self._gpiod_v2:
                # New gpiod v2.x API - completely revised approach
                chip = gpiod.chip(self._chip)
                
                # In v2.x, we need to use line_request() differently
                request = gpiod.line_request()
                request.consumer = "NooyenLaserRoom"
                request.request_type = gpiod.line_request.DIRECTION_INPUT
                
                # Handle pull-up for v2.x API
                if pull_up:
                    request.flags = gpiod.line_request.FLAG_BIAS_PULL_UP
                
                # Get the line offset for this pin
                offset = int(pin)
                
                # Request the line
                line = chip.get_lines([offset])
                line.request(request)
                
                # Store both chip and line for cleanup
                self._lines[pin] = {"line": line, "chip": chip}
            else:
                # Old gpiod v1.x API
                line = self._chip.get_line(pin)
                
                # Set up with appropriate flags
                flags = 0
                if pull_up:
                    flags |= gpiod.LINE_REQ_FLAG_BIAS_PULL_UP
                
                line.request(consumer="NooyenLaserRoom", type=gpiod.LINE_REQ_DIR_IN, flags=flags)
                self._lines[pin] = line
                
            logging.debug(f"Set up GPIO pin {pin} as input")
            return True
        except Exception as e:
            logging.error(f"Failed to set up GPIO pin {pin}: {e}")
            return False
    
    def write(self, pin, value):
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
                if self._gpiod_v2:
                    # In v2.x, lines are stored as dict and use set_values with array
                    self._lines[pin]["line"].set_values([value])
                else:
                    # In v1.x, lines are stored directly
                    self._lines[pin].set_value(value)
                
                logging.debug(f"Set GPIO pin {pin} to {value}")
                return True
            except Exception as e:
                logging.error(f"Failed to write to GPIO pin {pin}: {e}")
                return False
        
        return False
    
    def read(self, pin):
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
                if self._gpiod_v2:
                    # In v2.x, use get_values which returns an array
                    values = self._lines[pin]["line"].get_values()
                    value = values[0] if values else 0
                else:
                    # In v1.x, lines are stored directly
                    value = self._lines[pin].get_value()
                
                logging.debug(f"Read GPIO pin {pin} as {value}")
                return value
            except Exception as e:
                logging.error(f"Failed to read from GPIO pin {pin}: {e}")
                return None
        
        return None
    
    def cleanup(self, pin=None):
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
                    if self._gpiod_v2:
                        # In v2.x, lines are stored as dict with line and chip
                        self._lines[pin]["line"].release()
                        # Close chip if this is the last pin using it
                        if len(self._lines) == 1:
                            self._lines[pin]["chip"].close()
                    else:
                        # In v1.x, lines are stored directly
                        self._lines[pin].release()
                        
                    del self._lines[pin]
                    logging.debug(f"Released GPIO pin {pin}")
                except Exception as e:
                    logging.error(f"Error releasing GPIO pin {pin}: {e}")
        else:
            # Clean up all pins
            if self._gpiod_v2:
                # In v2.x, need to handle chips separately
                chips = set()
                
                # First release all lines
                for pin, item in list(self._lines.items()):
                    try:
                        item["line"].release()
                        # Track unique chips to close them after all lines are released
                        chips.add(item["chip"])
                        logging.debug(f"Released GPIO pin {pin}")
                    except Exception as e:
                        logging.error(f"Error releasing GPIO pin {pin}: {e}")
                
                # Then close all chips
                for chip in chips:
                    try:
                        chip.close()
                    except Exception as e:
                        logging.error(f"Error closing chip: {e}")
                
                self._lines.clear()
            else:
                # Old API - release all lines
                for pin, line in list(self._lines.items()):
                    try:
                        line.release()
                        logging.debug(f"Released GPIO pin {pin}")
                    except Exception as e:
                        logging.error(f"Error releasing GPIO pin {pin}: {e}")
                
                self._lines.clear()
                
                # Close the chip
                if self._chip:
                    try:
                        self._chip.close()
                        self._chip = None
                        logging.info("Closed GPIO chip")
                    except Exception as e:
                        logging.error(f"Error closing GPIO chip: {e}")