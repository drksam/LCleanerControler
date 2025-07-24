import os
import sys
import time
import logging
import threading  # <-- Added for background thread support
import uuid
import json
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import render_template, request, jsonify, redirect, url_for, flash, session, Blueprint
from flask_login import current_user, login_user, logout_user, login_required

# --- CHANGES: Use extensions.py for db and login_manager ---
from extensions import db, login_manager

# Import the configuration module
import config

# Load system configuration and operational settings
system_config = config.get_system_config()
operation_mode = system_config.get('operation_mode', 'simulation')
debug_level = system_config.get('debug_level', 'info')
bypass_safety = system_config.get('bypass_safety', False)

# DEBUG: Log the loaded config and debug level
logging.info(f"Loaded system_config: {system_config}")
logging.info(f"operation_mode: {operation_mode}")
logging.info(f"debug_level: {debug_level}")
logging.info(f"bypass_safety: {bypass_safety}")
logging.info(f"FORCE_HARDWARE: {os.environ.get('FORCE_HARDWARE')}")
logging.info(f"SIMULATION_MODE: {os.environ.get('SIMULATION_MODE')}")

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
    from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, Blueprint
    logger.info("Flask and extensions imported successfully")
except ImportError as e:
    logger.error(f"Error importing Flask or extensions: {e}")
    sys.exit(1)

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

# Load configuration
gpio_config = config.get_gpio_config()
stepper_config = config.get_stepper_config()
servo_config = config.get_servo_config()

# Initialize stepper motor with configuration
force_hardware = os.environ.get('FORCE_HARDWARE', 'False').lower() == 'true'

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

# Access control callback when user is authenticated/deauthenticated
def access_control_callback(granted, user_data):
    """Callback when a user is authenticated or deauthenticated"""
    try:
        # Import webhook integration module to avoid circular imports
        from webhook_integration import handle_login_event, handle_logout_event, handle_status_change_event
        from main import app  # Import the Flask app instance
        
        if granted:
            username = user_data.get('username', 'Unknown')
            access_level = user_data.get('access_level', 'operator')
            user_id = user_data.get('user_id', 0)
            card_id = user_data.get('card_id')
            logging.info(f"User {username} authenticated with access level {access_level}")
            # Send webhook event for user login and machine status change
            if user_id:
                try:
                    from models import User
                    user = User.query.get(user_id)
                    if user:
                        with app.app_context():
                            handle_login_event(user_id, card_id)
                            handle_status_change_event("active", {"user": username})
                        logging.info(f"Login and status change webhook events sent for user {username}")
                except Exception as e:
                    logging.error(f"Error sending login webhooks: {e}")
        else:
            reason = user_data.get('reason', 'Unknown reason')
            logging.info(f"Authentication removed: {reason}")
            # Send webhook event for user logout and machine status change
            user_id = user_data.get('user_id', 0)
            card_id = user_data.get('card_id')
            if user_id:
                try:
                    from models import User
                    user = User.query.get(user_id)
                    if user:
                        with app.app_context():
                            handle_logout_event(user_id, reason, card_id)
                            handle_status_change_event("idle", {"reason": reason})
                        logging.info(f"Logout and status change webhook events sent for user {user.username}")
                except Exception as e:
                    logging.error(f"Error sending logout webhooks: {e}")
    except Exception as e:
        logging.error(f"Error in access control callback: {e}")

controllers_initialized = False

# --- GLOBALS FOR ROUTES (ensure always defined) ---
outputs_initialized = False
output_controller = None
servo_initialized = False
servo = None
motor_initialized = False
stepper = None
sequences_initialized = False
sequence_runner = None
current_position = 0
preset_positions = {}
servo_position_a = 0
servo_position_b = 90
servo_inverted = False
rfid_initialized = False
input_controller = None
inputs_initialized = False
temp_controller = None
temp_initialized = False

