import os
import logging
import sys
import time
import threading
import uuid
import json
import secrets
from datetime import datetime, timedelta
from functools import wraps

# Import the configuration module
import config

# Load system configuration and operational settings
system_config = config.get_system_config()
operation_mode = system_config.get('operation_mode', 'simulation')
debug_level = system_config.get('debug_level', 'info')
bypass_safety = system_config.get('bypass_safety', False)

# Set simulation mode based on system configuration
if operation_mode == 'simulation':
    os.environ['SIMULATION_MODE'] = 'True'
else:
    # Clear simulation mode for prototype or normal operation
    os.environ.pop('SIMULATION_MODE', None)
    
    # Set FORCE_HARDWARE flag for prototype mode to prevent fallback to simulation
    if operation_mode == 'prototype':
        os.environ['FORCE_HARDWARE'] = 'True'
        logging.info("PROTOTYPE MODE: Setting FORCE_HARDWARE flag to prevent simulation fallback")

# Configure logging based on debug level setting
log_level = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR
}.get(debug_level, logging.INFO)

logging.basicConfig(level=log_level,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   stream=sys.stdout)
logger = logging.getLogger(__name__)

try:
    from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
    from flask_sqlalchemy import SQLAlchemy
    from flask_login import LoginManager, login_user, logout_user, login_required, current_user
    logger.info("Flask and extensions imported successfully")
except ImportError as e:
    logger.error(f"Error importing Flask or extensions: {e}")
    sys.exit(1)

# Import app and db from main.py instead of creating a new Flask instance
from main import app, db, login_manager

# Import models
from models import User, AccessLog, RFIDCard, ApiKey

# Import the RFID controller
from rfid_control import RFIDController

# Import GPIO controllers
from stepper_control_gpioctrl import StepperMotor
from servo_control_gpioctrl import ServoController
from output_control_gpiod import OutputController
from input_control_gpiod import InputController
logger.info("Using GPIOController implementation for GPIO")

# Import the sequence runner for automated operations
from sequence_runner import SequenceRunner, SequenceStatus

# Import statistics functions
from config import get_statistics, increment_laser_counter, add_laser_fire_time, reset_statistics

# Use the existing Flask app initialized earlier

# Load configuration
gpio_config = config.get_gpio_config()
stepper_config = config.get_stepper_config()
servo_config = config.get_servo_config()

# Initialize stepper motor with configuration
force_hardware = os.environ.get('FORCE_HARDWARE', 'False').lower() == 'true'

try:
    # Use GPIOController-based stepper
    stepper = StepperMotor()
    motor_initialized = True
    logger.info("Stepper motor initialized successfully")
except Exception as e:
    logger.error(f"Error initializing stepper motor: {e}")
    if force_hardware or operation_mode == 'prototype':
        logger.error("FORCE_HARDWARE is enabled in prototype mode - not falling back to simulation mode")
        motor_initialized = False
        stepper = None
        # In prototype mode, we raise the error to prevent silently degrading to simulation
        if operation_mode == 'prototype':
            raise
    else:
        logger.info("Falling back to simulation mode")
        # Create a simulated stepper motor for development purposes
        try:
            stepper = StepperMotor()  # GPIOController implementation supports simulation mode
            motor_initialized = True
        except Exception as inner_e:
            logger.error(f"Failed to create simulated stepper motor: {inner_e}")
            motor_initialized = False
            stepper = None

# Initialize servo controller with configuration
try:
    # Use GPIOController-based servo
    servo = ServoController()
    servo_initialized = True
    logger.info("Servo initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize servo: {e}")
    if force_hardware or operation_mode == 'prototype':
        logger.error("FORCE_HARDWARE is enabled in prototype mode - not falling back to simulation mode")
        servo_initialized = False
        servo = None
        # In prototype mode, we raise the error to prevent silently degrading to simulation
        if operation_mode == 'prototype':
            raise
    else:
        logger.info("Falling back to simulation mode")
        # Create a simulated servo for development purposes
        try:
            servo = ServoController()  # GPIOController implementation supports simulation mode
            servo_initialized = True
            logger.info("Simulated servo controller created successfully")
        except Exception as inner_e:
            logger.error(f"Failed to create simulated servo: {inner_e}")
            servo_initialized = False
            servo = None

# Initialize output controller for fan and red lights
try:
    output_controller = OutputController()
    outputs_initialized = True
    logger.info("Output controller initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize output controller: {e}")
    if force_hardware:
        logger.error("FORCE_HARDWARE is enabled in prototype mode - not falling back to simulation mode")
        outputs_initialized = False
        output_controller = None
        # In prototype mode, we raise the error to prevent silently degrading to simulation
        if operation_mode == 'prototype':
            raise
    else:
        logger.info("Falling back to simulation mode")
        # Create a simulated output controller for development purposes
        try:
            output_controller = OutputController()
            outputs_initialized = True
        except Exception as inner_e:
            logger.error(f"Failed to create simulated output controller: {inner_e}")
            outputs_initialized = False
            output_controller = None

# Store the current position in memory
current_position = 0
# Define preset positions (can be modified via the UI)
preset_positions = {
    "Position 1": 200,
    "Position 2": 400,
    "Position 3": 600,
    "Position 4": 800
}

# Servo positions
servo_position_a = 0
servo_position_b = 90
servo_inverted = False

# Create a background thread to monitor and update outputs
def update_outputs_thread():
    """Background thread to update fan and lights based on servo position"""
    while True:
        try:
            if servo_initialized and servo is not None and outputs_initialized and output_controller is not None:
                # Get current servo status
                servo_status = servo.get_status()
                current_angle = servo_status.get('current_angle', 0)
                
                # Get normal position from configuration
                normal_position = servo_config['position_normal']
                
                # Update outputs based on current servo position
                output_controller.update(current_angle, normal_position)
            
            # Sleep to reduce CPU usage
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error in output update thread: {e}")
            time.sleep(1)  # Sleep longer on error

# Start the background thread for output control
output_update_thread = threading.Thread(target=update_outputs_thread, daemon=True)
output_update_thread.start()

# Callback functions for hardware button/switch control
def stepper_callback(action, **kwargs):
    """Callback function for stepper motor actions triggered by physical buttons"""
    global current_position
    
    try:
        if action == 'jog':
            direction = kwargs.get('direction', 'forward')
            direction_int = 1 if direction == 'forward' or direction == 1 else 0
            step_size = stepper_config['jog_step_size']
            
            if motor_initialized and stepper is not None:
                stepper.jog(direction_int, step_size)
                current_position = stepper.get_position()
            else:
                # Simulate in dev environment
                steps = step_size if direction_int == 1 else -step_size
                current_position += steps
                
            logger.debug(f"Button jog: {direction} by {step_size} steps, new position: {current_position}")
            
        elif action == 'jog_step':
            direction = kwargs.get('direction', 'forward')
            direction_int = 1 if direction == 'forward' or direction == 1 else 0
            step_size = stepper_config['jog_step_size'] * 5  # Single press = 5x normal jog
            
            if motor_initialized and stepper is not None:
                stepper.jog(direction_int, step_size)
                current_position = stepper.get_position()
            else:
                # Simulate in dev environment
                steps = step_size if direction_int == 1 else -step_size
                current_position += steps
                
            logger.debug(f"Button single press: {direction} by {step_size} steps, new position: {current_position}")
            
        elif action == 'jog_stop':
            # Stop any ongoing movement
            if motor_initialized and stepper is not None:
                stepper.stop()
                current_position = stepper.get_position()
            logger.debug("Button jog stop")
            
        elif action == 'index':
            direction = kwargs.get('direction', 'forward')
            direction_int = 1 if direction == 'forward' or direction == 1 else 0
            index_distance = stepper_config['index_distance']
            
            if motor_initialized and stepper is not None:
                stepper.move_index()
                current_position = stepper.get_position()
            else:
                # Simulate in dev environment
                steps = index_distance if direction_int == 1 else -index_distance
                current_position += steps
                
            logger.debug(f"Button index movement, new position: {current_position}")
            
        elif action == 'home':
            if motor_initialized and stepper is not None:
                stepper.home()
                current_position = stepper.get_position()  # Should be 0
            else:
                # Simulate in dev environment
                current_position = 0
                
            logger.debug(f"Button home: position reset to {current_position}")
            
        elif action == 'move_to_preset':
            preset = kwargs.get('preset', 1)
            preset_pos = preset_positions.get(f"Position {preset}", 0)
            
            if motor_initialized and stepper is not None:
                stepper.move_to(preset_pos)
                current_position = stepper.get_position()
            else:
                # Simulate in dev environment
                current_position = preset_pos
                
            logger.debug(f"Button preset {preset}: moved to position {preset_pos}")
            
    except Exception as e:
        logger.error(f"Error in stepper button callback: {e}")

