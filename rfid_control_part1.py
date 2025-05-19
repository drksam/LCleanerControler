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
