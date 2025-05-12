#!/usr/bin/env python
"""
Hardware Component Tests

This module tests the individual hardware components using mock interfaces.
"""
import unittest
import time
import logging
from tests.test_base import BaseTestCase
from tests.hardware.mock_hardware import (
    MockHardwareController,
    MockHardwareException,
    HardwareState
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_hardware')

class HardwareComponentTest(BaseTestCase):
    """Test case for hardware components"""
    
    def setUp(self):
        """Set up test fixtures before each test"""
        super().setUp()
        self.controller = MockHardwareController()
        
        # Initialize test hardware
        self.stepper = self.controller.add_stepper('test_stepper')
        self.servo = self.controller.add_servo('test_servo')
        self.laser = self.controller.add_laser('test_laser')
        self.gpio = self.controller.add_gpio('test_gpio', 18)
        
    def tearDown(self):
        """Clean up after each test"""
        self.controller.reset_all()
        super().tearDown()
        
    def test_stepper_basic_movement(self):
        """Test basic stepper motor movement"""
        # Move forward
        result = self.stepper.move(100, "forward")
        self.assertTrue(result['success'])
        self.assertEqual(100, self.stepper.get_position())
        
        # Move backward
        result = self.stepper.move(50, "backward")
        self.assertTrue(result['success'])
        self.assertEqual(50, self.stepper.get_position())
        
    def test_stepper_error_handling(self):
        """Test stepper error handling"""
        # Set failure mode
        self.stepper.set_failure_mode("hardware_failure")
        
        # Attempt to move should raise an exception
        with self.assertRaises(MockHardwareException):
            self.stepper.move(100, "forward")
            
        # Reset and try again
        self.stepper.set_failure_mode(None)
        result = self.stepper.move(100, "forward")
        self.assertTrue(result['success'])
        
    def test_servo_movement(self):
        """Test servo movement"""
        # Initial position should be default angle
        self.assertEqual(90, self.servo.get_angle())
        
        # Move to new angle
        result = self.servo.move_to(45)
        self.assertTrue(result['success'])
        self.assertEqual(45, self.servo.get_angle())
        
        # Test invalid angle
        with self.assertRaises(ValueError):
            self.servo.move_to(200)
            
    def test_laser_firing(self):
        """Test laser firing"""
        # Fire for a short duration
        result = self.laser.fire(0.1)
        self.assertTrue(result['success'])
        self.assertTrue(self.laser.is_firing)
        
        # Wait for it to complete
        time.sleep(0.2)
        self.assertFalse(self.laser.is_firing)
        
        # Test stopping mid-fire
        result = self.laser.fire(1.0)
        self.assertTrue(result['success'])
        self.assertTrue(self.laser.is_firing)
        
        # Stop it immediately
        result = self.laser.stop()
        self.assertTrue(result['success'])
        self.assertFalse(self.laser.is_firing)
        
    def test_gpio_control(self):
        """Test GPIO control"""
        # Initial state should be inactive
        self.assertFalse(self.gpio.get_state())
        
        # Set to active
        result = self.gpio.set_state(True)
        self.assertTrue(result['success'])
        self.assertTrue(self.gpio.get_state())
        
        # Set back to inactive
        result = self.gpio.set_state(False)
        self.assertTrue(result['success'])
        self.assertFalse(self.gpio.get_state())
        
    def test_error_simulation(self):
        """Test hardware error simulation"""
        # Set failure modes for different components
        self.controller.simulate_hardware_failure("stepper", "test_stepper", "hardware_not_available")
        self.controller.simulate_hardware_failure("servo", "test_servo", "hardware_failure")
        self.controller.simulate_hardware_failure("laser", "test_laser", "timeout")
        self.controller.simulate_hardware_failure("gpio", "test_gpio", "unexpected")
        
        # All operations should fail
        with self.assertRaises(MockHardwareException):
            self.stepper.move(100, "forward")
            
        with self.assertRaises(MockHardwareException):
            self.servo.move_to(45)
            
        with self.assertRaises(MockHardwareException):
            self.laser.fire(0.1)
            
        with self.assertRaises(MockHardwareException):
            self.gpio.set_state(True)
            
        # Reset and verify operations now work
        self.controller.reset_all()
        
        self.assertTrue(self.stepper.move(100, "forward")['success'])
        self.assertTrue(self.servo.move_to(45)['success'])
        self.assertTrue(self.laser.fire(0.1)['success'])
        self.assertTrue(self.gpio.set_state(True)['success'])
        
    def test_hardware_state(self):
        """Test reporting of hardware state"""
        # All components should start in READY state
        state = self.controller.get_state()
        self.assertEqual("ready", state["steppers"]["test_stepper"])
        self.assertEqual("ready", state["servos"]["test_servo"])
        self.assertEqual("ready", state["lasers"]["test_laser"])
        self.assertFalse(state["gpios"]["test_gpio"])
        
        # Make some components busy
        self.stepper.state = HardwareState.BUSY
        self.servo.state = HardwareState.ERROR
        self.laser.is_firing = True
        self.laser.state = HardwareState.BUSY
        self.gpio.state = True
        
        # Check updated state
        state = self.controller.get_state()
        self.assertEqual("busy", state["steppers"]["test_stepper"])
        self.assertEqual("error", state["servos"]["test_servo"])
        self.assertEqual("busy", state["lasers"]["test_laser"])
        self.assertTrue(state["gpios"]["test_gpio"])

if __name__ == '__main__':
    unittest.main()