def servo_callback(action, **kwargs):
    """Callback function for servo actions triggered by physical buttons/switches"""
    global servo_position_a, servo_position_b, servo_inverted
    
    try:
        if action == 'fire':
            # Move to position B (the "fire" position)
            if servo_initialized and servo is not None:
                servo.move_to_b()
            logger.debug("Button fire: servo moved to position B")
            
        elif action == 'reset' or action == 'stop_fire':
            # Move to position A (the "normal" position)
            if servo_initialized and servo is not None:
                if action == 'stop_fire':
                    servo.stop_firing()
                else:
                    servo.move_to_a()
            logger.debug("Button reset: servo moved to position A")
            
        elif action == 'start_sequence':
            # Start the A-B-A-B sequence for FIBER mode
            if servo_initialized and servo is not None:
                servo.start_sequence()
            logger.debug("Button start sequence: servo sequence started")
            
        elif action == 'set_inverted':
            inverted = kwargs.get('inverted', False)
            if servo_initialized and servo is not None:
                result = servo.set_inverted(inverted)
                servo_inverted = result
            else:
                servo_inverted = inverted
                
            logger.debug(f"Switch set invert: servo inversion set to {inverted}")
            
    except Exception as e:
        logger.error(f"Error in servo button callback: {e}")

# Initialize input controller for physical button control
try:
    input_controller = InputController(
        stepper_handler=stepper_callback,
        servo_handler=servo_callback
    )
    inputs_initialized = True
    logger.info("Input controller initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize input controller: {e}")
    logger.info("Physical button control will not be available")
    inputs_initialized = False
    input_controller = None  # Explicitly set to None to avoid unbound variable issues

# Access control callback when user is authenticated/deauthenticated
def access_control_callback(granted, user_data):
    """Callback when a user is authenticated or deauthenticated"""
    try:
        # Import webhook integration module to avoid circular imports
        from webhook_integration import handle_login_event, handle_logout_event, handle_status_change_event
        
        if granted:
            username = user_data.get('username', 'Unknown')
            access_level = user_data.get('access_level', 'operator')
            user_id = user_data.get('user_id', 0)
            card_id = user_data.get('card_id')
            logger.info(f"User {username} authenticated with access level {access_level}")
            
            # Send webhook event for user login and machine status change
            if user_id:
                try:
                    user = User.query.get(user_id)
                    if user:
                        handle_login_event(user_id, card_id)
                        handle_status_change_event("active", {"user": username})
                        logger.info(f"Login and status change webhook events sent for user {username}")
                except Exception as e:
                    logger.error(f"Error sending login webhooks: {e}")
        else:
            reason = user_data.get('reason', 'Unknown reason')
            logger.info(f"Authentication removed: {reason}")
            
            # Send webhook event for user logout and machine status change
            user_id = user_data.get('user_id', 0)
            card_id = user_data.get('card_id')
            if user_id:
                try:
                    user = User.query.get(user_id)
                    if user:
                        handle_logout_event(user_id, reason, card_id)
                        handle_status_change_event("idle", {"reason": reason})
                        logger.info(f"Logout and status change webhook events sent for user {user.username}")
                except Exception as e:
                    logger.error(f"Error sending logout webhooks: {e}")
    except Exception as e:
        logger.error(f"Error in access control callback: {e}")

# Initialize RFID controller
try:
    rfid_controller = RFIDController(access_callback=access_control_callback)
    rfid_initialized = True
    logger.info("RFID controller initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize RFID controller: {e}")
    logger.info("RFID functionality will not be available")
    rfid_initialized = False
    rfid_controller = None

# Function to stop all operations (used by temperature controller)
def stop_all_operations():
    """Stop all motors, servos, and other operations due to high temperature"""
    app.logger.warning("AUTO-STOP: High temperature detected - stopping all operations")
    # Stop servo (move to normal position)
    try:
        if servo_initialized:
            servo.stop_firing()
    except Exception as e:
        app.logger.error(f"Error stopping servo: {e}")
    
    # Stop table movement
    try:
        if outputs_initialized:
            output_controller.set_table_forward(False)
            output_controller.set_table_backward(False)
    except Exception as e:
        app.logger.error(f"Error stopping table: {e}")
    
    # Stop stepper motor
    try:
        if motor_initialized:
            stepper.disable()
    except Exception as e:
        app.logger.error(f"Error disabling stepper: {e}")

# Import temperature controller
from temperature_control import TemperatureController

# Initialize temperature controller
try:
    temp_config = config.get_temperature_config()
    temp_controller = TemperatureController(
        temp_config=temp_config,
        stop_callback=stop_all_operations
    )
    temp_initialized = True
    app.logger.info("Temperature controller initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize temperature controller: {e}")
    if force_hardware:
        logger.error("FORCE_HARDWARE is enabled in prototype mode - not falling back to simulation mode")
        temp_initialized = False
        temp_controller = None
        # In prototype mode, we raise the error to prevent silently degrading to simulation
        if operation_mode == 'prototype':
            raise
    else:
        logger.info("Falling back to simulation mode")
        try:
            temp_controller = TemperatureController(stop_callback=stop_all_operations)
            temp_initialized = True
        except Exception as inner_e:
            logger.error(f"Failed to create simulated temperature controller: {inner_e}")
            temp_initialized = False
            temp_controller = None

# Initialize sequence runner for automated operation sequences
try:
    sequence_runner = SequenceRunner(
        stepper=stepper,
        servo=servo,
        output_controller=output_controller
    )
    sequences_initialized = True
    logger.info("Sequence runner initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize sequence runner: {e}")
    logger.info("Falling back to simulation mode")
    try:
        sequence_runner = SequenceRunner()
        sequences_initialized = True
    except Exception as inner_e:
        logger.error(f"Failed to create simulated sequence runner: {inner_e}")
        sequences_initialized = False
        sequence_runner = None

@app.route('/')
def index():
    """Render the main operation interface with simplified controls"""
    # Get output controller status for displaying on the main page
    output_status = {
        "fan_state": False,
        "red_lights_state": False,
        "table_forward": False,
        "table_backward": False,
        "table_at_front_limit": False,
        "table_at_back_limit": False,
        "fan_time_remaining": 0,
        "red_lights_time_remaining": 0,
        "simulation_mode": True
    }
    
    if outputs_initialized and output_controller:
        try:
            # Trying to avoid the SystemExit error with the lock
            if hasattr(output_controller, 'fan_on'):
                output_status['fan_state'] = output_controller.fan_on
            if hasattr(output_controller, 'red_lights_on'):
                output_status['red_lights_state'] = output_controller.red_lights_on
            if hasattr(output_controller, 'table_moving_forward'):
                output_status['table_forward'] = output_controller.table_moving_forward
            if hasattr(output_controller, 'table_moving_backward'):
                output_status['table_backward'] = output_controller.table_moving_backward
            if hasattr(output_controller, 'table_at_front_limit'):
                output_status['table_at_front_limit'] = output_controller.table_at_front_limit
            if hasattr(output_controller, 'table_at_back_limit'):
                output_status['table_at_back_limit'] = output_controller.table_at_back_limit
            if hasattr(output_controller, 'simulation_mode'):
                output_status['simulation_mode'] = output_controller.simulation_mode
        except Exception as e:
            logger.error(f"Error getting output status: {e}")
    
    # Get servo status
    servo_status = {}
    if servo_initialized and servo:
        try:
            servo_status = servo.get_status()
        except Exception as e:
            logger.error(f"Error getting servo status: {e}")
    
    # Get sequences to display on the main page
    sequences = {}
    try:
        sequences = config.get_sequences()
    except Exception as e:
        logger.error(f"Error getting sequences: {e}")
    
    return render_template('index.html', 
                           current_position=current_position,
                           servo_status=servo_status,
                           output_status=output_status,
                           sequences=sequences,
                           page="operation")

@app.route('/cleaning_head')
def cleaning_head():
    """Render the cleaning head control page"""
    # Get stepper config for steps per mm conversion
    stepper_config = config.get_stepper_config()
    
    return render_template('cleaning_head.html', 
                           motor_initialized=motor_initialized,
                           current_position=current_position,
                           preset_positions=preset_positions,
                           stepper_config=stepper_config,
                           page="cleaning_head")

@app.route('/trigger_servo')
def trigger_servo():
    """Render the trigger servo setup page"""
    return render_template('trigger_servo.html', 
                           servo_initialized=servo_initialized,
                           servo_position_a=servo_position_a,
                           servo_position_b=servo_position_b,
                           servo_inverted=servo_inverted,
                           page="trigger_servo")
                           
