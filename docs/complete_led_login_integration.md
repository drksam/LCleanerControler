# Complete LED and Login Integration Implementation

## Overview
Full integration of dual LED placement guide with Flask login system, including admin/user distinction and login-first workflow.

## Key Features Implemented

### 1. Dual LED Behavior
- **LED1 (Status)**: Shows authentication and system states
- **LED2 (Placement Guide)**: Shows where to scan RFID card

### 2. LED States and Colors

#### LED1 (Status LED)
- **LOGIN_SCREEN**: Blue solid
- **ACCESS_GRANTED**: Green solid (normal user)
- **ADMIN_LOGGED_IN**: Purple solid (admin user)
- **ACCESS_DENIED**: Red flash (bad login/unauthorized)
- **LOGGED_OUT**: Purple blink (logout transition)
- **BOOTING**: Blue rotating animation
- **IDLE**: Blue breathing

#### LED2 (Placement Guide)
- **LOGIN_SCREEN**: **White solid** (shows scan location)
- **ACCESS_GRANTED**: **Dim red** (user logged in, scan area visible)
- **ADMIN_LOGGED_IN**: **Dim red** (admin logged in, scan area visible)
- **ACCESS_DENIED**: Off (no guidance during denial)
- **LOGGED_OUT**: Off (no guidance during logout)
- **BOOTING/IDLE**: Same as LED1 (synchronized)

### 3. ESP32 Firmware Changes
- **New Command**: `set_individual_led` with parameters:
  - `led`: LED index (0 or 1)
  - `r`, `g`, `b`: RGB color values (0-255)
  - `brightness`: Optional brightness override
- **New Function**: `setIndividualLedColor(int ledIndex, uint8_t r, uint8_t g, uint8_t b, uint8_t brightness)`

### 4. Python Controller Enhancements
- **New State**: `LEDState.ADMIN_LOGGED_IN` for admin users
- **Individual LED Control**: Per-LED state tracking and command optimization
- **Helper Methods**:
  - `set_login_screen_active()`: White placement guide
  - `set_user_logged_in()`: Green status + dim red guide
  - `set_admin_logged_in()`: Purple status + dim red guide

### 5. Flask Application Integration
- **Login-First Workflow**: `/` route now requires authentication
- **LED Integration**: All login/logout routes update LED states
- **Admin Detection**: Purple LED for admin users, green for normal users
- **Error Handling**: Red flash for bad logins with auto-return to login screen

## Login Workflow

### 1. Application Startup
```
System boots → LED1: blue rotating, LED2: blue rotating
System ready → LED1: blue, LED2: white (LOGIN_SCREEN)
```

### 2. User Authentication
```
Login page loads → LED1: blue, LED2: white
Valid card/login → LED1: green (user) or purple (admin), LED2: dim red
Invalid login → LED1: red flash, LED2: off → auto-return to login screen
```

### 3. User Session
```
User active → LED1: green/purple, LED2: dim red (placement guide remains visible)
User logs out → LED1: purple blink, LED2: off → auto-return to login screen
```

## Technical Implementation Details

### ESP32 Commands
```json
// Set LED1 to green
{"cmd": "set_individual_led", "led": 0, "r": 0, "g": 255, "b": 0}

// Set LED2 to white placement guide
{"cmd": "set_individual_led", "led": 1, "r": 255, "g": 255, "b": 255}

// Set LED2 to dim red
{"cmd": "set_individual_led", "led": 1, "r": 50, "g": 0, "b": 0}
```

### Python Usage
```python
from ws2812b_controller import WS2812BController, LEDState

led_controller = WS2812BController()
led_controller.start()

# Login screen
led_controller.set_login_screen_active()

# Normal user login
led_controller.set_user_logged_in()

# Admin user login
led_controller.set_admin_logged_in()

# Bad login
led_controller.set_state(LEDState.ACCESS_DENIED)

# Logout
led_controller.set_state(LEDState.LOGGED_OUT)
```

### Flask Route Integration
```python
@main_bp.route('/login')
def login():
    # Sets LED to login screen state automatically
    led_controller.set_login_screen_active()
    
    # On successful login:
    if user.access_level == 'admin':
        led_controller.set_admin_logged_in()
    else:
        led_controller.set_user_logged_in()
    
    # On failed login:
    led_controller.set_state(LEDState.ACCESS_DENIED)
```

## Configuration Requirements

### 1. ESP32 Firmware
- Must compile and upload `ESPfirmware_simple.cpp` with individual LED support
- Requires FastLED library
- NUM_LEDS must be set to 2

### 2. Machine Configuration
```json
{
  "system": {
    "esp32_serial_port": "/dev/ttyUSB0"
  },
  "led_status": {
    "enabled": true,
    "num_leds": 2,
    "brightness": 50
  }
}
```

### 3. Flask Application
- `@login_required` decorator on main routes
- `login_manager.login_view = 'main_bp.login'`
- LED controller initialized in `init_controllers()`

## Testing

### Test Scripts
```bash
# Test dual LED functionality
python test_dual_led.py

# Test login integration (requires running Flask app)
# Visit http://localhost:5000 - should redirect to login
# Login with valid credentials - LEDs should respond
```

### Expected Behavior
1. **Startup**: Blue rotating on both LEDs
2. **Login Page**: Blue on LED1, white on LED2
3. **Valid Login**: Green/purple on LED1, dim red on LED2
4. **Invalid Login**: Red flash on LED1, LED2 off, auto-return to login
5. **Logout**: Purple blink on LED1, LED2 off, auto-return to login

## Troubleshooting

### Common Issues
1. **LED2 not turning white**: Check ESP32 firmware has individual LED support
2. **No LED response**: Verify serial port configuration and ESP32 connection
3. **Login not required**: Ensure `@login_required` on routes and correct login_view
4. **Admin/user colors wrong**: Check user.access_level in database

### Debug Steps
1. Check LED controller initialization in logs
2. Verify ESP32 serial communication
3. Test individual LED commands manually
4. Confirm user access levels in database

## Benefits
- **Clear User Guidance**: LED2 always shows where to scan
- **Admin Distinction**: Purple vs green for user types
- **Security**: Login required for all machine access
- **Visual Feedback**: Immediate LED response to all login actions
- **Optimized Performance**: Command reduction prevents LED flickering
