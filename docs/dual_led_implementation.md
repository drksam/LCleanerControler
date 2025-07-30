# Dual LED Placement Guide Implementation

## Overview
Implementation of LED2 as a placement guide for RFID card scanning while LED1 continues to show authentication status.

## LED Behavior Specification

### LED1 (Status LED)
- **BOOTING**: Blue rotating animation
- **IDLE**: Blue breathing (ready for card)
- **LOGIN_SCREEN**: Blue solid
- **CARD_DETECTED**: Blue flash
- **ACCESS_GRANTED**: Green solid
- **ACCESS_DENIED**: Red flash
- **LOGGED_OUT**: Purple blink

### LED2 (Placement Guide)
- **BOOTING**: Blue rotating (same as LED1)
- **IDLE**: Blue breathing (same as LED1 - shows scan area)
- **LOGIN_SCREEN**: **White solid** (indicates where to scan)
- **CARD_DETECTED**: Blue flash (same as LED1)
- **ACCESS_GRANTED**: **Dim red** (user logged in, still shows scan area)
- **ACCESS_DENIED**: Off (no guidance during denial)
- **LOGGED_OUT**: Off (no guidance during logout)

## Technical Implementation

### ESP32 Firmware Changes (ESPfirmware_simple.cpp)
1. **New Function**: `setIndividualLedColor(int ledIndex, uint8_t r, uint8_t g, uint8_t b, uint8_t brightness)`
2. **New Command**: `set_individual_led` with parameters:
   - `led`: LED index (0 or 1)
   - `r`, `g`, `b`: RGB color values
   - `brightness`: LED brightness (optional)

### Python Controller Changes (ws2812b_controller.py)
1. **New LED State**: `LEDState.LOGIN_SCREEN`
2. **New Color**: `dim_red` (50, 0, 0) for logged-in placement guide
3. **Dual LED Support**:
   - Individual LED tracking and state management
   - Dual animation methods for synchronized effects
   - Single LED1 animation methods with static LED2
4. **Helper Methods**:
   - `set_login_screen_active()`: Sets white placement guide
   - `set_user_logged_in()`: Sets dim red placement guide
   - `set_card_scan_ready()`: Sets blue breathing on both LEDs

## Usage Examples

### From Application Code
```python
from ws2812b_controller import WS2812BController, LEDState

led_controller = WS2812BController()
led_controller.start()

# Show login screen with white placement guide
led_controller.set_login_screen_active()

# User logged in - green status + dim red placement guide
led_controller.set_user_logged_in()

# Back to idle - both LEDs breathing blue
led_controller.set_card_scan_ready()
```

### State Transitions
```python
# Boot sequence
led_controller.set_state(LEDState.BOOTING)      # Both blue rotating

# Ready for cards
led_controller.set_state(LEDState.IDLE)         # Both blue breathing

# Login screen displayed
led_controller.set_state(LEDState.LOGIN_SCREEN) # LED1: blue, LED2: white

# Card detected
led_controller.set_state(LEDState.CARD_DETECTED) # Both blue flash

# Authentication successful
led_controller.set_state(LEDState.ACCESS_GRANTED) # LED1: green, LED2: dim red

# User logs out
led_controller.set_state(LEDState.LOGGED_OUT)   # LED1: purple blink, LED2: off

# Back to idle
led_controller.set_state(LEDState.IDLE)         # Both blue breathing
```

## Testing

Use the test script to verify functionality:
```bash
python test_dual_led.py
```

This will demonstrate:
1. Boot sequence with synchronized animations
2. Login screen with white placement guide
3. Logged-in state with dim red placement guide
4. Authentication flows with appropriate LED2 behavior
5. Individual LED control verification

## Benefits

1. **Clear User Guidance**: LED2 shows exactly where to scan the card
2. **State Awareness**: Different colors indicate system state
3. **Consistent UX**: LED2 behavior follows logical patterns
4. **Accessibility**: Visual indicators help users locate scan area
5. **Status Retention**: LED1 continues showing authentication status

## Integration Notes

- The ESP32 firmware must be recompiled and uploaded with the new individual LED support
- Existing code using the LED controller will continue to work unchanged
- New states and helper methods provide easy integration points
- Command optimization prevents LED flickering and reduces ESP32 load
