#!/usr/bin/env python
"""
Mock Hardware Interface for Testing

This module provides mock implementations of hardware components
for testing without requiring physical hardware.
"""
import time
import random
import threading
import logging
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('mock_hardware')

class HardwareState(Enum):
    """Possible states for hardware components"""
    UNKNOWN = "unknown"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    NOT_AVAILABLE = "not_available"

class MockHardwareException(Exception):
    """Exception raised by mock hardware components"""
    pass

class MockStepper:
    """Mock implementation of a stepper motor"""
    
    def __init__(self, name, config=None):
        """
        Initialize mock stepper motor
        
        Args:
            name: Name of the stepper motor
            config: Configuration dictionary with steps_per_rev, max_speed, acceleration
        """
        self.name = name
        self.config = config or {
            "steps_per_rev": 200,
            "max_speed": 1000,
            "acceleration": 500
        }
        self.current_position = 0
        self.target_position = 0
        self.state = HardwareState.READY
        self.failure_mode = None
        self.busy_lock = threading.Lock()
        
        logger.info(f"MockStepper '{name}' initialized")
    
    def move(self, steps, direction="forward"):
        """
        Move the stepper motor
        
        Args:
            steps: Number of steps to move
            direction: "forward" or "backward"
            
        Returns:
            dict: Result of the operation
        """
        # Check if we should simulate a failure
        if self.failure_mode is not None:
            logger.error(f"Simulated failure in stepper '{self.name}': {self.failure_mode}")
            raise MockHardwareException(f"Simulated failure: {self.failure_mode}")
            
        # Check if stepper is busy
        if not self.busy_lock.acquire(blocking=False):
            logger.warning(f"Stepper '{self.name}' is busy")
            return {"success": False, "error": "Stepper is busy"}
            
        try:
            logger.info(f"Moving stepper '{self.name}' {steps} steps {direction}")
            self.state = HardwareState.BUSY
            
            # Calculate distance and new position
            step_direction = 1 if direction == "forward" else -1
            self.target_position = self.current_position + (steps * step_direction)
            
            # Simulate movement time based on steps and speed
            move_time = steps / self.config["max_speed"]
            time.sleep(min(move_time, 0.5))  # Cap simulation time for testing
            
            # Update position
            self.current_position = self.target_position
            self.state = HardwareState.READY
            
            return {
                "success": True,
                "position": self.current_position,
                "steps_moved": steps,
                "direction": direction
            }
        except Exception as e:
            logger.error(f"Error moving stepper '{self.name}': {str(e)}")
            self.state = HardwareState.ERROR
            return {"success": False, "error": str(e)}
        finally:
            self.busy_lock.release()
    
    def get_position(self):
        """Get current position of the stepper"""
        return self.current_position
    
    def get_state(self):
        """Get current state of the stepper"""
        return self.state
    
    def set_failure_mode(self, failure_mode=None):
        """Set a failure mode for testing error handling"""
        self.failure_mode = failure_mode
        logger.info(f"Set failure mode for stepper '{self.name}': {failure_mode}")
        
    def reset(self):
        """Reset the stepper to initial state"""
        self.current_position = 0
        self.target_position = 0
        self.state = HardwareState.READY
        self.failure_mode = None
        logger.info(f"Reset stepper '{self.name}'")

