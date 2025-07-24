Current Communication Protocol Analysis
The current system sends these commands to ESP32:

STEPPER_SET_SPEED,<stepper_id>,<delay_value>
SERVO_SET_ANGLE,<servo_id>,<angle>
STEPPER_MOVE_TO,<stepper_id>,<position>
STEPPER_JOG,<stepper_id>,<direction>,<steps>
Required ESP32 Firmware Changes
1. Add New Command Types
Add these constants to your command parser:

#define STEPPER_SET_ACCELERATION 10
#define STEPPER_SET_DECELERATION 11

2. Add Acceleration/Deceleration Variables
For each stepper motor, add these variables (assuming you have a stepper struct):

struct StepperMotor {
    // Existing variables...
    int step_pin;
    int dir_pin;
    int enable_pin;
    long current_position;
    int speed_delay;
    
    // NEW: Add acceleration/deceleration
    int acceleration;     // Steps per second^2
    int deceleration;     // Steps per second^2
    int min_delay;        // Minimum delay (max speed)
    int max_delay;        // Maximum delay (min speed)
    bool use_acceleration; // Flag to enable/disable acceleration
};

3. Command Parser Updates
Add these cases to your command parser (typically in loop() or command handler):
case STEPPER_SET_ACCELERATION:
    if (parts_count >= 3) {
        int stepper_id = parts[1].toInt();
        int accel = parts[2].toInt();
        if (stepper_id >= 0 && stepper_id < MAX_STEPPERS) {
            steppers[stepper_id].acceleration = accel;
            steppers[stepper_id].use_acceleration = (accel > 0);
            Serial.println("OK");
        } else {
            Serial.println("ERROR: Invalid stepper ID");
        }
    } else {
        Serial.println("ERROR: Invalid acceleration command");
    }
    break;

case STEPPER_SET_DECELERATION:
    if (parts_count >= 3) {
        int stepper_id = parts[1].toInt();
        int decel = parts[2].toInt();
        if (stepper_id >= 0 && stepper_id < MAX_STEPPERS) {
            steppers[stepper_id].deceleration = decel;
            Serial.println("OK");
        } else {
            Serial.println("ERROR: Invalid stepper ID");
        }
    } else {
        Serial.println("ERROR: Invalid deceleration command");
    }
    break;

    4. Acceleration Profile Implementation
Replace your current stepper movement function with this acceleration-aware version:
void moveStepper(int stepper_id, long target_position) {
    if (stepper_id < 0 || stepper_id >= MAX_STEPPERS) return;
    
    StepperMotor* motor = &steppers[stepper_id];
    long current_pos = motor->current_position;
    long steps_to_move = abs(target_position - current_pos);
    
    if (steps_to_move == 0) return;
    
    // Set direction
    bool direction = (target_position > current_pos);
    digitalWrite(motor->dir_pin, direction ? HIGH : LOW);
    
    // Enable motor
    if (motor->enable_pin > 0) {
        digitalWrite(motor->enable_pin, LOW); // Assuming LOW enables
    }
    
    if (motor->use_acceleration && motor->acceleration > 0) {
        // Use acceleration profile
        moveWithAcceleration(motor, steps_to_move, direction);
    } else {
        // Use constant speed (existing behavior)
        moveConstantSpeed(motor, steps_to_move, direction);
    }
    
    // Update position
    motor->current_position = target_position;
}

void moveWithAcceleration(StepperMotor* motor, long total_steps, bool direction) {
    // Calculate acceleration profile
    long accel_steps = calculateAccelSteps(motor, total_steps);
    long decel_steps = calculateDecelSteps(motor, total_steps);
    long constant_steps = total_steps - accel_steps - decel_steps;
    
    int current_delay = motor->max_delay; // Start at slowest speed
    int target_delay = motor->speed_delay; // Target speed
    
    // Acceleration phase
    for (long i = 0; i < accel_steps; i++) {
        stepOnce(motor);
        current_delay = calculateAccelDelay(motor, i, accel_steps, motor->max_delay, target_delay);
        delayMicroseconds(current_delay);
    }
    
    // Constant speed phase
    for (long i = 0; i < constant_steps; i++) {
        stepOnce(motor);
        delayMicroseconds(target_delay);
    }
    
    // Deceleration phase
    for (long i = 0; i < decel_steps; i++) {
        stepOnce(motor);
        current_delay = calculateDecelDelay(motor, i, decel_steps, target_delay, motor->max_delay);
        delayMicroseconds(current_delay);
    }
}

