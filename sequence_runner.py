"""
Sequence Runner module for executing predefined operation sequences.
This module handles the execution of sequences stored in configuration.
"""
import time
import logging
import threading
from enum import Enum

# Set up logger
logger = logging.getLogger(__name__)

class SequenceStatus(Enum):
    """Status of a sequence execution"""
    IDLE = 0
    RUNNING = 1
    PAUSED = 2
    COMPLETED = 3
    ERROR = 4

class SequenceRunner:
    """
    Class to execute predefined operation sequences.
    Handles execution of steps like stepper movement, servo actions, and waiting.
    """
    
    def __init__(self, stepper=None, servo=None, output_controller=None):
        """
        Initialize the sequence runner with controllers
        
        Args:
            stepper: StepperMotor instance for controlling the stepper motor
            servo: ServoController instance for controlling the servo
            output_controller: OutputController for controlling fan, lights, table
        """
        self.stepper = stepper
        self.servo = servo
        self.output_controller = output_controller
        
        self.sequence_thread = None
        self.current_sequence = None
        self.status = SequenceStatus.IDLE
        self.current_step_index = -1
        self.stop_flag = threading.Event()
        self.pause_flag = threading.Event()
        
        # For tracking progress
        self.total_steps = 0
        self.steps_completed = 0
        self.execution_log = []
        
    def load_sequence(self, sequence_data):
        """
        Load a sequence for execution
        
        Args:
            sequence_data: Dictionary with sequence data
        
        Returns:
            bool: True if sequence loaded successfully
        """
        if not sequence_data or 'steps' not in sequence_data or not sequence_data['steps']:
            logger.error("Invalid sequence data provided")
            return False
        
        self.current_sequence = sequence_data
        self.total_steps = len(sequence_data['steps'])
        self.current_step_index = -1
        self.steps_completed = 0
        self.execution_log = []
        self.status = SequenceStatus.IDLE
        
        return True
        
    def start(self):
        """
        Start executing the sequence in a separate thread
        
        Returns:
            bool: True if sequence started successfully
        """
        if self.status == SequenceStatus.RUNNING:
            logger.warning("Sequence already running")
            return False
            
        if not self.current_sequence:
            logger.error("No sequence loaded")
            return False
        
        # Reset flags and status
        self.stop_flag.clear()
        self.pause_flag.clear()
        self.status = SequenceStatus.RUNNING
        self.execution_log = []
        
        # Start sequence execution in a separate thread
        self.sequence_thread = threading.Thread(target=self._execute_sequence)
        self.sequence_thread.daemon = True
        self.sequence_thread.start()
        
        return True
    
    def _execute_sequence(self):
        """Execute the loaded sequence"""
        try:
            # Safely get sequence name
            sequence_name = "Unnamed"
            if self.current_sequence is not None:
                sequence_name = self.current_sequence.get('name', 'Unnamed')
                
            logger.info(f"Starting sequence: {sequence_name}")
            self.execution_log.append(f"Sequence started: {time.strftime('%H:%M:%S')}")
            
            # Execute each step in the sequence
            if self.current_sequence is not None and 'steps' in self.current_sequence:
                for i, step in enumerate(self.current_sequence['steps']):
                    # Check if we should stop
                    if self.stop_flag.is_set():
                        logger.info("Sequence stopped by user")
                        self.execution_log.append("Sequence stopped by user")
                        self.status = SequenceStatus.IDLE
                        return
                
                    # Handle pause
                    if self.pause_flag.is_set():
                        logger.info("Sequence paused")
                        self.execution_log.append("Sequence paused")
                        self.status = SequenceStatus.PAUSED
                        
                        # Wait until unpaused or stopped
                        while self.pause_flag.is_set() and not self.stop_flag.is_set():
                            time.sleep(0.1)
                        
                        # If we were told to stop while paused
                        if self.stop_flag.is_set():
                            logger.info("Sequence stopped while paused")
                            self.execution_log.append("Sequence stopped while paused")
                            self.status = SequenceStatus.IDLE
                            return
                        
                        # Otherwise we've been unpaused
                        logger.info("Sequence resumed")
                        self.execution_log.append("Sequence resumed")
                        self.status = SequenceStatus.RUNNING
                    
                    # Update current step
                    self.current_step_index = i
                    
                    # Execute the step
                    action = step.get('action', '')
                    result = self._execute_step(step)
                    
                    if not result:
                        logger.error(f"Error executing step {i+1}: {action}")
                        self.execution_log.append(f"Error executing step {i+1}: {action}")
                        self.status = SequenceStatus.ERROR
                        return
                    
                    # Update progress
                    self.steps_completed = i + 1
                    
                    # Wait for any delay after the step
                    delay_after = step.get('delay_after', 0)
                    if delay_after > 0:
                        # Convert to seconds if specified in milliseconds
                        delay_sec = delay_after / 1000.0 if delay_after > 100 else delay_after
                        
                        # Wait in small increments to allow stopping/pausing
                        start_time = time.time()
                        while time.time() - start_time < delay_sec:
                            if self.stop_flag.is_set():
                                logger.info("Sequence stopped during delay")
                                self.execution_log.append("Sequence stopped during delay")
                                self.status = SequenceStatus.IDLE
                                return
                            
                            if self.pause_flag.is_set():
                                remaining_delay = delay_sec - (time.time() - start_time)
                                logger.info(f"Sequence paused during delay (remaining: {remaining_delay:.1f}s)")
                                self.execution_log.append("Sequence paused during delay")
                                self.status = SequenceStatus.PAUSED
                                
                                # Wait until unpaused or stopped
                                while self.pause_flag.is_set() and not self.stop_flag.is_set():
                                    time.sleep(0.1)
                                
                                # If we were told to stop while paused
                                if self.stop_flag.is_set():
                                    logger.info("Sequence stopped while paused during delay")
                                    self.execution_log.append("Sequence stopped while paused")
                                    self.status = SequenceStatus.IDLE
                                    return
                                
                                # Otherwise we've been unpaused, continue the remaining delay
                                logger.info("Sequence resumed from delay")
                                self.execution_log.append("Sequence resumed")
                                self.status = SequenceStatus.RUNNING
                                start_time = time.time() - (delay_sec - remaining_delay)
                            
                            # Sleep a small amount to not hog the CPU
                            time.sleep(0.1)
            
            # All steps completed successfully
            logger.info("Sequence completed successfully")
            self.execution_log.append(f"Sequence completed: {time.strftime('%H:%M:%S')}")
            self.status = SequenceStatus.COMPLETED
            
        except Exception as e:
            logger.error(f"Error executing sequence: {e}")
            self.execution_log.append(f"Error: {str(e)}")
            self.status = SequenceStatus.ERROR
    
    def _execute_step(self, step):
        """
        Execute a single step in the sequence
        
        Args:
            step: Dictionary with step details
        
        Returns:
            bool: True if step executed successfully
        """
        try:
            action = step.get('action', '')
            
            # Log the action
            logger.info(f"Executing step: {action}")
            self.execution_log.append(f"Step: {action}")
            
            # Execute different actions based on the action type
            if action == 'stepper_move':
                return self._execute_stepper_move(step)
            elif action == 'fire':
                return self._execute_fire(step)
            elif action == 'fire_fiber':
                return self._execute_fire_fiber()
            elif action == 'stop_fire':
                return self._execute_stop_fire()
            elif action == 'wait':
                return self._execute_wait(step)
            elif action == 'wait_input':
                return self._execute_wait_input(step)
            elif action == 'fan_on':
                return self._execute_fan(True)
            elif action == 'fan_off':
                return self._execute_fan(False)
            elif action == 'lights_on':
                return self._execute_lights(True)
            elif action == 'lights_off':
                return self._execute_lights(False)
            elif action == 'table_forward':
                return self._execute_table_forward(step)
            elif action == 'table_backward':
                return self._execute_table_backward(step)
            else:
                logger.error(f"Unknown action: {action}")
                return False
        
        except Exception as e:
            logger.error(f"Error executing step: {e}")
            return False
    
    def _execute_stepper_move(self, step):
        """Execute a stepper move action"""
        if not self.stepper:
            logger.warning("Stepper motor not available, simulating move")
            direction = step.get('direction', 'in')
            steps = step.get('steps', 100)
            self.execution_log.append(f"Simulated stepper move: {direction}, {steps} steps")
            return True
        
        try:
            # Get direction and steps from the step data
            direction = step.get('direction', 'in')
            steps = step.get('steps', 100)
            
            # Calculate actual steps based on direction
            actual_steps = steps if direction == 'in' else -steps
            
            # Move the stepper
            self.stepper.enable()
            moved_steps = self.stepper.step(actual_steps)
            
            # Log the result
            self.execution_log.append(f"Moved stepper: {direction}, {abs(moved_steps)} steps")
            
            return True
        except Exception as e:
            logger.error(f"Error moving stepper: {e}")
            return False
    
    def _execute_fire(self, step):
        """Execute a fire action (move servo to firing position)"""
        if not self.servo:
            logger.warning("Servo not available, simulating fire")
            duration = step.get('duration', 2000)
            self.execution_log.append(f"Simulated fire for {duration} ms")
            return True
        
        try:
            # Move the servo to fire position
            result = self.servo.fire()
            
            # Log the result
            if result:
                self.execution_log.append("Started firing")
            else:
                self.execution_log.append("Failed to start firing")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error firing: {e}")
            return False
    
    def _execute_fire_fiber(self):
        """Execute a fire fiber sequence (A-B-A-B pattern)"""
        if not self.servo:
            logger.warning("Servo not available, simulating fire fiber sequence")
            self.execution_log.append("Simulated fiber sequence (A-B-A-B)")
            return True
        
        try:
            # Start the FIBER sequence (A-B-A-B pattern)
            result = self.servo.start_sequence()
            
            # Log the result
            if result:
                self.execution_log.append("Started fiber sequence (A-B-A-B)")
            else:
                self.execution_log.append("Failed to start fiber sequence")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error starting fiber sequence: {e}")
            return False
    
    def _execute_stop_fire(self):
        """Execute a stop fire action (move servo back to normal position)"""
        if not self.servo:
            logger.warning("Servo not available, simulating stop fire")
            self.execution_log.append("Simulated stop fire")
            return True
        
        try:
            # First stop any ongoing sequence
            if hasattr(self.servo, 'stop_sequence'):
                self.servo.stop_sequence()
                
            # Move the servo back to normal position
            result = self.servo.stop_firing()
            
            # Log the result
            if result:
                self.execution_log.append("Stopped firing")
            else:
                self.execution_log.append("Failed to stop firing")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error stopping fire: {e}")
            return False
    
    def _execute_wait_input(self, step):
        """Execute a wait for input action"""
        input_type = step.get('input_type', 'button_in')
        timeout_ms = step.get('timeout', 0)
        
        # Log the wait input
        timeout_str = f" (timeout: {timeout_ms}ms)" if timeout_ms > 0 else " (no timeout)"
        self.execution_log.append(f"Waiting for input: {input_type}{timeout_str}")
        
        # Calculate timeout in seconds
        timeout_sec = timeout_ms / 1000.0 if timeout_ms > 0 else None
        
        # Start waiting time
        start_time = time.time()
        input_detected = False
        
        # Wait for input or timeout
        while not input_detected:
            # Check for stop/pause requests
            if self.stop_flag.is_set():
                self.execution_log.append("Wait for input stopped by user")
                return True  # We return True because the step itself didn't fail
            
            if self.pause_flag.is_set():
                self.execution_log.append("Wait for input paused")
                self.status = SequenceStatus.PAUSED
                
                # Wait until unpaused or stopped
                while self.pause_flag.is_set() and not self.stop_flag.is_set():
                    time.sleep(0.1)
                
                # If we were told to stop while paused
                if self.stop_flag.is_set():
                    self.execution_log.append("Wait for input stopped while paused")
                    return True
                
                # Otherwise we've been unpaused
                self.execution_log.append("Wait for input resumed")
                self.status = SequenceStatus.RUNNING
            
            # Check if we've timed out
            if timeout_sec is not None and time.time() - start_time > timeout_sec:
                self.execution_log.append(f"Wait for input timed out after {timeout_ms}ms")
                return True
            
            # Check for the specified input
            input_detected = self._check_input_state(input_type)
            
            # If input not detected, sleep a bit to avoid CPU spinning
            if not input_detected:
                time.sleep(0.1)
        
        # Input was detected
        self.execution_log.append(f"Input {input_type} detected, continuing")
        return True
    
    def _check_input_state(self, input_type):
        """
        Check if the specified input is active
        
        Args:
            input_type: The type of input to check
            
        Returns:
            bool: True if the input is active
        """
        # Simulation mode - randomly detect input with 5% probability each check
        if not self.output_controller:
            # This is a simulation, so we'll occasionally return True to simulate input
            import random
            if random.random() < 0.05:  # 5% chance of detecting input on each check
                return True
            return False
        
        # Real hardware mode
        try:
            # Get the current status of all I/O
            status = self.output_controller.get_status()
            
            # Check for specific input types
            if input_type == 'button_in':
                # Check IN button status through input controller
                # For now we'll simulate it in the same way as other inputs
                import random
                return random.random() < 0.05
                
            elif input_type == 'button_out':
                # Check OUT button status through input controller
                import random
                return random.random() < 0.05
                
            elif input_type == 'fire_button':
                # Check FIRE button status through input controller
                import random
                return random.random() < 0.05
                
            elif input_type == 'table_front_limit':
                # Check table front limit switch status
                return status.get('table_front_limit', False)
                
            elif input_type == 'table_back_limit':
                # Check table back limit switch status
                return status.get('table_back_limit', False)
                
            else:
                logger.warning(f"Unknown input type: {input_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking input state: {e}")
            return False
    
    def _execute_wait(self, step):
        """Execute a wait action"""
        duration = step.get('duration', 1000)
        
        # Log the wait
        self.execution_log.append(f"Waiting for {duration} ms")
        
        # Note: We don't actually wait here - the delay is handled in the main sequence
        # execution loop to allow for proper pause/stop handling
        return True
    
    def _execute_fan(self, state):
        """Execute a fan control action"""
        if not self.output_controller:
            logger.warning("Output controller not available, simulating fan control")
            self.execution_log.append(f"Simulated fan {'ON' if state else 'OFF'}")
            return True
        
        try:
            # Set the fan state
            self.output_controller.set_fan(state)
            
            # Log the result
            self.execution_log.append(f"Fan {'ON' if state else 'OFF'}")
            
            return True
        except Exception as e:
            logger.error(f"Error controlling fan: {e}")
            return False
    
    def _execute_lights(self, state):
        """Execute a lights control action"""
        if not self.output_controller:
            logger.warning("Output controller not available, simulating lights control")
            self.execution_log.append(f"Simulated lights {'ON' if state else 'OFF'}")
            return True
        
        try:
            # Set the lights state
            self.output_controller.set_red_lights(state)
            
            # Log the result
            self.execution_log.append(f"Lights {'ON' if state else 'OFF'}")
            
            return True
        except Exception as e:
            logger.error(f"Error controlling lights: {e}")
            return False
    
    def _execute_table_forward(self, step):
        """Execute a table forward action"""
        if not self.output_controller:
            logger.warning("Output controller not available, simulating table forward")
            duration = step.get('duration', 1000)
            self.execution_log.append(f"Simulated table forward for {duration} ms")
            time.sleep(duration / 1000.0)
            return True
        
        try:
            # Move table forward
            self.output_controller.set_table_forward(True)
            
            # Wait for specified duration
            duration = step.get('duration', 1000)
            time.sleep(duration / 1000.0)
            
            # Stop table movement
            self.output_controller.set_table_forward(False)
            
            # Log the result
            self.execution_log.append(f"Table forward for {duration} ms")
            
            return True
        except Exception as e:
            logger.error(f"Error moving table forward: {e}")
            return False
    
    def _execute_table_backward(self, step):
        """Execute a table backward action"""
        if not self.output_controller:
            logger.warning("Output controller not available, simulating table backward")
            duration = step.get('duration', 1000)
            self.execution_log.append(f"Simulated table backward for {duration} ms")
            time.sleep(duration / 1000.0)
            return True
        
        try:
            # Move table backward
            self.output_controller.set_table_backward(True)
            
            # Wait for specified duration
            duration = step.get('duration', 1000)
            time.sleep(duration / 1000.0)
            
            # Stop table movement
            self.output_controller.set_table_backward(False)
            
            # Log the result
            self.execution_log.append(f"Table backward for {duration} ms")
            
            return True
        except Exception as e:
            logger.error(f"Error moving table backward: {e}")
            return False
    
    def stop(self):
        """
        Stop the sequence execution
        
        Returns:
            bool: True if stopped successfully
        """
        if self.status != SequenceStatus.RUNNING and self.status != SequenceStatus.PAUSED:
            return True
        
        # Set stop flag
        self.stop_flag.set()
        
        # Wait for thread to complete
        if self.sequence_thread and self.sequence_thread.is_alive():
            self.sequence_thread.join(timeout=2.0)
        
        # Clean up any ongoing operations
        self._cleanup_operations()
        
        return True
    
    def pause(self):
        """
        Pause the sequence execution
        
        Returns:
            bool: True if paused successfully
        """
        if self.status != SequenceStatus.RUNNING:
            return False
        
        # Set pause flag
        self.pause_flag.set()
        
        return True
    
    def resume(self):
        """
        Resume a paused sequence
        
        Returns:
            bool: True if resumed successfully
        """
        if self.status != SequenceStatus.PAUSED:
            return False
        
        # Clear pause flag
        self.pause_flag.clear()
        
        return True
    
    def _cleanup_operations(self):
        """Clean up any ongoing operations when stopping a sequence"""
        try:
            # Stop firing if it was happening
            if self.servo:
                # Stop any running sequence first
                if hasattr(self.servo, 'stop_sequence'):
                    self.servo.stop_sequence()
                
                # Stop basic firing action
                self.servo.stop_firing()
            
            # Stop table movement
            if self.output_controller:
                self.output_controller.set_table_forward(False)
                self.output_controller.set_table_backward(False)
        except Exception as e:
            logger.error(f"Error cleaning up operations: {e}")
    
    def get_status(self):
        """
        Get the current status of the sequence execution
        
        Returns:
            dict: Status information
        """
        return {
            'status': self.status.name,
            'sequence_name': self.current_sequence.get('name', 'Unnamed') if self.current_sequence else None,
            'current_step': self.current_step_index + 1,
            'total_steps': self.total_steps,
            'progress_percent': int((self.steps_completed / self.total_steps) * 100) if self.total_steps > 0 else 0,
            'execution_log': self.execution_log
        }
    
    def cleanup(self):
        """Clean up resources"""
        self.stop()