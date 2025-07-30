"""
RFID controller module for MFRC522 RFID reader.
Handles card reading and authentication with ShopMachineMonitor server.
"""
import os
import time
import logging
import uuid
import threading
from datetime import datetime, timedelta
import requests
from config import load_config, save_config

# Check operating mode from system configuration
system_config = load_config().get('system', {})
OPERATION_MODE = system_config.get('operation_mode', 'normal')

# Check if in simulation mode
SIMULATION_MODE = os.environ.get('SIMULATION_MODE', 'False').lower() in ('true', '1', 't') or OPERATION_MODE == 'simulation'
PROTOTYPE_MODE = OPERATION_MODE == 'prototype'

# Import the MFRC522 module (installed via pip) if not in simulation mode
RFID_AVAILABLE = False
if not SIMULATION_MODE and not PROTOTYPE_MODE:
    try:
        # Try Pi 5 compatible wrapper first
        from mfrc522_pi5 import SimpleMFRC522
        mfrc522 = type('mfrc522', (), {'SimpleMFRC522': SimpleMFRC522})
        RFID_AVAILABLE = True
        logging.info("Using Pi 5 compatible RFID library")
    except ImportError:
        try:
            # Fallback to original library
            import mfrc522
            RFID_AVAILABLE = True
            logging.info("Using standard RFID library")
        except ImportError:
            logging.warning("MFRC522 module not available, RFID functionality disabled")
else:
    status_msg = "will be used but not required" if PROTOTYPE_MODE else "will not be used"
    logging.info(f"Running in {OPERATION_MODE} mode - RFID hardware {status_msg}")

logger = logging.getLogger(__name__)

