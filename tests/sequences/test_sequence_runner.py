#!/usr/bin/env python
"""
Sequence Runner Tests

This module tests the sequence runner functionality using mock hardware components.
"""
import unittest
import time
import logging
import json
import sys
from pathlib import Path

from tests.test_base import BaseTestCase
from tests.hardware.mock_hardware import MockHardwareController, MockHardwareException
from tests.test_config import SAMPLE_SEQUENCES

# Import the actual sequence runner
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from sequence_runner import (
    SequenceRunner,
    ErrorType,
    ErrorRecoveryAction
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_sequence_runner')

class MockSequenceRunner(SequenceRunner):
    """
    Mock implementation of SequenceRunner for testing
    
    This class overrides hardware interactions to use our mock hardware controller
    """
    
    def __init__(self, sequence_data, mock_controller):
        """Initialize with mock hardware controller"""
        super().__init__(sequence_data)
        self.mock_controller = mock_controller
        self.hardware_status = {}
        
    def _initialize_hardware(self):
        """Override to use mock hardware instead of real hardware"""
        # Mock hardware initialization
        self.hardware_ready = True
        return True
        
    def _get_hardware_state(self):
        """Override to get state from mock hardware controller"""
        return self.mock_controller.get_state()
        
    def _execute_step_action(self, step):
        """Override to execute step using mock hardware"""
        action_type = step.get('action', '')
        
        if action_type == 'stepper_move':
            direction = step.get('direction', 'forward')
            steps = step.get('steps', 100)
            stepper = self.mock_controller.get_stepper('test_stepper')
            
            if stepper is None:
                self._handle_error(step, ErrorType.HARDWARE_NOT_AVAILABLE, "Stepper motor not available")
                return False
                
            try:
                result = stepper.move(steps, direction)
                if not result['success']:
                    self._handle_error(step, ErrorType.HARDWARE_FAILURE, result.get('error', 'Unknown error'))
                    return False
                    
                return True
            except MockHardwareException as e:
                self._handle_error(step, ErrorType.HARDWARE_FAILURE, str(e))
                return False
                
        elif action_type == 'fire':
            duration = step.get('duration', 0.5)
            laser = self.mock_controller.get_laser('test_laser')
            
            if laser is None:
                self._handle_error(step, ErrorType.HARDWARE_NOT_AVAILABLE, "Laser not available")
                return False
                
            try:
                result = laser.fire(duration)
                if not result['success']:
                    self._handle_error(step, ErrorType.HARDWARE_FAILURE, result.get('error', 'Unknown error'))
                    return False
                    
                # For testing, we'll wait for the laser to finish firing
                time.sleep(duration)
                return True
            except MockHardwareException as e:
                self._handle_error(step, ErrorType.HARDWARE_FAILURE, str(e))
                return False
                
        elif action_type == 'delay':
            seconds = step.get('seconds', 1.0)
            time.sleep(seconds)
            return True
            
        elif action_type == 'servo_move':
            angle = step.get('angle', 90)
            servo = self.mock_controller.get_servo('test_servo')
            
            if servo is None:
                self._handle_error(step, ErrorType.HARDWARE_NOT_AVAILABLE, "Servo not available")
                return False
                
            try:
                result = servo.move_to(angle)
                if not result['success']:
                    self._handle_error(step, ErrorType.HARDWARE_FAILURE, result.get('error', 'Unknown error'))
                    return False
                    
                return True
            except MockHardwareException as e:
                self._handle_error(step, ErrorType.HARDWARE_FAILURE, str(e))
                return False
                
        else:
            # Unknown action type
            self._handle_error(step, ErrorType.INVALID_STEP, f"Unknown action type: {action_type}")
            return False
            
    def _update_status_display(self):
        """Override to avoid UI updates during tests"""
        pass
        
    def _check_emergency_stop(self):
        """Override to check mock emergency stop"""
        # Get emergency stop state from mock
        gpio = self.mock_controller.get_gpio('emergency_stop')
        if gpio and gpio.get_state():
            return True  # Emergency stop is active
        return False

class SequenceRunnerTest(BaseTestCase):
    """Test case for sequence runner"""
    
    def setUp(self):
        """Set up test fixtures before each test"""
        super().setUp()
        self.controller = MockHardwareController()
        
        # Initialize test hardware
        self.stepper = self.controller.add_stepper('test_stepper')
        self.servo = self.controller.add_servo('test_servo')
        self.laser = self.controller.add_laser('test_laser')
        self.emergency_stop = self.controller.add_gpio('emergency_stop', 12, False)
        
        # Create sample sequence data
        self.basic_sequence = self.create_test_sequence('basic_sequence')
        self.complex_sequence = self.create_test_sequence('complex_sequence')
        
    def tearDown(self):
        """Clean up after each test"""
        self.controller.reset_all()
        super().tearDown()
        
    def test_basic_sequence_execution(self):
        """Test execution of a basic sequence"""
        runner = MockSequenceRunner(self.basic_sequence, self.controller)
        
        # Start sequence
        self.assertTrue(runner.start())
        
        # Wait for sequence to complete (or timeout after 5 seconds)
        start_time = time.time()
        while runner.is_running() and time.time() - start_time < 5:
            time.sleep(0.1)
            
        # Verify sequence has completed
        self.assertFalse(runner.is_running())
        self.assertEqual('COMPLETED', runner.get_status())
        
        # Check final stepper position
        self.assertEqual(0, self.stepper.get_position())
        
    def test_sequence_error_handling(self):
        """Test sequence error recovery"""
        runner = MockSequenceRunner(self.complex_sequence, self.controller)
        
        # Set failure mode for the stepper during backward movement
        # This will be the 4th step, which has custom error recovery
        def set_failure_on_backward():
            """Set failure mode during sequence execution"""
            time.sleep(2)  # Wait for sequence to reach backward step
            self.stepper.set_failure_mode("hardware_failure")
            
        import threading
        failure_thread = threading.Thread(target=set_failure_on_backward)
        failure_thread.daemon = True
        failure_thread.start()
        
        # Start sequence
        self.assertTrue(runner.start())
        
        # Wait for sequence to complete (or timeout after 10 seconds)
        start_time = time.time()
        while runner.is_running() and time.time() - start_time < 10:
            time.sleep(0.1)
            
        # Verify sequence has completed with retries
        self.assertFalse(runner.is_running())
        self.assertEqual('COMPLETED', runner.get_status())
        
        # Check retry count in execution log
        log = runner.get_execution_log()
        retry_messages = [msg for msg in log if 'Retrying' in msg]
        self.assertGreater(len(retry_messages), 0)
        
    def test_emergency_stop(self):
        """Test emergency stop during sequence execution"""
        runner = MockSequenceRunner(self.complex_sequence, self.controller)
        
        # Set emergency stop to trigger during execution
        def trigger_emergency_stop():
            """Trigger emergency stop during sequence execution"""
            time.sleep(1)  # Wait for sequence to start
            self.emergency_stop.set_state(True)
            
        import threading
        emergency_thread = threading.Thread(target=trigger_emergency_stop)
        emergency_thread.daemon = True
        emergency_thread.start()
        
        # Start sequence
        self.assertTrue(runner.start())
        
        # Wait for sequence to abort (or timeout after 5 seconds)
        start_time = time.time()
        while runner.is_running() and time.time() - start_time < 5:
            time.sleep(0.1)
            
        # Verify sequence was aborted
        self.assertFalse(runner.is_running())
        self.assertEqual('ERROR', runner.get_status())
        
        # Check for emergency stop in execution log
        log = runner.get_execution_log()
        emergency_messages = [msg for msg in log if 'Emergency stop' in msg]
        self.assertGreater(len(emergency_messages), 0)

if __name__ == '__main__':
    unittest.main()