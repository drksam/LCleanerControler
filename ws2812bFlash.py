#!/usr/bin/env python3
"""
WS2812B LED Status Indicator Interface
This script provides a simple wrapper for controlling the WS2812B LED based on login state.
"""

import logging
import threading
import time

# Try to import the controller
try:
    from ws2812b_controller import WS2812BController, LEDState
    WS2812B_AVAILABLE = True
except ImportError:
    WS2812B_AVAILABLE = False

# Initialize logger
logger = logging.getLogger(__name__)

class StatusLED:
    """Simple wrapper for WS2812B LED status indicator"""
    
    def __init__(self):
        """Initialize the status LED"""
        self.controller = None
        self.initialized = False
        self.lock = threading.RLock()
    
    def initialize(self):
        """Initialize the LED controller"""
        if not WS2812B_AVAILABLE:
            logger.warning("WS2812B controller not available - LED status disabled")
            return False
            
        with self.lock:
            if self.initialized:
                return True
                
            try:
                self.controller = WS2812BController()
                self.initialized = True
                
                # Set initial state (idle/boot)
                self.set_booting()
                
                logger.info("WS2812B status LED initialized")
                return True
                
            except Exception as e:
                logger.error(f"Failed to initialize WS2812B status LED: {e}")
                return False
    
    def close(self):
        """Clean up resources"""
        with self.lock:
            if self.controller:
                self.controller.close()
                self.controller = None
                self.initialized = False
    
    # Status setting methods
    def set_idle(self):
        """Set idle state (blue breathing)"""
        if self.controller:
            self.controller.set_state(LEDState.IDLE)
    
    def set_authorized(self):
        """Set authorized state (solid green)"""
        if self.controller:
            self.controller.set_state(LEDState.ACCESS_GRANTED)
    
    def set_denied(self):
        """Set access denied state (red flash)"""
        if self.controller:
            self.controller.set_state(LEDState.ACCESS_DENIED)
    
    def set_logout(self):
        """Set logged out state (purple blinking)"""
        if self.controller:
            self.controller.set_state(LEDState.LOGGED_OUT)
    
    def set_warning(self):
        """Set warning state (yellow blinking)"""
        if self.controller:
            self.controller.set_state(LEDState.WARNING)
    
    def set_error(self):
        """Set error state (red SOS pattern)"""
        if self.controller:
            self.controller.set_state(LEDState.ERROR)
    
    def set_booting(self):
        """Set booting state (blue rotating)"""
        if self.controller:
            self.controller.set_state(LEDState.BOOTING)
    
    def set_connecting(self):
        """Set connecting state (purple pulsing)"""
        if self.controller:
            self.controller.set_state(LEDState.CONNECTING)
    
    def set_config(self):
        """Set configuration mode (white breathing)"""
        if self.controller:
            self.controller.set_state(LEDState.CONFIG)
    
    def set_card_detected(self):
        """Set card detected state (blue flash)"""
        if self.controller:
            self.controller.set_state(LEDState.CARD_DETECTED)

# Create global instance
status_led = StatusLED()

# For testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.DEBUG, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Initialize LED
    status_led.initialize()
    
    # Test each state
    try:
        print("Testing LED states...")
        
        print("1. IDLE state (blue breathing)")
        status_led.set_idle()
        time.sleep(5)
        
        print("2. AUTHORIZED state (solid green)")
        status_led.set_authorized()
        time.sleep(5)
        
        print("3. DENIED state (red flash)")
        status_led.set_denied()
        time.sleep(5)
        
        print("4. LOGOUT state (purple blinking)")
        status_led.set_logout()
        time.sleep(5)
        
        print("5. Back to IDLE state")
        status_led.set_idle()
        time.sleep(5)
        
    finally:
        # Clean up
        status_led.close()
