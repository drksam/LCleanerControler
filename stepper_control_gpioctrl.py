"""
Stepper motor control module using GPIOController for NooyenLaserRoom.
This replaces the gpiozero-based implementation with our ESP32-based GPIOController.
"""
import os
import time
import logging
import threading
import platform
from config import get_stepper_config, get_system_config
from gpio_controller_wrapper import StepperWrapper

class StepperMotor:
    """
    Stepper motor controller using GPIOController for NooyenLaserRoom.
    Provides high-level control for the stepper motor with position tracking.
    """
    
    def __init__(self):
        """Initialize the stepper motor controller."""
        # Load configuration
        config = get_stepper_config()
        system_config = get_system_config()
        
        # Get operation mode from system config
        operation_mode = system_config.get('operation_mode', 'simulation')
        
        # Basic configuration
        self.step_pin = config.get('step_pin', 25)
        self.dir_pin = config.get('dir_pin', 26)
        self.enable_pin = config.get('enable_pin', 27)
        self.position = 0
        self.target_position = 0
        self.speed = config.get('speed', 1000)
        self.enabled = False
        self.moving = False
        self.index_distance = config.get('index_distance', 50)
        self.max_position = config.get('max_position', 500)
        self.min_position = config.get('min_position', -500)
        
        # Set simulation mode based on system configuration
        self.simulation_mode = operation_mode == 'simulation'
        
        # Check for FORCE_HARDWARE flag
        self.force_hardware = os.environ.get('FORCE_HARDWARE', 'False').lower() == 'true'
        
        # Get serial port from config or use platform-specific default
        serial_port = config.get('serial_port')
        if not serial_port:
            # Default port based on platform
            if platform.system() == 'Windows':
                serial_port = "COM3"  # Default Windows port
            else:
                serial_port = "/dev/ttyUSB0"  # Default Linux port
        
        # Threading lock for thread safety
        self.lock = threading.Lock()
        
        # Initialize StepperWrapper
        try:
            self.stepper = StepperWrapper(
                step_pin=self.step_pin,
                dir_pin=self.dir_pin,
                enable_pin=self.enable_pin,
                min_position=self.min_position,
                max_position=self.max_position,
                simulation_mode=self.simulation_mode,
                serial_port=serial_port
            )
            
            # Set initial speed
            self.stepper.set_speed(self.speed)
            
            logging.info(f"Stepper motor initialized with GPIOController on port {serial_port}")
        except Exception as e:
            logging.error(f"Failed to initialize stepper motor: {e}")
            if self.force_hardware and operation_mode == 'prototype':
                logging.error("FORCE_HARDWARE is enabled - cannot fall back to simulation mode")
                raise  # Re-raise the exception to prevent fallback
            else:
                self.stepper = None
                logging.info("Falling back to simulation mode")
    
    def enable(self):
        """Enable the stepper motor."""
        with self.lock:
            if self.stepper:
                result = self.stepper.enable()
                if result:
                    self.enabled = True
                    logging.info("Stepper motor enabled")
                else:
                    logging.error("Failed to enable stepper motor")
                return result
            else:
                logging.error("Cannot enable: Stepper not initialized")
                return False
    
    def disable(self):
        """Disable the stepper motor."""
        with self.lock:
            if self.stepper:
                result = self.stepper.disable()
                if result:
                    self.enabled = False
                    logging.info("Stepper motor disabled")
                else:
                    logging.error("Failed to disable stepper motor")
                return result
            else:
                logging.error("Cannot disable: Stepper not initialized")
                return False
    
    def set_speed(self, speed):
        """Set the stepper motor speed."""
        with self.lock:
            if self.stepper:
                self.speed = speed
                result = self.stepper.set_speed(speed)
                logging.info(f"Stepper speed set to {speed}")
                return result
            else:
                logging.error("Cannot set speed: Stepper not initialized")
                return False
    
    def get_position(self):
        """Get the current position."""
        if self.stepper:
            return self.stepper.get_position()
        return self.position  # Fall back to tracked position if stepper not available
    
    def set_position(self, position):
        """Set the current position (without moving)."""
        with self.lock:
            self.position = position
            if self.stepper:
                self.stepper.set_position(position)
            logging.info(f"Stepper position set to {position}")
            return True
    
    def is_moving(self):
        """Check if the stepper is currently moving."""
        if self.stepper:
            return self.stepper.is_moving()
        return self.moving
    
    def move_to(self, position, wait=False):
        """
        Move to a specific position.
        
        Args:
            position: Target position
            wait: Whether to wait for the movement to complete
        
        Returns:
            True if movement started successfully, False otherwise
        """
        with self.lock:
            if not self.enabled:
                logging.warning("Cannot move: Stepper motor is disabled")
                return False
            
            # Clamp position to limits
            if position > self.max_position:
                position = self.max_position
                logging.warning(f"Position clamped to max: {position}")
            elif position < self.min_position:
                position = self.min_position
                logging.warning(f"Position clamped to min: {position}")
            
            self.target_position = position
            current_position = self.get_position()
            steps = abs(position - current_position)
            direction = 1 if position > current_position else 0
            
            if steps == 0:
                logging.info("Already at target position")
                return True
            
            if self.stepper:
                result = self.stepper.move_steps(steps, direction, wait)
                if result:
                    logging.info(f"Moving to position {position} with {steps} steps in direction {direction}")
                    self.moving = True
                    
                    # If not waiting, update position in a separate thread
                    if not wait and not self.simulation_mode:
                        def update_position():
                            # Wait for movement to complete
                            while self.stepper.is_moving():
                                time.sleep(0.1)
                            # Update position
                            with self.lock:
                                self.position = position
                                self.moving = False
                            logging.info(f"Movement completed, position: {position}")
                        
                        threading.Thread(target=update_position, daemon=True).start()
                    elif wait:
                        # If waiting, update position now
                        self.position = position
                        self.moving = False
                        logging.info(f"Movement completed, position: {position}")
                    
                    return True
                else:
                    logging.error("Failed to start movement")
                    return False
            else:
                logging.error("Cannot move: Stepper not initialized")
                return False
    
    def stop(self):
        """Stop any ongoing movement."""
        with self.lock:
            if self.stepper:
                result = self.stepper.stop()
                if result:
                    self.moving = False
                    logging.info("Stepper movement stopped")
                else:
                    logging.error("Failed to stop stepper movement")
                return result
            else:
                logging.error("Cannot stop: Stepper not initialized")
                return False
    
    def home(self, wait=True):
        """
        Home the stepper motor (move to position 0).
        
        Args:
            wait: Whether to wait for homing to complete
        
        Returns:
            True if homing started successfully, False otherwise
        """
        with self.lock:
            if not self.enabled:
                logging.warning("Cannot home: Stepper motor is disabled")
                return False
            
            if self.stepper:
                result = self.stepper.home(wait=wait)
                if result:
                    self.target_position = 0
                    self.moving = True
                    
                    # If not waiting, update position in a separate thread
                    if not wait and not self.simulation_mode:
                        def update_position():
                            # Wait for movement to complete
                            while self.stepper.is_moving():
                                time.sleep(0.1)
                            # Update position
                            with self.lock:
                                self.position = 0
                                self.moving = False
                            logging.info("Homing completed, position: 0")
                        
                        threading.Thread(target=update_position, daemon=True).start()
                    elif wait:
                        # If waiting, update position now
                        self.position = 0
                        self.moving = False
                        logging.info("Homing completed, position: 0")
                    
                    return True
                else:
                    logging.error("Failed to start homing")
                    return False
            else:
                logging.error("Cannot home: Stepper not initialized")
                return False
    
    def jog(self, direction, steps=10):
        """
        Jog the stepper motor in the specified direction.
        
        Args:
            direction: 1 for forward, 0 for backward
            steps: Number of steps to move
        
        Returns:
            True if jogging started successfully, False otherwise
        """
        with self.lock:
            if not self.enabled:
                logging.warning("Cannot jog: Stepper motor is disabled")
                return False
            
            current_position = self.get_position()
            step_change = steps * (1 if direction == 1 else -1)
            new_position = current_position + step_change
            
            # Check position limits
            if new_position > self.max_position:
                new_position = self.max_position
                step_change = self.max_position - current_position
                if step_change <= 0:
                    logging.warning("Cannot jog: Already at maximum position")
                    return False
                logging.warning(f"Jog adjusted to {step_change} steps due to max limit")
            elif new_position < self.min_position:
                new_position = self.min_position
                step_change = current_position - self.min_position
                if step_change <= 0:
                    logging.warning("Cannot jog: Already at minimum position")
                    return False
                logging.warning(f"Jog adjusted to {step_change} steps due to min limit")
            
            logging.info(f"Jogging {'forward' if direction == 1 else 'backward'} {abs(step_change)} steps")
            
            # Use move_to for consistent position tracking
            return self.move_to(new_position)
    
    def move_index(self):
        """
        Move the stepper motor by the index distance.
        
        Returns:
            True if the movement started successfully, False otherwise
        """
        with self.lock:
            if not self.enabled:
                logging.warning("Cannot move index: Stepper motor is disabled")
                return False
            
            current_position = self.get_position()
            new_position = current_position + self.index_distance
            
            logging.info(f"Moving index distance: {self.index_distance} from {current_position}")
            
            # Use move_to for consistent position tracking
            return self.move_to(new_position)
    
    def cleanup(self):
        """Clean up resources."""
        self.stop()
        self.disable()
        
        if self.stepper:
            self.stepper.close()
            logging.info("Stepper motor cleaned up")