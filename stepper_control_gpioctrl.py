"""
Stepper motor control module using GPIOController for ShopLaserRoom.
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
    Stepper motor controller using GPIOController for ShopLaserRoom.
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
        self.step_pin = config.get('esp_step_pin', 25)
        self.dir_pin = config.get('esp_dir_pin', 26)
        self.enable_pin = config.get('esp_enable_pin', 27)
        self.position = 0
        self.target_position = 0
        self.speed = config.get('speed', 1000)
        self.enabled = False
        self.moving = False
        self.index_distance = config.get('index_distance', 50)
        self.max_position = config.get('max_position', 500)
        self.min_position = config.get('min_position', -500)
        
        # Physical limit switch pins
        self.limit_a_pin = config.get('esp_limit_a_pin', 32)  # Min limit switch
        self.limit_b_pin = config.get('esp_limit_b_pin', 33)  # Max limit switch
        self.home_pin = config.get('esp_home_pin', 34) # Home position switch
        
        # Limit status
        self.limit_a_triggered = False
        self.limit_b_triggered = False
        self.home_triggered = False
        
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
        
        # Threading lock for thread safety - Use RLock to prevent deadlock
        self.lock = threading.RLock()
        
        # Initialize StepperWrapper
        try:
            # Check if we need to invert the enable pin logic
            # Some stepper drivers use LOW=Enable, HIGH=Disable
            invert_logic = config.get('stepper_config', {}).get('invert_enable_logic', False)
            logging.info(f"Using stepper enable pin logic: {'INVERTED' if invert_logic else 'NORMAL'}")
            
            self.stepper = StepperWrapper(
                step_pin=self.step_pin,
                dir_pin=self.dir_pin,
                enable_pin=self.enable_pin,
                min_position=self.min_position,
                max_position=self.max_position,
                limit_a_pin=self.limit_a_pin,
                limit_b_pin=self.limit_b_pin,
                home_pin=self.home_pin,
                simulation_mode=self.simulation_mode,
                serial_port=serial_port,
                invert_enable_logic=invert_logic
            )
            
            # Set initial speed
            self.stepper.set_speed(self.speed)
            
            # Auto-enable the stepper on initialization
            if self.stepper.enable():
                self.enabled = True
                logging.info("Stepper motor auto-enabled during initialization")
                
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
        logging.info("StepperMotor.enable called")
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
        logging.info("StepperMotor.disable called")
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
        logging.info(f"StepperMotor.set_speed called: speed={speed}")
        with self.lock:
            if self.stepper:
                self.speed = speed
                result = self.stepper.set_speed(speed)
                logging.info(f"Stepper speed set to {speed}")
                return result
            else:
                logging.error("Cannot set speed: Stepper not initialized")
                return False
    
    def set_acceleration(self, acceleration):
        """Set the stepper motor acceleration."""
        logging.info(f"StepperMotor.set_acceleration called: acceleration={acceleration}")
        with self.lock:
            if self.stepper:
                result = self.stepper.set_acceleration(acceleration)
                logging.info(f"Stepper acceleration set to {acceleration}")
                return result
            else:
                logging.error("Cannot set acceleration: Stepper not initialized")
                return False
    
    def set_deceleration(self, deceleration):
        """Set the stepper motor deceleration."""
        logging.info(f"StepperMotor.set_deceleration called: deceleration={deceleration}")
        with self.lock:
            if self.stepper:
                result = self.stepper.set_deceleration(deceleration)
                logging.info(f"Stepper deceleration set to {deceleration}")
                return result
            else:
                logging.error("Cannot set deceleration: Stepper not initialized")
                return False

    def get_position(self):
        logging.info(f"StepperMotor.get_position called, returning {self.position}")
        """Get the current position."""
        if self.stepper:
            return self.stepper.get_position()
        return self.position  # Fall back to tracked position if stepper not available
    
    def set_position(self, position):
        logging.info(f"StepperMotor.set_position called: position={position}")
        """Set the current position (without moving)."""
        with self.lock:
            self.position = position
            if self.stepper:
                self.stepper.set_position(position)
            logging.info(f"Stepper position set to {position}")
            return True
    
    def is_moving(self):
        logging.info(f"StepperMotor.is_moving called, returning {self.moving}")
        """Check if the stepper is currently moving."""
        if self.stepper:
            return self.stepper.is_moving()
        return self.moving
    
    def move_to(self, position, wait=False):
        logging.info(f"StepperMotor.move_to called: position={position}, wait={wait}")
        """
        Move to a specific position.
        
        Args:
            position: Target position
            wait: Whether to wait for the movement to complete
        
        Returns:
            True if movement started successfully, False otherwise
        """
        with self.lock:
            logging.info("StepperMotor.move_to: Lock acquired successfully")
            if not self.enabled:
                logging.warning("Cannot move: Stepper motor is disabled")
                return False
            
            logging.info("StepperMotor.move_to: Checking position limits and safety...")
            
            # Safety check: Prevent movement into negative positions
            if position < 0:
                logging.warning(f"Cannot move to negative position: {position}. Clamping to 0.")
                position = 0
            
            # Safety check: If home switch is triggered and trying to move backward, stop
            if self.stepper and self.stepper.get_home_state() and position < self.get_position():
                logging.warning("Home switch is triggered - cannot move further backward")
                return False
            
            # Clamp position to hardware limits
            if position > self.max_position:
                position = self.max_position
                logging.warning(f"Position clamped to max: {position}")
            elif position < self.min_position:
                position = self.min_position
                logging.warning(f"Position clamped to min: {position}")
            
            logging.info("StepperMotor.move_to: Setting target position...")
            self.target_position = position
            logging.info("StepperMotor.move_to: Getting current position...")
            try:
                current_position = self.get_position()
                logging.info(f"StepperMotor.move_to: Current position retrieved: {current_position}")
            except Exception as e:
                logging.error(f"Error getting position in move_to: {e}")
                # Use last known position if position query fails
                current_position = self.position
                logging.info(f"StepperMotor.move_to: Using fallback position: {current_position}")
            
            steps = abs(position - current_position)
            direction = 1 if position > current_position else 0
            logging.info(f"StepperMotor.move_to: Calculated steps={steps}, direction={direction}")
            
            if steps == 0:
                logging.info("Already at target position")
                return True
            
            if self.stepper:
                logging.info(f"About to call stepper.move_steps({steps}, {direction}, {wait})")
                result = self.stepper.move_steps(steps, direction, wait)
                logging.info(f"stepper.move_steps returned: {result}")
                if result:
                    logging.info(f"Moving to position {position} with {steps} steps in direction {direction}")
                    self.moving = True
                    
                    # If not waiting, update position in a separate thread
                    if not wait and not self.simulation_mode:
                        def update_position():
                            # Wait for movement to complete with timeout protection
                            max_wait_time = 10.0  # Maximum 10 seconds wait
                            start_time = time.time()
                            
                            while self.stepper.is_moving():
                                if time.time() - start_time > max_wait_time:
                                    logging.error(f"Movement timeout after {max_wait_time}s - forcing stop")
                                    self.stepper.stop()
                                    break
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
                # Force simulation mode for the jog operation
                logging.warning("Falling back to position simulation for jog operation")
                current_position = self.get_position()
                step_change = steps * (1 if direction == 1 else -1)
                self.position = current_position + step_change
                return True
    
    def stop(self):
        logging.info("StepperMotor.stop called")
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
        logging.info(f"StepperMotor.home called: wait={wait}")
        """
        Home the stepper motor by moving backward at 33% index speed until home switch is triggered.
        
        Args:
            wait: Whether to wait for homing to complete
        
        Returns:
            True if homing started successfully, False otherwise
        """
        with self.lock:
            # Enable stepper if not already enabled (required for homing)
            if not self.enabled:
                logging.info("Stepper not enabled, enabling for homing operation")
                enable_result = self.enable()
                # On Windows or in simulation mode, allow homing even if enable fails
                is_simulation = self.simulation_mode or platform.system() == 'Windows'
                if not enable_result and not is_simulation:
                    logging.warning("Cannot home: Failed to enable stepper motor")
                    return False
                elif is_simulation:
                    # In simulation mode or on Windows, force enable for testing
                    self.enabled = True
                    logging.info(f"Stepper enabled in simulation mode (Windows: {platform.system() == 'Windows'}, simulation_mode: {self.simulation_mode})")
            
            if self.stepper:
                # Check if already at home position
                if self.stepper.get_home_state():
                    logging.info("Already at home position")
                    self.position = 0
                    self.target_position = 0
                    return True
                
                # Calculate homing speed (33% of index speed)
                try:
                    config = get_stepper_config()
                    # Get index_speed from config, fallback to a reasonable default
                    index_speed = config.get('index_speed', 2000)
                    homing_speed = int(index_speed * 0.33)  # 33% of index speed
                    logging.info(f"Using homing speed: {homing_speed} (33% of {index_speed} index speed)")
                except Exception as e:
                    logging.error(f"Error getting config for homing: {e}")
                    homing_speed = 660  # Fallback: 33% of 2000 default index speed
                
                # Set homing speed temporarily
                original_speed = self.speed
                self.stepper.set_speed(homing_speed)
                
                # Start custom homing process
                self.moving = True
                self.target_position = -999999  # Large negative number to indicate homing
                
                if not wait:
                    # Check if we're already in a background thread (like Flask request)
                    import threading
                    current_thread = threading.current_thread()
                    is_main_thread = isinstance(current_thread, threading._MainThread)
                    
                    if is_main_thread:
                        # We're in the main thread, start homing in a separate thread
                        def homing_thread():
                            try:
                                result = self._perform_homing_sequence()
                                return result
                            finally:
                                # Restore original speed
                                self.stepper.set_speed(original_speed)
                        
                        threading.Thread(target=homing_thread, daemon=True).start()
                        return True
                    else:
                        # We're already in a background thread (Flask request), run directly
                        try:
                            result = self._perform_homing_sequence()
                            # Restore original speed
                            self.stepper.set_speed(original_speed)
                            return result
                        except Exception as e:
                            # Restore original speed on error
                            self.stepper.set_speed(original_speed)
                            raise e
                else:
                    # Perform homing synchronously
                    try:
                        result = self._perform_homing_sequence()
                        # Restore original speed
                        self.stepper.set_speed(original_speed)
                        return result
                    except Exception as e:
                        # Restore original speed on error
                        self.stepper.set_speed(original_speed)
                        raise e
            else:
                logging.error("Cannot home: Stepper not initialized")
                return False
    
    def _perform_homing_sequence(self):
        """
        Internal method to perform the actual homing sequence.
        Moves backward until home switch is triggered, then stops and zeros position.
        """
        logging.info("Starting homing sequence - moving backward until home switch")
        
        # Check if we're in simulation (Windows or simulation mode)
        is_simulation = self.simulation_mode or platform.system() == 'Windows'
        if is_simulation:
            logging.info("Running in simulation mode - simulating homing sequence")
            time.sleep(0.5)  # Simulate homing time
            with self.lock:
                self.position = 0
                self.target_position = 0
                self.moving = False
                # Set position to zero in stepper wrapper too if available
                if hasattr(self.stepper, 'set_position'):
                    self.stepper.set_position(0)
            logging.info("Homing completed successfully (simulated), position zeroed to: 0")
            return True
        
        # Move backward in small increments until home switch is triggered
        step_size = 50  # Small steps for precise homing
        max_steps = 10000  # Safety limit - max steps to travel while homing
        steps_taken = 0
        
        try:
            while not self.stepper.get_home_state() and steps_taken < max_steps:
                # Check if homing was interrupted
                if not self.moving:
                    logging.info("Homing was interrupted")
                    return False
                
                # Move backward one step increment using async movement
                result = self.stepper.move_steps(step_size, 0, wait=False)  # direction 0 = backward, async
                if not result:
                    logging.error("Failed to move during homing")
                    self.moving = False
                    return False
                
                # Wait for movement to complete by polling
                max_wait_time = 2.0  # Maximum time to wait for each step
                wait_start = time.time()
                while self.stepper.is_moving() and (time.time() - wait_start) < max_wait_time:
                    time.sleep(0.01)  # Small delay while waiting
                    # Check if homing was interrupted during wait
                    if not self.moving:
                        logging.info("Homing was interrupted during movement")
                        return False
                
                # Check if movement timed out
                if self.stepper.is_moving():
                    logging.warning(f"Movement timed out after {max_wait_time}s, continuing homing")
                    
                steps_taken += step_size
                
                # Small delay to allow switch state to update
                time.sleep(0.01)
            
            if self.stepper.get_home_state():
                # Home switch triggered - stop and zero position
                logging.info("Home switch triggered - zeroing position")
                with self.lock:
                    self.position = 0
                    self.target_position = 0
                    self.moving = False
                    # Set position to zero in stepper wrapper too
                    self.stepper.set_position(0)
                logging.info("Homing completed successfully, position zeroed to: 0")
                return True
            else:
                # Reached max steps without finding home
                logging.error(f"Homing failed - home switch not found after {steps_taken} steps")
                self.moving = False
                return False
                
        except Exception as e:
            logging.error(f"Error during homing sequence: {e}")
            self.moving = False
            return False
    
    def jog(self, direction, steps=10):
        logging.info(f"StepperMotor.jog called: direction={direction}, steps={steps}")
        """
        Jog the stepper motor in the specified direction.
        
        Args:
            direction: 1 for forward, 0 for backward
            steps: Number of steps to move
        
        Returns:
            True if jogging started successfully, False otherwise
        """
        # Check enabled state and calculate new position without holding the lock for too long
        with self.lock:
            if not self.enabled:
                logging.warning("Cannot jog: Stepper motor is disabled")
                return False
            
            try:
                current_position = self.get_position()
                logging.info(f"StepperMotor.get_position called, returning {current_position}")
            except Exception as e:
                logging.error(f"Error getting position in jog: {e}")
                # Use last known position if position query fails
                current_position = self.position
                
            step_change = steps * (1 if direction == 1 else -1)
            new_position = current_position + step_change
            
            # Safety check: Prevent movement into negative positions
            if new_position < 0:
                logging.warning(f"Cannot jog to negative position: {new_position}. Limiting to position 0.")
                new_position = 0
                step_change = 0 - current_position
                if step_change <= 0:
                    logging.warning("Cannot jog: Already at position 0 or negative")
                    return False
            
            # Safety check: If home switch is triggered and trying to move backward, stop
            if self.stepper and self.stepper.get_home_state() and direction == 0:  # direction 0 = backward
                logging.warning("Home switch is triggered - cannot jog backward")
                return False
            
            # Check hardware position limits
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
        
        # Release the lock before calling move_to to avoid deadlock
        try:
            return self.move_to(new_position)
        except Exception as e:
            logging.error(f"Error in move_to during jog: {e}")
            return False
    
    def move_index(self, direction=1):
        logging.info(f"StepperMotor.move_index called: direction={direction}")
        """
        Move the stepper motor by the index distance.
        
        Args:
            direction: 1 for forward, -1 for backward (or 0 for backward compatibility)
        
        Returns:
            True if the movement started successfully, False otherwise
        """
        # Check enabled state and get current position without holding the lock for too long
        with self.lock:
            logging.info(f"StepperMotor.move_index: Lock acquired, enabled={self.enabled}")
            if not self.enabled:
                logging.warning("Cannot move index: Stepper motor is disabled")
                return False
            
            try:
                current_position = self.get_position()
                logging.info(f"StepperMotor.move_index: Current position={current_position}")
            except Exception as e:
                logging.error(f"Error getting position in move_index: {e}")
                # Use last known position if position query fails
                current_position = self.position
                logging.info(f"StepperMotor.move_index: Using fallback position={current_position}")
            
            # Convert direction: 0 -> -1 for backward compatibility with jog direction format
            if direction == 0:
                direction = -1
                logging.info("StepperMotor.move_index: Converted direction 0 to -1")
            
            # Get current index distance from configuration to ensure we use the latest value
            try:
                current_config = get_stepper_config()
                current_index_distance = current_config.get('index_distance', self.index_distance)
                logging.info(f"StepperMotor.move_index: Using index_distance={current_index_distance}")
            except Exception as e:
                logging.error(f"Error loading config in move_index, using cached value: {e}")
                current_index_distance = self.index_distance
            
            # Calculate new position based on direction
            step_change = current_index_distance * direction
            new_position = current_position + step_change
            
            logging.info(f"Moving index distance: {step_change} from {current_position} to {new_position}")
        
        # Release the lock before calling move_to to avoid deadlock
        try:
            result = self.move_to(new_position)
            logging.info(f"StepperMotor.move_index: move_to returned {result}")
            return result
        except Exception as e:
            logging.error(f"Error in move_to during move_index: {e}")
            return False
    
    def cleanup(self):
        logging.info("StepperMotor.cleanup called")
        """Clean up resources."""
        self.stop()
        self.disable()
        
        if self.stepper:
            self.stepper.close()
            logging.info("Stepper motor cleaned up")
    
    def get_limit_states(self):
        """Get the current state of all limit switches.
        
        Returns:
            dict: Dictionary with the state of all limit switches
        """
        with self.lock:
            if self.stepper:
                return self.stepper.update_limit_states()
            else:
                return {
                    'limit_a': False,
                    'limit_b': False,
                    'home': False
                }
    
    def is_at_min_limit(self):
        """Check if the stepper is at minimum limit switch.
        
        Returns:
            bool: True if at minimum limit, False otherwise
        """
        if self.stepper:
            return self.stepper.get_limit_a_state()
        return False
    
    def is_at_max_limit(self):
        """Check if the stepper is at maximum limit switch.
        
        Returns:
            bool: True if at maximum limit, False otherwise
        """
        if self.stepper:
            return self.stepper.get_limit_b_state()
        return False
    
    def is_at_home(self):
        """Check if the stepper is at home position switch.
        
        Returns:
            bool: True if at home position, False otherwise
        """
        if self.stepper:
            return self.stepper.get_home_state()
        return False