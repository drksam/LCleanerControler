#!/usr/bin/env python3
"""
WS2812B LED Status Controller for LCleanerControler
This module controls a WS2812B RGB LED to indicate machine status.

Status colors follow these rules:
- Blue: IDLE state (machine ready, waiting for card)
- Green: ACCESS_GRANTED (authorized user active)
- Red: ACCESS_DENIED (unauthorized card)
- Purple: LOGGED_OUT (transitioning state)
- Yellow: Warning state (before timeout)
- Red SOS pattern: Error state

Animation patterns:
- Solid: Static color display
- Breathing: Slow pulsing of a color
- Blinking: Regular on/off of a color
- Rotating: Cycling through colors
- Flash: Brief, rapid flash
- SOS: SOS pattern (3 short, 3 long, 3 short flashes)
"""
import os
import time
import logging
import threading
import json
from enum import Enum
from config import load_config, get_gpio_config

# Check operating mode and determine if we're in simulation
system_config = load_config().get('system', {})
OPERATION_MODE = system_config.get('operation_mode', 'normal')
# Only use simulation mode if explicitly set via environment variable OR if operation_mode is 'simulation'
env_simulation = os.environ.get('SIMULATION_MODE', 'False').lower() in ('true', '1', 't')
config_simulation = OPERATION_MODE == 'simulation'
SIMULATION_MODE = env_simulation or config_simulation

# Initialize logger
logger = logging.getLogger(__name__)

# Define LED states as an Enum
class LEDState(Enum):
    IDLE = "idle"               # Blue - Machine ready, waiting for card
    ACCESS_GRANTED = "granted"  # Green - Authorized user active
    ACCESS_DENIED = "denied"    # Red - Unauthorized card
    LOGGED_OUT = "logout"       # Purple - Transitioning to idle
    WARNING = "warning"         # Yellow - Warning state
    ERROR = "error"             # Red SOS - Error state
    BOOTING = "booting"         # Blue rotating - System startup
    CONNECTING = "connecting"   # Purple pulsing - Connecting
    CONFIG = "config"           # White breathing - Configuration mode
    CARD_DETECTED = "card"      # Blue flash - Card detected
    LOGIN_SCREEN = "login"      # New state for login screen display
    ADMIN_LOGGED_IN = "admin"   # Purple solid - Admin user logged in

# Define animation patterns
class AnimationPattern(Enum):
    SOLID = "solid"
    BREATHING = "breathing"
    BLINKING = "blinking"
    ROTATING = "rotating"
    FLASH = "flash"
    SOS = "sos"