class MockServo:
    """Mock implementation of a servo motor"""
    
    def __init__(self, name, config=None):
        """
        Initialize mock servo
        
        Args:
            name: Name of the servo
            config: Configuration dictionary with min_pulse_width, max_pulse_width, default_angle
        """
        self.name = name
        self.config = config or {
            "min_pulse_width": 500,
            "max_pulse_width": 2500,
            "default_angle": 90
        }
        self.current_angle = self.config["default_angle"]
        self.state = HardwareState.READY
        self.failure_mode = None
        self.busy_lock = threading.Lock()
        
        logger.info(f"MockServo '{name}' initialized at {self.current_angle}°")
    
    def move_to(self, angle):
        """
        Move the servo to the specified angle
        
        Args:
            angle: Target angle in degrees (0-180)
            
        Returns:
            dict: Result of the operation
        """
        # Check if we should simulate a failure
        if self.failure_mode is not None:
            logger.error(f"Simulated failure in servo '{self.name}': {self.failure_mode}")
            raise MockHardwareException(f"Simulated failure: {self.failure_mode}")
            
        # Check if servo is busy
        if not self.busy_lock.acquire(blocking=False):
            logger.warning(f"Servo '{self.name}' is busy")
            return {"success": False, "error": "Servo is busy"}
            
        try:
            # Validate angle
            if angle < 0 or angle > 180:
                raise ValueError(f"Invalid angle: {angle}. Must be between 0 and 180.")
                
            logger.info(f"Moving servo '{self.name}' to {angle}°")
            self.state = HardwareState.BUSY
            
            # Simulate movement time based on angle difference
            angle_diff = abs(self.current_angle - angle)
            move_time = angle_diff / 180.0 * 0.5  # Max 0.5 seconds for a full sweep
            time.sleep(move_time)
            
            # Update angle
            self.current_angle = angle
            self.state = HardwareState.READY
            
            return {
                "success": True,
                "angle": angle
            }
        except Exception as e:
            logger.error(f"Error moving servo '{self.name}': {str(e)}")
            self.state = HardwareState.ERROR
            return {"success": False, "error": str(e)}
        finally:
            self.busy_lock.release()
    
    def get_angle(self):
        """Get current angle of the servo"""
        return self.current_angle
    
    def get_state(self):
        """Get current state of the servo"""
        return self.state
    
    def set_failure_mode(self, failure_mode=None):
        """Set a failure mode for testing error handling"""
        self.failure_mode = failure_mode
        logger.info(f"Set failure mode for servo '{self.name}': {failure_mode}")
        
    def reset(self):
        """Reset the servo to default angle"""
        self.current_angle = self.config["default_angle"]
        self.state = HardwareState.READY
        self.failure_mode = None
        logger.info(f"Reset servo '{self.name}' to {self.current_angle}°")

class MockLaser:
    """Mock implementation of a laser"""
    
    def __init__(self, name):
        """
        Initialize mock laser
        
        Args:
            name: Name of the laser
        """
        self.name = name
        self.is_firing = False
        self.state = HardwareState.READY
        self.failure_mode = None
        self.fire_thread = None
        self.busy_lock = threading.Lock()
        
        logger.info(f"MockLaser '{name}' initialized")
    
    def fire(self, duration):
        """
        Fire the laser for specified duration
        
        Args:
            duration: Duration to fire in seconds
            
        Returns:
            dict: Result of the operation
        """
        # Check if we should simulate a failure
        if self.failure_mode is not None:
            logger.error(f"Simulated failure in laser '{self.name}': {self.failure_mode}")
            raise MockHardwareException(f"Simulated failure: {self.failure_mode}")
            
        # Check if laser is busy
        if self.is_firing:
            logger.warning(f"Laser '{self.name}' is already firing")
            return {"success": False, "error": "Laser is already firing"}
            
        try:
            logger.info(f"Firing laser '{self.name}' for {duration} seconds")
            self.is_firing = True
            self.state = HardwareState.BUSY
            
            # Start fire thread
            def fire_task():
                try:
                    time.sleep(duration)
                finally:
                    self.is_firing = False
                    self.state = HardwareState.READY
                    logger.info(f"Laser '{self.name}' finished firing")
            
            self.fire_thread = threading.Thread(target=fire_task)
            self.fire_thread.daemon = True
            self.fire_thread.start()
            
            return {
                "success": True,
                "duration": duration
            }
        except Exception as e:
            logger.error(f"Error firing laser '{self.name}': {str(e)}")
            self.is_firing = False
            self.state = HardwareState.ERROR
            return {"success": False, "error": str(e)}
    
    def stop(self):
        """Stop the laser if it's firing"""
        if self.is_firing:
            logger.info(f"Stopping laser '{self.name}'")
            self.is_firing = False
            self.state = HardwareState.READY
            return {"success": True}
        else:
            logger.info(f"Laser '{self.name}' is not firing")
            return {"success": True, "message": "Laser is not firing"}
    
    def get_state(self):
        """Get current state of the laser"""
        return self.state
    
    def set_failure_mode(self, failure_mode=None):
        """Set a failure mode for testing error handling"""
        self.failure_mode = failure_mode
        logger.info(f"Set failure mode for laser '{self.name}': {failure_mode}")
        
    def reset(self):
        """Reset the laser to initial state"""
        self.stop()
        self.failure_mode = None
        logger.info(f"Reset laser '{self.name}'")