@app.route('/table')
def table():
    """Render the table control page"""
    return render_template('table.html', 
                           page="table")

def require_admin_in_normal_mode(view_function):
    """Decorator to restrict admin pages in normal mode but allow access in simulation/prototype mode"""
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        # Always allow in simulation or prototype mode
        if operation_mode in ['simulation', 'prototype']:
            return view_function(*args, **kwargs)
            
        # In normal mode, require admin rights
        if current_user.is_authenticated and current_user.access_level == 'admin':
            return view_function(*args, **kwargs)
        else:
            flash('This page requires admin access in normal mode.', 'danger')
            return redirect(url_for('index'))
    return decorated_function

@app.route('/settings')
@require_admin_in_normal_mode
def settings():
    """Render the settings/configuration interface"""
    # Get current configuration
    system_config = config.get_system_config()
    stepper_config = config.get_stepper_config()
    servo_config = config.get_servo_config()
    timing_config = config.get_timing_config()
    gpio_config = config.get_gpio_config()
    temp_config = config.get_temperature_config()
    
    return render_template('settings.html',
                           system_config=system_config,
                           stepper_config=stepper_config,
                           servo_config=servo_config,
                           timing_config=timing_config,
                           gpio_config=gpio_config,
                           temp_config=temp_config,
                           page="settings")

@app.route('/pinout')
@require_admin_in_normal_mode
def pinout():
    """Render the GPIO pinout guide page"""
    gpio_config = config.get_gpio_config()
    system_config = config.get_system_config()  # Get system config for operation mode
    return render_template('pinout.html', page="pinout", gpio_config=gpio_config, system_config=system_config)

@app.route('/rfid')
@require_admin_in_normal_mode
def rfid():
    """Render the RFID access control page for ShopMachineMonitor integration"""
    rfid_config = config.get_rfid_config()
    
    # Get all RFID cards from database
    rfid_cards = RFIDCard.query.all()
    
    # Get all users for assignment
    users = User.query.all()
    
    # Get recent access logs
    access_logs = AccessLog.query.order_by(AccessLog.timestamp.desc()).limit(20).all()
    
    return render_template('rfid.html', 
                          page="rfid", 
                          rfid_config=rfid_config,
                          rfid_cards=rfid_cards,
                          users=users,
                          access_logs=access_logs,
                          rfid_initialized=rfid_initialized)

