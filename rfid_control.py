"""
RFID controller module for MFRC522 RFID reader.
Handles card reading and authentication with NooyenMachineMonitor server.
"""
import os
import logging
import time
import uuid
import threading
from datetime import datetime, timedelta
import requests
from config import load_config, save_config

# Check if in simulation mode
SIMULATION_MODE = os.environ.get('SIMULATION_MODE', 'False').lower() in ('true', '1', 't')

# Import the MFRC522 module (installed via pip) if not in simulation mode
RFID_AVAILABLE = False
if not SIMULATION_MODE:
    try:
        import mfrc522
        RFID_AVAILABLE = True
    except ImportError:
        logging.warning("MFRC522 module not available, RFID functionality disabled")
else:
    logging.info("Running in simulation mode - no RFID hardware will be used")

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
        
        # Initialize RFID reader if available
        if RFID_AVAILABLE:
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
                'server_url': 'https://nooyenmachinemonitor.replit.app/api/auth',
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
            
            # Check if authentication has expired
            if self.authenticated_user and time.time() > self.auth_expiry:
                logging.info("User authentication expired")
                self._logout_user()
            
            # Sleep to prevent CPU overuse
            time.sleep(0.1)
    
    def _authenticate_card(self, card_id):
        """
        Authenticate a card with the NooyenMachineMonitor server or local database
        
        Args:
            card_id: The RFID card UID
        """
        # Don't re-authenticate if already authenticated
        if self.authenticated_user:
            return
        
        # First try server authentication
        server_auth_success = False
        
        if not self.config.get('offline_mode', False):
            try:
                # Prepare authentication request
                auth_url = self.config.get('server_url', 'https://nooyenmachinemonitor.replit.app/api/auth')
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
            bool: True if a user is authenticated and not expired
        """
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