class WS2812BController:
    """Controller for WS2812B RGB LED status indicator"""
    
    def __init__(self, pin=None, num_leds=1, brightness=50):
        """
        Initialize the WS2812B LED controller
        
        Args:
            pin: GPIO pin number for data line
            num_leds: Number of LEDs in the chain
            brightness: LED brightness (0-100)
        """
        # Get configuration
        self.config = load_config().get('led_status', {})
        gpio_config = get_gpio_config()
        
        # Set parameters
        self.pin = pin or gpio_config.get('esp_ws2812b_pin', 23)
        self.num_leds = num_leds or self.config.get('num_leds', 1)
        self.brightness = brightness or self.config.get('brightness', 50)
        self.enabled = self.config.get('enabled', True)
        
        # Initialize controller state
        self.simulation_mode = SIMULATION_MODE
        self.current_state = LEDState.LOGIN_SCREEN  # Start with login screen instead of idle
        self.current_animation = AnimationPattern.SOLID
        self.running = False
        self.animation_thread = None
        self._controller = None
        self.lock = threading.RLock()
        
        # Track current LED state to prevent redundant commands
        self.current_color = None
        self.current_rgb = None
        self.last_brightness = None
        
        # Track individual LED states for dual LED control
        self.led1_color = None
        self.led1_rgb = None
        self.led2_color = None
        self.led2_rgb = None
        
        # Color definitions (RGB)
        self.colors = {
            'red': (255, 0, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255),
            'yellow': (255, 255, 0),
            'purple': (128, 0, 128),
            'white': (255, 255, 255),
            'orange': (255, 165, 0),
            'off': (0, 0, 0),
            'dim_red': (50, 0, 0),  # Dim red for placement guide when logged in
        }
        
        # State to color mapping
        self.state_colors = {
            LEDState.IDLE: self.config.get('idle_color', 'blue'),
            LEDState.ACCESS_GRANTED: self.config.get('authorized_color', 'green'),
            LEDState.ACCESS_DENIED: self.config.get('denied_color', 'red'),
            LEDState.LOGGED_OUT: self.config.get('logout_color', 'purple'),
            LEDState.WARNING: self.config.get('warning_color', 'yellow'),
            LEDState.ERROR: self.config.get('error_color', 'red_sos'),
            LEDState.BOOTING: 'blue_rotating',
            LEDState.CONNECTING: 'purple_breathing',
            LEDState.CONFIG: 'white_breathing',
            LEDState.CARD_DETECTED: 'blue_flash',
            LEDState.LOGIN_SCREEN: 'blue',  # LED1 stays blue, LED2 will be white
            LEDState.ADMIN_LOGGED_IN: 'purple',  # Purple for admin users
        }
        
        # State to animation mapping
        self.state_animations = {
            LEDState.IDLE: AnimationPattern.SOLID,  # Changed from BREATHING to prevent interference
            LEDState.ACCESS_GRANTED: AnimationPattern.SOLID,
            LEDState.ACCESS_DENIED: AnimationPattern.FLASH,
            LEDState.LOGGED_OUT: AnimationPattern.BLINKING,
            LEDState.WARNING: AnimationPattern.BLINKING,
            LEDState.ERROR: AnimationPattern.SOS,
            LEDState.BOOTING: AnimationPattern.ROTATING,
            LEDState.CONNECTING: AnimationPattern.BREATHING,
            LEDState.CONFIG: AnimationPattern.BREATHING,
            LEDState.CARD_DETECTED: AnimationPattern.FLASH,
            LEDState.LOGIN_SCREEN: AnimationPattern.SOLID,
            LEDState.ADMIN_LOGGED_IN: AnimationPattern.SOLID,
        }
        
        # Dual LED behavior mapping - LED2 placement guide colors
        self.led2_placement_colors = {
            LEDState.BOOTING: 'blue',         # Same as LED1 during boot
            LEDState.IDLE: 'blue',            # Same as LED1 during idle
            LEDState.LOGIN_SCREEN: 'white',   # White when login screen is active
            LEDState.ACCESS_GRANTED: 'dim_red',   # Dim red when user is logged in
            LEDState.ADMIN_LOGGED_IN: 'dim_red',  # Dim red when admin is logged in
            LEDState.ACCESS_DENIED: 'off',    # Off during access denied
            LEDState.LOGGED_OUT: 'off',       # Off during logout
            LEDState.WARNING: 'off',          # Off during warnings
            LEDState.ERROR: 'off',            # Off during errors
            LEDState.CONNECTING: 'blue',      # Same as LED1 during connecting
            LEDState.CONFIG: 'blue',          # Same as LED1 during config
            LEDState.CARD_DETECTED: 'blue',   # Same as LED1 when card detected
        }
        
        # Initialize hardware or simulation
        self._init_hardware()
        
    def _init_hardware(self):
        """Initialize the LED hardware controller"""
        if self.simulation_mode:
            logger.info("Running in simulation mode - WS2812B LED will be simulated")
            return
            
        try:
            # Use the shared GPIO controller to prevent port conflicts
            from gpio_controller_wrapper import SharedGPIOController
            
            # Get the serial port from config
            config = load_config()
            serial_port = config.get('system', {}).get('esp32_serial_port', '/dev/ttyUSB0')
            
            # Get shared GPIOController instance
            self._controller = SharedGPIOController.get_controller(port=serial_port, simulation_mode=self.simulation_mode)
            
            if self._controller is None:
                logger.warning("SharedGPIOController not available - WS2812B LED will be simulated")
                self.simulation_mode = True
                return
            
            # Initialize WS2812B on ESP32
            self._send_cmd({"cmd": "init_ws2812b", "pin": self.pin, "num_leds": self.num_leds})
            
            # Set initial brightness
            self._set_brightness(self.brightness)
            
            logger.info(f"WS2812B LED initialized on pin {self.pin} with {self.num_leds} LEDs")
            
        except ImportError:
            logger.warning("GPIOController wrapper not available - WS2812B LED will be simulated")
            self.simulation_mode = True
        except Exception as e:
            logger.error(f"Failed to initialize WS2812B LED: {e}")
            self.simulation_mode = True
    
    def _send_cmd(self, cmd):
        """Send a command to the ESP32 controller"""
        if not self.simulation_mode and self._controller:
            with self.lock:
                try:
                    self._controller._send_cmd(cmd)
                except Exception as e:
                    logger.error(f"Failed to send command to ESP32: {e}")
    
    def _set_brightness(self, brightness):
        """Set the LED brightness (0-100)"""
        # Ensure brightness is in range
        brightness = max(0, min(100, brightness))
        self.brightness = brightness
        
        if not self.simulation_mode and self._controller:
            self._send_cmd({"cmd": "set_ws2812b_brightness", "brightness": brightness})
        
        logger.debug(f"LED brightness set to {brightness}%")
    
    def _set_color(self, color):
        """Set the LED color, only if different from current state"""
        # Handle compound color patterns (e.g., 'blue_rotating')
        if '_' in color:
            color = color.split('_')[0]
            
        # Get RGB values
        rgb = self.colors.get(color, self.colors['blue'])
        
        # Check if color has actually changed
        if self.current_color == color and self.current_rgb == rgb:
            return  # No change needed
        
        # Update state tracking
        self.current_color = color
        self.current_rgb = rgb
        
        if self.simulation_mode:
            logger.info(f"[SIMULATION] LED color set to {color} {rgb}")
            return
        
        if not self.simulation_mode and self._controller:
            # Send multiple command formats to ensure compatibility
            success = False
            
            # Try the enhanced command format first (for FastLED firmware)
            try:
                result = self._send_cmd({"cmd": "set_ws2812b_color", "r": rgb[0], "g": rgb[1], "b": rgb[2]})
                # Assume success if command was sent without exception
                success = True
                logger.debug(f"LED color set successfully via set_ws2812b_color: {color} {rgb}")
            except Exception as e:
                logger.debug(f"set_ws2812b_color command failed: {e}")
            
            # Try the direct LED command format as backup
            if not success:
                try:
                    result = self._send_cmd({
                        "cmd": "led", 
                        "subcommand": "set_color", 
                        "r": rgb[0], 
                        "g": rgb[1], 
                        "b": rgb[2], 
                        "brightness": self.brightness
                    })
                    # Assume success if command was sent without exception
                    success = True
                    logger.debug(f"LED color set successfully via led command: {color} {rgb}")
                except Exception as e:
                    logger.debug(f"led command failed: {e}")
            
            if not success:
                logger.warning(f"Failed to set LED color to {color} {rgb} - check ESP32 connection")
                # Reset tracking on failure so we retry next time
                self.current_color = None
                self.current_rgb = None
        
        logger.info(f"LED state change: {color} {rgb}")
    
    def _reset_state_tracking(self):
        """Reset state tracking to ensure next color command is sent"""
        self.current_color = None
        self.current_rgb = None
        self.last_brightness = None
        self.led1_color = None
        self.led1_rgb = None
        self.led2_color = None
        self.led2_rgb = None
    
    def _set_individual_led(self, led_index, color, brightness=None):
        """Set individual LED color, only if different from current state"""
        if not self.enabled:
            return
            
        # Handle compound color patterns (e.g., 'blue_rotating') but NOT color names like 'dim_red'
        if '_' in color and color not in self.colors:
            color = color.split('_')[0]
            
        # Get RGB values
        rgb = self.colors.get(color, self.colors['blue'])
        actual_brightness = brightness if brightness is not None else self.brightness
        
        # Check if this LED's color has actually changed
        current_led_color = self.led1_color if led_index == 0 else self.led2_color
        current_led_rgb = self.led1_rgb if led_index == 0 else self.led2_rgb
        
        if current_led_color == color and current_led_rgb == rgb:
            return  # No change needed
        
        # Update state tracking
        if led_index == 0:
            self.led1_color = color
            self.led1_rgb = rgb
        else:
            self.led2_color = color
            self.led2_rgb = rgb
        
        if self.simulation_mode:
            logger.info(f"[SIMULATION] LED {led_index} color set to {color} {rgb}")
            return
        
        if not self.simulation_mode and self._controller:
            success = False
            
            # Try the individual LED command
            try:
                result = self._send_cmd({
                    "cmd": "set_individual_led",
                    "led": led_index,
                    "r": rgb[0],
                    "g": rgb[1],
                    "b": rgb[2],
                    "brightness": actual_brightness
                })
                # Assume success if command was sent without exception
                # ESP32 may not always return "ok" but command still works
                success = True
                logger.debug(f"LED {led_index} color set successfully: {color} {rgb}")
            except Exception as e:
                logger.debug(f"Individual LED command failed: {e}")
                success = False
            
            if not success:
                logger.warning(f"Failed to set LED {led_index} color to {color} {rgb} - check ESP32 connection")
                # Reset tracking on failure so we retry next time
                if led_index == 0:
                    self.led1_color = None
                    self.led1_rgb = None
                else:
                    self.led2_color = None
                    self.led2_rgb = None
        
        logger.info(f"LED {led_index} state change: {color} {rgb}")
    
    def _send_color_command(self, rgb, brightness_factor=1.0):
        """Send color command with brightness factor, only if different from last sent"""
        if not self.enabled or self.simulation_mode:
            return
            
        # Calculate actual RGB values with brightness factor
        actual_rgb = (
            int(rgb[0] * brightness_factor),
            int(rgb[1] * brightness_factor), 
            int(rgb[2] * brightness_factor)
        )
        
        # Check if this exact command was already sent (with some tolerance for brightness)
        if (self.current_rgb and 
            abs(self.current_rgb[0] - actual_rgb[0]) < 5 and
            abs(self.current_rgb[1] - actual_rgb[1]) < 5 and
            abs(self.current_rgb[2] - actual_rgb[2]) < 5):
            return  # Skip commands that are too similar
            
        # Update state tracking
        self.current_rgb = actual_rgb
        
        if self._controller:
            try:
                self._send_cmd({
                    "cmd": "set_ws2812b_color", 
                    "r": actual_rgb[0], 
                    "g": actual_rgb[1], 
                    "b": actual_rgb[2]
                })
            except:
                # Fallback to LED command
                try:
                    self._send_cmd({
                        "cmd": "led",
                        "subcommand": "set_color",
                        "r": actual_rgb[0], 
                        "g": actual_rgb[1], 
                        "b": actual_rgb[2],
                        "brightness": int(self.brightness * brightness_factor)
                    })
                except:
                    pass  # Ignore failures in animation
    
    def _animate_solid(self, color, duration=0):
        """Display a solid color"""
        self._set_color(color)
        if duration > 0:
            time.sleep(duration)
    
    def _animate_breathing(self, color, duration=10, cycle_time=2.0):
        """Breathing animation effect"""
        start_time = time.time()
        rgb = self.colors.get(color, self.colors['blue'])
        
        while self.running and (duration == 0 or time.time() - start_time < duration):
            # Calculate brightness based on sine wave
            t = (time.time() % cycle_time) / cycle_time
            # Sine wave from 0.1 to 1.0 (to avoid complete darkness)
            factor = 0.1 + 0.9 * ((math.sin(2 * math.pi * t) + 1) / 2)
            
            # Send color command with brightness factor (includes change detection)
            self._send_color_command(rgb, factor)
            
            # Reduce update frequency to prevent command flooding
            time.sleep(0.1)  # Update at 10Hz instead of 20Hz
    
    def _animate_blinking(self, color, duration=10, blink_rate=0.5):
        """Blinking animation effect"""
        start_time = time.time()
        rgb = self.colors.get(color, self.colors['blue'])
        
        while self.running and (duration == 0 or time.time() - start_time < duration):
            # Turn on
            self._send_color_command(rgb, 1.0)
            
            # Wait half the blink period
            time.sleep(blink_rate / 2)
            
            # Turn off if still running
            if self.running:
                self._send_color_command((0, 0, 0), 1.0)
                
                # Wait half the blink period
                time.sleep(blink_rate / 2)
    
    def _animate_rotating(self, duration=10, cycle_time=3.0):
        """Rotating colors animation"""
        start_time = time.time()
        colors = ['red', 'green', 'blue', 'yellow', 'purple', 'white']
        
        while self.running and (duration == 0 or time.time() - start_time < duration):
            # Calculate current color index based on time
            t = (time.time() % cycle_time) / cycle_time
            color_idx = int(t * len(colors))
            
            # Set current color
            self._set_color(colors[color_idx])
            
            # Small delay for smoothness
            time.sleep(0.05)
    
    def _animate_flash(self, color, duration=1.0, flash_count=3):
        """Flash animation effect"""
        rgb = self.colors.get(color, self.colors['blue'])
        flash_duration = duration / (flash_count * 2)  # Each flash has on and off state
        
        for _ in range(flash_count):
            if not self.running:
                break
                
            # Flash on
            if not self.simulation_mode and self._controller:
                self._send_cmd({"cmd": "set_ws2812b_color", "r": rgb[0], "g": rgb[1], "b": rgb[2]})
            
            time.sleep(flash_duration)
            
            # Flash off
            if not self.running:
                break
                
            if not self.simulation_mode and self._controller:
                self._send_cmd({"cmd": "set_ws2812b_color", "r": 0, "g": 0, "b": 0})
            
            time.sleep(flash_duration)
    
    def _animate_sos(self, color='red', duration=10):
        """SOS pattern animation (3 short, 3 long, 3 short)"""
        start_time = time.time()
        rgb = self.colors.get(color, self.colors['red'])
        
        # Timing for SOS pattern
        dit = 0.2  # Short flash
        dah = 0.6  # Long flash
        gap = 0.2  # Gap between flashes
        word_gap = 0.6  # Gap between letters
        
        while self.running and (duration == 0 or time.time() - start_time < duration):
            if not self.running:
                break
                
            # S (3 short flashes)
            for _ in range(3):
                # Flash on
                if not self.simulation_mode and self._controller:
                    self._send_cmd({"cmd": "set_ws2812b_color", "r": rgb[0], "g": rgb[1], "b": rgb[2]})
                
                time.sleep(dit)
                
                # Flash off
                if not self.simulation_mode and self._controller:
                    self._send_cmd({"cmd": "set_ws2812b_color", "r": 0, "g": 0, "b": 0})
                
                time.sleep(gap)
            
            time.sleep(word_gap)
            
            # O (3 long flashes)
            for _ in range(3):
                # Flash on
                if not self.simulation_mode and self._controller:
                    self._send_cmd({"cmd": "set_ws2812b_color", "r": rgb[0], "g": rgb[1], "b": rgb[2]})
                
                time.sleep(dah)
                
                # Flash off
                if not self.simulation_mode and self._controller:
                    self._send_cmd({"cmd": "set_ws2812b_color", "r": 0, "g": 0, "b": 0})
                
                time.sleep(gap)
            
            time.sleep(word_gap)
            
            # S (3 short flashes)
            for _ in range(3):
                # Flash on
                if not self.simulation_mode and self._controller:
                    self._send_cmd({"cmd": "set_ws2812b_color", "r": rgb[0], "g": rgb[1], "b": rgb[2]})
                
                time.sleep(dit)
                
                # Flash off
                if not self.simulation_mode and self._controller:
                    self._send_cmd({"cmd": "set_ws2812b_color", "r": 0, "g": 0, "b": 0})
                
                time.sleep(gap)
            
            time.sleep(word_gap * 2)
    
    # Dual LED animation methods (both LEDs show same animation)
    def _animate_dual_solid(self, led1_color, led2_color):
        """Display solid colors on both LEDs"""
        self._set_individual_led(0, led1_color)
        self._set_individual_led(1, led2_color)
        time.sleep(0.1)
    
    def _animate_dual_breathing(self, led1_color, led2_color, duration=10, cycle_time=2.0):
        """Breathing animation on both LEDs"""
        start_time = time.time()
        led1_rgb = self.colors.get(led1_color, self.colors['blue'])
        led2_rgb = self.colors.get(led2_color, self.colors['blue'])
        
        while self.running and (duration == 0 or time.time() - start_time < duration):
            t = (time.time() % cycle_time) / cycle_time
            factor = 0.1 + 0.9 * ((math.sin(2 * math.pi * t) + 1) / 2)
            
            # Send individual LED commands with brightness factor
            if not self.simulation_mode and self._controller:
                self._send_individual_led_command(0, led1_rgb, factor)
                self._send_individual_led_command(1, led2_rgb, factor)
            
            time.sleep(0.1)
    
    def _animate_dual_blinking(self, led1_color, led2_color, duration=10, blink_rate=0.5):
        """Blinking animation on both LEDs"""
        start_time = time.time()
        
        while self.running and (duration == 0 or time.time() - start_time < duration):
            # Turn on
            self._set_individual_led(0, led1_color)
            self._set_individual_led(1, led2_color)
            time.sleep(blink_rate / 2)
            
            # Turn off
            if self.running:
                self._set_individual_led(0, 'off')
                self._set_individual_led(1, 'off')
                time.sleep(blink_rate / 2)
    
    def _animate_dual_rotating(self, duration=10, cycle_time=3.0):
        """Rotating colors animation on both LEDs"""
        start_time = time.time()
        colors = ['red', 'green', 'blue', 'yellow', 'purple']
        
        while self.running and (duration == 0 or time.time() - start_time < duration):
            for color in colors:
                if not self.running:
                    break
                self._set_individual_led(0, color)
                self._set_individual_led(1, color)
                time.sleep(cycle_time / len(colors))
    
    def _animate_dual_flash(self, led1_color, led2_color, duration=1.0, flash_count=3):
        """Flash animation on both LEDs"""
        for _ in range(flash_count):
            if not self.running:
                break
            # Flash on
            self._set_individual_led(0, led1_color)
            self._set_individual_led(1, led2_color)
            time.sleep(0.1)
            # Flash off
            self._set_individual_led(0, 'off')
            self._set_individual_led(1, 'off')
            time.sleep(0.1)
        time.sleep(duration)
    
    def _animate_dual_sos(self, led1_color, led2_color, duration=10):
        """SOS pattern on both LEDs"""
        start_time = time.time()
        dit = 0.2
        dah = 0.6
        gap = 0.2
        word_gap = 1.0
        
        while self.running and (duration == 0 or time.time() - start_time < duration):
            # S (3 short)
            for _ in range(3):
                self._set_individual_led(0, led1_color)
                self._set_individual_led(1, led2_color)
                time.sleep(dit)
                self._set_individual_led(0, 'off')
                self._set_individual_led(1, 'off')
                time.sleep(gap)
            
            time.sleep(word_gap)
            
            # O (3 long)
            for _ in range(3):
                self._set_individual_led(0, led1_color)
                self._set_individual_led(1, led2_color)
                time.sleep(dah)
                self._set_individual_led(0, 'off')
                self._set_individual_led(1, 'off')
                time.sleep(gap)
            
            time.sleep(word_gap)
            
            # S (3 short)
            for _ in range(3):
                self._set_individual_led(0, led1_color)
                self._set_individual_led(1, led2_color)
                time.sleep(dit)
                self._set_individual_led(0, 'off')
                self._set_individual_led(1, 'off')
                time.sleep(gap)
            
            time.sleep(word_gap * 2)
    
    # Single LED1 animation methods (LED2 stays static)
    def _animate_solid_led1(self, color):
        """Display solid color on LED1 only"""
        self._set_individual_led(0, color)
        time.sleep(0.1)
    
    def _animate_breathing_led1(self, color, duration=10, cycle_time=2.0):
        """Breathing animation on LED1 only"""
        start_time = time.time()
        rgb = self.colors.get(color, self.colors['blue'])
        
        while self.running and (duration == 0 or time.time() - start_time < duration):
            t = (time.time() % cycle_time) / cycle_time
            factor = 0.1 + 0.9 * ((math.sin(2 * math.pi * t) + 1) / 2)
            
            if not self.simulation_mode and self._controller:
                self._send_individual_led_command(0, rgb, factor)
            
            time.sleep(0.1)
    
    def _animate_blinking_led1(self, color, duration=10, blink_rate=0.5):
        """Blinking animation on LED1 only"""
        start_time = time.time()
        
        while self.running and (duration == 0 or time.time() - start_time < duration):
            self._set_individual_led(0, color)
            time.sleep(blink_rate / 2)
            
            if self.running:
                self._set_individual_led(0, 'off')
                time.sleep(blink_rate / 2)
    
    def _animate_rotating_led1(self, duration=10, cycle_time=3.0):
        """Rotating colors animation on LED1 only"""
        start_time = time.time()
        colors = ['red', 'green', 'blue', 'yellow', 'purple']
        
        while self.running and (duration == 0 or time.time() - start_time < duration):
            for color in colors:
                if not self.running:
                    break
                self._set_individual_led(0, color)
                time.sleep(cycle_time / len(colors))
    
    def _animate_flash_led1(self, color, duration=1.0, flash_count=3):
        """Flash animation on LED1 only"""
        for _ in range(flash_count):
            if not self.running:
                break
            self._set_individual_led(0, color)
            time.sleep(0.1)
            self._set_individual_led(0, 'off')
            time.sleep(0.1)
        time.sleep(duration)
    
    def _animate_sos_led1(self, color, duration=10):
        """SOS pattern on LED1 only"""
        start_time = time.time()
        dit = 0.2
        dah = 0.6
        gap = 0.2
        word_gap = 1.0
        
        while self.running and (duration == 0 or time.time() - start_time < duration):
            # S (3 short)
            for _ in range(3):
                self._set_individual_led(0, color)
                time.sleep(dit)
                self._set_individual_led(0, 'off')
                time.sleep(gap)
            
            time.sleep(word_gap)
            
            # O (3 long)
            for _ in range(3):
                self._set_individual_led(0, color)
                time.sleep(dah)
                self._set_individual_led(0, 'off')
                time.sleep(gap)
            
            time.sleep(word_gap)
            
            # S (3 short)
            for _ in range(3):
                self._set_individual_led(0, color)
                time.sleep(dit)
                self._set_individual_led(0, 'off')
                time.sleep(gap)
            
            time.sleep(word_gap * 2)
    
    def _send_individual_led_command(self, led_index, rgb, brightness_factor=1.0):
        """Send individual LED command with brightness factor"""
        if not self.enabled or self.simulation_mode:
            return
            
        actual_rgb = (
            int(rgb[0] * brightness_factor),
            int(rgb[1] * brightness_factor), 
            int(rgb[2] * brightness_factor)
        )
        
        # Check if this exact command was already sent (with tolerance)
        current_led_rgb = self.led1_rgb if led_index == 0 else self.led2_rgb
        if (current_led_rgb and 
            abs(current_led_rgb[0] - actual_rgb[0]) < 5 and
            abs(current_led_rgb[1] - actual_rgb[1]) < 5 and
            abs(current_led_rgb[2] - actual_rgb[2]) < 5):
            return
            
        # Update tracking
        if led_index == 0:
            self.led1_rgb = actual_rgb
        else:
            self.led2_rgb = actual_rgb
        
        if self._controller:
            try:
                self._send_cmd({
                    "cmd": "set_individual_led",
                    "led": led_index,
                    "r": actual_rgb[0],
                    "g": actual_rgb[1],
                    "b": actual_rgb[2],
                    "brightness": int(self.brightness * brightness_factor)
                })
            except:
                pass  # Ignore failures in animation
    
    def _run_animation(self):
        """Run the current animation pattern with dual LED support"""
        # Get color for LED1 (main status LED)
        color_setting = self.state_colors.get(self.current_state, 'blue')
        
        # Extract color and potential animation override
        if '_' in color_setting:
            color, animation_override = color_setting.split('_')
            if animation_override == 'breathing':
                self.current_animation = AnimationPattern.BREATHING
            elif animation_override == 'blinking':
                self.current_animation = AnimationPattern.BLINKING
            elif animation_override == 'rotating':
                self.current_animation = AnimationPattern.ROTATING
            elif animation_override == 'flash':
                self.current_animation = AnimationPattern.FLASH
            elif animation_override == 'sos':
                self.current_animation = AnimationPattern.SOS
            else:
                color = color_setting
        else:
            color = color_setting
        
        # Set LED2 (placement guide) color based on current state
        led2_color = self.led2_placement_colors.get(self.current_state, 'off')
        
        # For states where LED2 should follow LED1, run dual animations
        if self.current_state in [LEDState.BOOTING, LEDState.IDLE, LEDState.CONNECTING, 
                                 LEDState.CONFIG, LEDState.CARD_DETECTED]:
            # Both LEDs show the same animation
            if self.current_animation == AnimationPattern.SOLID:
                self._animate_dual_solid(color, led2_color)
            elif self.current_animation == AnimationPattern.BREATHING:
                self._animate_dual_breathing(color, led2_color)
            elif self.current_animation == AnimationPattern.BLINKING:
                self._animate_dual_blinking(color, led2_color)
            elif self.current_animation == AnimationPattern.ROTATING:
                self._animate_dual_rotating()
            elif self.current_animation == AnimationPattern.FLASH:
                self._animate_dual_flash(color, led2_color)
            elif self.current_animation == AnimationPattern.SOS:
                self._animate_dual_sos(color, led2_color)
        else:
            # LED1 shows animation, LED2 shows static placement guide color
            self._set_individual_led(1, led2_color)  # Set LED2 to placement guide color
            
            # Run LED1 animation
            if self.current_animation == AnimationPattern.SOLID:
                self._animate_solid_led1(color)
            elif self.current_animation == AnimationPattern.BREATHING:
                self._animate_breathing_led1(color)
            elif self.current_animation == AnimationPattern.BLINKING:
                self._animate_blinking_led1(color)
            elif self.current_animation == AnimationPattern.ROTATING:
                self._animate_rotating_led1()
            elif self.current_animation == AnimationPattern.FLASH:
                self._animate_flash_led1(color)
            elif self.current_animation == AnimationPattern.SOS:
                self._animate_sos_led1(color)
    
    def set_state(self, state):
        """
        Set the LED state
        
        Args:
            state: LEDState enum value or string matching an LEDState name
        """
        if not self.enabled:
            return
            
        if isinstance(state, str):
            try:
                state = LEDState(state)
            except ValueError:
                # Try to match by name
                for led_state in LEDState:
                    if led_state.name.lower() == state.lower():
                        state = led_state
                        break
                else:
                    logger.warning(f"Unknown LED state: {state}")
                    return
        
        with self.lock:
            self.current_state = state
            self.current_animation = self.state_animations.get(state, AnimationPattern.SOLID)
            
            # Reset state tracking to ensure immediate color update for new state
            self._reset_state_tracking()
            
            # If already running, animation thread will pick up new state
            if not self.running:
                self.start()
                
        logger.info(f"LED state set to {state.name}")
    
    def set_login_screen_active(self):
        """Helper method to set login screen state (LED2 white placement guide)"""
        self.set_state(LEDState.LOGIN_SCREEN)
    
    def set_user_logged_in(self):
        """Helper method to set logged in state (LED2 dim red placement guide)"""
        self.set_state(LEDState.ACCESS_GRANTED)
    
    def set_admin_logged_in(self):
        """Helper method to set admin logged in state (LED1 purple, LED2 dim red placement guide)"""
        self.set_state(LEDState.ADMIN_LOGGED_IN)
    
    def set_card_scan_ready(self):
        """Helper method to set idle state (both LEDs blue breathing)"""
        self.set_state(LEDState.IDLE)
    
    def start(self):
        """Start the LED controller"""
        if not self.enabled:
            return
            
        with self.lock:
            if self.running:
                return
                
            self.running = True
            self.animation_thread = threading.Thread(target=self._animation_loop, daemon=True)
            self.animation_thread.start()
            
        logger.info("LED controller started")
    
    def stop(self):
        """Stop the LED controller"""
        with self.lock:
            self.running = False
            
            if self.animation_thread:
                self.animation_thread.join(timeout=1.0)
                self.animation_thread = None
            
            # Turn off the LED
            if not self.simulation_mode and self._controller:
                self._send_cmd({"cmd": "set_ws2812b_color", "r": 0, "g": 0, "b": 0})
            
        logger.info("LED controller stopped")
    
    def _animation_loop(self):
        """Main animation loop"""
        logger.debug("Starting animation loop")
        
        while self.running:
            try:
                self._run_animation()
            except Exception as e:
                logger.error(f"Error in animation loop: {e}")
                time.sleep(1)  # Avoid tight loop on error
        
        logger.debug("Animation loop ended")
    
    def close(self):
        """Clean up resources"""
        self.stop()
        
        # Turn off both LEDs individually
        if not self.simulation_mode and self._controller:
            self._send_cmd({"cmd": "set_individual_led", "led": 0, "r": 0, "g": 0, "b": 0})
            self._send_cmd({"cmd": "set_individual_led", "led": 1, "r": 0, "g": 0, "b": 0})
            
        # Release the shared controller reference
        if not self.simulation_mode:
            try:
                from gpio_controller_wrapper import SharedGPIOController
                SharedGPIOController.release_controller()
            except ImportError:
                pass


