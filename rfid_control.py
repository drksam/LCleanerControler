"""
RFID controller module for MFRC522 RFID reader.
Handles card reading and authentication with ShopMachineMonitor server.
"""
import os
import logging
import time
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
        import mfrc522
        RFID_AVAILABLE = True
    except ImportError:
        logging.warning("MFRC522 module not available, RFID functionality disabled")
else:
    logging.info(f"Running in {OPERATION_MODE} mode - RFID hardware {"will be used but not required" if PROTOTYPE_MODE else "will not be used"}")

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
        
        # In simulation mode, set up a default authenticated user
        if SIMULATION_MODE:
            self._setup_simulation_user()
        # In prototype mode, RFID is optional but will be used if available
        elif PROTOTYPE_MODE:
            self._setup_prototype_mode()
        # In normal mode, initialize RFID reader if available
        elif RFID_AVAILABLE:
            self._initialize_rfid_reader()
    
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
        while self.running:
            if self.reader:
                try:
                    # Check if a card is present
                    id, text = self.reader.read_no_block()
                    if id:
                        logging.info(f"Card detected, ID: {id}")
                        self._authenticate_card(id)
                except Exception as e:
                    logging.error(f"Error reading RFID card: {e}")
            
            # Check if authentication has expired (not in simulation or prototype mode)
            if not SIMULATION_MODE and not PROTOTYPE_MODE and self.authenticated_user and time.time() > self.auth_expiry:
                logging.info("User authentication expired")
                self._logout_user()
            
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
        
        # Don't re-authenticate if already authenticated
        if self.authenticated_user:
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
                        self.authenticated_user = user_data
                        
                        # Log the access
                        self._log_access(card_id, 'login', user_data.get('user_id'))
                        
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
                from main import db
                
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
                        self.authenticated_user = user.to_dict()
                        
                        # Log the access
                        self._log_access(card_id, 'login', user.id)
                        
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
            from main import db
            
            machine_id = self.config.get('machine_id', 'laser_room_1')
            
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
```
</copilot-edited-file>  # The complete file with the suggested code changes incorporated. 
```python
"""
RFID controller module for MFRC522 RFID reader.
Handles card reading and authentication with ShopMachineMonitor server.
"""
import os
import logging
import time
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
        import mfrc522
        RFID_AVAILABLE = True
    except ImportError:
        logging.warning("MFRC522 module not available, RFID functionality disabled")
else:
    logging.info(f"Running in {OPERATION_MODE} mode - RFID hardware {"will be used but not required" if PROTOTYPE_MODE else "will not be used"}")

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
        
        # In simulation mode, set up a default authenticated user
        if SIMULATION_MODE:
            self._setup_simulation_user()
        # In prototype mode, RFID is optional but will be used if available
        elif PROTOTYPE_MODE:
            self._setup_prototype_mode()
        # In normal mode, initialize RFID reader if available
        elif RFID_AVAILABLE:
            self._initialize_rfid_reader()
    
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
        while self.running:
            if self.reader:
                try:
                    # Check if a card is present
                    id, text = self.reader.read_no_block()
                    if id:
                        logging.info(f"Card detected, ID: {id}")
                        self._authenticate_card(id)
                except Exception as e:
                    logging.error(f"Error reading RFID card: {e}")
            
            # Check if authentication has expired (not in simulation or prototype mode)
            if not SIMULATION_MODE and not PROTOTYPE_MODE and self.authenticated_user and time.time() > self.auth_expiry:
                logging.info("User authentication expired")
                self._logout_user()
            
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
        
        # Don't re-authenticate if already authenticated
        if self.authenticated_user:
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
                        self.authenticated_user = user_data
                        
                        # Log the access
                        self._log_access(card_id, 'login', user_data.get('user_id'))
                        
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
                from main import db
                
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
                        self.authenticated_user = user.to_dict()
                        
                        # Log the access
                        self._log_access(card_id, 'login', user.id)
                        
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
            from main import db
            
            machine_id = self.config.get('machine_id', 'laser_room_1')
            
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