class MockGPIO:
    """Mock implementation of GPIO pins"""
    
    def __init__(self, name, pin, active_high=True):
        """
        Initialize mock GPIO
        
        Args:
            name: Name of the GPIO
            pin: Pin number
            active_high: Whether the pin is active high (True) or active low (False)
        """
        self.name = name
        self.pin = pin
        self.active_high = active_high
        self.state = False  # Initial state is inactive
        self.failure_mode = None
        
        logger.info(f"MockGPIO '{name}' initialized on pin {pin} (active_{'high' if active_high else 'low'})")
    
    def set_state(self, state):
        """
        Set the GPIO state
        
        Args:
            state: True for active, False for inactive
            
        Returns:
            dict: Result of the operation
        """
        # Check if we should simulate a failure
        if self.failure_mode is not None:
            logger.error(f"Simulated failure in GPIO '{self.name}': {self.failure_mode}")
            raise MockHardwareException(f"Simulated failure: {self.failure_mode}")
            
        try:
            logger.info(f"Setting GPIO '{self.name}' to {'active' if state else 'inactive'}")
            self.state = state
            return {"success": True, "state": state}
        except Exception as e:
            logger.error(f"Error setting GPIO '{self.name}': {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_state(self):
        """Get current state of the GPIO"""
        return self.state
    
    def get_logical_state(self):
        """Get logical state (active/inactive) accounting for active_high setting"""
        return self.state if self.active_high else not self.state
    
    def set_failure_mode(self, failure_mode=None):
        """Set a failure mode for testing error handling"""
        self.failure_mode = failure_mode
        logger.info(f"Set failure mode for GPIO '{self.name}': {failure_mode}")
        
    def reset(self):
        """Reset the GPIO to inactive state"""
        self.state = False
        self.failure_mode = None
        logger.info(f"Reset GPIO '{self.name}'")

class MockHardwareController:
    """Controller for all mock hardware components"""
    
    def __init__(self):
        """Initialize the mock hardware controller"""
        self.steppers = {}
        self.servos = {}
        self.lasers = {}
        self.gpios = {}
        logger.info("MockHardwareController initialized")
        
    def add_stepper(self, name, config=None):
        """Add a stepper motor to the controller"""
        self.steppers[name] = MockStepper(name, config)
        return self.steppers[name]
        
    def add_servo(self, name, config=None):
        """Add a servo to the controller"""
        self.servos[name] = MockServo(name, config)
        return self.servos[name]
        
    def add_laser(self, name):
        """Add a laser to the controller"""
        self.lasers[name] = MockLaser(name)
        return self.lasers[name]
        
    def add_gpio(self, name, pin, active_high=True):
        """Add a GPIO to the controller"""
        self.gpios[name] = MockGPIO(name, pin, active_high)
        return self.gpios[name]
        
    def get_stepper(self, name):
        """Get a stepper by name"""
        return self.steppers.get(name)
        
    def get_servo(self, name):
        """Get a servo by name"""
        return self.servos.get(name)
        
    def get_laser(self, name):
        """Get a laser by name"""
        return self.lasers.get(name)
        
    def get_gpio(self, name):
        """Get a GPIO by name"""
        return self.gpios.get(name)
        
    def reset_all(self):
        """Reset all hardware components"""
        for stepper in self.steppers.values():
            stepper.reset()
            
        for servo in self.servos.values():
            servo.reset()
            
        for laser in self.lasers.values():
            laser.reset()
            
        for gpio in self.gpios.values():
            gpio.reset()
            
        logger.info("All mock hardware reset")
        
    def get_state(self):
        """Get the state of all hardware components"""
        return {
            "steppers": {name: stepper.get_state().value for name, stepper in self.steppers.items()},
            "servos": {name: servo.get_state().value for name, servo in self.servos.items()},
            "lasers": {name: laser.get_state().value for name, laser in self.lasers.items()},
            "gpios": {name: gpio.get_state() for name, gpio in self.gpios.items()}
        }
        
    def simulate_hardware_failure(self, component_type, component_name, failure_mode):
        """
        Simulate a hardware failure
        
        Args:
            component_type: Type of component ("stepper", "servo", "laser", "gpio")
            component_name: Name of the component
            failure_mode: Type of failure to simulate
            
        Returns:
            bool: True if failure was set, False if component not found
        """
        component = None
        
        if component_type == "stepper":
            component = self.steppers.get(component_name)
        elif component_type == "servo":
            component = self.servos.get(component_name)
        elif component_type == "laser":
            component = self.lasers.get(component_name)
        elif component_type == "gpio":
            component = self.gpios.get(component_name)
            
        if component is None:
            logger.warning(f"Cannot simulate failure: {component_type} '{component_name}' not found")
            return False
            
        component.set_failure_mode(failure_mode)
        return True