# Import needed for breathing animation
import math

# For testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.DEBUG, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create controller
    led = WS2812BController()
    
    # Test each state
    try:
        print("Testing LED states...")
        
        print("1. IDLE state (blue breathing)")
        led.set_state(LEDState.IDLE)
        time.sleep(5)
        
        print("2. ACCESS_GRANTED state (solid green)")
        led.set_state(LEDState.ACCESS_GRANTED)
        time.sleep(5)
        
        print("3. ACCESS_DENIED state (red flash)")
        led.set_state(LEDState.ACCESS_DENIED)
        time.sleep(5)
        
        print("4. LOGGED_OUT state (purple blinking)")
        led.set_state(LEDState.LOGGED_OUT)
        time.sleep(5)
        
        print("5. WARNING state (yellow blinking)")
        led.set_state(LEDState.WARNING)
        time.sleep(5)
        
        print("6. ERROR state (red SOS pattern)")
        led.set_state(LEDState.ERROR)
        time.sleep(10)
        
        print("7. BOOTING state (blue rotating)")
        led.set_state(LEDState.BOOTING)
        time.sleep(5)
        
        print("8. CONNECTING state (purple breathing)")
        led.set_state(LEDState.CONNECTING)
        time.sleep(5)
        
        print("9. Back to IDLE state")
        led.set_state(LEDState.IDLE)
        time.sleep(5)
        
    finally:
        # Clean up
        led.close()