def init_controllers(app=None):
    logging.info("init_controllers() called")
    global controllers_initialized
    if controllers_initialized:
        return
    controllers_initialized = True
    import os, sys, time, threading  # Removed 'logging' from here
    from functools import wraps
    import config
    from models import User, AccessLog, RFIDCard, ApiKey
    from rfid_control import RFIDController
    from stepper_control_gpioctrl import StepperMotor
    from servo_control_gpioctrl import ServoController
    from output_control_gpiod import OutputController
    from input_control_gpiod import InputController
    from sequence_runner import SequenceRunner, SequenceStatus
    from config import get_statistics, increment_laser_counter, add_laser_fire_time, reset_statistics
    from temperature_control import TemperatureController
    # All global variables used in routes
    global system_config, operation_mode, debug_level, bypass_safety, log_level, logger
    global gpio_config, stepper_config, servo_config, force_hardware
    global stepper, motor_initialized, servo, servo_initialized
    global output_controller, outputs_initialized, input_controller, inputs_initialized
    global rfid_controller, rfid_initialized, temp_controller, temp_initialized
    global sequence_runner, sequences_initialized
    global current_position, preset_positions
    global servo_position_a, servo_position_b, servo_inverted
    # ...existing code for system_config, operation_mode, debug_level, bypass_safety, log_level, logging.basicConfig, logger...
    # ...existing code for environment variables and FORCE_HARDWARE...
    # ...existing code for controller initializations, callbacks, and background thread startup...
    # For any use of 'app', use the passed-in app argument, not a global
    # For example, in stop_all_operations, use app.logger.warning(...)
    # If app is None, skip app-context-dependent code

    # --- Begin hardware controller initialization ---
    try:
        output_controller = OutputController()
        outputs_initialized = True
        logging.info("OutputController initialized successfully")
    except Exception as e:
        outputs_initialized = False
        logging.error(f"Failed to initialize OutputController: {e}")

    try:
        servo = ServoController()
        servo_initialized = True
        logging.info("ServoController initialized successfully")
    except Exception as e:
        servo_initialized = False
        logging.error(f"Failed to initialize ServoController: {e}")

    try:
        stepper = StepperMotor()
        motor_initialized = True
        logging.info("StepperMotor initialized successfully")
    except Exception as e:
        motor_initialized = False
        logging.error(f"Failed to initialize StepperMotor: {e}")

    try:
        input_controller = InputController()
        inputs_initialized = True
        logging.info("InputController initialized successfully")
    except Exception as e:
        inputs_initialized = False
        logging.error(f"Failed to initialize InputController: {e}")

    # Initialize temperature controller
    try:
        from config import get_temperature_config
        temp_config = get_temperature_config()
        temp_controller = TemperatureController(temp_config=temp_config)
        temp_initialized = True
        logging.info("TemperatureController initialized successfully")
    except Exception as e:
        temp_initialized = False
        logging.error(f"Failed to initialize TemperatureController: {e}")
    # --- End hardware controller initialization ---

# --- Add background thread for automatic fan/lights update logic ---
def start_output_update_thread():
    """Start a background thread to regularly call output_controller.update() for auto fan/lights logic."""
    def update_loop():
        while True:
            try:
                # Only run if outputs are initialized
                if outputs_initialized and output_controller is not None:
                    # Get current servo position (if available)
                    servo_angle = None
                    if servo_initialized and servo is not None:
                        try:
                            status = servo.get_status()
                            servo_angle = status.get('current_angle', 0)
                        except Exception:
                            servo_angle = 0
                    else:
                        servo_angle = 0
                    # Use 0 as fallback for normal_position
                    output_controller.update(servo_angle, 0)
            except Exception as e:
                logging.error(f"Error in output update thread: {e}")
            time.sleep(0.5)  # Update interval (seconds)
    t = threading.Thread(target=update_loop, daemon=True)
    t.start()

# Start the update thread after controllers are initialized
init_controllers()
start_output_update_thread()

# Only define blueprint and routes at the top level
main_bp = Blueprint('main_bp', __name__)

@main_bp.route('/')
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

@main_bp.route('/cleaning_head')
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

@main_bp.route('/trigger_servo')
def trigger_servo():
    """Render the trigger servo setup page"""
    timing_config = config.get_timing_config()
    return render_template('trigger_servo.html', 
                           servo_initialized=servo_initialized,
                           servo_position_a=servo_position_a,
                           servo_position_b=servo_position_b,
                           servo_inverted=servo_inverted,
                           fan_off_delay=timing_config.get('fan_off_delay', 600000),
                           red_lights_off_delay=timing_config.get('red_lights_off_delay', 60000),
                           page="trigger_servo")

@main_bp.route('/table')
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

@main_bp.route('/settings')
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

@main_bp.route('/pinout')
@require_admin_in_normal_mode
def pinout():
    """Render the GPIO pinout guide page"""
    gpio_config = config.get_gpio_config()
    system_config = config.get_system_config()  # Get system config for operation mode
    return render_template('pinout.html', page="pinout", gpio_config=gpio_config, system_config=system_config)

@main_bp.route('/rfid')
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

