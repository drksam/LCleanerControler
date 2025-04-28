import time
import logging
import threading
from gpiozero import Servo, AngularServo
import os
from config import get_servo_config, add_laser_fire_time, increment_laser_counter, get_timing_config

class ServoController:
    """
    Class to control a PWM servo with two preset positions (A and B),
    inversion capability, and sequence mode for the laser trigger.
    """
    
    def __init__(self, servo_pin, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000, 
                 min_angle=-90, max_angle=90, initial_angle=0):
        """
        Initialize the servo controller
        
        Args:
            servo_pin (int): BCM pin number connected to the servo signal wire
            min_pulse_width (float): The pulse width corresponding to the minimum angle in seconds
            max_pulse_width (float): The pulse width corresponding to the maximum angle in seconds
            min_angle (int): The minimum angle in degrees
            max_angle (int): The maximum angle in degrees
            initial_angle (int): The initial angle to set on startup
        """
        self.servo_pin = servo_pin
        self.min_angle = min_angle
        self.max_angle = max_angle
        
        # Default positions
        self.position_a = 0  # Middle position
        self.position_b = 90  # Full right position
        self.inverted = False
        
        # Sequence mode state
        self.sequence_mode = False
        self.sequence_thread = None
        self.sequence_stop_flag = threading.Event()
        
        # Fire tracking - for statistics
        self.fire_start_time = 0
        self.is_firing = False
        
        # Threading lock for thread safety
        self.lock = threading.Lock()
        
        # Check system configuration mode
        import config
        system_config = config.get_system_config()
        operation_mode = system_config.get('operation_mode', 'simulation')
        
        # Set simulation mode based on system configuration
        self.simulation_mode = operation_mode == 'simulation'
        
        if self.simulation_mode:
            logging.info("Running in simulation mode - no GPIO operations will be performed")
            self.initialized = True
            self.servo = None
            return
            
        try:
            self.servo = AngularServo(
                servo_pin,
                min_pulse_width=min_pulse_width,
                max_pulse_width=max_pulse_width,
                min_angle=min_angle,
                max_angle=max_angle
            )
            self.servo.angle = initial_angle
            self.initialized = True
            logging.info(f"Servo initialized on pin {servo_pin}")
        except Exception as e:
            logging.error(f"Failed to initialize servo: {e}")
            self.initialized = False
            self.simulation_mode = True  # Fall back to simulation mode
            self.servo = None
            
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
        
    def move_to_a(self, auto_detach=True, detach_delay=0.5):
        """Move servo to position A"""
        if self.simulation_mode:
            angle = self.position_b if self.inverted else self.position_a
            logging.info(f"Simulation: Moved to position A ({angle} degrees)")
            return True
            
        if not self.initialized:
            # Try to reattach if not initialized
            if not self.reattach():
                logging.error("Cannot move servo: not initialized and reattach failed")
                return False
            
        angle = self.position_b if self.inverted else self.position_a
        try:
            self.servo.angle = angle
            logging.info(f"Moved to position A ({angle} degrees)")
            
            # Optionally detach after a delay to prevent jitter
            if auto_detach:
                time.sleep(detach_delay)  # Wait for servo to settle
                self.detach()
                
            return True
        except Exception as e:
            logging.error(f"Failed to move servo: {e}")
            return False
            
    def move_to_b(self, auto_detach=True, detach_delay=0.5):
        """Move servo to position B"""
        if self.simulation_mode:
            angle = self.position_a if self.inverted else self.position_b
            logging.info(f"Simulation: Moved to position B ({angle} degrees)")
            return True
        
        if not self.initialized:
            # Try to reattach if not initialized
            if not self.reattach():
                logging.error("Cannot move servo: not initialized and reattach failed")
                return False
            
        angle = self.position_a if self.inverted else self.position_b
        try:
            self.servo.angle = angle
            logging.info(f"Moved to position B ({angle} degrees)")
            
            # Optionally detach after a delay to prevent jitter
            if auto_detach:
                time.sleep(detach_delay)  # Wait for servo to settle
                self.detach()
                
            return True
        except Exception as e:
            logging.error(f"Failed to move servo: {e}")
            return False
            
    def move_to_angle(self, angle, auto_detach=True, detach_delay=0.5):
        """Move servo to a specific angle"""
        if self.simulation_mode:
            logging.info(f"Simulation: Moved to {angle} degrees")
            return True
            
        if not self.initialized:
            # Try to reattach if not initialized
            if not self.reattach():
                logging.error("Cannot move servo: not initialized and reattach failed")
                return False
            
        if angle < self.min_angle:
            angle = self.min_angle
        elif angle > self.max_angle:
            angle = self.max_angle
            
        try:
            self.servo.angle = angle
            logging.info(f"Moved to {angle} degrees")
            
            # Optionally detach after a delay to prevent jitter
            if auto_detach:
                time.sleep(detach_delay)  # Wait for servo to settle
                self.detach()
                
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
                # Real hardware mode
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
        current_angle = None
        
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
                pass
                
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
            self.initialized = False
            return True
            
        if self.initialized:
            try:
                # Close the GPIO pin
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
            
        if not self.initialized:
            try:
                self.servo = AngularServo(
                    self.servo_pin,
                    min_pulse_width=0.5/1000,
                    max_pulse_width=2.5/1000,
                    frame_width=20/1000,  # 20ms frame width (standard for most servos)
                    min_angle=self.min_angle,
                    max_angle=self.max_angle
                )
                
                # Set initial angle if provided
                if initial_angle is not None:
                    self.servo.angle = initial_angle
                
                self.initialized = True
                logging.info(f"Servo reattached to pin {self.servo_pin}")
                return True
            except Exception as e:
                logging.error(f"Error reattaching servo: {e}")
                return False
        return True
    
    def cleanup(self):
        """Clean up GPIO pins"""
        if self.simulation_mode:
            # In simulation mode, just log the action
            logging.info("Simulation: Servo GPIO cleaned up")
            self.initialized = False
            return
            
        if self.initialized:
            # Move to the middle position before cleanup
            try:
                self.servo.angle = 0
                time.sleep(0.5)  # Wait for the servo to move
            except:
                pass
                
            # Close the GPIO pin
            self.servo.close()
            self.initialized = False
            logging.info("Servo GPIO cleaned up")