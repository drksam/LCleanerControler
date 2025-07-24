Required Firmware Changes
1. Add Input Pin Configuration in init_stepper Command
Current: The init_stepper command accepts limit_a, limit_b, and home parameters but doesn't configure them as inputs.

Required Change
// In the init_stepper command handler, add:
pinMode(limit_a_pin, INPUT_PULLUP);  // Pin 18 (changed from 32)
pinMode(limit_b_pin, INPUT_PULLUP);  // Pin 19 (changed from 33)  
pinMode(home_pin, INPUT_PULLUP);     // Pin 21 (changed from 34)
2. Add New Command: get_pin_states
Purpose: Read current state of input pins and return them in status response.

Required Command:
{"cmd": "get_pin_states", "id": 0}

Expected Response Format:

{
  "status": {
    "stepper_0": {
      "limit_a": false,
      "limit_b": false, 
      "home": false,
      "position": 1234,
      "moving": false
    }
  },
  "id": 0
}

3. Modify get_status Command Response
Current: Returns {'status': 'stepper_initialized', 'id': 0}

Required Enhancement: Include pin states in the status response:

{
  "status": {
    "stepper_0": {
      "limit_a": false,     // digitalRead(limit_a_pin) == LOW
      "limit_b": false,     // digitalRead(limit_b_pin) == LOW  
      "home": false,        // digitalRead(home_pin) == LOW
      "moving": false,
      "position": 1234
    }
  },
  "id": 0
}

4. Pin Reading Logic
Implementation: Add function to read input pins:

bool readLimitSwitch(int pin) {
  // Return true when switch is triggered (pin reads LOW due to pull-up)
  return digitalRead(pin) == LOW;
}

5. Integration with Existing Homing
Current: home_stepper command exists but doesn't use switch detection.

Required Enhancement: Modify homing to stop when home pin reads LOW:

// In stepper movement loop during homing:
if (digitalRead(home_pin) == LOW) {
  // Stop movement, set position to 0
  stepper.stop();
  stepper.setCurrentPosition(0);
  // Send completion event
}

6. **NEW: Hardware Limit Switch Safety Implementation**
Purpose: Add real-time limit switch monitoring during stepper movement to prevent damage.

Required Implementation: Add limit switch checking in the stepper movement loop:

```cpp
// In the main stepper movement execution loop, add safety checks:
void checkLimitSwitches(int direction) {
  // Check CW limit (Limit A) - stop if moving clockwise and switch triggered
  if (direction == 1 && digitalRead(limit_a_pin) == LOW) {
    stepper.stop();
    stepper.setCurrentPosition(stepper.currentPosition()); // Maintain current position
    // Send limit hit event
    sendLimitHitEvent("limit_a", stepper.currentPosition());
    return;
  }
  
  // Check CCW limit (Limit B) - stop if moving counter-clockwise and switch triggered  
  if (direction == 0 && digitalRead(limit_b_pin) == LOW) {
    stepper.stop();
    stepper.setCurrentPosition(stepper.currentPosition()); // Maintain current position
    // Send limit hit event
    sendLimitHitEvent("limit_b", stepper.currentPosition());
    return;
  }
}

// Call this function in every stepper movement iteration:
// - In move_stepper command execution
// - In home_stepper command execution  
// - During any continuous movement
```

Integration Points for Limit Checking:
- **move_stepper command**: Check limits on every step or every few steps
- **home_stepper command**: Check home switch AND limit switches
- **continuous movement**: Monitor limits throughout movement duration

Event Response for Limit Hit:
```json
{
  "event": "limit_hit",
  "limit": "limit_a",  // or "limit_b"
  "position": 1234,
  "id": 0
}
```

Implementation Specifications
Pin Configuration (Do Not Change)
Servo: Pin 12 (existing, preserve)
Stepper EN: Pin 27 (existing, preserve)
Stepper DIR: Pin 26 (existing, preserve)
Stepper STEP: Pin 25 (existing, preserve)
**NEW Pin Assignments:**
Limit A: Pin 18 (configure as INPUT_PULLUP) - CW limit switch
Limit B: Pin 19 (configure as INPUT_PULLUP) - CCW limit switch  
Home: Pin 21 (configure as INPUT_PULLUP) - Home position switch
Switch Logic
Pull-up resistors: Enabled via INPUT_PULLUP
Active state: LOW (when switch closes to ground)
Inactive state: HIGH (when switch open, pulled up to 3.3V)
Reading: digitalRead(pin) == LOW means switch is triggered
Critical Requirements
1. Preserve ALL existing functionality - servo control, stepper commands, movement, etc.
2. Add input reading ONLY - do not modify existing command behavior
3. Response format consistency - maintain existing response structure where possible
4. Non-blocking operation - pin reading should not interfere with stepper movement
5. Reliable switch detection - debouncing not required (hardware pull-ups sufficient)
6. **NEW: Hardware safety limits** - immediately stop movement when limit switch in movement direction is triggered
7. **Direction mapping**: 
   - CW movement (direction = 1) → check Limit A (pin 18)
   - CCW movement (direction = 0) → check Limit B (pin 19)
8. **Limit switch behavior**: Stop movement, maintain position, send event notification
9. **Real-time monitoring**: Check limit switches during ALL stepper movements, not just at start/end
Testing Commands for Validation
After firmware update, these commands should work:

```json
{"cmd": "get_status"}
{"cmd": "get_pin_states", "id": 0}  
{"cmd": "home_stepper", "id": 0}
```

Expected pin state changes when manually triggering switches:
- Home switch (pin 21): `"home": true` when pressed, `"home": false` when released
- Limit A switch (pin 18): `"limit_a": true` when pressed, `"limit_a": false` when released  
- Limit B switch (pin 19): `"limit_b": true` when pressed, `"limit_b": false` when released

**NEW: Expected limit safety behavior during movement:**
1. **CW Movement Test**: Send move_stepper command with direction=1, manually trigger Limit A (pin 18)
   - Expected: Movement stops immediately, position maintained, limit_hit event sent
2. **CCW Movement Test**: Send move_stepper command with direction=0, manually trigger Limit B (pin 19)  
   - Expected: Movement stops immediately, position maintained, limit_hit event sent
3. **Homing Test**: Send home_stepper command, manually trigger Home switch (pin 21)
   - Expected: Movement stops, position set to 0, homing complete event sent

**Hardware Wiring Updates Required:**
- Move Limit A connection from ESP32 pin 32 → pin 18
- Move Limit B connection from ESP32 pin 33 → pin 19
- Move Home switch connection from ESP32 pin 34 → pin 21