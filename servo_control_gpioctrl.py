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
        
        # Toggle state tracking
        self.fire_toggle_active = False
        self.fiber_toggle_active = False
        
        # Threading lock for thread safety
        self.lock = threading.RLock()  # Use reentrant lock to prevent deadlock in toggle functions
        
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
    
    def fire_momentary(self, auto_detach=True, detach_delay=0.5):
        """
        Momentary Fire: A→B, hold, on release B→A
        This should be called on button press, and stop_firing() on button release
        """
        return self.fire(auto_detach=False)  # Don't auto-detach, wait for release
    
    def fire_toggle(self):
        """
        Toggle Fire: A→B, hold, on press again B→A
        Toggles between firing and stopped states
        """
        with self.lock:
            current_time = int(time.time() * 1000)
            
            # Add debouncing - ignore rapid calls within 500ms
            if hasattr(self, '_last_toggle_time') and (current_time - self._last_toggle_time) < 500:
                logging.warning(f"fire_toggle() debounced - ignoring rapid call (last call {current_time - self._last_toggle_time}ms ago)")
                if self.fire_toggle_active:
                    return {"status": "active", "position": "B"}
                else:
                    return {"status": "inactive", "position": "A"}
            
            self._last_toggle_time = current_time
            logging.info(f"fire_toggle() called, current state: fire_toggle_active={self.fire_toggle_active}")
            
            if not self.fire_toggle_active:
                # Start firing
                logging.info("Starting fire toggle (moving to position B)")
                if self.fire(auto_detach=False):
                    self.fire_toggle_active = True
                    logging.info("Fire toggle activated")
                    return {"status": "active", "position": "B"}
                else:
                    logging.error("Failed to start firing in toggle mode")
                    return {"status": "error", "message": "Failed to start firing"}
            else:
                # Stop firing - use manual stop instead of stop_firing() to avoid resetting toggle states
                logging.info("Stopping fire toggle (moving to position A)")
                
                # Calculate and record firing time
                if self.is_firing and self.fire_start_time > 0:
                    end_time = int(time.time() * 1000)
                    firing_time = end_time - self.fire_start_time
                    
                    # Record firing time if it meets threshold
                    threshold = get_timing_config().get('fire_count_threshold', 100)
                    if firing_time >= threshold:
                        increment_laser_counter()
                        add_laser_fire_time(firing_time)
                        logging.info(f"Laser fired for {firing_time}ms, counter incremented")
                
                # Reset firing state but keep toggle state control local
                self.is_firing = False
                self.fire_start_time = 0
                
                # Move to position A
                result = self.move_to_a(auto_detach=True)
                if result:
                    self.fire_toggle_active = False
                    logging.info("Fire toggle deactivated")
                    return {"status": "inactive", "position": "A"}
                else:
                    logging.error("Failed to stop firing in toggle mode")
                    return {"status": "error", "message": "Failed to stop firing"}
    
    def fiber_fire_momentary(self):
        """
        Momentary Fiber: A→B, B→A, A→B, hold, on release B→A
        Sequence: Move to B, return to A, move to B again, then hold until release
        """
        with self.lock:
            if not self.initialized:
                if not self.reattach():
                    logging.error("Cannot start fiber fire: servo not initialized")
                    return False
            
            try:
                # Sequence: A→B→A→B, then hold at B
                logging.info("Starting fiber fire momentary sequence: A→B→A→B→hold")
                
                # Step 1: A→B
                logging.info("Fiber sequence step 1: Moving to position B")
                if not self.move_to_b(auto_detach=False):
                    return False
                time.sleep(0.3)  # Longer pause for visibility
                
                # Step 2: B→A  
                logging.info("Fiber sequence step 2: Moving to position A")
                if not self.move_to_a(auto_detach=False):
                    return False
                time.sleep(0.3)  # Longer pause for visibility
                
                # Step 3: A→B and hold
                logging.info("Fiber sequence step 3: Moving to position B (final hold)")
                if not self.move_to_b(auto_detach=False):
                    return False
                
                # Track firing state
                self.fire_start_time = int(time.time() * 1000)
                self.is_firing = True
                
                logging.info("Fiber fire momentary sequence complete - holding at B")
                return True
                
            except Exception as e:
                logging.error(f"Error in fiber fire momentary sequence: {e}")
                return False
    
    def fiber_fire_toggle(self):
        """
        Toggle Fiber: A→B, B→A, A→B, hold, on press again B→A
        Same sequence as momentary but toggles on/off with button presses
        """
        with self.lock:
            current_time = int(time.time() * 1000)
            
            # Add debouncing - ignore rapid calls within 100ms (shorter for fiber since the sequence has delays)
            if hasattr(self, '_last_fiber_toggle_time') and (current_time - self._last_fiber_toggle_time) < 100:
                logging.warning(f"fiber_fire_toggle() debounced - ignoring rapid call (last call {current_time - self._last_fiber_toggle_time}ms ago)")
                if self.fiber_toggle_active:
                    return {"status": "active", "position": "B", "sequence": "complete"}
                else:
                    return {"status": "inactive", "position": "A", "sequence": "unknown"}
            
            self._last_fiber_toggle_time = current_time
            
            if not self.fiber_toggle_active:
                # Start fiber sequence
                if self.fiber_fire_momentary():
                    self.fiber_toggle_active = True
                    self._fiber_toggle_start_time = current_time  # Record when toggle started
                    logging.info("Fiber toggle activated")
                    return {"status": "active", "position": "B", "sequence": "complete"}
                else:
                    return {"status": "error", "message": "Failed to start fiber sequence"}
            else:
                # Ensure minimum hold time before allowing deactivation (prevent immediate toggle off)
                if hasattr(self, '_fiber_toggle_start_time'):
                    hold_time = current_time - self._fiber_toggle_start_time
                    min_hold_time = 1000  # Minimum 1 second hold
                    if hold_time < min_hold_time:
                        logging.warning(f"Fiber toggle deactivation ignored - minimum hold time not met (held for {hold_time}ms, required {min_hold_time}ms)")
                        return {"status": "active", "position": "B", "sequence": "complete"}
                
                # Stop firing - use manual stop instead of stop_firing() to avoid resetting other toggle states
                logging.info("Stopping fiber toggle (moving to position A)")
                
                # Calculate and record firing time
                if self.is_firing and self.fire_start_time > 0:
                    end_time = int(time.time() * 1000)
                    firing_time = end_time - self.fire_start_time
                    
                    # Record firing time if it meets threshold
                    threshold = get_timing_config().get('fire_count_threshold', 100)
                    if firing_time >= threshold:
                        increment_laser_counter()
                        add_laser_fire_time(firing_time)
                        logging.info(f"Laser fired for {firing_time}ms, counter incremented")
                
                # Reset firing state but keep toggle state control local
                self.is_firing = False
                self.fire_start_time = 0
                
                # Move to position A
                result = self.move_to_a(auto_detach=True)
                if result:
                    self.fiber_toggle_active = False
                    logging.info("Fiber toggle deactivated")
                    return {"status": "inactive", "position": "A", "sequence": "unknown"}
                else:
                    logging.error("Failed to stop fiber firing")
                    return {"status": "error", "message": "Failed to stop fiber firing"}
    
    def stop_all_firing(self):
        """
        Emergency stop - move servo to position A from any position
        This is critical for E-Stop functionality
        """
        with self.lock:
            logging.warning("EMERGENCY STOP - Moving servo to position A")
            
            # Reset all toggle states
            self.fire_toggle_active = False
            self.fiber_toggle_active = False
            
            # Stop any sequence mode
            if hasattr(self, 'sequence_stop_flag'):
                self.sequence_stop_flag.set()
            
            # Reset firing state
            self.is_firing = False
            self.fire_start_time = 0
            
            # Move to position A immediately
            return self.move_to_a(auto_detach=False)
    
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
    
    def stop_firing(self, reset_toggles=True):
        """
        Stop any active firing operation and return servo to position A.
        This is called by the web API to stop momentary or toggle firing.
        
        Args:
            reset_toggles (bool): Whether to reset toggle states. Set to False when called internally.
        """
        with self.lock:
            logging.info("stop_firing() called")
            if self.is_firing or self.fire_toggle_active or self.fiber_toggle_active:
                logging.info(f"Stopping firing: is_firing={self.is_firing}, fire_toggle={self.fire_toggle_active}, fiber_toggle={self.fiber_toggle_active}")
                
                # Calculate and record firing time
                if self.is_firing and self.fire_start_time > 0:
                    end_time = int(time.time() * 1000)
                    firing_time = end_time - self.fire_start_time
                    
                    # Record firing time if it meets threshold
                    threshold = get_timing_config().get('fire_count_threshold', 100)
                    if firing_time >= threshold:
                        increment_laser_counter()
                        add_laser_fire_time(firing_time)
                        logging.info(f"Laser fired for {firing_time}ms, counter incremented")
                
                # Reset firing state
                self.is_firing = False
                self.fire_start_time = 0
                
                # Only reset toggle states if requested (external calls like stop button)
                if reset_toggles:
                    self.fire_toggle_active = False
                    self.fiber_toggle_active = False
                
                # Move to position A
                result = self.move_to_a(auto_detach=True)
                if result:
                    logging.info("Firing stopped - servo moved to position A")
                return result
            else:
                # Nothing to stop, but ensure we're at position A
                logging.info("Nothing to stop, ensuring servo is at position A")
                return self.move_to_a(auto_detach=True)
    
    def get_toggle_states(self):
        """
        Get the current toggle states for fire and fiber operations.
        This is called by the web API to check button states.
        """
        return {
            "fire_toggle_active": self.fire_toggle_active,
            "fiber_toggle_active": self.fiber_toggle_active,
            "is_firing": self.is_firing,
            "sequence_mode": self.sequence_mode
        }