@app.route('/jog', methods=['POST'])
def jog():
    """Jog the motor in the specified direction"""
    global current_position
    
    if not motor_initialized or stepper is None:
        # In development mode, simulate motor movement without actual hardware
        try:
            direction = request.json.get('direction')
            steps = int(request.json.get('steps', 10))
            
            if direction == 'forward':
                # Simulate movement
                current_position += steps
                logger.debug(f"Simulated jog: forward {steps} steps")
            elif direction == 'backward':
                # Simulate movement
                current_position -= steps
                logger.debug(f"Simulated jog: backward {steps} steps")
            else:
                return jsonify({"status": "error", "message": "Invalid direction"}), 400
            
            return jsonify({
                "status": "success", 
                "position": current_position,
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated jog operation: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        direction = request.json.get('direction')
        steps = int(request.json.get('steps', 10))
        
        # Use GPIOController jog implementation
        direction_int = 1 if direction == 'forward' else 0
        result = stepper.jog(direction_int, steps)
        if result:
            current_position = stepper.get_position()
        else:
            return jsonify({"status": "error", "message": "Jog operation failed"}), 500
        
        return jsonify({
            "status": "success", 
            "position": current_position
        })
    except Exception as e:
        logger.error(f"Error in jog operation: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Stop the motor immediately
@app.route('/stop_motor', methods=['POST'])
def stop_motor():
    """Stop the motor movement immediately"""
    global current_position
    
    if not motor_initialized or stepper is None:
        # In development mode, simulate motor action without actual hardware
        try:
            logger.debug("Simulated motor stop action")
            return jsonify({"status": "success", "position": current_position, "simulated": True})
        except Exception as e:
            logger.error(f"Error in simulated motor stop: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        # Call the new stop method to interrupt any ongoing movement immediately
        stepper.stop()
        logger.info(f"Motor stopped at position {current_position}")
        return jsonify({"status": "success", "position": current_position})
    except Exception as e:
        logger.error(f"Error stopping motor: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/home', methods=['POST'])
def home():
    """Home the motor (find zero position)"""
    global current_position
    
    if not motor_initialized or stepper is None:
        # In development mode, simulate homing without actual hardware
        try:
            # Simulate homing operation with delay
            import time
            time.sleep(0.5)  # Simulate some delay for homing
            
            # Set position to 0
            current_position = 0
            logger.debug("Simulated homing completed")
            
            return jsonify({
                "status": "success", 
                "position": current_position,
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated homing operation: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        # Use GPIOController home implementation
        result = stepper.home()
        if result:
            current_position = stepper.get_position()  # Should be 0
        else:
            return jsonify({"status": "error", "message": "Home operation failed"}), 500
            
        return jsonify({
            "status": "success", 
            "position": current_position
        })
    except Exception as e:
        logger.error(f"Error in homing operation: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/move_to', methods=['POST'])
def move_to():
    """Move to a specific position"""
    global current_position
    
    if not motor_initialized or stepper is None:
        # In development mode, simulate movement without actual hardware
        try:
            target_position = int(request.json.get('position', 0))
            
            # Simulate some delay for movement
            import time
            
            # Calculate delay based on distance to move
            distance = abs(target_position - current_position)
            # Simulate speed: 1 step per millisecond (slower for larger distances)
            delay_time = min(2.0, distance / 1000)  # Cap at 2 seconds
            time.sleep(delay_time)
            
            # Update position
            current_position = target_position
            logger.debug(f"Simulated move to position {target_position} (took {delay_time:.2f}s)")
            
            return jsonify({
                "status": "success", 
                "position": current_position,
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated move operation: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        target_position = int(request.json.get('position', 0))
        
        # Use GPIOController move_to implementation
        result = stepper.move_to(target_position)
        if result:
            current_position = stepper.get_position()
        else:
            return jsonify({"status": "error", "message": "Move operation failed"}), 500
        
        return jsonify({
            "status": "success", 
            "position": current_position
        })
    except Exception as e:
        logger.error(f"Error in move operation: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/enable_motor', methods=['POST'])
def enable_motor():
    """Enable or disable the motor"""
    if not motor_initialized or stepper is None:
        # In development mode, simulate enable/disable without actual hardware
        try:
            enable = request.json.get('enable', True)
            logger.debug(f"Simulated motor {'enable' if enable else 'disable'}")
            
            return jsonify({
                "status": "success", 
                "enabled": enable,
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated motor enable/disable operation: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        enable = request.json.get('enable', True)
        
        if enable:
            stepper.enable()
        else:
            stepper.disable()
        
        return jsonify({
            "status": "success", 
            "enabled": enable
        })
    except Exception as e:
        logger.error(f"Error in motor enable/disable operation: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/save_position', methods=['POST'])
def save_position():
    """Save current position to a preset"""
    global preset_positions
    global current_position
    
    try:
        position_name = request.json.get('name')
        
        preset_positions[position_name] = current_position
        logger.debug(f"Saved position '{position_name}' with value {current_position}")
        
        return jsonify({
            "status": "success", 
            "preset_positions": preset_positions
        })
    except Exception as e:
        logger.error(f"Error saving position: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Servo control routes
@app.route('/servo/set_position_a', methods=['POST'])
def set_servo_position_a():
    """Set the servo's position A"""
    global servo_position_a
    
    if not servo_initialized or servo is None:
        # In development mode, simulate servo control without actual hardware
        try:
            angle = int(request.json.get('angle', 0))
            servo_position_a = angle
            logger.debug(f"Simulated servo position A set to {angle} degrees")
            
            return jsonify({
                "status": "success", 
                "position_a": angle,
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated servo position A setting: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        angle = int(request.json.get('angle', 0))
        result_angle = servo.set_position_a(angle)
        servo_position_a = result_angle
        
        return jsonify({
            "status": "success", 
            "position_a": result_angle
        })
    except Exception as e:
        logger.error(f"Error setting servo position A: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/servo/set_position_b', methods=['POST'])
def set_servo_position_b():
    """Set the servo's position B"""
    global servo_position_b
    
    if not servo_initialized or servo is None:
        # In development mode, simulate servo control without actual hardware
        try:
            angle = int(request.json.get('angle', 90))
            servo_position_b = angle
            logger.debug(f"Simulated servo position B set to {angle} degrees")
            
            return jsonify({
                "status": "success", 
                "position_b": angle,
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated servo position B setting: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        angle = int(request.json.get('angle', 90))
        result_angle = servo.set_position_b(angle)
        servo_position_b = result_angle
        
        return jsonify({
            "status": "success", 
            "position_b": result_angle
        })
    except Exception as e:
        logger.error(f"Error setting servo position B: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/servo/set_inverted', methods=['POST'])
def set_servo_inverted():
    """Set the servo's inversion status"""
    global servo_inverted
    
    if not servo_initialized or servo is None:
        # In development mode, simulate servo control without actual hardware
        try:
            inverted = request.json.get('inverted', False)
            servo_inverted = inverted
            logger.debug(f"Simulated servo inversion set to {inverted}")
            
            return jsonify({
                "status": "success", 
                "inverted": inverted,
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated servo inversion setting: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        inverted = request.json.get('inverted', False)
        result = servo.set_inverted(inverted)
        servo_inverted = result
        
        return jsonify({
            "status": "success", 
            "inverted": result
        })
    except Exception as e:
        logger.error(f"Error setting servo inversion: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/servo/move_to_a', methods=['POST'])
def move_servo_to_a():
    """Move the servo to position A"""
    if not servo_initialized or servo is None:
        # In development mode, simulate servo control without actual hardware
        try:
            logger.debug(f"Simulated servo move to position A ({servo_position_a} degrees)")
            
            return jsonify({
                "status": "success", 
                "position": "A",
                "angle": servo_position_a,
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated servo move to A: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        success = servo.move_to_a()
        
        return jsonify({
            "status": "success" if success else "error", 
            "position": "A",
            "angle": servo_position_a
        })
    except Exception as e:
        logger.error(f"Error moving servo to position A: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/servo/move_to_b', methods=['POST'])
def move_servo_to_b():
    """Move the servo to position B"""
    if not servo_initialized or servo is None:
        # In development mode, simulate servo control without actual hardware
        try:
            logger.debug(f"Simulated servo move to position B ({servo_position_b} degrees)")
            
            return jsonify({
                "status": "success", 
                "position": "B",
                "angle": servo_position_b,
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated servo move to B: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        success = servo.move_to_b()
        
        return jsonify({
            "status": "success" if success else "error", 
            "position": "B",
            "angle": servo_position_b
        })
    except Exception as e:
        logger.error(f"Error moving servo to position B: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/servo/move_to_angle', methods=['POST'])
def move_servo_to_angle():
    """Move the servo to a specific angle"""
    if not servo_initialized or servo is None:
        # In development mode, simulate servo control without actual hardware
        try:
            angle = int(request.json.get('angle', 0))
            logger.debug(f"Simulated servo move to {angle} degrees")
            
            return jsonify({
                "status": "success", 
                "angle": angle,
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated servo move to angle: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        angle = int(request.json.get('angle', 0))
        success = servo.move_to_angle(angle)
        
        return jsonify({
            "status": "success" if success else "error", 
            "angle": angle
        })
    except Exception as e:
        logger.error(f"Error moving servo to angle: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/servo/detach', methods=['POST'])
def detach_servo():
    """Detach the servo to prevent jitter"""
    if not servo_initialized or servo is None:
        # In development mode, simulate detaching
        logger.debug("Simulated servo detach")
        return jsonify({
            "status": "success",
            "message": "Servo detached (simulated)",
            "simulated": True
        })
    
    try:
        success = servo.detach()
        return jsonify({
            "status": "success" if success else "error",
            "message": "Servo detached" if success else "Failed to detach servo"
        })
    except Exception as e:
        logger.error(f"Error detaching servo: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/servo/reattach', methods=['POST'])
def reattach_servo():
    """Reattach the servo"""
    if not servo_initialized or servo is None:
        # In development mode, simulate reattaching
        logger.debug("Simulated servo reattach")
        return jsonify({
            "status": "success",
            "message": "Servo reattached (simulated)",
            "simulated": True
        })
    
    try:
        # Get initial angle if provided
        data = request.json or {}
        initial_angle = data.get('angle')
        
        success = servo.reattach(initial_angle)
        return jsonify({
            "status": "success" if success else "error",
            "message": "Servo reattached" if success else "Failed to reattach servo"
        })
    except Exception as e:
        logger.error(f"Error reattaching servo: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/servo/status', methods=['GET'])
def get_servo_status():
    """Get the current status of the servo"""
    if not servo_initialized or servo is None:
        # In development mode, simulate servo status
        return jsonify({
            "status": "success",
            "servo_status": {
                "initialized": servo_initialized,
                "position_a": servo_position_a,
                "position_b": servo_position_b,
                "inverted": servo_inverted,
                "current_angle": None
            },
            "simulated": True
        })
    
    try:
        servo_status = servo.get_status()
        
        return jsonify({
            "status": "success",
            "servo_status": servo_status
        })
    except Exception as e:
        logger.error(f"Error getting servo status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Error handlers
# Configuration update route
@app.route('/update_config', methods=['POST'])
def update_config():
    """Update configuration parameters"""
    try:
        section = request.json.get('section')
        key = request.json.get('key')
        value = request.json.get('value')
        
        # Convert value to appropriate type
        if isinstance(value, str):
            if value.isdigit():
                value = int(value)
            elif '.' in value and all(part.isdigit() for part in value.split('.')):
                # Handle floating point numbers
                value = float(value)
            elif value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
            
        # Update configuration
        success = config.update_config(section, key, value)
        
        if success:
            logger.info(f"Updated config {section}.{key} to {value}")
            # Restart the system if GPIO pins or system settings have changed
            restart_needed = section == 'gpio' or section == 'system'
            
            return jsonify({
                "status": "success",
                "message": f"Configuration updated successfully",
                "restart_needed": restart_needed
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Invalid configuration parameter: {section}.{key}"
            }), 400
            
    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Index movement route
@app.route('/index_move', methods=['POST'])
def index_move():
    """Move the stepper motor by the index distance"""
    global current_position
    
    # Get the index distance in steps from configuration
    index_distance = stepper_config['index_distance']
    direction = request.json.get('direction', 'forward')
    
    # Determine direction multiplier
    direction_multiplier = 1 if direction == 'forward' else -1
    
    # Calculate the number of steps to move
    steps_to_move = index_distance * direction_multiplier
    
    if not motor_initialized or stepper is None:
        # In development mode, simulate index movement
        try:
            # Simulate some delay for movement
            import time
            time.sleep(1)
            
            # Update position
            current_position += steps_to_move
            logger.debug(f"Simulated index move {direction} by {index_distance} steps")
            
            # Convert to mm for logging
            mm_moved = index_distance / stepper_config.get('steps_per_mm', 100)
            logger.debug(f"That's approximately {mm_moved:.2f} mm")
            
            return jsonify({
                "status": "success", 
                "position": current_position,
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated index move operation: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        # Use GPIOController move_index implementation
        direction_int = 1 if direction == 'forward' else 0
        result = stepper.move_index()
        if result:
            current_position = stepper.get_position()
            logger.info(f"Index moved {direction} to position {current_position}")
        else:
            return jsonify({"status": "error", "message": "Index move failed"}), 500
        
        return jsonify({
            "status": "success", 
            "position": current_position
        })
    except Exception as e:
        logger.error(f"Error in index move operation: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Fan control routes
@app.route('/fan/status', methods=['GET'])
def get_fan_status():
    """Get the current fan status"""
    if not outputs_initialized or output_controller is None:
        # In development mode, simulate fan status
        return jsonify({
            "status": "success", 
            "fan_state": False,
            "simulated": True
        })
    
    try:
        # Avoid using get_status due to lock issue
        fan_state = False
        time_remaining = 0
        
        # Safely access the attributes directly to avoid lock issues
        if hasattr(output_controller, 'fan_on'):
            fan_state = output_controller.fan_on
            
        return jsonify({
            "status": "success",
            "fan_state": fan_state,
            "time_remaining": time_remaining
        })
    except Exception as e:
        logger.error(f"Error getting fan status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/fan/set', methods=['POST'])
def set_fan():
    """Set the fan state manually"""
    if not outputs_initialized or output_controller is None:
        # In development mode, simulate fan control
        state = request.json.get('state', False)
        return jsonify({
            "status": "success", 
            "fan_state": state,
            "simulated": True
        })
    
    try:
        state = request.json.get('state', False)
        output_controller.set_fan(state)
        
        return jsonify({
            "status": "success",
            "fan_state": state
        })
    except Exception as e:
        logger.error(f"Error setting fan state: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Red lights control routes
@app.route('/lights/status', methods=['GET'])
def get_lights_status():
    """Get the current red lights status"""
    if not outputs_initialized or output_controller is None:
        # In development mode, simulate lights status
        return jsonify({
            "status": "success", 
            "lights_state": False,
            "simulated": True
        })
    
    try:
        # Avoid using get_status due to lock issue
        lights_state = False
        time_remaining = 0
        
        # Safely access the attributes directly to avoid lock issues
        if hasattr(output_controller, 'red_lights_on'):
            lights_state = output_controller.red_lights_on
            
        return jsonify({
            "status": "success",
            "lights_state": lights_state,
            "time_remaining": time_remaining
        })
    except Exception as e:
        logger.error(f"Error getting lights status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/lights/set', methods=['POST'])
def set_lights():
    """Set the red lights state manually"""
    if not outputs_initialized or output_controller is None:
        # In development mode, simulate lights control
        state = request.json.get('state', False)
        return jsonify({
            "status": "success", 
            "lights_state": state,
            "simulated": True
        })
    
    try:
        state = request.json.get('state', False)
        output_controller.set_red_lights(state)
        
        return jsonify({
            "status": "success",
            "lights_state": state
        })
    except Exception as e:
        logger.error(f"Error setting lights state: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Fire action route (move servo to B position, triggers fan and lights)
@app.route('/fire', methods=['POST'])
def fire():
    """Fire action - move servo to B position with optional mode (toggle or momentary)"""
    # Get the fire mode from request JSON (default to momentary if not specified)
    data = request.get_json(silent=True) or {}
    mode = data.get('mode', 'momentary')
    
    logger.debug(f"Fire action requested with mode: {mode}")
    
    if not servo_initialized or servo is None:
        # In development mode, simulate fire action
        try:
            logger.debug(f"Simulated fire action (servo move to position B: {servo_position_b} degrees, mode: {mode})")
            time.sleep(0.1)  # Small delay to simulate servo movement
            
            return jsonify({
                "status": "success", 
                "position": "B",
                "angle": servo_position_b,
                "mode": mode,
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated fire action: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        # Try to reattach servo if not initialized
        if not servo.initialized:
            logger.info("Attempting to reattach servo before firing")
            servo.reattach()
        
        # The mode could be used to implement different behavior in the servo control
        # For example, toggle mode might save state in the servo control module
        # For now, we're just passing through to the standard fire() method
        success = servo.fire()
        
        if success:
            # Add event to statistics if in toggle mode
            if mode == 'toggle':
                # For toggle mode, we count this as a proper fire event for statistics
                config.increment_laser_counter()
                # Start a timer or update the stats appropriately
            
            return jsonify({
                "status": "success", 
                "position": "B",
                "angle": servo_position_b,
                "mode": mode,
                "message": f"Firing initiated ({mode} mode)"
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to initiate firing - servo may not be initialized"
            }), 500
    except Exception as e:
        logger.error(f"Error in fire action: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
        
# Fire Fiber route (starts the A-B-A-B sequence)
@app.route('/fire_fiber', methods=['POST'])
def fire_fiber():
    """Start the servo sequence for FIBER mode (A-B-A-B pattern)"""
    # Get the fire mode from request JSON (default to momentary if not specified)
    data = request.get_json(silent=True) or {}
    mode = data.get('mode', 'momentary')
    
    logger.debug(f"Fire fiber action requested with mode: {mode}")
    
    if not servo_initialized or servo is None:
        # In development mode, simulate sequence action
        try:
            logger.debug(f"Simulated FIRE FIBER sequence start (mode: {mode})")
            time.sleep(0.1)  # Add a small delay to simulate operation
            
            return jsonify({
                "status": "success", 
                "sequence_mode": True,
                "mode": mode,
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated FIRE FIBER sequence: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        # Start the predefined sequence
        result = servo.start_sequence()
        
        # For toggle mode, update statistics
        if mode == 'toggle' and result:
            # Count as a fire event for statistics in toggle mode
            config.increment_laser_counter()
            # We may also want to update fire time in a background task
        
        return jsonify({
            "status": "success" if result else "error", 
            "sequence_mode": True,
            "mode": mode
        })
    except Exception as e:
        logger.error(f"Error in FIRE FIBER sequence: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Statistics page routes
# Sequences routes
@app.route('/sequences')
def sequences():
    """Render the sequence programming page"""
    try:
        # Get all saved sequences
        sequences = config.get_sequences()
        return render_template('sequences.html', 
                              sequences=sequences,
                              page="sequences")
    except Exception as e:
        logger.error(f"Error loading sequences page: {e}")
        return render_template('sequences.html', 
                              sequences={},
                              error=str(e),
                              page="sequences")

@app.route('/sequences/<sequence_id>')
def get_sequence(sequence_id):
    """Get a specific sequence by ID"""
    try:
        sequence = config.get_sequence(sequence_id)
        if sequence:
            return jsonify({
                "status": "success",
                "sequence": sequence
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Sequence '{sequence_id}' not found"
            }), 404
    except Exception as e:
        logger.error(f"Error getting sequence {sequence_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/sequences/save', methods=['POST'])
def save_sequence():
    """Save a sequence"""
    try:
        data = request.json
        sequence_id = data.get('sequence_id')
        sequence_data = data.get('sequence_data')
        
        if not sequence_id or not sequence_data:
            return jsonify({
                "status": "error",
                "message": "Missing sequence ID or data"
            }), 400
            
        # Save the sequence
        result = config.save_sequence(sequence_id, sequence_data)
        
        if result:
            return jsonify({
                "status": "success",
                "message": f"Sequence '{sequence_data.get('name', 'Unnamed')}' saved successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to save sequence"
            }), 500
    except Exception as e:
        logger.error(f"Error saving sequence: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/sequences/delete/<sequence_id>', methods=['POST'])
def delete_sequence(sequence_id):
    """Delete a sequence"""
    try:
        result = config.delete_sequence(sequence_id)
        
        if result:
            return jsonify({
                "status": "success",
                "message": f"Sequence deleted successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Sequence '{sequence_id}' not found or could not be deleted"
            }), 404
    except Exception as e:
        logger.error(f"Error deleting sequence {sequence_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/sequences/run/<sequence_id>', methods=['POST'])
def run_sequence(sequence_id):
    """Run a sequence"""
    if not sequences_initialized or sequence_runner is None:
        return jsonify({
            "status": "error",
            "message": "Sequence runner not initialized"
        }), 500
    
    try:
        # Get the sequence
        sequence = config.get_sequence(sequence_id)
        if not sequence:
            return jsonify({
                "status": "error",
                "message": f"Sequence '{sequence_id}' not found"
            }), 404
        
        # Load and start the sequence
        sequence_runner.load_sequence(sequence)
        result = sequence_runner.start()
        
        if result:
            return jsonify({
                "status": "success",
                "message": f"Sequence '{sequence.get('name', 'Unnamed')}' started"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to start sequence"
            }), 500
    except Exception as e:
        logger.error(f"Error running sequence {sequence_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/sequences/pause', methods=['POST'])
def pause_sequence():
    """Pause a running sequence"""
    if not sequences_initialized or sequence_runner is None:
        return jsonify({
            "status": "error",
            "message": "Sequence runner not initialized"
        }), 500
    
    try:
        result = sequence_runner.pause()
        
        if result:
            return jsonify({
                "status": "success",
                "message": "Sequence paused"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to pause sequence"
            }), 400
    except Exception as e:
        logger.error(f"Error pausing sequence: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/sequences/resume', methods=['POST'])
def resume_sequence():
    """Resume a paused sequence"""
    if not sequences_initialized or sequence_runner is None:
        return jsonify({
            "status": "error",
            "message": "Sequence runner not initialized"
        }), 500
    
    try:
        result = sequence_runner.resume()
        
        if result:
            return jsonify({
                "status": "success",
                "message": "Sequence resumed"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to resume sequence"
            }), 400
    except Exception as e:
        logger.error(f"Error resuming sequence: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/sequences/stop', methods=['POST'])
def stop_sequence():
    """Stop a running sequence"""
    if not sequences_initialized or sequence_runner is None:
        return jsonify({
            "status": "error",
            "message": "Sequence runner not initialized"
        }), 500
    
    try:
        result = sequence_runner.stop()
        
        if result:
            return jsonify({
                "status": "success",
                "message": "Sequence stopped"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to stop sequence"
            }), 400
    except Exception as e:
        logger.error(f"Error stopping sequence: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/sequences/status')
def sequence_status():
    """Get the current status of the sequence runner"""
    if not sequences_initialized or sequence_runner is None:
        return jsonify({
            "status": "success",
            "sequence_status": {
                "status": "IDLE",
                "sequence_name": None,
                "current_step": 0,
                "total_steps": 0,
                "progress_percent": 0,
                "execution_log": []
            },
            "simulated": True
        })
    
    try:
        status = sequence_runner.get_status()
        
        return jsonify({
            "status": "success",
            "sequence_status": status
        })
    except Exception as e:
        logger.error(f"Error getting sequence status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/statistics')
def statistics():
    """Render the statistics page"""
    # Get current statistics
    stats = config.get_statistics()
    
    # Get the threshold value from config
    timing_config = config.get_timing_config()
    laser_fire_threshold = timing_config.get('laser_fire_threshold', 2000)
    
    # Format the total time for display
    total_time_ms = stats.get('laser_fire_time', 0)
    total_seconds = total_time_ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    total_time_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    # Get current time for log
    from datetime import datetime
    now = datetime.now()
    
    return render_template('statistics.html',
                          stats=stats,
                          laser_fire_threshold=laser_fire_threshold,
                          total_time_formatted=total_time_formatted,
                          now=now,
                          page="statistics")

@app.route('/statistics/data')
def get_statistics_data():
    """Get current statistics data for AJAX updates"""
    # Get current statistics
    stats = config.get_statistics()
    
    # Format the total time for display
    total_time_ms = stats.get('laser_fire_time', 0)
    total_seconds = total_time_ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    total_time_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    return jsonify({
        "status": "success",
        "laser_fire_count": stats.get('laser_fire_count', 0),
        "laser_fire_time": stats.get('laser_fire_time', 0),
        "total_time_formatted": total_time_formatted
    })

@app.route('/statistics/reset_counter', methods=['POST'])
def reset_counter():
    """Reset the laser fire counter"""
    try:
        # Get current statistics
        stats = config.get_statistics()
        
        # Update with counter reset
        stats['laser_fire_count'] = 0
        config.save_config({"statistics": stats})
        
        return jsonify({
            "status": "success"
        })
    except Exception as e:
        logger.error(f"Error resetting counter: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/statistics/reset_timer', methods=['POST'])
def reset_timer():
    """Reset the laser fire timer"""
    try:
        # Get current statistics
        stats = config.get_statistics()
        
        # Update with timer reset
        stats['laser_fire_time'] = 0
        config.save_config({"statistics": stats})
        
        return jsonify({
            "status": "success"
        })
    except Exception as e:
        logger.error(f"Error resetting timer: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/statistics/reset_all', methods=['POST'])
def reset_all_stats():
    """Reset all laser statistics"""
    try:
        # Reset all statistics
        config.reset_statistics()
        
        return jsonify({
            "status": "success"
        })
    except Exception as e:
        logger.error(f"Error resetting all statistics: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Servo sequence routes
@app.route('/servo/sequence', methods=['POST'])
def servo_sequence():
    """Start or stop the servo sequence"""
    if not servo_initialized or servo is None:
        # In development mode, simulate servo action without actual hardware
        try:
            enabled = request.json.get('enabled', False)
            logger.debug(f"Simulated sequence {'start' if enabled else 'stop'}")
            
            return jsonify({
                "status": "success", 
                "sequence_mode": enabled,
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated sequence action: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        enabled = request.json.get('enabled', False)
        
        if enabled:
            # Start sequence mode
            result = servo.start_sequence()
        else:
            # Stop sequence mode
            result = servo.stop_sequence()
        
        if result:
            return jsonify({
                "status": "success", 
                "sequence_mode": enabled
            })
        else:
            return jsonify({"status": "error", "message": "Failed to change sequence mode"}), 500
    except Exception as e:
        logger.error(f"Error in sequence action: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Table control routes
@app.route('/table/forward', methods=['POST'])
def table_forward():
    """Move the table forward"""
    if not outputs_initialized or output_controller is None:
        # In development mode, simulate table movement without actual hardware
        try:
            state = request.json.get('state', False)
            logger.debug(f"Simulated table forward: {'ON' if state else 'OFF'}")
            
            return jsonify({
                "status": "success", 
                "state": state,
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated table forward: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        state = request.json.get('state', False)
        result = output_controller.set_table_forward(state)
        
        return jsonify({
            "status": "success" if result else "warning",
            "state": state,
            "message": None if result else "Cannot move table (limit switch activated)"
        })
    except Exception as e:
        logger.error(f"Error in table forward: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/table/backward', methods=['POST'])
def table_backward():
    """Move the table backward"""
    if not outputs_initialized or output_controller is None:
        # In development mode, simulate table movement without actual hardware
        try:
            state = request.json.get('state', False)
            logger.debug(f"Simulated table backward: {'ON' if state else 'OFF'}")
            
            return jsonify({
                "status": "success", 
                "state": state,
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated table backward: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        state = request.json.get('state', False)
        result = output_controller.set_table_backward(state)
        
        return jsonify({
            "status": "success" if result else "warning",
            "state": state,
            "message": None if result else "Cannot move table (limit switch activated)"
        })
    except Exception as e:
        logger.error(f"Error in table backward: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/table/status')
def table_status():
    """Get the current table status"""
    if not outputs_initialized or output_controller is None:
        # In development mode, return simulated status
        return jsonify({
            "status": "success",
            "table_forward_state": False,
            "table_backward_state": False,
            "table_front_switch_state": False,
            "table_back_switch_state": False,
            "simulated": True
        })
    
    try:
        # Avoid using get_status due to lock issue
        table_forward = False
        table_backward = False
        table_front_limit = False
        table_back_limit = False
        
        # Safely access the attributes directly to avoid lock issues
        if hasattr(output_controller, 'table_moving_forward'):
            table_forward = output_controller.table_moving_forward
        if hasattr(output_controller, 'table_moving_backward'):
            table_backward = output_controller.table_moving_backward
        if hasattr(output_controller, 'table_at_front_limit'):
            table_front_limit = output_controller.table_at_front_limit
        if hasattr(output_controller, 'table_at_back_limit'):
            table_back_limit = output_controller.table_at_back_limit
            
        return jsonify({
            "status": "success",
            "table_forward_state": table_forward,
            "table_backward_state": table_backward,
            "table_front_switch_state": table_front_limit,
            "table_back_switch_state": table_back_limit
        })
    except Exception as e:
        logger.error(f"Error getting table status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Stop firing route
@app.route('/stop_fire', methods=['POST'])
def stop_fire():
    """Stop firing - move servo back to position A and stop fiber sequence"""
    global fiber_sequence_running, sequence_runner

    # Stop any running fiber sequence
    fiber_sequence_running = False
    
    if not servo_initialized or servo is None:
        # In development mode, simulate servo action without actual hardware
        try:
            logger.debug("Simulated stop fire action")
            time.sleep(0.1)  # Small delay to simulate servo movement
            
            return jsonify({
                "status": "success", 
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated stop fire action: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        # First stop any running sequences
        if 'sequence_runner' in globals() and sequence_runner:
            # Stop any running sequence (if the runner has a stop method)
            if hasattr(sequence_runner, 'stop'):
                sequence_runner.stop()
            
        # Stop sequence mode if active
        if hasattr(servo, 'stop_sequence'):
            servo.stop_sequence()
            
        # Use the dedicated stop_firing method if it exists
        if hasattr(servo, 'stop_firing'):
            result = servo.stop_firing(auto_detach=False, detach_delay=0)
        else:
            # Fallback to basic move_to_a
            result = servo.move_to_a(auto_detach=False, detach_delay=0)
        
        if result:
            logger.info("Firing stopped successfully")
            return jsonify({
                "status": "success",
                "message": "Firing stopped successfully"
            })
        else:
            logger.error("Failed to stop firing")
            return jsonify({
                "status": "error", 
                "message": "Failed to stop firing - servo may not be initialized"
            }), 500
    except Exception as e:
        logger.error(f"Error in stop fire action: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Temperature monitoring routes
@app.route('/temperature')
def temperature():
    """Render the temperature monitoring and configuration page"""
    temp_config = config.get_temperature_config()
    
    # Get current time for log
    from datetime import datetime
    now = datetime.now()
    
    return render_template('temperature.html',
                           temp_config=temp_config,
                           now=now,
                           page="temperature")

@app.route('/temperature/status')
def temperature_status():
    """Get the current temperature status from all sensors"""
    if not temp_initialized or temp_controller is None:
        # In development mode, simulate temperature readings
        try:
            # Create simulated temperature data
            import random
            from datetime import datetime
            
            # Load configuration for temperature settings
            temp_config = config.get_temperature_config()
            high_limit = temp_config.get('high_limit', 50.0)
            sensor_limits = temp_config.get('sensor_limits', {})
            
            # Get sensor-specific limits or fall back to global
            simulator1_limit = sensor_limits.get("simulator1", high_limit)
            simulator2_limit = sensor_limits.get("simulator2", high_limit)
            
            # Create simulated sensor data - reduce random variation to minimize flickering
            simulator1_temp = round(25.0 + random.uniform(-0.5, 0.8), 1)
            simulator2_temp = round(30.0 + random.uniform(-0.5, 0.8), 1)
            
            # Determine if temperatures exceed limits
            sim1_high_temp = simulator1_temp > simulator1_limit
            sim2_high_temp = simulator2_temp > simulator2_limit
            high_temp_condition = sim1_high_temp or sim2_high_temp
            
            status = {
                "status": "success",
                "sensors": {
                    "simulator1": {
                        "temperature": simulator1_temp,
                        "temp": simulator1_temp,  # Include both for compatibility
                        "last_reading": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "name": "Control Sensor",
                        "high_limit": simulator1_limit,
                        "high_temp": sim1_high_temp
                    },
                    "simulator2": {
                        "temperature": simulator2_temp,
                        "temp": simulator2_temp,  # Include both for compatibility
                        "last_reading": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "name": "Output Sensor", 
                        "high_limit": simulator2_limit,
                        "high_temp": sim2_high_temp
                    }
                },
                "high_limit": high_limit,
                "monitoring_interval": temp_config.get('monitoring_interval', 5),
                "high_temp_condition": high_temp_condition,
                "monitoring_enabled": True,
                "devices_found": 2,
                "sensor_limits": sensor_limits,
                "simulated": True,
                "primary_sensor": temp_config.get('primary_sensor', None),
                # Include temperatures field for compatibility with JS expecting that format
                "temperatures": {
                    "simulator1": {
                        "temp": simulator1_temp,
                        "last_reading": datetime.now(),
                        "name": "Control Sensor"
                    },
                    "simulator2": {
                        "temp": simulator2_temp,
                        "last_reading": datetime.now(),
                        "name": "Output Sensor"
                    }
                }
            }
            
            logger.debug("Simulated temperature status returned")
            return jsonify(status)
        except Exception as e:
            logger.error(f"Error getting simulated temperature status: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        # Get temperature status from controller
        status = temp_controller.get_status()
        
        # Add status field for consistency
        status["status"] = "success"
        
        # Ensure we have both temperatures and sensors fields for compatibility
        if 'sensors' in status and 'temperatures' not in status:
            status['temperatures'] = {}
            for sensor_id, sensor_data in status['sensors'].items():
                status['temperatures'][sensor_id] = {
                    'temp': sensor_data.get('temperature', 0),
                    'last_reading': sensor_data.get('last_reading', ''),
                    'name': sensor_data.get('name', f"Sensor {sensor_id}")
                }
        elif 'temperatures' in status and 'sensors' not in status:
            status['sensors'] = {}
            for temp_id, temp_data in status['temperatures'].items():
                status['sensors'][temp_id] = {
                    'temperature': temp_data.get('temp', 0),
                    'temp': temp_data.get('temp', 0),
                    'last_reading': temp_data.get('last_reading', ''),
                    'name': temp_data.get('name', f"Sensor {temp_id}"),
                    'high_limit': status.get('high_limit', 50.0),
                    'high_temp': False
                }
        
        logger.debug(f"Temperature status returned with {len(status.get('sensors', {}))} sensors")
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting temperature status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/temperature/update_sensor_name', methods=['POST'])
def update_sensor_name():
    """Update the name of a temperature sensor"""
    try:
        data = request.json
        
        if not data or 'sensor_id' not in data or 'name' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing sensor_id or name in request"
            }), 400
        
        sensor_id = data['sensor_id']
        name = data['name']
        
        # Validate name
        if not name or len(name) > 30:  # Set reasonable limit for name length
            return jsonify({
                "status": "error",
                "message": "Sensor name must be between 1 and 30 characters"
            }), 400
            
        # Update sensor name in configuration
        temp_config = config.get_temperature_config()
        
        # Make sure device_ids exists in the configuration
        if 'device_ids' not in temp_config:
            temp_config['device_ids'] = {}
            
        # Update the name in device_ids mapping
        temp_config['device_ids'][sensor_id] = name
        
        # Update the temperature configuration
        config.update_config('temperature', 'device_ids', temp_config['device_ids'])
        
        # Log for debugging
        logger.debug(f"Updated sensor name: {sensor_id} -> {name}, full config: {temp_config}")
        
        # Update the temperature controller if initialized
        if temp_initialized and temp_controller:
            temp_controller.update_config(temp_config)
        
        return jsonify({
            "status": "success",
            "message": f"Sensor name updated to '{name}'",
            "sensor_id": sensor_id,
            "name": name
        })
    except Exception as e:
        logger.error(f"Error updating sensor name: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/temperature/update_config', methods=['POST'])
def update_temperature_config():
    """Update temperature monitoring configuration"""
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        # Extract and validate high temperature limit
        if 'high_limit' in data:
            try:
                high_limit = float(data['high_limit'])
                if high_limit < 0 or high_limit > 100:
                    return jsonify({"status": "error", "message": "High limit must be between 0°C and 100°C"}), 400
                data['high_limit'] = high_limit
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid high limit value"}), 400
        
        # Extract and validate sampling interval (renamed to monitoring_interval for consistency)
        if 'monitoring_interval' in data:
            try:
                monitoring_interval = float(data['monitoring_interval'])
                if monitoring_interval < 1 or monitoring_interval > 60:
                    return jsonify({"status": "error", "message": "Monitoring interval must be between 1 and 60 seconds"}), 400
                data['monitoring_interval'] = monitoring_interval
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid monitoring interval value"}), 400
        
        # Extract enabled status
        if 'enabled' in data:
            data['enabled'] = bool(data['enabled'])
        
        # Extract and validate sensor-specific limits
        if 'sensor_limits' in data and isinstance(data['sensor_limits'], dict):
            sensor_limits = {}
            for sensor_id, limit in data['sensor_limits'].items():
                try:
                    limit_val = float(limit)
                    if limit_val < 0 or limit_val > 100:
                        return jsonify({"status": "error", "message": f"Sensor limit for {sensor_id} must be between 0°C and 100°C"}), 400
                    sensor_limits[sensor_id] = limit_val
                except ValueError:
                    return jsonify({"status": "error", "message": f"Invalid sensor limit value for {sensor_id}"}), 400
            data['sensor_limits'] = sensor_limits
            
        # Extract and validate GPIO pin for 1-Wire
        if 'w1_gpio_pin' in data:
            try:
                w1_gpio_pin = int(data['w1_gpio_pin'])
                # Validate if it's a reasonable GPIO pin number for Raspberry Pi
                valid_gpio_pins = [2, 4, 17, 27]  # Commonly used GPIO pins for 1-Wire
                if w1_gpio_pin not in valid_gpio_pins:
                    return jsonify({"status": "error", "message": f"Invalid GPIO pin for 1-Wire. Valid options are: {valid_gpio_pins}"}), 400
                data['w1_gpio_pin'] = w1_gpio_pin
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid GPIO pin value for 1-Wire"}), 400
                
        # Handle primary sensor selection
        if 'primary_sensor' in data:
            primary_sensor = data['primary_sensor']
            if primary_sensor == "":
                # Allow clearing the primary sensor
                data['primary_sensor'] = None
            elif primary_sensor and not isinstance(primary_sensor, str):
                return jsonify({"status": "error", "message": "Invalid primary sensor value"}), 400
        
        # Update the configuration in config.py
        for key, value in data.items():
            config.update_config('temperature', key, value)
        
        # Update the temperature controller configuration if initialized
        if temp_initialized and temp_controller:
            temp_controller.update_config(data)
        
        return jsonify({
            "status": "success",
            "message": "Temperature configuration updated",
            "config": config.get_temperature_config()
        })
    except Exception as e:
        logger.error(f"Error updating temperature configuration: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# API routes for output controls are already defined elsewhere

# Make global variables available to all templates
@app.context_processor
def inject_globals():
    # Get temperature data
    temp_status = {}
    if temp_initialized and temp_controller:
        try:
            temp_status = temp_controller.get_status()
        except Exception as e:
            logger.error(f"Error getting temperature status: {e}")
    
    # Check if sensors have been found (to hide hardware warning)
    sensors_found = False
    if temp_initialized and temp_controller and temp_status:
        sensors_found = temp_status.get('devices_found', 0) > 0
        
    return {
        'motor_initialized': motor_initialized,
        'servo_initialized': servo_initialized,
        'temp_initialized': temp_initialized,
        'temp_status': temp_status,
        'sensors_found': sensors_found
    }

@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html', error="Page not found", page="operation"), 404

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Authentication using RFID controller
        if rfid_initialized and rfid_controller:
            auth_result = rfid_controller.authenticate_user(username, password)
            if auth_result:
                # Get the user from database
                user = User.query.filter_by(username=username).first()
                if user:
                    # Login with Flask-Login
                    login_user(user)
                    flash(f'Welcome, {user.username}!', 'success')
                    return redirect(url_for('index'))
            else:
                error = 'Invalid username or password'
        else:
            # Direct database authentication if RFID controller not available
            user = User.query.filter_by(username=username, active=True).first()
            if user and user.check_password(password):
                # Login with Flask-Login
                login_user(user)
                flash(f'Welcome, {user.username}!', 'success')
                return redirect(url_for('index'))
            else:
                error = 'Invalid username or password'
    
    return render_template('login.html', page="login", error=error)

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    if rfid_initialized and rfid_controller:
        rfid_controller.logout()
    
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))
    
@app.route('/api/rfid/status')
def rfid_status():
    """Get the current RFID authentication status"""
    if rfid_initialized and rfid_controller and rfid_controller.is_authenticated():
        user = rfid_controller.get_authenticated_user()
        return jsonify({
            'authenticated': True,
            'user': user,
            'expiry': rfid_controller.auth_expiry
        })
    else:
        return jsonify({
            'authenticated': False
        })

@app.route('/api/rfid/logout', methods=['POST'])
def rfid_logout():
    """Manually log out the current RFID user"""
    if rfid_initialized and rfid_controller:
        rfid_controller.logout()
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/rfid/card', methods=['POST'])
@login_required
def register_rfid_card():
    """Register a new RFID card or update an existing one"""
    if current_user.access_level != 'admin':
        return jsonify({'error': 'Access denied. Admin rights required.'}), 403
        
    try:
        card_id = request.json.get('card_id')
        user_id = request.json.get('user_id')
        active = request.json.get('active', True)
        
        if not card_id or not user_id:
            return jsonify({'error': 'Card ID and User ID are required'}), 400
            
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        # Check if card already exists
        card = RFIDCard.query.filter_by(card_id=card_id).first()
        if card:
            # Update existing card
            card.user_id = user_id
            card.active = active
        else:
            # Create new card
            card = RFIDCard(
                card_id=card_id,
                user_id=user_id,
                active=active,
                issue_date=datetime.utcnow()
            )
            db.session.add(card)
            
        db.session.commit()
        return jsonify({'success': True, 'card_id': card_id})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error registering RFID card: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rfid/config', methods=['POST'])
@login_required
def update_rfid_config():
    """Update RFID configuration"""
    if current_user.access_level != 'admin':
        return jsonify({'error': 'Access denied. Admin rights required.'}), 403
        
    try:
        server_url = request.json.get('server_url')
        api_key = request.json.get('api_key')
        machine_id = request.json.get('machine_id')
        session_hours = request.json.get('session_hours')
        offline_mode = request.json.get('offline_mode')
        
        # Update configuration in database
        if server_url:
            config.update_config('rfid', 'server_url', server_url)
        if api_key:
            config.update_config('rfid', 'api_key', api_key)
        if machine_id:
            config.update_config('rfid', 'machine_id', machine_id)
        if session_hours:
            config.update_config('rfid', 'session_hours', int(session_hours))
        if offline_mode is not None:
            config.update_config('rfid', 'offline_mode', bool(offline_mode))
            
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating RFID config: {e}")
        return jsonify({'error': str(e)}), 500

# GPIO API routes for IO testing panel
@app.route('/api/gpio/inputs')
def get_gpio_inputs():
    """Get the current state of GPIO inputs for testing"""
    # Check if we're in prototype mode with hardware forced
    force_hardware = os.environ.get('FORCE_HARDWARE', 'False').lower() == 'true'
    
    # In prototype mode, we should use real hardware values from input_controller
    if force_hardware and inputs_initialized and input_controller:
        try:
            # Get actual hardware input values from input controller
            input_states = input_controller.get_input_states()
            
            # Map the button states to GPIO pins according to config
            gpio_config = config.get_gpio_config()
            input_data = {
                f"gpio{gpio_config['in_button_pin']}": input_states.get('in_button', False),
                f"gpio{gpio_config['out_button_pin']}": input_states.get('out_button', False),
                f"gpio{gpio_config['fire_button_pin']}": input_states.get('fire_button', False),
                f"gpio{gpio_config['servo_invert_pin']}": input_states.get('servo_invert', False),
                f"gpio{gpio_config['home_switch_pin']}": input_states.get('home_switch', False),
                f"gpio{gpio_config['table_back_limit_pin']}": input_states.get('table_back_limit', False),
                f"gpio{gpio_config['table_front_limit_pin']}": input_states.get('table_front_limit', False),
                "status": "success",
                "simulated": False
            }
            return jsonify(input_data)
        except Exception as e:
            logger.error(f"Error getting hardware GPIO input states: {e}")
            # Fall through to simulation if error occurs
    
    # Use simulation for all other modes or if input_controller is not available
    import random
    
    # Load GPIO configuration to map correct pin numbers
    gpio_config = config.get_gpio_config()
    
    return jsonify({
        "status": "success",
        f"gpio{gpio_config['in_button_pin']}": random.choice([True, False]),  # IN Button
        f"gpio{gpio_config['out_button_pin']}": random.choice([True, False]),  # OUT Button
        f"gpio{gpio_config['fire_button_pin']}": random.choice([True, False]),  # FIRE Button
        f"gpio{gpio_config['servo_invert_pin']}": random.choice([True, False]),   # Servo Invert
        f"gpio{gpio_config['home_switch_pin']}": random.choice([True, False]),  # Home Switch
        f"gpio{gpio_config['table_back_limit_pin']}": random.choice([True, False]),  # Table Back Limit
        f"gpio{gpio_config['table_front_limit_pin']}": random.choice([True, False]),  # Table Front Limit
        "simulated": True
    })

@app.route('/api/gpio/outputs', methods=['POST'])
def set_gpio_outputs():
    """Set GPIO outputs for testing"""
    # Check if we're in prototype mode with hardware forced
    force_hardware = os.environ.get('FORCE_HARDWARE', 'False').lower() == 'true'
    
    # In prototype mode with hardware forced, use actual hardware outputs
    if force_hardware and outputs_initialized and output_controller:
        try:
            device = request.json.get('device')
            state = request.json.get('state', False)
            
            # Log the state change request
            logger.info(f"Hardware output state change: {device} -> {state}")
            
            # Set the actual hardware state based on device type
            result = False
            if device == 'fan':
                result = output_controller.set_fan(state)
            elif device == 'red_lights':
                result = output_controller.set_red_lights(state)
            elif device == 'table_forward':
                result = output_controller.set_table_forward(state)
            elif device == 'table_backward':
                result = output_controller.set_table_backward(state)
            else:
                return jsonify({
                    "status": "error", 
                    "message": f"Unknown device: {device}"
                }), 400
            
            return jsonify({
                "status": "success" if result else "warning",
                "message": f"{device} set to {state}",
                "device": device,
                "state": state,
                "simulated": False
            })
        except Exception as e:
            logger.error(f"Error setting hardware GPIO output: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    # For non-prototype mode or if hardware initialization failed, use simulation
    try:
        device = request.json.get('device')
        state = request.json.get('state', False)
        
        # Log the state change request
        logger.debug(f"Simulated output state change: {device} -> {state}")
        
        # Always acknowledge the request in simulation mode
        return jsonify({
            "status": "success",
            "message": f"{device} set to {state} (simulated)",
            "device": device,
            "state": state,
            "simulated": True
        })
    except Exception as e:
        logger.error(f"Error setting simulated GPIO output: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/system/mode')
def get_system_mode():
    """Get the current system operation mode for client-side use"""
    try:
        # Get current mode from system config
        operation_mode = system_config.get('operation_mode', 'unknown')
        
        # Check if we're forcing hardware
        force_hardware = os.environ.get('FORCE_HARDWARE', 'False').lower() == 'true'
        
        return jsonify({
            "status": "success",
            "mode": operation_mode,
            "force_hardware": force_hardware
        })
    except Exception as e:
        logger.error(f"Error getting system mode: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "mode": "unknown"
        }), 500

@app.errorhandler(500)
def server_error(e):
    return render_template('index.html', error="Internal server error", page="operation"), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