class RFIDController:
    """Controller for RFID reader and authentication"""
    
    def __init__(self, access_callback=None):
        """
        Initialize the RFID controller
        
        Args:
            access_callback: Callback function when access granted/denied
                Signature: access_callback(granted, user_data)
        """
        self.config = self._get_rfid_config()
        self.access_callback = access_callback
        self.reader = None
        self.authenticated_user = None
        self.auth_expiry = 0
        self.running = False
        self.reader_thread = None
        self.operation_mode = OPERATION_MODE
        
        # Add debouncing to prevent rapid multiple scans of same card
        self.last_card_id = None
        self.last_scan_time = 0
        self.scan_cooldown = 2.0  # 2 seconds between scans of same card
        
        # Track authentication timing for login detection
        self.last_auth_time = 0
        self.login_consumed = False  # Flag to track if authentication was used for login
        self.current_session_id = None  # Track current user session ID (not the object itself)
        
        # In simulation mode, set up a default authenticated user
        if SIMULATION_MODE:
            self._setup_simulation_user()
        # In prototype mode, RFID is optional but will be used if available
        elif PROTOTYPE_MODE:
            self._setup_prototype_mode()
        # In normal mode, initialize RFID reader if available
        elif RFID_AVAILABLE:
            self._initialize_rfid_reader()
    
    @property
    def current_session(self):
        """Backward compatibility property - returns session object or None"""
        if self.current_session_id:
            try:
                from models import UserSession
                from main import app, db
                with app.app_context():
                    return db.session.query(UserSession).filter_by(id=self.current_session_id).first()
            except:
                return None
        return None
    
    def _setup_simulation_user(self):
        """Set up a default authenticated user in simulation mode"""
        # Always authenticated in simulation mode
        self.authenticated_user = {
            'user_id': 999,
            'username': 'SimulationUser',
            'access_level': 'admin',
            'name': 'Simulation User'
        }
        # Set a long expiry time
        self.auth_expiry = time.time() + (24 * 3600)  # 24 hours
        logging.info("Simulation mode: automatic authentication enabled")
        
        # Call the access callback to notify about simulation authentication
        if self.access_callback:
            self.access_callback(True, self.authenticated_user)
    
    def _create_user_session(self, user_data, login_method='rfid', switched_from_user_id=None):
        """Create a new user session and close any existing one"""
        try:
            from models import UserSession, User
            from main import app, db
            from flask_login import login_user
            
            with app.app_context():
                # Close current session if exists
                if self.current_session_id:
                    self._close_user_session()
                
                # Create new session
                session = UserSession(
                    user_id=user_data.get('user_id'),
                    login_time=datetime.now(),  # Use local time instead of UTC
                    login_method=login_method,
                    switched_from_user_id=switched_from_user_id,
                    machine_id=self.config.get('machine_id', 'laser_room_1'),
                    card_id=user_data.get('card_id')
                )
                
                db.session.add(session)
                db.session.commit()
                
                self.current_session_id = session.id  # Store session ID instead of the object
                
                # Update Flask-Login current_user for auto-switch and RFID logins
                if login_method in ['auto_switch', 'rfid']:
                    user = User.query.get(user_data.get('user_id'))
                    if user:
                        login_user(user, remember=False)
                        logging.info(f"Updated Flask-Login session for {user.username} via {login_method}")
                
                logging.info(f"Created new user session for {user_data.get('username')} (ID: {session.id})")
                
        except Exception as e:
            logging.error(f"Error creating user session: {e}")
    
    def _close_user_session(self):
        """Close the current user session"""
        try:
            from models import UserSession
            from main import app, db
            
            if not self.current_session_id:
                return
                
            with app.app_context():
                # Get session ID from current session
                session_id = self.current_session_id
                
                # Query for a fresh session object to avoid detached instance issues
                session = db.session.query(UserSession).filter_by(id=session_id).first()
                if session:
                    session.logout_time = datetime.now()  # Use local time for consistency
                    session.calculate_performance_score()
                    db.session.commit()
                    logging.info(f"Closed user session {session.id} for {session.user.username if session.user else 'Unknown'}")
                
                self.current_session_id = None
                
        except Exception as e:
            logging.error(f"Error closing user session: {e}")
    
    def record_first_fire(self):
        """Record the first fire time for performance tracking"""
        try:
            from models import UserSession
            from main import app, db
            
            if not self.current_session_id:
                return
                
            with app.app_context():
                # Get session ID from current session
                session_id = self.current_session_id
                
                # Query for a fresh session object to avoid detached instance issues
                session = db.session.query(UserSession).filter_by(id=session_id).first()
                if session and not session.first_fire_time:
                    session.first_fire_time = datetime.now()  # Use local time for consistency
                    session.calculate_performance_score()
                    db.session.commit()
                    
                    if session.performance_score:
                        logging.info(f"First fire recorded for {session.user.username if session.user else 'Unknown'} - Performance: {session.performance_score:.2f}s")
                
        except Exception as e:
            logging.error(f"Error recording first fire: {e}")
    
    def update_session_stats(self, fire_count_increment=0, fire_time_increment_ms=0, table_cycles_increment=0):
        """Update session statistics"""
        try:
            from models import UserSession
            from main import app, db
            
            if not self.current_session_id:
                logging.warning("Cannot update session stats: no active session")
                return
                
            with app.app_context():
                # Get session ID from current session
                session_id = self.current_session_id
                
                # Query for a fresh session object to avoid detached instance issues
                session = db.session.query(UserSession).filter_by(id=session_id).first()
                if session:
                    old_count = session.session_fire_count or 0
                    old_time = session.session_fire_time_ms or 0
                    old_cycles = session.session_table_cycles or 0
                    
                    session.session_fire_count = old_count + fire_count_increment
                    session.session_fire_time_ms = old_time + fire_time_increment_ms
                    session.session_table_cycles = old_cycles + table_cycles_increment
                    
                    # Recalculate performance score if cycles are updated
                    if table_cycles_increment > 0:
                        session.calculate_performance_score()
                    
                    db.session.commit()
                    
                    logging.info(f"Session stats updated for {session.user.username if session.user else 'Unknown'}: "
                               f"fire count {old_count} → {session.session_fire_count}, "
                               f"fire time {old_time}ms → {session.session_fire_time_ms}ms, "
                               f"table cycles {old_cycles} → {session.session_table_cycles}")
                else:
                    logging.warning(f"Session {session_id} not found in database")
                
        except Exception as e:
            logging.error(f"Error updating session stats: {e}")
    
    def update_table_cycles(self, cycles_increment=1):
        """Update table cycle count for the current session"""
        self.update_session_stats(table_cycles_increment=cycles_increment)
    
    def _setup_prototype_mode(self):
        """Set up RFID behavior in prototype mode"""
        # In prototype mode, try to initialize the reader but don't require it
        try:
            if RFID_AVAILABLE:
                self._initialize_rfid_reader()
                logging.info("Prototype mode: RFID reader initialized but not required for operation")
            else:
                logging.info("Prototype mode: RFID reader not available, continuing without authentication")
                
            # In prototype mode, always have a default user for testing
            self.authenticated_user = {
                'user_id': 998,
                'username': 'PrototypeUser',
                'access_level': 'admin',
                'name': 'Prototype User'
            }
            # Set a long expiry time
            self.auth_expiry = time.time() + (24 * 3600)  # 24 hours
            
            # Call the access callback to notify about prototype mode authentication
            if self.access_callback:
                self.access_callback(True, self.authenticated_user)
        except Exception as e:
            logging.error(f"Error in prototype mode RFID setup: {e}")
            logging.info("Continuing in prototype mode without RFID functionality")
    
    def _initialize_rfid_reader(self):
        """Initialize the RFID reader hardware"""
        try:
            # Create an object of the class MFRC522
            self.reader = mfrc522.SimpleMFRC522()
            logging.info("RFID reader initialized successfully")
            
            # Start the reader thread
            self.running = True
            self.reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self.reader_thread.start()
        except Exception as e:
            logging.error(f"Error initializing RFID reader: {e}")
            self.reader = None
    
    def _get_rfid_config(self):
        """Get RFID reader configuration"""
        config = load_config()
        if 'rfid' not in config:
            # Add default RFID configuration
            config['rfid'] = {
                'server_url': 'https://Shopmachinemonitor.replit.app/api/auth',
                'api_key': '',
                'machine_id': 'laser_room_1',
                'session_hours': 8,
                'access_control_enabled': True,
                'offline_mode': True
            }
            save_config(config)
        return config.get('rfid', {})
    
    def _reader_loop(self):
        """Background thread to monitor for card reads"""
        # LED control disabled - handled by Flask app to prevent conflicts
        # Try to import status LED controller
        try:
            # from ws2812bFlash import status_led
            has_led = False  # Disabled - LED managed by Flask app
        except ImportError:
            has_led = False
            
        while self.running:
            if self.reader:
                try:
                    # Check if a card is present
                    id, text = self.reader.read_no_block()
                    if id:
                        # Debouncing: ignore rapid scans of the same card
                        current_time = time.time()
                        if (self.last_card_id == id and 
                            current_time - self.last_scan_time < self.scan_cooldown):
                            continue  # Skip this scan, too soon after last scan of same card
                        
                        self.last_card_id = id
                        self.last_scan_time = current_time
                        
                        logging.info(f"Card detected, ID: {id}")
                        
                        # Show card detection on LED - disabled (handled by Flask app)
                        if has_led:
                            pass  # status_led.set_card_detected()  # LED managed by Flask app
                            
                        # Authenticate card
                        self._authenticate_card(id)
                except Exception as e:
                    logging.error(f"Error reading RFID card: {e}")
            
            # Check if authentication has expired (not in simulation or prototype mode)
            if not SIMULATION_MODE and not PROTOTYPE_MODE and self.authenticated_user and time.time() > self.auth_expiry:
                logging.info("User authentication expired")
                self._logout_user()
                
                # Set LED back to idle - disabled (handled by Flask app)
                if has_led:
                    pass  # status_led.set_idle()  # LED managed by Flask app
            
            # Sleep to prevent CPU overuse
            time.sleep(0.1)
    
    def _authenticate_card(self, card_id):
        """
        Authenticate a card with the ShopMachineMonitor server or local database
        
        Args:
            card_id: The RFID card UID
        """
        # In simulation mode, always authenticate successfully
        if SIMULATION_MODE:
            # Already authenticated in initialization
            return True
        
        # In prototype mode, show authentication data but don't restrict access
        if PROTOTYPE_MODE:
            try:
                # Try to look up the card in the database for display purposes
                from models import User, RFIDCard
                from main import app, db
                
                # Use Flask application context for database access
                with app.app_context():
                    # Look up the card but don't restrict access
                    rfid_card = RFIDCard.query.filter_by(card_id=str(card_id)).first()
                    
                    if rfid_card and rfid_card.user:
                        user = rfid_card.user
                        # Store user data for display only
                        self.authenticated_user = {
                            'user_id': user.id,
                            'username': user.username,
                            'access_level': user.access_level,
                            'name': f"{user.first_name} {user.last_name}" if user.first_name else user.username
                        }
                        # Log the access attempt
                        self._log_access(card_id, 'login', user.id, 'Prototype mode - access not restricted')
                        logging.info(f"Prototype mode: Card recognized for user {user.username}, access not restricted")
                        
                        # Call the access callback with the user data
                        if self.access_callback:
                            self.access_callback(True, self.authenticated_user)
                    else:
                        logging.info(f"Prototype mode: Unknown card {card_id}, access not restricted")
                        # Log the access attempt
                        self._log_access(card_id, 'unrecognized_card', None, 'Prototype mode - access not restricted')
                
                return True
            except Exception as e:
                logging.error(f"Error in prototype mode card lookup: {e}")
                return True  # still allow access in prototype mode
        
        # Don't re-authenticate if already authenticated with the same card
        # But allow user switching if different card is scanned
        current_user_id = None
        if self.authenticated_user:
            current_user_id = self.authenticated_user.get('user_id')
            
        # Check if this is a different user (user switching scenario)
        switching_users = False
        new_user_data = None
        current_user_card_rescan = False
        
        # Look up the new card to see if it belongs to a different user
        try:
            from models import User, RFIDCard, UserSession
            from main import app, db
            
            with app.app_context():
                rfid_card = RFIDCard.query.filter_by(card_id=str(card_id), active=True).first()
                if rfid_card and rfid_card.user:
                    new_user_id = rfid_card.user_id
                    if current_user_id and current_user_id != new_user_id:
                        switching_users = True
                        new_user_data = {
                            'user_id': rfid_card.user.id,
                            'username': rfid_card.user.username,
                            'access_level': rfid_card.user.access_level,
                            'card_id': card_id
                        }
                        logging.info(f"User switching detected: {self.authenticated_user.get('username')} -> {rfid_card.user.username}")
                    elif current_user_id and current_user_id == new_user_id:
                        # Same user rescanned their own card
                        current_user_card_rescan = True
                        logging.debug(f"Current user {rfid_card.user.username} rescanned their own card")
        except Exception as e:
            logging.error(f"Error checking for user switching: {e}")
        
        # If same user is already authenticated and rescanned their own card, just update timing
        if self.authenticated_user and current_user_card_rescan:
            self.last_auth_time = time.time()
            self.login_consumed = False
            logging.debug(f"User {self.authenticated_user.get('username')} re-scanned card - updating timing")
            return True
        
        # Normal mode - Full authentication required
        # First try server authentication
        server_auth_success = False
        
        if not self.config.get('offline_mode', False):
            try:
                # Prepare authentication request
                auth_url = self.config.get('server_url', 'https://Shopmachinemonitor.replit.app/api/auth')
                api_key = self.config.get('api_key', '')
                machine_id = self.config.get('machine_id', 'laser_room_1')
                
                payload = {
                    'card_id': str(card_id),
                    'machine_id': machine_id,
                    'api_key': api_key
                }
                
                # Send authentication request
                response = requests.post(auth_url, json=payload, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('authorized', False):
                        user_data = data.get('user_data', {})
                        access_level = user_data.get('access_level', 'operator')
                        username = user_data.get('username', 'Unknown User')
                        
                        # Set expiry time (default 8 hours or from server)
                        expiry_hours = data.get('expiry_hours', 8)
                        self.auth_expiry = time.time() + (expiry_hours * 3600)
                        
                        # Store authenticated user
                        old_user_id = current_user_id if switching_users else None
                        self.authenticated_user = user_data
                        self.last_auth_time = time.time()
                        self.login_consumed = False
                        
                        # Create user session
                        login_method = 'auto_switch' if switching_users else 'rfid'
                        self._create_user_session(user_data, login_method, old_user_id)
                        
                        # Log the access
                        self._log_access(card_id, 'login', user_data.get('user_id'))
                        
                        if switching_users:
                            logging.info(f"User switched to {username} (level: {access_level})")
                        else:
                            logging.info(f"Access granted to {username} (level: {access_level})")
                        
                        # Call the access callback
                        if self.access_callback:
                            self.access_callback(True, user_data)
                        
                        server_auth_success = True
                    else:
                        # Authentication failed
                        reason = data.get('reason', 'Unknown reason')
                        logging.warning(f"Access denied: {reason}")
                        
                        # Log the access attempt
                        self._log_access(card_id, 'access_denied', None, f"Server denied: {reason}")
                        
                        # Call the access callback
                        if self.access_callback:
                            self.access_callback(False, {'reason': reason})
                
            except Exception as e:
                logging.error(f"Server authentication error: {e}")
                # Fall back to offline authentication
        
        # If server authentication failed or offline mode is enabled, try local authentication
        if not server_auth_success and self.config.get('offline_mode', False):
            try:
                # Import models here to avoid circular import
                from models import User, RFIDCard
                from main import app, db
                
                # Use Flask application context for database access
                with app.app_context():
                    # Look up the card in the local database
                    rfid_card = RFIDCard.query.filter_by(card_id=str(card_id), active=True).first()
                    
                    if rfid_card:
                        # Check if the card is expired
                        if rfid_card.expiry_date and rfid_card.expiry_date < datetime.utcnow():
                            reason = "Card has expired"
                            logging.warning(f"Access denied: {reason}")
                            
                            # Log the access attempt
                            self._log_access(card_id, 'access_denied', rfid_card.user_id, reason)
                            
                            # Call the access callback
                            if self.access_callback:
                                self.access_callback(False, {'reason': reason})
                                
                            return False
                        
                        # Get the user
                        user = User.query.get(rfid_card.user_id)
                        
                        if user and user.active:
                            # User is valid
                            session_hours = self.config.get('session_hours', 8)
                            self.auth_expiry = time.time() + (session_hours * 3600)
                            
                            # Store authenticated user data
                            old_user_id = current_user_id if switching_users else None
                            self.authenticated_user = user.to_dict()
                            self.last_auth_time = time.time()
                            self.login_consumed = False
                            
                            # Create user session
                            login_method = 'auto_switch' if switching_users else 'rfid'
                            user_data_with_card = self.authenticated_user.copy()
                            user_data_with_card['card_id'] = card_id
                            self._create_user_session(user_data_with_card, login_method, old_user_id)
                            
                            # Log the access
                            self._log_access(card_id, 'login', user.id)
                            
                            if switching_users:
                                logging.info(f"User switched to {user.username} (level: {user.access_level})")
                            else:
                                logging.info(f"Offline access granted to {user.username} (level: {user.access_level})")
                            
                            # Call the access callback
                            if self.access_callback:
                                self.access_callback(True, self.authenticated_user)
                                
                            return True
                        else:
                            reason = "User account is inactive"
                            logging.warning(f"Access denied: {reason}")
                            
                            # Log the access attempt
                            self._log_access(card_id, 'access_denied', rfid_card.user_id if rfid_card else None, reason)
                            
                            # Call the access callback
                            if self.access_callback:
                                self.access_callback(False, {'reason': reason})
                                
                            return False
                    else:
                        reason = "Card not found in local database"
                        logging.warning(f"Access denied: {reason}")
                        
                        # Log the access attempt
                        self._log_access(card_id, 'access_denied', None, reason)
                        
                        # Call the access callback
                        if self.access_callback:
                            self.access_callback(False, {'reason': reason})
                            
                        return False
                
            except Exception as e:
                logging.error(f"Local authentication error: {e}")
                
                # Call the access callback
                if self.access_callback:
                    self.access_callback(False, {'reason': f"Authentication error: {e}"})
                    
                return False
        
        return server_auth_success
    
    def _log_access(self, card_id, action, user_id=None, details=None):
        """
        Log an access attempt
        
        Args:
            card_id: The RFID card ID
            action: The action (login, logout, access_denied)
            user_id: The user ID (if known)
            details: Additional details about the action
        """
        try:
            # Import models here to avoid circular import
            from models import AccessLog
            from main import db, app
            
            machine_id = self.config.get('machine_id', 'laser_room_1')
            
            # Use Flask application context for database operations
            with app.app_context():
                try:
                    # Try with machine_id first (newer schema)
                    log_entry = AccessLog(
                        user_id=user_id,
                        card_id=str(card_id) if card_id else None,
                        machine_id=machine_id,
                        action=action,
                        details=details,
                        timestamp=datetime.utcnow()
                    )
                    
                    db.session.add(log_entry)
                    db.session.commit()
                    
                except Exception as schema_error:
                    # If machine_id column doesn't exist, try without it (fallback for older schema)
                    if "no column named machine_id" in str(schema_error):
                        logging.warning("AccessLog table missing machine_id column, logging without it")
                        try:
                            db.session.rollback()  # Rollback failed transaction
                            
                            # Create log entry without machine_id for older schema compatibility
                            log_entry = AccessLog(
                                user_id=user_id,
                                card_id=str(card_id) if card_id else None,
                                action=action,
                                details=details,
                                timestamp=datetime.utcnow()
                            )
                            # Don't set machine_id to avoid column error
                            
                            db.session.add(log_entry)
                            db.session.commit()
                            
                        except Exception as fallback_error:
                            logging.error(f"Failed to log access even without machine_id: {fallback_error}")
                            db.session.rollback()
                    else:
                        # Re-raise if it's a different error
                        raise schema_error
            
        except Exception as e:
            logging.error(f"Error logging access: {e}")
    
    def is_authenticated(self):
        """
        Check if a user is currently authenticated
        
        Returns:
            bool: True if a user is authenticated and not expired, or if in simulation/prototype mode
        """
        # In simulation or prototype mode, always return authenticated
        if SIMULATION_MODE or PROTOTYPE_MODE:
            return True
            
        # Normal mode - check actual authentication
        return self.authenticated_user is not None and time.time() <= self.auth_expiry
    
    def get_authenticated_user(self):
        """
        Get the currently authenticated user
        
        Returns:
            dict: User data or None if no user authenticated
        """
        if self.is_authenticated():
            return self.authenticated_user
        return None
    
    def logout(self):
        """Manually log out the current user"""
        # In simulation mode, do not actually log out
        if SIMULATION_MODE:
            logging.info("Logout request ignored in simulation mode")
            return
            
        # In prototype mode, we'll still allow logout but it won't restrict access
        if PROTOTYPE_MODE:
            logging.info("User logged out in prototype mode (will not restrict access)")
            
        self._logout_user()
    
    def _logout_user(self):
        """Internal method to log out user and clean up"""
        if self.authenticated_user:
            user_id = self.authenticated_user.get('user_id')
            username = self.authenticated_user.get('username', 'Unknown User')
            logging.info(f"User {username} logged out")
            
            # Close user session
            self._close_user_session()
            
            # Log the logout
            if user_id:
                self._log_access(None, 'logout', user_id)
            
            # In prototype mode, don't clear the authentication
            if not PROTOTYPE_MODE:
                self.authenticated_user = None
                self.auth_expiry = 0
            
            # Call the access callback
            if self.access_callback:
                self.access_callback(False, {'reason': 'Logged out'})
    
    def authenticate_user(self, username, password):
        """
        Authenticate a user with username and password (for web login)
        
        Args:
            username: The username
            password: The password
            
        Returns:
            bool: True if authentication succeeded
        """
        # In simulation mode, always return true
        if SIMULATION_MODE:
            logging.info(f"Simulation mode: automatic authentication for user {username}")
            self._setup_simulation_user()
            return True
            
        # In prototype mode, authenticate for display but don't restrict access
        if PROTOTYPE_MODE:
            try:
                # Import models here to avoid circular import
                from models import User
                
                user = User.query.filter_by(username=username).first()
                
                if user:
                    # User is valid in prototype mode regardless of password
                    self.authenticated_user = {
                        'user_id': user.id,
                        'username': user.username,
                        'access_level': user.access_level,
                        'name': f"{user.first_name} {user.last_name}" if hasattr(user, 'first_name') else user.username
                    }
                    # Log the access
                    self._log_access(None, 'login', user.id, 'Prototype mode - login without password check')
                    
                    logging.info(f"Prototype mode login for {user.username} (access level: {user.access_level})")
                    
                    # Call the access callback
                    if self.access_callback:
                        self.access_callback(True, self.authenticated_user)
                    
                    return True
                else:
                    # Create a default user in prototype mode
                    self._setup_prototype_mode()
                    return True
            except Exception as e:
                logging.error(f"Error in prototype mode login: {e}")
                # Still return true in prototype mode
                self._setup_prototype_mode()
                return True
        
        # Normal mode - standard authentication
        try:
            # Import models here to avoid circular import
            from models import User
            
            user = User.query.filter_by(username=username, active=True).first()
            
            if user and user.check_password(password):
                # User is valid
                session_hours = self.config.get('session_hours', 8)
                self.auth_expiry = time.time() + (session_hours * 3600)
                
                # Store authenticated user data
                self.authenticated_user = user.to_dict()
                self.last_auth_time = time.time()
                self.login_consumed = False
                
                # Create user session for web login
                self._create_user_session(self.authenticated_user, 'web')
                
                # Log the access
                self._log_access(None, 'login', user.id, 'Web login')
                
                logging.info(f"Web login access granted to {user.username} (level: {user.access_level})")
                
                # Call the access callback
                if self.access_callback:
                    self.access_callback(True, self.authenticated_user)
                    
                return True
            else:
                reason = "Invalid username or password"
                logging.warning(f"Web login denied: {reason}")
                
                # Log the access attempt
                self._log_access(None, 'access_denied', None, f"Web login: {reason}")
                
                # Call the access callback
                if self.access_callback:
                    self.access_callback(False, {'reason': reason})
                    
                return False
                
        except Exception as e:
            logging.error(f"Web authentication error: {e}")
            
            # Call the access callback
            if self.access_callback:
                self.access_callback(False, {'reason': f"Authentication error: {e}"})
                
            return False
    
    def cleanup(self):
        """Clean up resources and stop threads"""
        self.running = False
        if self.reader_thread:
            self.reader_thread.join(timeout=1.0)
        logging.info("RFID controller stopped")

# Create a global RFID reader instance for direct card scanning
rfid_reader = None

def initialize_rfid_reader():
    """Initialize the global RFID reader for card scanning"""
    global rfid_reader
    
    if SIMULATION_MODE or PROTOTYPE_MODE:
        logger.info("RFID reader not initialized - running in simulation/prototype mode")
        return None
        
    if not RFID_AVAILABLE:
        logger.warning("RFID reader not available - mfrc522 library not found")
        return None
        
    try:
        rfid_reader = mfrc522.SimpleMFRC522()
        logger.info("Global RFID reader initialized successfully")
        return rfid_reader
    except Exception as e:
        logger.error(f"Failed to initialize global RFID reader: {e}")
        return None

# Initialize the reader when module is imported
initialize_rfid_reader()