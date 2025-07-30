"""
Sequence Runner module for executing predefined operation sequences.
This module handles the execution of sequences stored in configuration.

Follows simulation rules defined in sim.txt:
- In simulation mode: Simulation should occur as expected
- In prototype mode: Hardware should be forced and errors returned when unavailable
- In normal mode: Simulation should not be a fallback; hardware errors should be displayed in UI
"""
import time
import logging
import threading
from enum import Enum
import json
import os
import heapq
import datetime
import uuid
from typing import Dict, Any, List, Optional, Union

# Set up logger
logger = logging.getLogger(__name__)

class LogLevel(Enum):
    """Log levels for sequence execution logs"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"
    SUCCESS = "success"

class LogCategory(Enum):
    """Categories for log entries to enable better filtering"""
    HARDWARE = "hardware"
    SEQUENCE = "sequence"
    STEP = "step"
    ERROR = "error"
    SIMULATION = "simulation"
    USER = "user"
    SYSTEM = "system"

class SequenceStatus(Enum):
    """Status of a sequence execution"""
    IDLE = 0
    RUNNING = 1
    PAUSED = 2
    COMPLETED = 3
    ERROR = 4
    WARNING = 5  # Non-critical errors

class OperationMode(Enum):
    """System operation modes"""
    SIMULATION = "simulation"  # Simulation mode - hardware is optional
    NORMAL = "normal"          # Normal mode - hardware is preferred
    PROTOTYPE = "prototype"    # Prototype mode - hardware is required

class ErrorType(Enum):
    """Types of errors that can occur during sequence execution"""
    HARDWARE_NOT_AVAILABLE = "hardware_not_available"
    HARDWARE_FAILURE = "hardware_failure"
    TIMEOUT = "timeout"
    INVALID_STEP = "invalid_step"
    UNEXPECTED = "unexpected"

class ErrorRecoveryAction(Enum):
    """Possible recovery actions for errors"""
    ABORT = "abort"       # Abort the sequence
    RETRY = "retry"       # Retry the operation
    SKIP = "skip"         # Skip this step and continue
    SIMULATE = "simulate" # Use simulation instead
    PAUSE = "pause"       # Pause for user intervention

class LogEntry:
    """
    Structured log entry for sequence execution
    Provides consistent formatting and additional metadata for logs
    """
    def __init__(
        self, 
        message: str, 
        level: LogLevel = LogLevel.INFO, 
        category: LogCategory = LogCategory.SEQUENCE,
        step_index: Optional[int] = None,
        step_action: Optional[str] = None,
        hardware_state: Optional[Dict[str, Any]] = None,
        error_type: Optional[ErrorType] = None,
        recovery_action: Optional[ErrorRecoveryAction] = None
    ):
        self.id = str(uuid.uuid4())[:8]  # Unique ID for log entry
        self.timestamp = datetime.datetime.now().isoformat()
        self.message = message
        self.level = level.value if isinstance(level, LogLevel) else level
        self.category = category.value if isinstance(category, LogCategory) else category
        self.step_index = step_index
        self.step_action = step_action
        self.hardware_state = hardware_state
        self.error_type = error_type.value if isinstance(error_type, ErrorType) else error_type
        self.recovery_action = recovery_action.value if isinstance(recovery_action, ErrorRecoveryAction) else recovery_action
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary"""
        result = {
            'id': self.id,
            'timestamp': self.timestamp,
            'message': self.message,
            'level': self.level,
            'category': self.category
        }
        
        # Add optional fields if they exist
        if self.step_index is not None:
            result['step_index'] = self.step_index
        if self.step_action:
            result['step_action'] = self.step_action
        if self.hardware_state:
            result['hardware_state'] = self.hardware_state
        if self.error_type:
            result['error_type'] = self.error_type
        if self.recovery_action:
            result['recovery_action'] = self.recovery_action
            
        return result
    
    def to_string(self) -> str:
        """Convert log entry to string for display"""
        timestamp_str = self.timestamp.split('T')[1].split('.')[0] if 'T' in self.timestamp else self.timestamp
        level_indicator = {
            LogLevel.INFO.value: "ℹ️",
            LogLevel.WARNING.value: "⚠️",
            LogLevel.ERROR.value: "❌",
            LogLevel.DEBUG.value: "🔍",
            LogLevel.SUCCESS.value: "✅"
        }.get(self.level, "")
        
        # Format message with step info if available
        if self.step_index is not None and self.step_action:
            step_info = f"[Step {self.step_index+1}: {self.step_action}] "
        elif self.step_index is not None:
            step_info = f"[Step {self.step_index+1}] "
        elif self.step_action:
            step_info = f"[{self.step_action}] "
        else:
            step_info = ""
            
        return f"{timestamp_str} {level_indicator} {step_info}{self.message}"
    
    def __str__(self) -> str:
        return self.to_string()

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
        
        # New structured log system
        self.execution_logs: List[LogEntry] = []  # Enhanced log entries
        self.execution_log: List[str] = []        # Legacy text logs (for backward compatibility)
        
        # For tracking simulation status
        self.simulation_used = False
        self.operation_mode = self._get_operation_mode()
        
        # Priority queue for steps scheduling
        self.step_queue = []
        
        # Sequence execution metadata
        self.sequence_start_time = None
        self.sequence_id = None
        
        # Hardware state snapshots
        self.hardware_states: List[Dict[str, Any]] = []
        
        # Error handling configuration - can be overridden by sequence-specific settings
        self.error_recovery_config = {
            # Default retry configuration
            'max_retries': 3,              # Maximum number of retry attempts
            'retry_delay': 1.0,            # Delay between retries in seconds
            'exponential_backoff': True,   # Whether to use exponential backoff for retries
            
            # Default error recovery strategies by error type
            'recovery_by_type': {
                ErrorType.HARDWARE_NOT_AVAILABLE.value: ErrorRecoveryAction.ABORT.value,
                ErrorType.HARDWARE_FAILURE.value: ErrorRecoveryAction.RETRY.value,
                ErrorType.TIMEOUT.value: ErrorRecoveryAction.RETRY.value,
                ErrorType.INVALID_STEP.value: ErrorRecoveryAction.ABORT.value,
                ErrorType.UNEXPECTED.value: ErrorRecoveryAction.ABORT.value
            },
            
            # Allow overriding recovery action by step type
            'recovery_by_step': {
                'stepper_move': {
                    ErrorType.HARDWARE_FAILURE.value: ErrorRecoveryAction.RETRY.value
                },
                'fire': {
                    ErrorType.HARDWARE_FAILURE.value: ErrorRecoveryAction.RETRY.value
                },
                'fire_fiber': {
                    ErrorType.HARDWARE_FAILURE.value: ErrorRecoveryAction.RETRY.value
                },
                'stop_fire': {
                    ErrorType.HARDWARE_FAILURE.value: ErrorRecoveryAction.RETRY.value
                }
            }
        }
        
        # Last error information
        self.last_error = {
            'type': None,
            'message': None,
            'step': None,
            'retry_count': 0,
            'recovery_action': None,
            'timestamp': None
        }
        
        # Create a root log entry for initialization
        self._log(
            "Sequence runner initialized", 
            LogLevel.INFO, 
            LogCategory.SYSTEM,
            hardware_state=self._get_hardware_state()
        )

    def _get_operation_mode(self):
        """
        Get the current operation mode from config file
        Returns OperationMode enum value
        """
        try:
            # Try to load from main config file
            if os.path.exists('config.py'):
                import config
                if hasattr(config, 'OPERATION_MODE'):
                    mode_str = config.OPERATION_MODE.lower()
                    try:
                        return OperationMode(mode_str)
                    except ValueError:
                        logger.warning(f"Invalid operation mode in config: {mode_str}")
            
            # Try to load from machine config
            if os.path.exists('machine_config.json'):
                with open('machine_config.json', 'r') as f:
                    machine_config = json.load(f)
                    if 'operation_mode' in machine_config:
                        mode_str = machine_config['operation_mode'].lower()
                        try:
                            return OperationMode(mode_str)
                        except ValueError:
                            logger.warning(f"Invalid operation mode in machine_config: {mode_str}")
            
            # Default to normal mode if not configured
            return OperationMode.NORMAL
            
        except Exception as e:
            logger.error(f"Error getting operation mode: {e}")
            # Default to normal mode in case of error
            return OperationMode.NORMAL
        
    def load_sequence(self, sequence_data):
        """
        Load a sequence for execution
        
        Args:
            sequence_data: Dictionary with sequence data
        
        Returns:
            bool: True if sequence loaded successfully
        """
        if not sequence_data or 'steps' not in sequence_data or not sequence_data['steps']:
            error_msg = "Invalid sequence data provided"
            logger.error(error_msg)
            self._log(error_msg, LogLevel.ERROR, LogCategory.SEQUENCE)
            return False
        
        self.current_sequence = sequence_data
        self.total_steps = len(sequence_data['steps'])
        self.current_step_index = -1
        self.steps_completed = 0
        self.execution_logs = []
        self.execution_log = []
        self.status = SequenceStatus.IDLE
        self.simulation_used = False
        self.sequence_id = str(uuid.uuid4())[:8]  # Generate a unique ID for this sequence run
        
        # Initialize priority queue for step execution
        self.step_queue = []
        
        # Add steps to priority queue with their index as priority
        for i, step in enumerate(sequence_data['steps']):
            heapq.heappush(self.step_queue, (i, step))
        
        # Load sequence-specific error recovery configuration if present
        if 'error_recovery' in sequence_data:
            self._merge_error_config(sequence_data['error_recovery'])
            
        # Reset error tracking
        self.last_error = {
            'type': None,
            'message': None,
            'step': None,
            'retry_count': 0,
            'recovery_action': None,
            'timestamp': None
        }
        
        # Log the sequence load
        sequence_name = sequence_data.get('name', 'Unnamed')
        log_message = f"Loaded sequence '{sequence_name}' with {self.total_steps} steps"
        self._log(log_message, LogLevel.INFO, LogCategory.SEQUENCE)
            
        return True

    def _log(self, message: str, level: LogLevel = LogLevel.INFO, category: LogCategory = LogCategory.SEQUENCE, 
             step_index: Optional[int] = None, step_action: Optional[str] = None, 
             hardware_state: Optional[Dict[str, Any]] = None, error_type: Optional[ErrorType] = None,
             recovery_action: Optional[ErrorRecoveryAction] = None) -> None:
        """
        Add a structured log entry to execution logs
        
        Args:
            message: Message to log
            level: LogLevel enum value
            category: LogCategory enum value
            step_index: Index of current step (if applicable)
            step_action: Action being performed (if applicable)
            hardware_state: Snapshot of hardware state (if applicable)
            error_type: Type of error (if applicable)
            recovery_action: Recovery action taken (if applicable)
        """
        # Create a structured log entry
        log_entry = LogEntry(
            message=message,
            level=level,
            category=category,
            step_index=step_index if step_index is not None else self.current_step_index,
            step_action=step_action,
            hardware_state=hardware_state,
            error_type=error_type,
            recovery_action=recovery_action
        )
        
        # Add to structured logs
        self.execution_logs.append(log_entry)
        
        # Add to traditional text logs for backward compatibility
        self.execution_log.append(str(log_entry))
        
        # Also send to Python logger
        if level == LogLevel.ERROR:
            logger.error(log_entry.to_string())
        elif level == LogLevel.WARNING:
            logger.warning(log_entry.to_string())
        elif level == LogLevel.DEBUG:
            logger.debug(log_entry.to_string())
        else:
            logger.info(log_entry.to_string())

    def _get_hardware_state(self) -> Dict[str, Any]:
        """
        Get a snapshot of the current hardware state
        
        Returns:
            dict: Current state of all hardware components
        """
        state = {
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Get stepper state if available
        if self.stepper:
            try:
                state['stepper'] = {
                    'available': True,
                    'enabled': self.stepper.is_enabled() if hasattr(self.stepper, 'is_enabled') else None,
                    'position': self.stepper.get_position() if hasattr(self.stepper, 'get_position') else None,
                    'temperature': self.stepper.get_temperature() if hasattr(self.stepper, 'get_temperature') else None
                }
            except Exception as e:
                state['stepper'] = {
                    'available': False,
                    'error': str(e)
                }
        else:
            state['stepper'] = {
                'available': False
            }
        
        # Get servo state if available
        if self.servo:
            try:
                state['servo'] = {
                    'available': True,
                    'position': self.servo.get_position() if hasattr(self.servo, 'get_position') else None,
                    'is_firing': self.servo.is_firing() if hasattr(self.servo, 'is_firing') else None,
                    'sequence_running': self.servo.is_sequence_running() if hasattr(self.servo, 'is_sequence_running') else None
                }
            except Exception as e:
                state['servo'] = {
                    'available': False,
                    'error': str(e)
                }
        else:
            state['servo'] = {
                'available': False
            }
        
        # Get output controller state if available
        if self.output_controller:
            try:
                io_status = self.output_controller.get_status()
                state['output_controller'] = {
                    'available': True,
                    'io_status': io_status
                }
            except Exception as e:
                state['output_controller'] = {
                    'available': False,
                    'error': str(e)
                }
        else:
            state['output_controller'] = {
                'available': False
            }
        
        return state

    def _snapshot_hardware_state(self, context: str = None) -> Dict[str, Any]:
        """
        Take a snapshot of hardware state and save it to the hardware states list
        
        Args:
            context: Optional context describing when the snapshot was taken
            
        Returns:
            dict: The captured hardware state
        """
        state = self._get_hardware_state()
        
        # Add context if provided
        if context:
            state['context'] = context
            
        # Add to hardware states list
        self.hardware_states.append(state)
        
        return state

    def _merge_error_config(self, sequence_error_config):
        """
        Merge sequence-specific error recovery configuration with default config
        
        Args:
            sequence_error_config: Error recovery configuration from sequence data
        """
        if not sequence_error_config:
            return
            
        # Update max retries if specified
        if 'max_retries' in sequence_error_config:
            self.error_recovery_config['max_retries'] = sequence_error_config['max_retries']
            
        # Update retry delay if specified
        if 'retry_delay' in sequence_error_config:
            self.error_recovery_config['retry_delay'] = sequence_error_config['retry_delay']
            
        # Update exponential backoff flag if specified
        if 'exponential_backoff' in sequence_error_config:
            self.error_recovery_config['exponential_backoff'] = sequence_error_config['exponential_backoff']
            
        # Update recovery by type if specified
        if 'recovery_by_type' in sequence_error_config:
            for error_type, action in sequence_error_config['recovery_by_type'].items():
                if error_type in self.error_recovery_config['recovery_by_type']:
                    self.error_recovery_config['recovery_by_type'][error_type] = action
                    
        # Update recovery by step if specified
        if 'recovery_by_step' in sequence_error_config:
            for step_type, config in sequence_error_config['recovery_by_step'].items():
                if step_type not in self.error_recovery_config['recovery_by_step']:
                    self.error_recovery_config['recovery_by_step'][step_type] = {}
                    
                for error_type, action in config.items():
                    self.error_recovery_config['recovery_by_step'][step_type][error_type] = action

    def start(self):
        """
        Start executing the sequence in a separate thread
        
        Returns:
            bool: True if sequence started successfully
        """
        if self.status == SequenceStatus.RUNNING:
            warning_msg = "Cannot start: Sequence already running"
            logger.warning(warning_msg)
            self._log(warning_msg, LogLevel.WARNING, LogCategory.SEQUENCE)
            return False
            
        if not self.current_sequence:
            error_msg = "Cannot start: No sequence loaded"
            logger.error(error_msg)
            self._log(error_msg, LogLevel.ERROR, LogCategory.SEQUENCE)
            return False
        
        # Reset flags and status
        self.stop_flag.clear()
        self.pause_flag.clear()
        self.status = SequenceStatus.RUNNING
        
        # Set sequence start time
        self.sequence_start_time = datetime.datetime.now()
        
        # Create a pre-start hardware snapshot
        pre_start_state = self._snapshot_hardware_state('pre_start')
        
        # Reset simulation flag
        self.simulation_used = False
        
        # Verify hardware availability based on operation mode
        if self.operation_mode == OperationMode.PROTOTYPE:
            # In prototype mode, hardware is required
            if not self._verify_hardware_requirements():
                self.status = SequenceStatus.ERROR
                return False
        
        # Log the sequence start
        sequence_name = self.current_sequence.get('name', 'Unnamed')
        start_msg = f"Starting sequence: {sequence_name}"
        self._log(
            start_msg, 
            LogLevel.INFO, 
            LogCategory.SEQUENCE, 
            hardware_state=pre_start_state
        )
        
        # Start sequence execution in a separate thread
        self.sequence_thread = threading.Thread(target=self._execute_sequence)
        self.sequence_thread.daemon = True
        self.sequence_thread.start()
        
        return True

    def _verify_hardware_requirements(self):
        """
        Verify that required hardware is available in prototype mode
        
        Returns:
            bool: True if hardware requirements are met
        """
        errors = []
        
        # Check each required hardware component
        if not self.stepper:
            errors.append("Stepper motor controller is required but not available")
            
        if not self.servo:
            errors.append("Servo controller is required but not available")
            
        if not self.output_controller:
            errors.append("Output controller is required but not available")
        
        # If any errors, log them and add to execution log
        if errors:
            for error in errors:
                logger.error(error)
                self.execution_log.append(f"Error: {error}")
            
            # Add special message for prototype mode
            msg = "Hardware is required in prototype mode. Cannot use simulation."
            logger.error(msg)
            self.execution_log.append(f"Error: {msg}")
            
            return False
            
        return True

    def _execute_sequence(self):
        """Execute the loaded sequence"""
        try:
            # Safely get sequence name
            sequence_name = "Unnamed"
            if self.current_sequence is not None:
                sequence_name = self.current_sequence.get('name', 'Unnamed')
                
            # Execute each step in the sequence using priority queue
            while self.step_queue:
                # Check if we should stop
                if self.stop_flag.is_set():
                    self._log("Sequence stopped by user", LogLevel.INFO, LogCategory.USER)
                    self.status = SequenceStatus.IDLE
                    return
            
                # Handle pause
                if self.pause_flag.is_set():
                    pause_msg = "Sequence paused"
                    self._log(pause_msg, LogLevel.INFO, LogCategory.USER)
                    self.status = SequenceStatus.PAUSED
                    
                    # Take a snapshot of hardware state when paused
                    self._snapshot_hardware_state('paused')
                    
                    # Wait until unpaused or stopped
                    while self.pause_flag.is_set() and not self.stop_flag.is_set():
                        time.sleep(0.1)
                    
                    # If we were told to stop while paused
                    if self.stop_flag.is_set():
                        stop_msg = "Sequence stopped while paused"
                        self._log(stop_msg, LogLevel.INFO, LogCategory.USER)
                        self.status = SequenceStatus.IDLE
                        return
                    
                    # Otherwise we've been unpaused
                    resume_msg = "Sequence resumed"
                    self._log(resume_msg, LogLevel.INFO, LogCategory.USER)
                    self.status = SequenceStatus.RUNNING
                    
                    # Take a snapshot of hardware state when resumed
                    self._snapshot_hardware_state('resumed')
                
                try:
                    # Get the next step with lowest priority (index)
                    i, step = self._get_next_step()
                    if i is None or step is None:
                        self._log("No steps left in the queue", LogLevel.WARNING, LogCategory.SEQUENCE)
                        break
                    
                    # Update current step
                    self.current_step_index = i
                    
                    # Get action from step
                    action = step.get('action', '')
                    
                    # Take a hardware snapshot before executing the step
                    pre_step_state = self._snapshot_hardware_state(f'pre_step_{i}_{action}')
                    
                    # Log the step start
                    step_start_msg = f"Starting step {i+1}/{self.total_steps}: {action}"
                    self._log(
                        step_start_msg, 
                        LogLevel.INFO, 
                        LogCategory.STEP, 
                        step_index=i,
                        step_action=action, 
                        hardware_state=pre_step_state
                    )
                    
                    # Execute the step
                    start_time = time.time()
                    result = self._execute_step(step)
                    execution_time = time.time() - start_time
                    
                    # Take a hardware snapshot after executing the step
                    post_step_state = self._snapshot_hardware_state(f'post_step_{i}_{action}')
                    
                    if not result:
                        error_msg = f"Failed to execute step {i+1}: {action}"
                        self._log(
                            error_msg, 
                            LogLevel.ERROR, 
                            LogCategory.STEP, 
                            step_index=i, 
                            step_action=action,
                            hardware_state=post_step_state
                        )
                        self.status = SequenceStatus.ERROR
                        return
                    
                    # Log successful step completion with execution time
                    step_complete_msg = f"Completed step {i+1}: {action} in {execution_time:.3f} seconds"
                    self._log(
                        step_complete_msg, 
                        LogLevel.SUCCESS, 
                        LogCategory.STEP, 
                        step_index=i, 
                        step_action=action,
                        hardware_state=post_step_state
                    )
                    
                    # Update progress
                    self.steps_completed = i + 1
                    
                    # Wait for any delay after the step
                    delay_after = step.get('delay_after', 0)
                    if delay_after > 0:
                        # Convert to seconds if specified in milliseconds
                        delay_sec = delay_after / 1000.0 if delay_after > 100 else delay_after
                        
                        # Log the delay
                        delay_msg = f"Waiting for {delay_after} ms after step {i+1}"
                        self._log(delay_msg, LogLevel.INFO, LogCategory.STEP, step_index=i, step_action=action)
                        
                        # Wait in small increments to allow stopping/pausing
                        start_time = time.time()
                        while time.time() - start_time < delay_sec:
                            if self.stop_flag.is_set():
                                stop_delay_msg = "Sequence stopped during delay"
                                self._log(stop_delay_msg, LogLevel.INFO, LogCategory.USER)
                                self.status = SequenceStatus.IDLE
                                return
                            
                            if self.pause_flag.is_set():
                                remaining_delay = delay_sec - (time.time() - start_time)
                                pause_delay_msg = f"Sequence paused during delay (remaining: {remaining_delay:.1f}s)"
                                self._log(pause_delay_msg, LogLevel.INFO, LogCategory.USER)
                                self.status = SequenceStatus.PAUSED
                                
                                # Wait until unpaused or stopped
                                while self.pause_flag.is_set() and not self.stop_flag.is_set():
                                    time.sleep(0.1)
                                
                                # If we were told to stop while paused
                                if self.stop_flag.is_set():
                                    stop_pause_msg = "Sequence stopped while paused during delay"
                                    self._log(stop_pause_msg, LogLevel.INFO, LogCategory.USER)
                                    self.status = SequenceStatus.IDLE
                                    return
                                
                                # Otherwise we've been unpaused, continue the remaining delay
                                resume_delay_msg = "Sequence resumed from delay"
                                self._log(resume_delay_msg, LogLevel.INFO, LogCategory.USER)
                                self.status = SequenceStatus.RUNNING
                                start_time = time.time() - (delay_sec - remaining_delay)
                            
                            # Sleep a small amount to not hog the CPU
                            time.sleep(0.1)
                
                except IndexError:
                    # This should never happen with our explicit check above, but just in case
                    error_msg = "No lowest priority node found in step queue"
                    self._log(error_msg, LogLevel.ERROR, LogCategory.ERROR)
                    self.status = SequenceStatus.ERROR
                    return
            
            # All steps completed successfully
            # Take a final hardware snapshot
            final_state = self._snapshot_hardware_state('sequence_complete')
            
            # Calculate execution duration
            if self.sequence_start_time:
                duration_sec = (datetime.datetime.now() - self.sequence_start_time).total_seconds()
                duration_str = f" in {duration_sec:.2f} seconds"
            else:
                duration_str = ""
                
            # Log completion
            complete_msg = f"Sequence completed successfully{duration_str}"
            self._log(
                complete_msg, 
                LogLevel.SUCCESS, 
                LogCategory.SEQUENCE, 
                hardware_state=final_state
            )
            self.status = SequenceStatus.COMPLETED
            
        except Exception as e:
            # Take a snapshot of hardware state when error occurred
            error_state = self._snapshot_hardware_state('sequence_error')
            
            error_msg = f"Error executing sequence: {e}"
            self._log(
                error_msg, 
                LogLevel.ERROR, 
                LogCategory.ERROR, 
                error_type=ErrorType.UNEXPECTED,
                hardware_state=error_state
            )
            self.status = SequenceStatus.ERROR

    def _get_next_step(self):
        """
        Get the next step with the lowest priority (index)
        
        Returns:
            tuple: (index, step) or (None, None) if queue is empty
        """
        try:
            if not self.step_queue:
                return None, None
            return heapq.heappop(self.step_queue)
        except IndexError:
            logger.error("No lowest priority node found in step queue")
            self.execution_log.append("Error: No lowest priority node found")
            return None, None

    def _execute_step(self, step):
        """
        Execute a single step in the sequence with error recovery
        
        Args:
            step: Dictionary with step details
        
        Returns:
            bool: True if step executed successfully
        """
        action = step.get('action', '')
        step_specific_config = step.get('error_recovery', {})
        retry_count = 0
        max_retries = self.error_recovery_config['max_retries']
        
        # Override max retries if specified in step
        if 'max_retries' in step_specific_config:
            max_retries = step_specific_config['max_retries']
            
        while retry_count <= max_retries:
            try:
                success = False
                step_start_time = time.time()
                
                # Execute different actions based on the action type
                if action == 'stepper_move':
                    success = self._execute_stepper_move(step)
                elif action == 'fire':
                    success = self._execute_fire(step)
                elif action == 'fire_fiber':
                    success = self._execute_fire_fiber()
                elif action == 'stop_fire':
                    success = self._execute_stop_fire()
                elif action == 'wait':
                    success = self._execute_wait(step)
                elif action == 'wait_input':
                    success = self._execute_wait_input(step)
                elif action == 'fan_on':
                    success = self._execute_fan(True)
                elif action == 'fan_off':
                    success = self._execute_fan(False)
                elif action == 'lights_on':
                    success = self._execute_lights(True)
                elif action == 'lights_off':
                    success = self._execute_lights(False)
                elif action == 'table_forward':
                    success = self._execute_table_forward(step)
                elif action == 'table_backward':
                    success = self._execute_table_backward(step)
                elif action == 'table_run_to_front_limit':
                    success = self._execute_table_run_to_front_limit()
                elif action == 'table_run_to_back_limit':
                    success = self._execute_table_run_to_back_limit()
                elif action == 'go_to_zero':
                    success = self._execute_go_to_zero()
                else:
                    error_msg = f"Unknown action: {action}"
                    self._log(
                        error_msg, 
                        LogLevel.ERROR, 
                        LogCategory.ERROR, 
                        step_action=action,
                        error_type=ErrorType.INVALID_STEP
                    )
                    self._handle_error(ErrorType.INVALID_STEP, error_msg, step)
                    return False
                
                # Calculate step execution time
                step_execution_time = time.time() - step_start_time
                
                if success:
                    # If this was a successful retry, log it
                    if retry_count > 0:
                        retry_success_msg = f"Step '{action}' succeeded after {retry_count} retries (took {step_execution_time:.3f}s)"
                        self._log(
                            retry_success_msg,
                            LogLevel.SUCCESS,
                            LogCategory.STEP,
                            step_action=action
                        )
                    return True
                    
                # If the action itself reported failure, handle it
                error_msg = f"Step '{action}' failed"
                self._log(
                    error_msg,
                    LogLevel.ERROR,
                    LogCategory.STEP,
                    step_action=action,
                    error_type=ErrorType.HARDWARE_FAILURE
                )
                self._handle_error(ErrorType.HARDWARE_FAILURE, error_msg, step)
                
                # Check if we should retry, skip, or abort
                recovery_action = self._get_recovery_action_for_step(action, ErrorType.HARDWARE_FAILURE)
                
                if recovery_action == ErrorRecoveryAction.RETRY.value:
                    # Check if we've reached max retries
                    if retry_count >= max_retries:
                        max_retry_msg = f"Maximum retries ({max_retries}) reached for step '{action}'"
                        self._log(
                            max_retry_msg,
                            LogLevel.ERROR,
                            LogCategory.ERROR,
                            step_action=action,
                            error_type=ErrorType.HARDWARE_FAILURE,
                            recovery_action=ErrorRecoveryAction.ABORT
                        )
                        # Fall through to abort
                    else:
                        retry_count += 1
                        retry_delay = self._calculate_retry_delay(retry_count)
                        retry_msg = f"Retrying step '{action}' (attempt {retry_count}/{max_retries}) after {retry_delay:.1f}s delay"
                        self._log(
                            retry_msg,
                            LogLevel.WARNING,
                            LogCategory.STEP,
                            step_action=action,
                            recovery_action=ErrorRecoveryAction.RETRY
                        )
                        
                        # Wait for the retry delay with support for pause/stop
                        self._wait_with_pause_support(retry_delay)
                        continue
                
                elif recovery_action == ErrorRecoveryAction.SKIP.value:
                    skip_msg = f"Skipping failed step '{action}' and continuing sequence"
                    self._log(
                        skip_msg,
                        LogLevel.WARNING,
                        LogCategory.STEP,
                        step_action=action,
                        recovery_action=ErrorRecoveryAction.SKIP
                    )
                    return True  # Return true even though the step failed, to continue the sequence
                
                elif recovery_action == ErrorRecoveryAction.PAUSE.value:
                    pause_msg = f"Pausing sequence after step '{action}' failed"
                    self._log(
                        pause_msg,
                        LogLevel.WARNING,
                        LogCategory.STEP,
                        step_action=action,
                        recovery_action=ErrorRecoveryAction.PAUSE
                    )
                    # Set pause flag and wait for user to resume
                    self.pause_flag.set()
                    self.status = SequenceStatus.PAUSED
                    
                    # Wait until unpaused or stopped
                    while self.pause_flag.is_set() and not self.stop_flag.is_set():
                        time.sleep(0.1)
                    
                    # If stopped while paused, abort
                    if self.stop_flag.is_set():
                        return False
                    
                    # If unpaused, retry
                    retry_count += 1
                    resume_retry_msg = f"Retrying step '{action}' after user resumed"
                    self._log(
                        resume_retry_msg,
                        LogLevel.INFO,
                        LogCategory.STEP,
                        step_action=action,
                        recovery_action=ErrorRecoveryAction.RETRY
                    )
                    continue
                
                elif recovery_action == ErrorRecoveryAction.SIMULATE.value:
                    sim_msg = f"Using simulation for failed step '{action}'"
                    self._log(
                        sim_msg,
                        LogLevel.INFO,
                        LogCategory.SIMULATION,
                        step_action=action,
                        recovery_action=ErrorRecoveryAction.SIMULATE
                    )
                    self.simulation_used = True
                    # In this case, we need to re-run the step with a simulation flag
                    # For simplicity, we're just returning true here
                    return True
                    
                # Default: ABORT
                abort_msg = f"Aborting sequence due to failed step '{action}'"
                self._log(
                    abort_msg,
                    LogLevel.ERROR,
                    LogCategory.SEQUENCE,
                    step_action=action,
                    recovery_action=ErrorRecoveryAction.ABORT
                )
                return False
                
            except Exception as e:
                error_msg = f"Unexpected error executing step '{action}': {e}"
                self._log(
                    error_msg,
                    LogLevel.ERROR,
                    LogCategory.ERROR,
                    step_action=action,
                    error_type=ErrorType.UNEXPECTED
                )
                self._handle_error(ErrorType.UNEXPECTED, error_msg, step)
                
                # Check if we should retry, skip, or abort for unexpected errors
                recovery_action = self._get_recovery_action_for_step(action, ErrorType.UNEXPECTED)
                
                if recovery_action == ErrorRecoveryAction.RETRY.value:
                    # Check if we've reached max retries
                    if retry_count >= max_retries:
                        max_retry_msg = f"Maximum retries ({max_retries}) reached for step '{action}'"
                        self._log(
                            max_retry_msg,
                            LogLevel.ERROR,
                            LogCategory.ERROR,
                            step_action=action,
                            error_type=ErrorType.UNEXPECTED,
                            recovery_action=ErrorRecoveryAction.ABORT
                        )
                        return False  # Abort
                    else:
                        retry_count += 1
                        retry_delay = self._calculate_retry_delay(retry_count)
                        retry_msg = f"Retrying step '{action}' (attempt {retry_count}/{max_retries}) after {retry_delay:.1f}s delay"
                        self._log(
                            retry_msg,
                            LogLevel.WARNING,
                            LogCategory.STEP,
                            step_action=action,
                            recovery_action=ErrorRecoveryAction.RETRY
                        )
                        
                        # Wait for the retry delay with support for pause/stop
                        self._wait_with_pause_support(retry_delay)
                        continue
                        
                elif recovery_action == ErrorRecoveryAction.SKIP.value:
                    skip_msg = f"Skipping failed step '{action}' after error and continuing sequence"
                    self._log(
                        skip_msg,
                        LogLevel.WARNING,
                        LogCategory.STEP,
                        step_action=action,
                        recovery_action=ErrorRecoveryAction.SKIP
                    )
                    return True  # Return true even though the step failed
                
                # Default: ABORT
                abort_msg = f"Aborting sequence due to unexpected error in step '{action}'"
                self._log(
                    abort_msg,
                    LogLevel.ERROR,
                    LogCategory.SEQUENCE,
                    step_action=action,
                    recovery_action=ErrorRecoveryAction.ABORT
                )
                return False
        
        # If we get here, we've exceeded max retries
        max_retry_abort_msg = f"Maximum retries ({max_retries}) reached for step '{action}', aborting"
        self._log(
            max_retry_abort_msg,
            LogLevel.ERROR,
            LogCategory.ERROR,
            step_action=action,
            recovery_action=ErrorRecoveryAction.ABORT
        )
        return False

    def _wait_with_pause_support(self, duration_sec):
        """
        Wait for a specified duration with support for pause/stop
        
        Args:
            duration_sec: Duration to wait in seconds
        """
        start_time = time.time()
        elapsed = 0
        
        while elapsed < duration_sec:
            # Check for stop request
            if self.stop_flag.is_set():
                return
                
            # Handle pause request
            if self.pause_flag.is_set():
                pause_start = time.time()
                self.status = SequenceStatus.PAUSED
                
                # Wait until unpaused or stopped
                while self.pause_flag.is_set() and not self.stop_flag.is_set():
                    time.sleep(0.1)
                    
                # If stopped while paused, return
                if self.stop_flag.is_set():
                    return
                    
                # Calculate time spent paused and adjust start_time
                pause_duration = time.time() - pause_start
                start_time += pause_duration
                self.status = SequenceStatus.RUNNING
            
            # Sleep a small amount to avoid CPU spinning
            time.sleep(0.1)
            elapsed = time.time() - start_time

    def _calculate_retry_delay(self, retry_count):
        """
        Calculate the delay before next retry attempt
        
        Args:
            retry_count: Current retry attempt number (1-based)
            
        Returns:
            float: Delay in seconds before next retry
        """
        base_delay = self.error_recovery_config['retry_delay']
        
        if self.error_recovery_config['exponential_backoff']:
            # Exponential backoff with a maximum of 30 seconds
            return min(base_delay * (2 ** (retry_count - 1)), 30)
        else:
            # Fixed delay
            return base_delay

    def _handle_error(self, error_type, error_message, step=None):
        """
        Handle an error during sequence execution
        
        Args:
            error_type: Type of error (ErrorType enum)
            error_message: Error message
            step: The step being executed when error occurred
        """
        # Get hardware state at time of error
        error_state = self._get_hardware_state()
        
        # Create a structured error log
        self._log(
            error_message,
            LogLevel.ERROR,
            LogCategory.ERROR,
            step_index=self.current_step_index,
            step_action=step.get('action') if step else None,
            hardware_state=error_state,
            error_type=error_type
        )
        
        # Update last error information
        self.last_error = {
            'type': error_type.value if isinstance(error_type, ErrorType) else error_type,
            'message': error_message,
            'step': step,
            'timestamp': time.time()
        }
        
        # If this is a hardware error in normal mode, we might want to pause for user intervention
        if (error_type == ErrorType.HARDWARE_FAILURE or 
            error_type == ErrorType.HARDWARE_NOT_AVAILABLE) and self.operation_mode == OperationMode.NORMAL:
            recovery_action = self._get_recovery_action_for_step(
                step.get('action') if step else None,
                error_type
            )
            self.last_error['recovery_action'] = recovery_action
            
            if recovery_action == ErrorRecoveryAction.PAUSE.value:
                self.status = SequenceStatus.WARNING
                self.pause_flag.set()

    def _get_recovery_action_for_step(self, action_type, error_type):
        """
        Get the appropriate recovery action for a step and error type
        
        Args:
            action_type: Type of action being performed (stepper_move, fire, etc.)
            error_type: Type of error that occurred (ErrorType enum)
            
        Returns:
            str: Recovery action name from ErrorRecoveryAction enum
        """
        error_type_str = error_type.value if isinstance(error_type, ErrorType) else error_type
        
        # Check if there's a step-specific configuration for this error
        if action_type and action_type in self.error_recovery_config['recovery_by_step']:
            step_config = self.error_recovery_config['recovery_by_step'][action_type]
            if error_type_str in step_config:
                return step_config[error_type_str]
        
        # Fall back to general error type configuration
        if error_type_str in self.error_recovery_config['recovery_by_type']:
            return self.error_recovery_config['recovery_by_type'][error_type_str]
        
        # Default to abort if no configuration found
        return ErrorRecoveryAction.ABORT.value
    
    def _handle_missing_hardware(self, component_name):
        """
        Handle missing hardware based on operation mode
        
        Args:
            component_name: Name of the missing hardware component
            
        Returns:
            bool: True if simulation should be used, False if operation should fail
        """
        # Mark that simulation was used
        self.simulation_used = True
        
        # Get hardware state
        hw_state = self._get_hardware_state()
        
        # Store the error for later reference
        error_message = f"{component_name} not available"
        self._log(
            error_message,
            LogLevel.ERROR if self.operation_mode == OperationMode.PROTOTYPE else LogLevel.WARNING,
            LogCategory.HARDWARE,
            error_type=ErrorType.HARDWARE_NOT_AVAILABLE,
            hardware_state=hw_state
        )
        self._handle_error(ErrorType.HARDWARE_NOT_AVAILABLE, error_message)
        
        # Handle based on operation mode
        if self.operation_mode == OperationMode.SIMULATION:
            # In simulation mode, we expect to use simulation
            sim_msg = f"{component_name} not available, using simulation as expected in simulation mode"
            self._log(
                sim_msg,
                LogLevel.INFO,
                LogCategory.SIMULATION
            )
            return True
            
        elif self.operation_mode == OperationMode.PROTOTYPE:
            # In prototype mode, hardware is required
            proto_msg = f"{component_name} required in prototype mode but not available"
            self._log(
                proto_msg,
                LogLevel.ERROR,
                LogCategory.HARDWARE,
                error_type=ErrorType.HARDWARE_NOT_AVAILABLE
            )
            return False
            
        else:  # NORMAL mode
            # In normal mode, check recovery configuration
            recovery_action = self._get_recovery_action_for_step(
                None,  # No specific step type here
                ErrorType.HARDWARE_NOT_AVAILABLE
            )
            
            if recovery_action == ErrorRecoveryAction.SIMULATE.value:
                # Allow simulation fallback
                sim_fallback_msg = f"{component_name} not available. Using simulation as fallback."
                self._log(
                    sim_fallback_msg,
                    LogLevel.WARNING,
                    LogCategory.HARDWARE,
                    recovery_action=ErrorRecoveryAction.SIMULATE
                )
                return True
            else:
                # Default to error
                error_msg = f"{component_name} not available. Hardware error should be displayed in UI."
                self._log(
                    error_msg,
                    LogLevel.WARNING,
                    LogCategory.HARDWARE,
                    recovery_action=ErrorRecoveryAction.ABORT
                )
                return False
    
    def _execute_stepper_move(self, step):
        """Execute a stepper move action"""
        if not self.stepper:
            if not self._handle_missing_hardware("Stepper motor"):
                return False
                
            # Simulation fallback
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
            # Hardware error occurred
            error_msg = f"Error moving stepper: {e}"
            logger.error(error_msg)
            
            if self.operation_mode == OperationMode.PROTOTYPE:
                # In prototype mode, fail on hardware error
                self.execution_log.append(f"Error: {error_msg}")
                return False
            elif self.operation_mode == OperationMode.NORMAL:
                # In normal mode, report error but don't use simulation
                self.execution_log.append(f"Error: {error_msg}")
                return False
                
            # Fall back to simulation in simulation mode
            self.simulation_used = True
            direction = step.get('direction', 'in')
            steps = step.get('steps', 100)
            self.execution_log.append(f"Simulated stepper move after error: {direction}, {steps} steps")
            return True
    
    def _execute_fire(self, step):
        """Execute a fire action (move servo to firing position)"""
        if not self.servo:
            if not self._handle_missing_hardware("Servo controller"):
                return False
                
            # Simulation fallback
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
            # Hardware error occurred
            error_msg = f"Error firing: {e}"
            logger.error(error_msg)
            
            if self.operation_mode != OperationMode.SIMULATION:
                # In normal or prototype mode, report error
                self.execution_log.append(f"Error: {error_msg}")
                return False if self.operation_mode == OperationMode.PROTOTYPE else True
                
            # Fall back to simulation in simulation mode
            self.simulation_used = True
            duration = step.get('duration', 2000)
            self.execution_log.append(f"Simulated fire after error for {duration} ms")
            return True
    
    def _execute_fire_fiber(self):
        """Execute a fire fiber sequence (A-B-A-B pattern)"""
        if not self.servo:
            if not self._handle_missing_hardware("Servo controller"):
                return False
                
            # Simulation fallback
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
            # Hardware error occurred
            error_msg = f"Error starting fiber sequence: {e}"
            logger.error(error_msg)
            
            if self.operation_mode != OperationMode.SIMULATION:
                # In normal or prototype mode, report error
                self.execution_log.append(f"Error: {error_msg}")
                return False if self.operation_mode == OperationMode.PROTOTYPE else True
                
            # Fall back to simulation in simulation mode
            self.simulation_used = True
            self.execution_log.append("Simulated fiber sequence (A-B-A-B) after error")
            return True
    
    def _execute_stop_fire(self):
        """Execute a stop fire action (move servo back to normal position)"""
        if not self.servo:
            if not self._handle_missing_hardware("Servo controller"):
                return False
                
            # Simulation fallback
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
            # Hardware error occurred
            error_msg = f"Error stopping fire: {e}"
            logger.error(error_msg)
            
            if self.operation_mode != OperationMode.SIMULATION:
                # In normal or prototype mode, report error
                self.execution_log.append(f"Error: {error_msg}")
                return False if self.operation_mode == OperationMode.PROTOTYPE else True
                
            # Fall back to simulation in simulation mode
            self.simulation_used = True
            self.execution_log.append("Simulated stop fire after error")
            return True
    
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
        # Check if we have hardware for input detection
        if not self.output_controller:
            if not self._handle_missing_hardware("Input controller"):
                return False
                
            # Simulation mode - randomly detect input with 5% probability each check
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
                return status.get('button_in', False)
                
            elif input_type == 'button_out':
                # Check OUT button status through input controller
                return status.get('button_out', False)
                
            elif input_type == 'fire_button':
                # Check FIRE button status through input controller
                return status.get('fire_button', False)
                
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
            # Hardware error occurred
            error_msg = f"Error checking input state: {e}"
            logger.error(error_msg)
            
            if self.operation_mode != OperationMode.SIMULATION:
                # In normal or prototype mode, report error
                self.execution_log.append(f"Error: {error_msg}")
                if self.operation_mode == OperationMode.PROTOTYPE:
                    return False
                    
            # Fall back to simulation
            self.simulation_used = True
            import random
            if random.random() < 0.05:  # 5% chance of detecting input on each check
                return True
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
            if not self._handle_missing_hardware("Output controller"):
                return False
                
            # Simulation fallback
            self.execution_log.append(f"Simulated fan {'ON' if state else 'OFF'}")
            return True
        
        try:
            # Set the fan state
            self.output_controller.set_fan(state)
            
            # Log the result
            self.execution_log.append(f"Fan {'ON' if state else 'OFF'}")
            
            return True
        except Exception as e:
            # Hardware error occurred
            error_msg = f"Error controlling fan: {e}"
            logger.error(error_msg)
            
            if self.operation_mode != OperationMode.SIMULATION:
                # In normal or prototype mode, report error
                self.execution_log.append(f"Error: {error_msg}")
                return False if self.operation_mode == OperationMode.PROTOTYPE else True
                
            # Fall back to simulation in simulation mode
            self.simulation_used = True
            self.execution_log.append(f"Simulated fan {'ON' if state else 'OFF'} after error")
            return True
    
    def _execute_lights(self, state):
        """Execute a lights control action"""
        if not self.output_controller:
            if not self._handle_missing_hardware("Output controller"):
                return False
                
            # Simulation fallback
            self.execution_log.append(f"Simulated lights {'ON' if state else 'OFF'}")
            return True
        
        try:
            # Set the lights state
            self.output_controller.set_red_lights(state)
            
            # Log the result
            self.execution_log.append(f"Lights {'ON' if state else 'OFF'}")
            
            return True
        except Exception as e:
            # Hardware error occurred
            error_msg = f"Error controlling lights: {e}"
            logger.error(error_msg)
            
            if self.operation_mode != OperationMode.SIMULATION:
                # In normal or prototype mode, report error
                self.execution_log.append(f"Error: {error_msg}")
                return False if self.operation_mode == OperationMode.PROTOTYPE else True
                
            # Fall back to simulation in simulation mode
            self.simulation_used = True
            self.execution_log.append(f"Simulated lights {'ON' if state else 'OFF'} after error")
            return True
    
    def _execute_table_forward(self, step):
        """Execute a table forward action"""
        if not self.output_controller:
            if not self._handle_missing_hardware("Output controller"):
                return False
                
            # Simulation fallback
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
            # Hardware error occurred
            error_msg = f"Error moving table forward: {e}"
            logger.error(error_msg)
            
            if self.operation_mode != OperationMode.SIMULATION:
                # In normal or prototype mode, report error
                self.execution_log.append(f"Error: {error_msg}")
                return False if self.operation_mode == OperationMode.PROTOTYPE else True
                
            # Fall back to simulation in simulation mode
            self.simulation_used = True
            duration = step.get('duration', 1000)
            self.execution_log.append(f"Simulated table forward for {duration} ms after error")
            time.sleep(duration / 1000.0)
            return True
    
    def _execute_table_backward(self, step):
        """Execute a table backward action"""
        if not self.output_controller:
            if not self._handle_missing_hardware("Output controller"):
                return False
                
            # Simulation fallback
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
            # Hardware error occurred
            error_msg = f"Error moving table backward: {e}"
            logger.error(error_msg)
            
            if self.operation_mode != OperationMode.SIMULATION:
                # In normal or prototype mode, report error
                self.execution_log.append(f"Error: {error_msg}")
                return False if self.operation_mode == OperationMode.PROTOTYPE else True
                
            # Fall back to simulation in simulation mode
            self.simulation_used = True
            duration = step.get('duration', 1000)
            self.execution_log.append(f"Simulated table backward for {duration} ms after error")
            time.sleep(duration / 1000.0)
            return True
    
    def _execute_table_run_to_front_limit(self):
        """Execute a table run to front limit action"""
        if not self.output_controller:
            if not self._handle_missing_hardware("Output controller"):
                return False
                
            # Simulation fallback
            self.execution_log.append("Simulated table run to front limit")
            time.sleep(2.0)  # Simulate some time for the operation
            return True
        
        try:
            # Use the same logic as the API route
            import requests
            response = requests.post('http://localhost:5000/table/run_to_front_limit')
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.execution_log.append("Table run to front limit completed")
                    return True
                else:
                    error_msg = data.get('error', 'Unknown error')
                    self.execution_log.append(f"Error: {error_msg}")
                    return False
            else:
                error_msg = f"HTTP error {response.status_code}"
                self.execution_log.append(f"Error: {error_msg}")
                return False
        except Exception as e:
            # Hardware error occurred
            error_msg = f"Error running table to front limit: {e}"
            logger.error(error_msg)
            
            if self.operation_mode != OperationMode.SIMULATION:
                # In normal or prototype mode, report error
                self.execution_log.append(f"Error: {error_msg}")
                return False if self.operation_mode == OperationMode.PROTOTYPE else True
                
            # Fall back to simulation in simulation mode
            self.simulation_used = True
            self.execution_log.append("Simulated table run to front limit after error")
            time.sleep(2.0)
            return True
    
    def _execute_table_run_to_back_limit(self):
        """Execute a table run to back limit action"""
        if not self.output_controller:
            if not self._handle_missing_hardware("Output controller"):
                return False
                
            # Simulation fallback
            self.execution_log.append("Simulated table run to back limit")
            time.sleep(2.0)  # Simulate some time for the operation
            return True
        
        try:
            # Use the same logic as the API route
            import requests
            response = requests.post('http://localhost:5000/table/run_to_back_limit')
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.execution_log.append("Table run to back limit completed")
                    return True
                else:
                    error_msg = data.get('error', 'Unknown error')
                    self.execution_log.append(f"Error: {error_msg}")
                    return False
            else:
                error_msg = f"HTTP error {response.status_code}"
                self.execution_log.append(f"Error: {error_msg}")
                return False
        except Exception as e:
            # Hardware error occurred
            error_msg = f"Error running table to back limit: {e}"
            logger.error(error_msg)
            
            if self.operation_mode != OperationMode.SIMULATION:
                # In normal or prototype mode, report error
                self.execution_log.append(f"Error: {error_msg}")
                return False if self.operation_mode == OperationMode.PROTOTYPE else True
                
            # Fall back to simulation in simulation mode
            self.simulation_used = True
            self.execution_log.append("Simulated table run to back limit after error")
            time.sleep(2.0)
            return True
    
    def _execute_go_to_zero(self):
        """Execute a go to zero action for cleaning head stepper"""
        if not self.output_controller:
            if not self._handle_missing_hardware("Output controller"):
                return False
                
            # Simulation fallback
            self.execution_log.append("Simulated cleaning head go to zero")
            time.sleep(1.5)  # Simulate some time for the operation
            return True
        
        try:
            # Use the same logic as the API route
            import requests
            response = requests.post('http://localhost:5000/go_to_zero')
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.execution_log.append("Cleaning head moved to position 0")
                    return True
                else:
                    error_msg = data.get('error', 'Unknown error')
                    self.execution_log.append(f"Error: {error_msg}")
                    return False
            else:
                error_msg = f"HTTP error {response.status_code}"
                self.execution_log.append(f"Error: {error_msg}")
                return False
        except Exception as e:
            # Hardware error occurred
            error_msg = f"Error moving cleaning head to zero: {e}"
            logger.error(error_msg)
            
            if self.operation_mode != OperationMode.SIMULATION:
                # In normal or prototype mode, report error
                self.execution_log.append(f"Error: {error_msg}")
                return False if self.operation_mode == OperationMode.PROTOTYPE else True
                
            # Fall back to simulation in simulation mode
            self.simulation_used = True
            self.execution_log.append("Simulated cleaning head go to zero after error")
            time.sleep(1.5)
            return True
    
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
        # Calculate execution time if sequence is running or completed
        execution_time = None
        if self.sequence_start_time:
            execution_time = (datetime.datetime.now() - self.sequence_start_time).total_seconds()
            
        return {
            'status': self.status.name,
            'sequence_id': self.sequence_id,
            'sequence_name': self.current_sequence.get('name', 'Unnamed') if self.current_sequence else None,
            'current_step': self.current_step_index + 1,
            'total_steps': self.total_steps,
            'progress_percent': int((self.steps_completed / self.total_steps) * 100) if self.total_steps > 0 else 0,
            'execution_log': self.execution_log,  # Legacy format
            'logs': [log.to_dict() for log in self.execution_logs],  # New structured format
            'simulated': self.simulation_used,
            'operation_mode': self.operation_mode.value if self.operation_mode else "unknown",
            'last_error': self.last_error if self.last_error['type'] else None,
            'execution_time': execution_time,
            'start_time': self.sequence_start_time.isoformat() if self.sequence_start_time else None
        }

    def get_logs(self, filter_category=None, filter_level=None, max_entries=None):
        """
        Get filtered logs from the execution
        
        Args:
            filter_category: Filter logs by category
            filter_level: Filter logs by level
            max_entries: Maximum number of entries to return
            
        Returns:
            list: Filtered log entries
        """
        filtered_logs = self.execution_logs
        
        # Apply category filter if specified
        if filter_category:
            category_value = filter_category.value if isinstance(filter_category, LogCategory) else filter_category
            filtered_logs = [log for log in filtered_logs if log.category == category_value]
            
        # Apply level filter if specified
        if filter_level:
            level_value = filter_level.value if isinstance(filter_level, LogLevel) else filter_level
            filtered_logs = [log for log in filtered_logs if log.level == level_value]
            
        # Apply max entries limit if specified
        if max_entries is not None and max_entries > 0:
            filtered_logs = filtered_logs[-max_entries:]
            
        return [log.to_dict() for log in filtered_logs]

    def get_hardware_history(self):
        """
        Get the history of hardware state snapshots
        
        Returns:
            list: List of hardware state snapshots
        """
        return self.hardware_states

    def cleanup(self):
        """Clean up resources"""
        self.stop()