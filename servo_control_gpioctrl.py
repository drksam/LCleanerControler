"""
Servo control module using GPIOController for NooyenLaserRoom.
This replaces the gpiozero-based implementation with our ESP32-based GPIOController.
"""
import os
import time
import logging
import threading
import platform
from config import get_servo_config, get_timing_config, get_system_config
from config import increment_laser_counter, add_laser_fire_time
from gpio_controller_wrapper import ServoWrapper

class ServoController:
    """
    Servo controller using GPIOController for NooyenLaserRoom.
    Controls the servo that presses the laser trigger.
    """
    
    def __init__(self):
        """Initialize the servo controller."""
        # Load configuration
        config = get_servo_config()
        system_config = get_system_config()
        
        # Get operation mode from system config
        operation_mode = system_config.get('operation_mode', 'simulation')
        
        # Use ESP32 pin for servo control
        self.servo_pin = config.get('esp_servo_pwm_pin', 12)
        self.position_a = config.get('position_a', 0)
        self.position_b = config.get('position_b', 90)
        self.inverted = config.get('inverted', False)
        self.min_angle = config.get('min_angle', 0)
        self.max_angle = config.get('max_angle', 180)
        
        # Sequence mode variables
        self.sequence_mode = False
        self.sequence_thread = None
        self.sequence_stop_flag = threading.Event()
        
        # Fire tracking - for statistics
        self.fire_start_time = 0
        self.is_firing = False
        
        # Threading lock for thread safety
        self.lock = threading.Lock()
        
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
        
        # Initialize ServoWrapper
        self.initialized = False
        try:
            self.servo = ServoWrapper(
                pin=self.servo_pin,
                initial_angle=self.position_a,
                min_angle=self.min_angle,
                max_angle=self.max_angle,
                simulation_mode=self.simulation_mode,
                serial_port=serial_port
            )
            self.initialized = True
            logging.info(f"Servo initialized on ESP32 pin {self.servo_pin} using port {serial_port}")
        except Exception as e:
            logging.error(f"Failed to initialize servo: {e}")
            if self.force_hardware and operation_mode == 'prototype':
                logging.error("FORCE_HARDWARE is enabled - cannot fall back to simulation mode")
                raise  # Re-raise the exception to prevent fallback
            else:
                self.servo = None
                self.initialized = False
                logging.info("Falling back to simulation mode")
    
    def set_position_a(self, angle):
        """Set the angle for position A"""
        if angle < self.min_angle:
            angle = self.min_angle
        elif angle > self.max_angle:
            angle = self.max_angle
        self.position_a = angle
        logging.info(f"Position A set to {angle} degrees")
        return angle
        
    def set_position_b(self, angle):
        """Set the angle for position B"""
        if angle < self.min_angle:
            angle = self.min_angle
        elif angle > self.max_angle:
            angle = self.max_angle
        self.position_b = angle
        logging.info(f"Position B set to {angle} degrees")
        return angle
        
    def set_inverted(self, inverted):
        """Set whether the servo positions should be inverted"""
        self.inverted = inverted
        logging.info(f"Servo inversion set to {inverted}")
        return inverted
        
    def move_to_a(self, auto_detach=False, detach_delay=0.5):
        """Move servo to position A (no auto-detach by default)"""
        if not self.initialized:
            # Try to reattach if not initialized
            if not self.reattach():
                logging.error("Cannot move servo: not initialized and reattach failed")
                return False
            
        angle = self.position_b if self.inverted else self.position_a
        
        if self.simulation_mode:
            logging.info(f"Simulation: Moved to position A ({angle} degrees)")
            return True
            
        try:
            self.servo.angle = angle
            logging.info(f"Moved to position A ({angle} degrees)")
            return True
        except Exception as e:
            logging.error(f"Failed to move servo: {e}")
            return False
            
    def move_to_b(self, auto_detach=False, detach_delay=0.5):
        """Move servo to position B (no auto-detach by default)"""
        if not self.initialized:
            # Try to reattach if not initialized
            if not self.reattach():
                logging.error("Cannot move servo: not initialized and reattach failed")
                return False
            
        angle = self.position_a if self.inverted else self.position_b
        
        if self.simulation_mode:
            logging.info(f"Simulation: Moved to position B ({angle} degrees)")
            return True
        
        try:
            self.servo.angle = angle
            logging.info(f"Moved to position B ({angle} degrees)")
            return True
        except Exception as e:
            logging.error(f"Failed to move servo: {e}")
            return False
            
    def move_to_angle(self, angle, auto_detach=False, detach_delay=0.5):
        """Move servo to a specific angle (no auto-detach by default)"""
        if not self.initialized:
            # Try to reattach if not initialized
            if not self.reattach():
                logging.error("Cannot move servo: not initialized and reattach failed")
                return False
            
        if angle < self.min_angle:
            angle = self.min_angle
        elif angle > self.max_angle:
            angle = self.max_angle
            
        if self.simulation_mode:
            logging.info(f"Simulation: Moved to {angle} degrees")
            return True
            
        try:
            self.servo.angle = angle
            logging.info(f"Moved to {angle} degrees")
            return True
        except Exception as e:
            logging.error(f"Failed to move servo: {e}")
            return False
            
    def _run_sequence(self):
        """Run the A-B-A-B sequence for laser firing in a separate thread"""
        try:
            # Load configuration
            servo_config = get_servo_config()
            timing_config = get_timing_config()
            sequence_delay = servo_config['sequence_delay'] / 1000.0  # Convert to seconds
            threshold = timing_config['laser_fire_threshold']
            
            # Calculate angles
            angle_a = self.position_b if self.inverted else self.position_a
            angle_b = self.position_a if self.inverted else self.position_b
            
            if self.simulation_mode:
                # In simulation mode, just log the movements and timing
                logging.info(f"Simulation: Moving to position A ({angle_a} degrees)")
                time.sleep(sequence_delay)
                
                # Step 1: Move to B (0.5 sec)
                if self.sequence_stop_flag.is_set():
                    return
                logging.info(f"Simulation: Moving to position B ({angle_b} degrees)")
                time.sleep(sequence_delay)
                
                # Step 2: Move to A (0.5 sec)
                if self.sequence_stop_flag.is_set():
                    return
                logging.info(f"Simulation: Moving back to position A ({angle_a} degrees)")
                time.sleep(sequence_delay)
                
                # Step 3: Move to B (hold)
                if self.sequence_stop_flag.is_set():
                    return
                logging.info(f"Simulation: Moving to position B ({angle_b} degrees) and holding")
                
                # Start tracking laser firing time
                self.fire_start_time = int(time.time() * 1000)
                self.is_firing = True
                
                # Wait until stop flag is set
                while not self.sequence_stop_flag.is_set():
                    time.sleep(0.1)
                    
                # Return to position A
                logging.info(f"Simulation: Emergency stop - Moving to position A ({angle_a} degrees)")
            else:
                # Ensure we're attached first
                if not self.initialized:
                    self.reattach()
                
                # First, ensure we're starting from position A
                self.servo.angle = angle_a
                time.sleep(sequence_delay)
                
                # Step 1: Move to B (0.5 sec)
                if self.sequence_stop_flag.is_set():
                    return
                    
                self.servo.angle = angle_b
                time.sleep(sequence_delay)
                
                # Step 2: Move to A (0.5 sec)
                if self.sequence_stop_flag.is_set():
                    return
                    
                self.servo.angle = angle_a
                time.sleep(sequence_delay)
                
                # Step 3: Move to B (hold)
                if self.sequence_stop_flag.is_set():
                    return
                    
                self.servo.angle = angle_b
                
                # Start tracking laser firing time
                self.fire_start_time = int(time.time() * 1000)
                self.is_firing = True
                
                # Wait until stop flag is set
                while not self.sequence_stop_flag.is_set():
                    time.sleep(0.1)
                    
                # Return to position A
                self.servo.angle = angle_a
            
            # Calculate and record firing time (same for both modes)
            end_time = int(time.time() * 1000)
            firing_time = end_time - self.fire_start_time
            
            # If firing lasted longer than threshold, increment counter and add time
            if firing_time >= threshold:
                increment_laser_counter()
                add_laser_fire_time(firing_time)
                logging.info(f"Laser fired for {firing_time}ms, counter incremented")
                
            self.is_firing = False
            self.fire_start_time = 0
            
            time.sleep(sequence_delay)  # Wait for servo to settle
            
            # Detach only in real hardware mode
            if not self.simulation_mode:
                self.detach()  # Detach when done
                
        except Exception as e:
            logging.error(f"Error in sequence mode: {e}")
            self.is_firing = False
        finally:
            self.sequence_mode = False
            self.sequence_stop_flag.clear()
    
    def start_sequence(self):
        """Start the sequence mode (A-0.5sec, B-0.5sec, A-0.5sec, B-hold)"""
        with self.lock:
            if self.sequence_mode:
                logging.warning("Sequence already running")
                return False
                
            # Stop any existing sequence
            self.stop_sequence()
            
            # Make sure we're attached
            if not self.initialized:
                if not self.reattach():
                    logging.error("Cannot start sequence: servo not initialized")
                    return False
                    
            # Clear any existing stop flag
            self.sequence_stop_flag.clear()
            self.sequence_mode = True
            
            # Start sequence in a separate thread
            self.sequence_thread = threading.Thread(target=self._run_sequence)
            self.sequence_thread.daemon = True
            self.sequence_thread.start()
            
            logging.info("Laser sequence started")
            return True
    
    def stop_sequence(self):
        """Stop the sequence mode and immediately return to position A"""
        with self.lock:
            if not self.sequence_mode:
                return True
                
            # Set the stop flag to signal the sequence thread to stop
            self.sequence_stop_flag.set()
            
            # Wait for thread to finish if it exists
            if self.sequence_thread and self.sequence_thread.is_alive():
                self.sequence_thread.join(timeout=1.0)  # Reduced timeout for faster response
                
            self.sequence_mode = False
            logging.info("Laser sequence stopped")
            
            # Make sure we're back at position A immediately without delay
            return self.move_to_a(auto_detach=False, detach_delay=0)
    
    def fire(self, auto_detach=True, detach_delay=0.5):
        """
        Fire the laser (move to position B) and track firing time
        This is used for direct firing (not sequence mode)
        """
        with self.lock:
            if not self.initialized:
                # Try to reattach if not initialized
                if not self.reattach():
                    logging.error("Cannot fire: servo not initialized")
                    return False
            
            # Abort if already in sequence mode
            if self.sequence_mode:
                logging.warning("Cannot fire: sequence mode active")
                return False
                
            # Start tracking firing time
            self.fire_start_time = int(time.time() * 1000)
            self.is_firing = True
            
            # Move to position B (fire position)
            result = self.move_to_b(auto_detach=False)  # Don't auto-detach when firing
            
            if result:
                logging.info("Laser fired")
                return True
            else:
                self.is_firing = False
                self.fire_start_time = 0
                return False
    
    def stop_firing(self, auto_detach=False, detach_delay=0):
        """
        Stop firing immediately (move to position A with no delay) and update statistics
        """
        with self.lock:
            # Always try to stop sequence mode first, even if is_firing is false
            if hasattr(self, 'sequence_stop_flag'):
                self.sequence_stop_flag.set()
            
            if not self.is_firing:
                return True
                
            # Record end time and calculate duration
            end_time = int(time.time() * 1000)
            firing_time = end_time - self.fire_start_time
            
            # Reset firing state immediately before moving
            self.is_firing = False
            
            # Move back to position A immediately without detach delay
            result = True
            angle = self.position_b if self.inverted else self.position_a
            
            if self.simulation_mode:
                logging.info(f"Simulation: Emergency stop - Moved to position A ({angle} degrees)")
            else:
                try:
                    # Move servo back to position A as fast as possible
                    if self.initialized:
                        self.servo.angle = angle
                        logging.info(f"Emergency stop - Moved to position A ({angle} degrees)")
                    else:
                        logging.warning("Emergency stop - Servo not initialized")
                        result = False
                except Exception as e:
                    logging.error(f"Error in emergency stop: {e}")
                    result = False
            
            # If firing exceeded threshold, increment counter and add time
            if firing_time >= get_timing_config()['laser_fire_threshold']:
                increment_laser_counter()
                add_laser_fire_time(firing_time)
                logging.info(f"Laser fired for {firing_time}ms, counter incremented")
            else:
                logging.info(f"Laser fired for {firing_time}ms (below threshold)")
                
            # Optionally detach after returning to position A (only in real hardware mode)
            if result and auto_detach and not self.simulation_mode:
                time.sleep(detach_delay)
                self.detach()
                
            return result
                
    def get_status(self):
        """Get the current status of the servo"""
        # We only need to read data, so we'll avoid using the lock
        # to prevent issues with gunicorn worker timeouts
        current_time = int(time.time() * 1000)
        
        if self.simulation_mode:
            # In simulation mode, we don't have a real servo angle to report
            # So we'll simulate one based on the current state
            if self.is_firing:
                # If firing, report position B
                current_angle = self.position_a if self.inverted else self.position_b
            else:
                # If not firing, report position A
                current_angle = self.position_b if self.inverted else self.position_a
        elif self.initialized:
            try:
                current_angle = self.servo.angle
            except:
                current_angle = None
        else:
            current_angle = None
                
        return {
            "initialized": self.initialized,
            "position_a": self.position_a,
            "position_b": self.position_b,
            "inverted": self.inverted,
            "current_angle": current_angle,
            "sequence_mode": self.sequence_mode,
            "is_firing": self.is_firing,
            "fire_duration": current_time - self.fire_start_time if self.is_firing else 0,
            "simulation_mode": self.simulation_mode
        }
        
    def detach(self):
        """Detach the servo (stop sending PWM signals) to prevent jitter at rest"""
        if self.simulation_mode:
            # In simulation mode, just log the action
            logging.info("Simulation: Servo detached")
            return True
            
        if self.initialized and self.servo:
            try:
                # Close the servo
                self.servo.close()
                self.initialized = False
                logging.info("Servo detached")
                return True
            except Exception as e:
                logging.error(f"Error detaching servo: {e}")
                return False
        return False
        
    def reattach(self, initial_angle=None):
        """Reattach the servo to allow movement again"""
        if self.simulation_mode:
            # In simulation mode, just log the action
            logging.info(f"Simulation: Servo reattached to pin {self.servo_pin}")
            self.initialized = True
            return True
            
        try:
            # Initialize a new servo instance
            self.servo = ServoWrapper(
                pin=self.servo_pin,
                initial_angle=initial_angle if initial_angle is not None else self.position_a,
                min_angle=self.min_angle,
                max_angle=self.max_angle,
                simulation_mode=self.simulation_mode
            )
            
            self.initialized = True
            logging.info(f"Servo reattached to pin {self.servo_pin}")
            return True
        except Exception as e:
            logging.error(f"Error reattaching servo: {e}")
            return False
    
    def cleanup(self):
        """Clean up GPIO pins"""
        # Stop any ongoing operations
        self.stop_sequence()
        self.stop_firing()
        
        if self.simulation_mode:
            # In simulation mode, just log the action
            logging.info("Simulation: Servo GPIO cleaned up")
            self.initialized = False
            return
            
        if self.initialized and self.servo:
            try:
                # Close the servo
                self.servo.close()
                self.initialized = False
                logging.info("Servo GPIO cleaned up")
            except Exception as e:
                logging.error(f"Error cleaning up servo: {e}")
        else:
            logging.debug("No servo to clean up")