void moveConstantSpeed(StepperMotor* motor, long steps, bool direction) {
    // Existing constant speed implementation
    for (long i = 0; i < steps; i++) {
        stepOnce(motor);
        delayMicroseconds(motor->speed_delay);
    }
}

void stepOnce(StepperMotor* motor) {
    digitalWrite(motor->step_pin, HIGH);
    delayMicroseconds(2); // Minimum pulse width
    digitalWrite(motor->step_pin, LOW);
}

long calculateAccelSteps(StepperMotor* motor, long total_steps) {
    // Calculate steps needed to reach target speed
    // This is a simplified linear acceleration
    long max_accel_steps = total_steps / 3; // Use max 1/3 of move for acceleration
    return min(max_accel_steps, (long)(motor->acceleration * 100)); // Adjust multiplier as needed
}

long calculateDecelSteps(StepperMotor* motor, long total_steps) {
    // Similar calculation for deceleration
    long max_decel_steps = total_steps / 3;
    return min(max_decel_steps, (long)(motor->deceleration * 100));
}

int calculateAccelDelay(StepperMotor* motor, long current_step, long total_accel_steps, int start_delay, int end_delay) {
    // Linear interpolation from start_delay to end_delay
    float progress = (float)current_step / (float)total_accel_steps;
    return start_delay + (int)((end_delay - start_delay) * progress);
}

int calculateDecelDelay(StepperMotor* motor, long current_step, long total_decel_steps, int start_delay, int end_delay) {
    // Linear interpolation from start_delay to end_delay
    float progress = (float)current_step / (float)total_decel_steps;
    return start_delay + (int)((end_delay - start_delay) * progress);
}

5. Initialization Updates
In your setup function, initialize the new variables:

void setup() {
    // Existing setup code...
    
    for (int i = 0; i < MAX_STEPPERS; i++) {
        steppers[i].acceleration = 0;      // Disabled by default
        steppers[i].deceleration = 0;      // Disabled by default
        steppers[i].use_acceleration = false;
        steppers[i].min_delay = 100;       // Fastest speed
        steppers[i].max_delay = 3500;      // Slowest speed
    }
}

Communication Protocol Extension
The Python wrapper will send these new commands:

STEPPER_SET_ACCELERATION,<stepper_id>,<acceleration_value>
STEPPER_SET_DECELERATION,<stepper_id>,<deceleration_value>
Expected responses:

OK on success
ERROR: <reason> on failure
Servo Compatibility
IMPORTANT: The servo functionality should remain completely unchanged. The servo commands (SERVO_SET_ANGLE, etc.) should not be modified and should continue to work exactly as before. Only add the stepper acceleration/deceleration functionality without touching any servo-related code.

Testing Sequence
Test that existing stepper movements work without acceleration (acceleration = 0)
Test that servo movements still work normally
Test stepper movements with acceleration enabled
Verify that speed, acceleration, and deceleration settings persist correctly
This implementation maintains backward compatibility while adding the acceleration/deceleration functionality that the Python wrapper is already prepared to use.










Updated ESP32 Firmware Changes Needed
The ESP32 firmware should handle these JSON commands in its command parser:
// In your JSON command parser (probably in a loop that processes incoming JSON)
if (cmd == "set_stepper_acceleration") {
    int stepper_id = doc["id"].as<int>();
    int acceleration = doc["acceleration"].as<int>();
    
    if (stepper_id >= 0 && stepper_id < MAX_STEPPERS) {
        steppers[stepper_id].acceleration = acceleration;
        steppers[stepper_id].use_acceleration = (acceleration > 0);
        Serial.println("{\"status\":\"ok\",\"message\":\"acceleration_set\"}");
    } else {
        Serial.println("{\"status\":\"error\",\"message\":\"invalid_stepper_id\"}");
    }
}
else if (cmd == "set_stepper_deceleration") {
    int stepper_id = doc["id"].as<int>();
    int deceleration = doc["deceleration"].as<int>();
    
    if (stepper_id >= 0 && stepper_id < MAX_STEPPERS) {
        steppers[stepper_id].deceleration = deceleration;
        Serial.println("{\"status\":\"ok\",\"message\":\"deceleration_set\"}");
    } else {
        Serial.println("{\"status\":\"error\",\"message\":\"invalid_stepper_id\"}");
    }
}