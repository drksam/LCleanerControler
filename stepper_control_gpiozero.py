import time
import logging
import os
from gpiozero import DigitalOutputDevice, DigitalInputDevice

class StepperMotor:
    """
    Class to control a stepper motor using a stepper driver 
    (like A4988, DRV8825, etc.) connected to Raspberry Pi GPIO pins
    """
    
    def __init__(self, dir_pin, step_pin, enable_pin=None, home_switch_pin=None, 
                 step_delay=0.005, max_steps=2000):
        """
        Initialize the stepper motor controller
        
        Args:
            dir_pin (int): BCM pin number connected to the direction pin of the driver
            step_pin (int): BCM pin number connected to the step pin of the driver
            enable_pin (int, optional): BCM pin number connected to the enable pin of the driver
            home_switch_pin (int, optional): BCM pin number connected to the home limit switch
            step_delay (float, optional): Delay between steps in seconds
            max_steps (int, optional): Maximum number of steps allowed in one direction
        """
        self.step_delay = step_delay
        self.max_steps = max_steps
        
        # Check system configuration mode
        import config
        system_config = config.get_system_config()
        operation_mode = system_config.get('operation_mode', 'simulation')
        
        # Set simulation mode based on system configuration
        self.simulation_mode = operation_mode == 'simulation'
        
        if self.simulation_mode:
            logging.info("Running in simulation mode - no GPIO operations will be performed")
            self.is_enabled = True
            return
            
        try:
            # Setup GPIO
            self.dir_pin = DigitalOutputDevice(dir_pin)
            self.step_pin = DigitalOutputDevice(step_pin)
            
            if enable_pin is not None:
                self.enable_pin = DigitalOutputDevice(enable_pin, active_high=False)  # Active LOW
                # Enable the motor by default
                self.enable_pin.on()  # This will output LOW (enabled)
            else:
                self.enable_pin = None
                
            if home_switch_pin is not None:
                # Setup home switch with pull-up resistor
                self.home_switch = DigitalInputDevice(home_switch_pin, pull_up=True)
            else:
                self.home_switch = None
                
            # Set initial direction
            self.dir_pin.on()  # High
            
            self.is_enabled = True
            logging.info("Stepper motor initialized on pins: DIR=%s, STEP=%s, ENABLE=%s, HOME=%s", 
                        dir_pin, step_pin, 
                        enable_pin if enable_pin is not None else "None",
                        home_switch_pin if home_switch_pin is not None else "None")
        except Exception as e:
            logging.error(f"Error initializing stepper motor: {e}")
            # Fallback to simulation mode if GPIO setup fails
            self.simulation_mode = True
            self.is_enabled = True
            logging.info("Falling back to simulation mode")
    
    def enable(self):
        """Enable the motor driver"""
        if self.simulation_mode:
            logging.debug("Simulation: Motor enabled")
            self.is_enabled = True
            return
            
        if self.enable_pin is not None:
            self.enable_pin.on()  # This will output LOW (enabled)
            self.is_enabled = True
            logging.debug("Motor enabled")
    
    def disable(self):
        """Disable the motor driver to save power and allow manual movement"""
        if self.simulation_mode:
            logging.debug("Simulation: Motor disabled")
            self.is_enabled = False
            return
            
        if self.enable_pin is not None:
            self.enable_pin.off()  # This will output HIGH (disabled)
            self.is_enabled = False
            logging.debug("Motor disabled")
    
    # Add a class-level stop flag
    stop_flag = False
    
    def stop(self):
        """Stop any ongoing movement immediately"""
        logging.info("Stop signal received for stepper motor")
        self.__class__.stop_flag = True
        # Disable the motor for immediate stop if enabled
        if self.is_enabled and self.enable_pin is not None and not self.simulation_mode:
            self.disable()
        return True
        
    def reset_stop_flag(self):
        """Reset the stop flag to allow movement again"""
        self.__class__.stop_flag = False
        logging.debug("Stepper motor stop flag reset")
        return True
        
    def step(self, steps):
        """
        Move the motor a specified number of steps
        
        Args:
            steps (int): Number of steps to move (positive = forward, negative = backward)
        
        Returns:
            int: Actual number of steps moved
        """
        # Reset stop flag before starting
        self.__class__.stop_flag = False
        
        if self.simulation_mode:
            logging.debug(f"Simulation: Moving {'forward' if steps >= 0 else 'backward'} by {abs(steps)} steps")
            
            # Simulate movement with stop check capability
            steps_to_simulate = abs(steps)
            step_time = self.step_delay * 2  # Simulate time taken for steps
            
            # Check the stop flag immediately - abort if already set
            if self.__class__.stop_flag:
                logging.info("Simulation: Movement interrupted before starting (stop flag set)")
                self.__class__.stop_flag = False
                return 0
            
            # For more responsive simulation, break the sleep into smaller chunks
            chunks_per_step = 5  # Check for stop flag 5 times per step
            chunk_time = step_time / (steps_to_simulate * chunks_per_step)
            
            # Simulate steps with more responsive interruption capability
            for i in range(steps_to_simulate):
                for _ in range(chunks_per_step):
                    # Small sleep chunk to simulate one step
                    time.sleep(chunk_time)
                    
                    # Check if stop has been requested - respond immediately
                    if self.__class__.stop_flag:
                        logging.info(f"Simulation: Movement interrupted after {i} steps")
                        self.__class__.stop_flag = False
                        actual_steps = i if steps >= 0 else -i
                        return actual_steps
            
            return steps
            
        if not self.is_enabled and self.enable_pin is not None:
            self.enable()
            
        # Ensure within limits
        if abs(steps) > self.max_steps:
            logging.warning(f"Step count limited to {self.max_steps}")
            steps = self.max_steps if steps > 0 else -self.max_steps
            
        # Set direction
        if steps >= 0:
            self.dir_pin.on()  # Forward (HIGH)
            num_steps = steps
        else:
            self.dir_pin.off()  # Backward (LOW)
            num_steps = abs(steps)
            
        logging.debug(f"Moving {'forward' if steps >= 0 else 'backward'} by {num_steps} steps")
        
        # Perform stepping with stop check
        steps_completed = 0
        for i in range(num_steps):
            # Check if stop has been requested
            if self.__class__.stop_flag:
                logging.info(f"Stepper movement interrupted after {i} steps")
                self.__class__.stop_flag = False  # Reset flag
                return i if steps >= 0 else -i
                
            self.step_pin.on()
            time.sleep(self.step_delay)
            self.step_pin.off()
            time.sleep(self.step_delay)
            steps_completed += 1
            
        return steps_completed if steps >= 0 else -steps_completed
    
    def find_home(self):
        """
        Home the motor by moving it until the home switch is triggered
        
        Returns:
            bool: True if homing was successful, False otherwise
        """
        if self.simulation_mode:
            logging.info("Simulation: Homing sequence completed")
            time.sleep(1)  # Simulate homing time
            return True
            
        if self.home_switch is None:
            logging.error("Cannot home motor: No home switch configured")
            return False
            
        if not self.is_enabled and self.enable_pin is not None:
            self.enable()
            
        logging.info("Starting homing sequence")
        
        # First check if we're already at home
        if self.home_switch.is_active:  # Switch is triggered (LOW)
            logging.info("Already at home position")
            # Move away from home switch a bit
            self.step(50)
            
        # Move backward until we hit the home switch
        logging.info("Moving to find home switch...")
        self.dir_pin.off()  # Set direction to backward (LOW)
        
        # Step until home switch is activated or max steps reached
        steps_taken = 0
        while not self.home_switch.is_active:  # Not triggered (HIGH)
            # Check if stop has been requested
            if self.__class__.stop_flag:
                logging.info(f"Homing interrupted after {steps_taken} steps")
                self.__class__.stop_flag = False  # Reset flag
                return False
                
            self.step_pin.on()
            time.sleep(self.step_delay)
            self.step_pin.off()
            time.sleep(self.step_delay)
            
            steps_taken += 1
            if steps_taken >= self.max_steps:
                logging.error("Homing failed: Reached maximum steps without finding home")
                return False
                
        logging.info(f"Home switch found after {steps_taken} steps")
        
        # Check if stop has been requested
        if self.__class__.stop_flag:
            logging.info("Homing interrupted after finding home switch")
            self.__class__.stop_flag = False  # Reset flag
            return False
        
        # Back off slightly from the switch
        self.step(10)  # Move forward a bit
        
        # Check if stop has been requested
        if self.__class__.stop_flag:
            logging.info("Homing interrupted after backing off from switch")
            self.__class__.stop_flag = False  # Reset flag
            return False
        
        # Approach home switch slowly for precision
        self.dir_pin.off()  # Set direction back to backward (LOW)
        while not self.home_switch.is_active:  # Not triggered (HIGH)
            # Check if stop has been requested
            if self.__class__.stop_flag:
                logging.info("Precision homing interrupted")
                self.__class__.stop_flag = False  # Reset flag
                return False
                
            self.step_pin.on()
            time.sleep(self.step_delay * 2)  # Slower approach
            self.step_pin.off()
            time.sleep(self.step_delay * 2)
            
        logging.info("Homing completed successfully")
        return True
        
    def cleanup(self):
        """Clean up GPIO pins"""
        if self.simulation_mode:
            logging.info("Simulation: GPIO cleanup (no action needed)")
            return
            
        if self.enable_pin is not None:
            self.disable()
        
        # gpiozero will handle cleanup internally when objects are closed
        try:
            self.dir_pin.close()
            self.step_pin.close()
            if self.enable_pin is not None:
                self.enable_pin.close()
            if self.home_switch is not None:
                self.home_switch.close()
        except Exception as e:
            logging.error(f"Error during GPIO cleanup: {e}")
            
        logging.info("Stepper motor GPIO cleaned up")