@main_bp.route('/jog', methods=['POST'])
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
        
        # Start jog operation asynchronously - don't wait for completion
        try:
            result = stepper.jog(direction_int, steps)
        except Exception as jog_error:
            logger.error(f"Jog command failed: {jog_error}")
            # Still try to get position even if jog failed
            try:
                current_position = stepper.get_position()
            except:
                pass
            return jsonify({
                "status": "error", 
                "message": f"Jog command failed: {str(jog_error)}",
                "position": current_position
            }), 500
        
        # Return immediately with current position (before movement)
        try:
            current_position = stepper.get_position()
        except Exception as pos_error:
            logger.warning(f"Could not get position after jog: {pos_error}")
            # Use last known position
            pass
        
        if result:
            return jsonify({
                "status": "success", 
                "position": current_position,
                "message": f"Jog {'forward' if direction_int == 1 else 'backward'} {steps} steps started"
            })
        else:
            return jsonify({"status": "error", "message": "Jog operation failed to start"}), 500
        
    except Exception as e:
        logger.error(f"Error in jog operation: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/jog_continuous', methods=['POST'])
def jog_continuous():
    """Continuous jog for hold-to-jog functionality - optimized for rapid calls"""
    global current_position
    
    if not motor_initialized or stepper is None:
        # In development mode, simulate motor movement without actual hardware
        try:
            direction = request.json.get('direction')
            steps = int(request.json.get('steps', 10))
            
            if direction == 'forward':
                # Simulate movement
                current_position += steps
            elif direction == 'backward':
                # Simulate movement
                current_position -= steps
            else:
                return jsonify({"status": "error", "message": "Invalid direction"}), 400
            
            return jsonify({
                "status": "success", 
                "position": current_position,
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in continuous jog simulation: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        direction = request.json.get('direction')
        steps = int(request.json.get('steps', 10))
        
        # Load current configuration to get jog speed settings
        from config import load_config
        current_config = load_config()
        jog_speed = current_config['stepper'].get('jog_speed', 1000)
        acceleration = current_config['stepper'].get('acceleration', 1000)
        deceleration = current_config['stepper'].get('deceleration', 1000)
        
        # Apply speed settings to the stepper motor
        if hasattr(stepper, 'set_speed'):
            stepper.set_speed(jog_speed)
            logger.debug(f"Set jog speed to {jog_speed}")
            
        # Apply acceleration settings if supported
        if hasattr(stepper, 'set_acceleration'):
            stepper.set_acceleration(acceleration)
            logger.debug(f"Set acceleration to {acceleration}")
            
        # Apply deceleration settings if supported  
        if hasattr(stepper, 'set_deceleration'):
            stepper.set_deceleration(deceleration)
            logger.debug(f"Set deceleration to {deceleration}")
        
        # Use GPIOController jog implementation with async movement
        direction_int = 1 if direction == 'forward' else 0
        
        # Start jog operation asynchronously for continuous movement
        try:
            result = stepper.jog(direction_int, steps)
        except Exception as jog_error:
            logger.error(f"Continuous jog command failed: {jog_error}")
            # Still try to get position even if jog failed
            try:
                current_position = stepper.get_position()
            except:
                pass
            return jsonify({
                "status": "error", 
                "message": f"Continuous jog failed: {str(jog_error)}",
                "position": current_position
            }), 500
        
        if result:
            # Get updated position after jog command
            try:
                current_position = stepper.get_position()
            except Exception as pos_error:
                logger.warning(f"Could not get position after continuous jog: {pos_error}")
                # Use last known position
                pass
            return jsonify({
                "status": "success", 
                "position": current_position
            })
        else:
            return jsonify({"status": "error", "message": "Continuous jog failed"}), 500
        
    except Exception as e:
        logger.error(f"Error in continuous jog operation: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Stop the motor immediately
@main_bp.route('/stop_motor', methods=['POST'])
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

@main_bp.route('/home', methods=['POST'])
def home():
    """Home the motor (find zero position) or stop if already homing"""
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
                "message": "Homing completed (simulated)",
                "simulated": True
            })
        except Exception as e:
            logger.error(f"Error in simulated homing operation: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    try:
        # Check if stepper is currently moving (homing in progress)
        if stepper.is_moving():
            logger.info("Stopping homing operation in progress")
            stepper.stop()
            return jsonify({
                "status": "success", 
                "message": "Homing stopped",
                "position": stepper.get_position()
            })
        
        # Start homing operation
        logger.info("Starting homing operation")
        result = stepper.home(wait=False)  # Don't wait so we can respond immediately
        if result:
            current_position = 0  # Will be updated when homing completes
            return jsonify({
                "status": "success", 
                "message": "Homing started - moving backward to home switch at 33% speed",
                "position": "homing_in_progress"
            })
        else:
            return jsonify({"status": "error", "message": "Failed to start homing operation"}), 500
            
    except Exception as e:
        logger.error(f"Error in homing operation: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/move_to', methods=['POST'])
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

@main_bp.route('/enable_motor', methods=['POST'])
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

@main_bp.route('/save_position', methods=['POST'])
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
@main_bp.route('/servo/set_position_a', methods=['POST'])
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

@main_bp.route('/servo/set_position_b', methods=['POST'])
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

@main_bp.route('/settings/fan_off_delay', methods=['POST'])
def set_fan_off_delay():
    """Set the fan auto-off delay time"""
    try:
        data = request.get_json()
        delay_seconds = data.get('delay_seconds')
        
        if delay_seconds is None:
            return jsonify({"status": "error", "message": "delay_seconds is required"}), 400
        
        # Convert seconds to milliseconds and validate range
        delay_ms = int(delay_seconds) * 1000
        if delay_ms < 10000 or delay_ms > 1800000:  # 10 seconds to 30 minutes
            return jsonify({"status": "error", "message": "Delay must be between 10 and 1800 seconds"}), 400
        
        # Update the configuration
        config.update_config('timing', 'fan_off_delay', delay_ms)
        
        # Update the output controller if available
        if output_controller:
            # Reload the timing config in the output controller
            output_controller.update_timing_config()
            logger.info(f"Updated output controller timing config with fan_off_delay {delay_ms}ms")
        
        logger.info(f"Fan off delay updated to {delay_seconds} seconds ({delay_ms}ms)")
        return jsonify({
            "status": "success", 
            "delay_seconds": delay_seconds,
            "delay_ms": delay_ms
        })
    except Exception as e:
        logger.error(f"Error setting fan off delay: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/settings/red_lights_off_delay', methods=['POST'])
def set_red_lights_off_delay():
    """Set the red lights auto-off delay time"""
    try:
        data = request.get_json()
        delay_seconds = data.get('delay_seconds')
        
        if delay_seconds is None:
            return jsonify({"status": "error", "message": "delay_seconds is required"}), 400
        
        # Convert seconds to milliseconds and validate range
        delay_ms = int(delay_seconds) * 1000
        if delay_ms < 5000 or delay_ms > 300000:  # 5 seconds to 5 minutes
            return jsonify({"status": "error", "message": "Delay must be between 5 and 300 seconds"}), 400
        
        # Update the configuration
        config.update_config('timing', 'red_lights_off_delay', delay_ms)
        
        # Update the output controller if available
        if output_controller:
            # Reload the timing config in the output controller
            output_controller.update_timing_config()
            logger.info(f"Updated output controller timing config with red_lights_off_delay {delay_ms}ms")
        
        logger.info(f"Red lights off delay updated to {delay_seconds} seconds ({delay_ms}ms)")
        return jsonify({
            "status": "success", 
            "delay_seconds": delay_seconds,
            "delay_ms": delay_ms
        })
    except Exception as e:
        logger.error(f"Error setting red lights off delay: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/servo/move_to_a', methods=['POST'])
def servo_move_to_a():
    """Move servo to position A"""
    try:
        if servo_initialized and servo is not None:
            result_angle = servo.move_to_a()
            logger.info(f"Moved to position A ({servo_position_a} degrees)")
            return jsonify({
                "status": "success",
                "angle": servo_position_a
            })
        else:
            logger.debug(f"Simulated servo move to position A ({servo_position_a} degrees)")
            return jsonify({
                "status": "success",
                "angle": servo_position_a,
                "simulated": True
            })
    except Exception as e:
        logger.error(f"Error moving servo to position A: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/servo/move_to_b', methods=['POST'])
def servo_move_to_b():
    """Move servo to position B"""
    try:
        if servo_initialized and servo is not None:
            result_angle = servo.move_to_b()
            logger.info(f"Moved to position B ({servo_position_b} degrees)")
            return jsonify({
                "status": "success",
                "angle": result_angle
            })
        else:
            logger.debug(f"Simulated servo move to position B ({servo_position_b} degrees)")
            return jsonify({
                "status": "success",
                "angle": servo_position_b,
                "simulated": True
            })
    except Exception as e:
        logger.error(f"Error moving servo to position B: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/servo/move_to_angle', methods=['POST'])
def servo_move_to_angle():
    """Move servo to a specific angle"""
    try:
        data = request.get_json()
        angle = data.get('angle')
        
        if angle is None:
            return jsonify({"status": "error", "message": "angle is required"}), 400
        
        # Validate angle range
        angle = int(angle)
        if angle < 0 or angle > 180:
            return jsonify({"status": "error", "message": "Angle must be between 0 and 180 degrees"}), 400
        
        if servo_initialized and servo is not None:
            result_angle = servo.move_to_angle(angle)
            logger.info(f"Moved to angle {angle} degrees")
            return jsonify({
                "status": "success",
                "angle": result_angle
            })
        else:
            logger.debug(f"Simulated servo move to angle {angle} degrees")
            return jsonify({
                "status": "success",
                "angle": angle,
                "simulated": True
            })
    except Exception as e:
        logger.error(f"Error moving servo to angle: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/servo/detach', methods=['POST'])
def servo_detach():
    """Detach servo to prevent jitter"""
    try:
        if servo_initialized and servo is not None:
            servo.detach()
            logger.info("Servo detached")
            return jsonify({
                "status": "success",
                "message": "Servo detached"
            })
        else:
            logger.debug("Simulated servo detach")
            return jsonify({
                "status": "success",
                "message": "Servo detached (simulated)",
                "simulated": True
            })
    except Exception as e:
        logger.error(f"Error detaching servo: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/servo/reattach', methods=['POST'])
def servo_reattach():
    """Reattach servo for control"""
    try:
        if servo_initialized and servo is not None:
            servo.reattach()
            logger.info("Servo reattached")
            return jsonify({
                "status": "success",
                "message": "Servo reattached"
            })
        else:
            logger.debug("Simulated servo reattach")
            return jsonify({
                "status": "success",
                "message": "Servo reattached (simulated)",
                "simulated": True
            })
    except Exception as e:
        logger.error(f"Error reattaching servo: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/fire', methods=['POST'])
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
        
        # Use appropriate method based on mode
        if mode == 'toggle':
            result = servo.fire_toggle()
            if result.get("status") == "error":
                return jsonify(result), 500
            
            # Count laser fire event for statistics
            if result.get("status") == "active":
                config.increment_laser_counter()
            
            return jsonify({
                "status": "success",
                "position": result.get("position", "B"),
                "angle": servo_position_b,
                "mode": mode,
                "toggle_state": result.get("status"),
                "message": f"Fire toggle {result.get('status')}"
            })
        else:
            # Momentary mode - fire and hold until stop_firing is called
            success = servo.fire_momentary()
            
            if success:
                config.increment_laser_counter()
                return jsonify({
                    "status": "success", 
                    "position": "B",
                    "angle": servo_position_b,
                    "mode": mode,
                    "message": "Momentary firing initiated (hold until release)"
                })
            else:
                return jsonify({
                    "status": "error", 
                    "message": "Failed to initiate momentary firing"
                }), 500
    except Exception as e:
        logger.error(f"Error in fire action: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
        
# Fire Fiber route (starts the A-B-A-B sequence)
@main_bp.route('/fire_fiber', methods=['POST'])
def fire_fiber():
    """Trigger the fiber firing sequence (momentary or toggle)"""
    if not servo_initialized or servo is None:
        return jsonify({"status": "error", "message": "Servo not initialized", "simulated": True}), 500
    data = request.get_json() or {}
    mode = data.get('mode', 'momentary')
    try:
        if mode == 'momentary':
            success = servo.fiber_fire_momentary()
            if success:
                return jsonify({
                    "status": "success", 
                    "mode": "momentary",
                    "sequence": "A→B→A→B (holding)",
                    "message": "Fiber firing sequence initiated (hold until release)"
                })
            else:
                return jsonify({
                    "status": "error", 
                    "message": "Failed to start fiber firing sequence"
                }), 500
        elif mode == 'toggle':
            result = servo.fiber_fire_toggle()
            if result.get("status") == "error":
                return jsonify(result), 500
            
            return jsonify({
                "status": "success", 
                "mode": "toggle",
                "toggle_state": result.get("status"),
                "sequence": result.get("sequence", "unknown"),
                "message": f"Fiber toggle {result.get('status')}"
            })
        else:
            return jsonify({"status": "error", "message": "Invalid mode"}), 400
    except Exception as e:
        logger.error(f"Error in fire_fiber: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/stop_firing', methods=['POST'])
def stop_firing():
    """Stop any firing operation - moves servo back to position A"""
    if not servo_initialized or servo is None:
        return jsonify({"status": "error", "message": "Servo not initialized", "simulated": True}), 500
    try:
        success = servo.stop_firing()
        if success:
            return jsonify({
                "status": "success",
                "position": "A", 
                "angle": servo_position_a,
                "message": "Firing stopped - servo returned to position A"
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to stop firing"
            }), 500
    except Exception as e:
        logger.error(f"Error in stop_firing: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/stop_fiber', methods=['POST'])
def stop_fiber():
    """Stop the fiber firing sequence - same as stop_firing"""
    if not servo_initialized or servo is None:
        return jsonify({"status": "error", "message": "Servo not initialized", "simulated": True}), 500
    try:
        success = servo.stop_firing()  # Use the general stop method
        if success:
            return jsonify({
                "status": "success",
                "position": "A",
                "angle": servo_position_a, 
                "message": "Fiber firing stopped - servo returned to position A"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to stop fiber firing"
            }), 500
    except Exception as e:
        logger.error(f"Error in stop_fiber: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/servo_status', methods=['GET'])
def servo_status():
    """Get current servo toggle states and firing status"""
    if not servo_initialized or servo is None:
        return jsonify({"status": "error", "message": "Servo not initialized", "simulated": True}), 500
    try:
        states = servo.get_toggle_states()
        current_pos = "B" if states.get("is_firing") else "A"
        
        return jsonify({
            "status": "success",
            "toggle_states": states,
            "current_position": current_pos,
            "position_a": "A",
            "position_b": "B"
        })
    except Exception as e:
        logger.error(f"Error getting servo status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/servo/status', methods=['GET'])
def servo_status_alias():
    """Alias for servo_status route for consistency"""
    return servo_status()

# Error handlers
# Configuration update route
@main_bp.route('/update_config', methods=['POST'])
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
@main_bp.route('/index_move', methods=['POST'])
def index_move():
    """Move the stepper motor by the index distance"""
    global current_position
    
    # Get the current index distance from configuration (reload to get latest value)
    from config import load_config
    current_config = load_config()
    index_distance = current_config['stepper']['index_distance']
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
        # Apply current speed settings before the operation
        index_speed = current_config['stepper'].get('index_speed', 2000)
        acceleration = current_config['stepper'].get('acceleration', 1000)
        deceleration = current_config['stepper'].get('deceleration', 1000)
        
        # Apply speed settings to the stepper motor
        if hasattr(stepper, 'set_speed'):
            stepper.set_speed(index_speed)
            logger.debug(f"Set index speed to {index_speed}")
            
        # Apply acceleration settings if supported
        if hasattr(stepper, 'set_acceleration'):
            stepper.set_acceleration(acceleration)
            logger.debug(f"Set acceleration to {acceleration}")
            
        # Apply deceleration settings if supported  
        if hasattr(stepper, 'set_deceleration'):
            stepper.set_deceleration(deceleration)
            logger.debug(f"Set deceleration to {deceleration}")
        
        # Use GPIOController move_index implementation with direction
        direction_int = 1 if direction == 'forward' else -1
        
        try:
            result = stepper.move_index(direction_int)
        except Exception as index_error:
            logger.error(f"Index move command failed: {index_error}")
            # Still try to get position even if index move failed
            try:
                current_position = stepper.get_position()
            except:
                pass
            return jsonify({
                "status": "error", 
                "message": f"Index move failed: {str(index_error)}",
                "position": current_position
            }), 500
        
        if result:
            try:
                current_position = stepper.get_position()
                logger.info(f"Index moved {direction} to position {current_position}")
            except Exception as pos_error:
                logger.warning(f"Could not get position after index move: {pos_error}")
                # Use last known position
                pass
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
@main_bp.route('/fan/status', methods=['GET'])
def get_fan_status():
    """Get the current fan status"""
    global outputs_initialized, output_controller
    if not outputs_initialized or output_controller is None:
        # In development mode, simulate fan status
        return jsonify({
            "status": "success", 
            "fan_state": False,
            "fan_mode": "manual",
            "simulated": True
        })
    
    try:
        # Avoid using get_status due to lock issue
        fan_state = False
        time_remaining = 0
        
        # Safely access the attributes directly to avoid lock issues
        if hasattr(output_controller, 'fan_on'):
            fan_state = output_controller.fan_on
        
        # Get current fan mode
        fan_mode = "manual"  # default
        if hasattr(output_controller, 'fan_mode'):
            fan_mode = output_controller.fan_mode
            
        return jsonify({
            "status": "success",
            "fan_state": fan_state,
            "fan_mode": fan_mode,
            "time_remaining": time_remaining
        })
    except Exception as e:
        logger.error(f"Error getting fan status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/fan/set', methods=['POST'])
def set_fan():
    """Set the fan state and mode (manual/auto)"""
    global outputs_initialized, output_controller
    logger.info(f"Fan set endpoint called with data: {request.json}")
    
    if not outputs_initialized or output_controller is None:
        # In development mode, simulate fan control
        state = request.json.get('state', False)
        mode = request.json.get('mode', 'manual')
        logger.info(f"Simulated fan control: state={state}, mode={mode}")
        return jsonify({
            "status": "success", 
            "fan_state": state,
            "fan_mode": mode,
            "simulated": True
        })
    
    try:
        state = request.json.get('state')
        mode = request.json.get('mode', 'manual')
        
        logger.info(f"Setting fan - state: {state}, mode: {mode}")
        
        if mode == 'auto':
            # Set fan to auto mode
            if hasattr(output_controller, 'set_fan_mode'):
                output_controller.set_fan_mode('auto')
                logger.info("Fan mode set to auto")
            current_state = output_controller.fan_on
        else:
            # Manual mode - set specific state
            if hasattr(output_controller, 'set_fan_mode'):
                output_controller.set_fan_mode('manual')
                logger.info("Fan mode set to manual")
            if state is not None:
                output_controller.set_fan(state)
                logger.info(f"Fan state set to {state}")
                current_state = state
            else:
                current_state = output_controller.fan_on
        
        return jsonify({
            "status": "success",
            "fan_state": current_state,
            "fan_mode": mode
        })
    except Exception as e:
        logger.error(f"Error setting fan state/mode: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Red lights control routes
@main_bp.route('/lights/status', methods=['GET'])
def get_lights_status():
    """Get the current red lights status"""
    global outputs_initialized, output_controller
    if not outputs_initialized or output_controller is None:
        # In development mode, simulate lights status
        return jsonify({
            "status": "success", 
            "lights_state": False,
            "lights_mode": "manual",
            "simulated": True
        })
    
    try:
        # Avoid using get_status due to lock issue
        lights_state = False
        time_remaining = 0
        
        # Safely access the attributes directly to avoid lock issues
        if hasattr(output_controller, 'red_lights_on'):
            lights_state = output_controller.red_lights_on
        
        # Get current lights mode
        lights_mode = "manual"  # default
        if hasattr(output_controller, 'lights_mode'):
            lights_mode = output_controller.lights_mode
            
        return jsonify({
            "status": "success",
            "lights_state": lights_state,
            "lights_mode": lights_mode,
            "time_remaining": time_remaining
        })
    except Exception as e:
        logger.error(f"Error getting lights status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/lights/set', methods=['POST'])
def set_lights():
    """Set the red lights state and mode (manual/auto)"""
    global outputs_initialized, output_controller
    logger.info(f"Lights set endpoint called with data: {request.json}")
    
    if not outputs_initialized or output_controller is None:
        # In development mode, simulate lights control
        state = request.json.get('state', False)
        mode = request.json.get('mode', 'manual')
        logger.info(f"Simulated lights control: state={state}, mode={mode}")
        return jsonify({
            "status": "success", 
            "lights_state": state,
            "lights_mode": mode,
            "simulated": True
        })
    
    try:
        state = request.json.get('state')
        mode = request.json.get('mode', 'manual')
        
        logger.info(f"Setting lights - state: {state}, mode: {mode}")
        
        if mode == 'auto':
            # Set lights to auto mode
            if hasattr(output_controller, 'set_lights_mode'):
                output_controller.set_lights_mode('auto')
                logger.info("Lights mode set to auto")
            current_state = output_controller.red_lights_on
        else:
            # Manual mode - set specific state
            if hasattr(output_controller, 'set_lights_mode'):
                output_controller.set_lights_mode('manual')
                logger.info("Lights mode set to manual")
            if state is not None:
                output_controller.set_red_lights(state)
                logger.info(f"Lights state set to {state}")
                current_state = state
            else:
                current_state = output_controller.red_lights_on
        
        return jsonify({
            "status": "success",
            "lights_state": current_state,
            "lights_mode": mode
        })
    except Exception as e:
        logger.error(f"Error setting lights state/mode: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
        
        return jsonify({
            "status": "success",
            "lights_state": state
        })
    except Exception as e:
        logger.error(f"Error setting lights state: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Statistics page routes
# Sequences routes
@main_bp.route('/sequences')
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

@main_bp.route('/sequences/<sequence_id>')
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
                "message": f"Sequence {sequence_id} not found"
            }), 404
    except Exception as e:
        logger.error(f"Error getting sequence {sequence_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/sequences/save', methods=['POST'])
def save_sequence():
    """Save a sequence"""
    try:
        data = request.json
        sequence_id = data.get('sequence_id')
        sequence_data = data.get('sequence_data')
        
        if not sequence_id or not sequence_data:
            return jsonify({
                "status": "error",
                "message": "Missing sequence_id or sequence_data"
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

@main_bp.route('/sequences/delete/<sequence_id>', methods=['POST'])
def delete_sequence(sequence_id):
    """Delete a sequence"""
    try:
        result = config.delete_sequence(sequence_id)
        if result:
            return jsonify({
                "status": "success",
                "message": f"Sequence {sequence_id} deleted successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Failed to delete sequence {sequence_id}"
            }), 500
    except Exception as e:
        logger.error(f"Error deleting sequence {sequence_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/sequences/run/<sequence_id>', methods=['POST'])
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
                "message": f"Sequence {sequence_id} not found"
            }), 404
        # Load and start the sequence
        sequence_runner.load_sequence(sequence)
        result = sequence_runner.start()
        if result:
            return jsonify({
                "status": "success",
                "message": f"Sequence {sequence_id} started"
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Failed to start sequence {sequence_id}"
            }), 500
    except Exception as e:
        logger.error(f"Error running sequence {sequence_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/sequences/pause', methods=['POST'])
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
            }), 500
    except Exception as e:
        logger.error(f"Error pausing sequence: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/sequences/resume', methods=['POST'])
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
            }), 500
    except Exception as e:
        logger.error(f"Error resuming sequence: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/sequences/stop', methods=['POST'])
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
            }), 500
    except Exception as e:
        logger.error(f"Error stopping sequence: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/sequences/status')
def sequence_status():
    """Get the current status of the sequence runner"""
    if not sequences_initialized or sequence_runner is None:
        return jsonify({
            "status": "error",
            "message": "Sequence runner not initialized"
        }), 500
    try:
        status = sequence_runner.get_status()
        return jsonify({
            "status": "success",
            "sequence_status": status
        })
    except Exception as e:
        logger.error(f"Error getting sequence status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/statistics')
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
    now = datetime.now()
    return render_template('statistics.html',
                          stats=stats,
                          laser_fire_threshold=laser_fire_threshold,
                          total_time_formatted=total_time_formatted,
                          now=now,
                          page="statistics")

@main_bp.route('/statistics/data')
def get_statistics_data():
    """Get statistics data as JSON"""
    try:
        stats = config.get_statistics()
        
        # Return the stats data directly at the top level for JavaScript compatibility
        return jsonify({
            "status": "success",
            "laser_fire_count": stats.get('laser_fire_count', 0),
            "total_laser_fire_time": stats.get('total_laser_fire_time', 0)
        })
    except Exception as e:
        logger.error(f"Error getting statistics data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/statistics/reset_counter', methods=['POST'])
def reset_counter():
    """Reset the laser fire counter"""
    try:
        config.reset_statistics('counter')
        return jsonify({
            "status": "success",
            "message": "Laser fire counter reset"
        })
    except Exception as e:
        logger.error(f"Error resetting counter: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/statistics/reset_timer', methods=['POST'])
def reset_timer():
    """Reset the laser fire timer"""
    try:
        config.reset_statistics('timer')
        return jsonify({
            "status": "success",
            "message": "Laser fire timer reset"
        })
    except Exception as e:
        logger.error(f"Error resetting timer: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/statistics/reset_all', methods=['POST'])
def reset_all_stats():
    """Reset all statistics"""
    try:
        config.reset_statistics('all')
        return jsonify({
            "status": "success",
            "message": "All statistics reset"
        })
    except Exception as e:
        logger.error(f"Error resetting all statistics: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Servo sequence routes
@main_bp.route('/servo/sequence', methods=['POST'])
def servo_sequence():
    """Start a custom servo sequence"""
    if not servo_initialized or servo is None:
        return jsonify({
            "status": "error",
            "message": "Servo not initialized"
        }), 500
    try:
        data = request.json or {}
        sequence = data.get('sequence')
        if not sequence:
            return jsonify({
                "status": "error",
                "message": "No sequence provided"
            }), 400
        result = servo.run_custom_sequence(sequence)
        if result:
            return jsonify({
                "status": "success",
                "message": "Servo sequence started"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to start servo sequence"
            }), 500
    except Exception as e:
        logger.error(f"Error running servo sequence: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Table control routes
@main_bp.route('/table/forward', methods=['POST'])
def table_forward():
    """Move the table forward or stop forward movement"""
    logger.info("table_forward route called")
    if not outputs_initialized or output_controller is None:
        logger.error("table_forward: Output controller not initialized")
        return jsonify({
            "status": "error",
            "message": "Output controller not initialized"
        }), 500
    try:
        # Get state from request data (true = start, false = stop)
        data = request.get_json() or {}
        state = data.get('state', True)  # Default to True for backwards compatibility
        logger.info(f"table_forward: calling output_controller.set_table_forward({state})")
        
        output_controller.set_table_forward(state)
        logger.info(f"table_forward: set_table_forward completed successfully")
        action = "moving forward" if state else "stopped forward"
        response = jsonify({
            "status": "success",
            "message": f"Table {action}"
        })
        logger.info(f"table_forward: returning response")
        return response
    except Exception as e:
        logger.error(f"Error controlling table forward: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/table/backward', methods=['POST'])
def table_backward():
    """Move the table backward or stop backward movement"""
    if not outputs_initialized or output_controller is None:
        return jsonify({
            "status": "error",
            "message": "Output controller not initialized"
        }), 500
    try:
        # Get state from request data (true = start, false = stop)
        data = request.get_json() or {}
        state = data.get('state', True)  # Default to True for backwards compatibility
        
        output_controller.set_table_backward(state)
        action = "moving backward" if state else "stopped backward"
        return jsonify({
            "status": "success",
            "message": f"Table {action}"
        })
    except Exception as e:
        logger.error(f"Error moving table backward: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/table/status', methods=['GET'])
def table_status():
    """Get the current table status"""
    if not outputs_initialized or output_controller is None:
        return jsonify({
            "status": "error",
            "message": "Output controller not initialized"
        }), 500
    try:
        return jsonify({
            "status": "success",
            "table_moving_forward": output_controller.table_moving_forward,
            "table_moving_backward": output_controller.table_moving_backward,
            "table_at_front_limit": output_controller.table_at_front_limit,
            "table_at_back_limit": output_controller.table_at_back_limit
        })
    except Exception as e:
        logger.error(f"Error getting table status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Temperature monitoring routes
@main_bp.route('/temperature')
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

@main_bp.route('/temperature/status')
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
        # Get temperature status from controller (with forced update)
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

@main_bp.route('/temperature/diagnose', methods=['POST'])
def temperature_diagnose():
    """Diagnose temperature sensor issues"""
    try:
        if not temp_initialized or temp_controller is None:
            return jsonify({
                "status": "error", 
                "message": "Temperature controller not initialized"
            }), 500
            
        # Run the diagnosis
        result = temp_controller.diagnose_sensors()
        
        return jsonify({
            "status": "success",
            "message": "Sensor diagnosis completed. Check logs for details.",
            "result": result
        })
    except Exception as e:
        logger.error(f"Error during temperature sensor diagnosis: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/temperature/update_sensor_name', methods=['POST'])
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

@main_bp.route('/temperature/update_config', methods=['POST'])
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
@main_bp.app_context_processor
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

@main_bp.errorhandler(404)
def page_not_found(e):
    return render_template('index.html', error="Page not found", page="operation"), 404

@main_bp.errorhandler(500)
def server_error(e):
    return render_template('index.html', error="Internal server error", page="operation"), 500

@main_bp.route('/login', methods=['GET', 'POST'])
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

@main_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    if rfid_initialized and rfid_controller:
        rfid_controller.logout()
    
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))
    
@main_bp.route('/api/rfid/status')
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

@main_bp.route('/api/rfid/logout', methods=['POST'])
def rfid_logout():
    """Manually log out the current RFID user"""
    if rfid_initialized and rfid_controller:
        rfid_controller.logout()
        return jsonify({'success': True})
    return jsonify({'success': False})

@main_bp.route('/api/rfid/card', methods=['POST'])
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

@main_bp.route('/api/rfid/config', methods=['POST'])
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
@main_bp.route('/api/gpio/inputs')
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

@main_bp.route('/api/gpio/outputs', methods=['POST'])
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

@main_bp.route('/api/system/mode')
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

# Emergency Stop (E-Stop) route
@main_bp.route('/estop', methods=['POST'])
def emergency_stop():
    """Emergency stop: immediately stop all outputs (fan, lights, table, etc.)"""
    if not outputs_initialized or output_controller is None:
        return jsonify({
            "status": "success",
            "message": "E-Stop simulated (no hardware)"
        })
    try:
        # Always move servo to position A before stopping outputs
        if servo_initialized and servo is not None:
            output_controller.stop_all_outputs(servo=servo)
        else:
            output_controller.stop_all_outputs()
        return jsonify({
            "status": "success",
            "message": "All outputs stopped by E-Stop"
        })
    except Exception as e:
        logger.error(f"Error in E-Stop: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
