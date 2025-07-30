#include <Arduino.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <FastLED.h>  // Include FastLED library for WS2812B

#define MAX_SERVOS 4
#define MAX_STEPPERS 2
#define WS2812B_PIN 23       // LED data pin
#define NUM_LEDS 1           // Number of LEDs in the strip
#define LED_BRIGHTNESS 50    // Default brightness (0-255)

Servo servos[MAX_SERVOS];
int attachedPins[MAX_SERVOS] = {-1, -1, -1, -1};

struct StepperConfig {
  int stepPin;
  int dirPin;
  int enablePin;
  int limitA;
  int limitB;
  int home;
  int position;
  int minLimit;
  int maxLimit;
  int target;
  bool active;
  bool paused;
  bool direction;
  bool homing;
  bool enableConfigured;
  unsigned long lastStepTime;
  int speed;
  
  // NEW: Acceleration/Deceleration support
  int acceleration;        // Steps per second^2
  int deceleration;        // Steps per second^2
  int minDelay;           // Minimum delay (max speed) in microseconds
  int maxDelay;           // Maximum delay (min speed) in microseconds
  bool useAcceleration;   // Flag to enable/disable acceleration
  int currentDelay;       // Current delay during acceleration/deceleration
  long totalSteps;        // Total steps for current move
  long stepsTaken;        // Steps taken in current move
  long accelSteps;        // Steps for acceleration phase
  long decelSteps;        // Steps for deceleration phase
  int movePhase;          // 0=accel, 1=constant, 2=decel
};

StepperConfig steppers[MAX_STEPPERS];

// WS2812B LED variables
CRGB leds[NUM_LEDS];
bool ledInitialized = false;
int ledAnimationMode = 0;  // 0=solid, 1=blinking, 2=breathing, 3=rotating
uint8_t ledBrightness = LED_BRIGHTNESS;
unsigned long lastLedUpdate = 0;
unsigned long ledAnimationSpeed = 100; // Animation speed in ms
bool ledAnimationDirection = true;     // For breathing effect
int ledAnimationStep = 0;              // For animation progress

void handleCommand(String input);
void updateSteppers();
void sendStepperDone(int id);
void initializeStepperAcceleration(int id);
long calculateAccelSteps(int id, long totalSteps);
long calculateDecelSteps(int id, long totalSteps);
int calculateAccelDelay(int id, long currentStep, long totalAccelSteps, int startDelay, int endDelay);
int calculateDecelDelay(int id, long currentStep, long totalDecelSteps, int startDelay, int endDelay);
void startAcceleratedMove(int id, int targetPos, int moveSpeed);
bool readLimitSwitch(int pin);
void checkLimitSwitches(int id, int direction);
void sendLimitHitEvent(int id, const char* limitName, int position);
void sendPinStates(int id);
void handleLedCommand(JsonDocument& doc);
void updateLedAnimations();
void setLedColor(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness = 255);

void setup() {
  Serial.begin(115200);
  
  // Print startup information
  Serial.println();
  Serial.println("ESP32 LCleaner Controller Starting...");
  Serial.printf("Free heap: %d bytes\n", ESP.getFreeHeap());
  Serial.printf("CPU Frequency: %d MHz\n", ESP.getCpuFreqMHz());
  
  // Initialize steppers with safe defaults
  for (int i = 0; i < MAX_STEPPERS; i++) {
    steppers[i] = {0};
    // Initialize acceleration/deceleration parameters
    steppers[i].acceleration = 0;      // Disabled by default
    steppers[i].deceleration = 0;      // Disabled by default
    steppers[i].useAcceleration = false;
    steppers[i].minDelay = 500;        // Fastest speed (2kHz) - more conservative
    steppers[i].maxDelay = 5000;       // Slowest speed (200Hz) - slower start
    steppers[i].currentDelay = 1000;   // Default delay
    steppers[i].movePhase = 0;
  }
  
  // Initialize WS2812B LED with safety checks
  if (NUM_LEDS > 0) {
    FastLED.addLeds<WS2812B, WS2812B_PIN, GRB>(leds, NUM_LEDS);
    FastLED.setBrightness(ledBrightness);
    setLedColor(0, 0, 50); // Default blue color on startup
    FastLED.show();
    ledInitialized = true;
    Serial.println("LED initialized successfully");
  } else {
    Serial.println("LED initialization skipped - NUM_LEDS is 0");
  }
  
  Serial.println("Setup completed successfully");
  Serial.printf("Free heap after setup: %d bytes\n", ESP.getFreeHeap());
}

void loop() {
  static String inputString = "";
  
  // Read serial commands with proper buffering
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      if (inputString.length() > 0) {
        handleCommand(inputString);
        inputString = "";
      }
    } else if (c != '\r') { // Ignore carriage return characters
      inputString += c;
      // Prevent buffer overflow
      if (inputString.length() > 500) {
        inputString = "";
        Serial.println("{\"error\":\"command_too_long\"}");
      }
    }
  }
  
  // Update stepper motors
  updateSteppers();
  
  // Update LED animations safely
  updateLedAnimations();
  
  // Small delay to prevent overwhelming the loop
  delay(1);
}

void handleCommand(String input) {
  // Trim whitespace and check input length
  input.trim();
  if (input.length() == 0 || input.length() > 500) {
    Serial.println("{\"error\":\"invalid_command_length\"}");
    return;
  }
  
  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, input);
  if (err) {
    Serial.println("{\"error\":\"parse_error\"}");
    return;
  }

  const char* cmd = doc["cmd"];
  if (!cmd) {
    Serial.println("{\"error\":\"missing_cmd\"}");
    return;
  }

  if (strcmp(cmd, "set_servo") == 0) {
    int pin = doc["pin"];
    int angle = doc["angle"];
    bool found = false;
    for (int i = 0; i < MAX_SERVOS; i++) {
      if (attachedPins[i] == pin) {
        servos[i].write(angle);
        found = true;
        break;
      }
    }
    if (!found) {
      for (int i = 0; i < MAX_SERVOS; i++) {
        if (attachedPins[i] == -1) {
          servos[i].setPeriodHertz(50);
          servos[i].attach(pin);
          servos[i].write(angle);
          attachedPins[i] = pin;
          found = true;
          break;
        }
      }
    }
    StaticJsonDocument<128> res;
    res["status"] = found ? "ok" : "servo_attach_failed";
    JsonObject s = res.createNestedObject("servo");
    s["pin"] = pin;
    s["angle"] = angle;
    serializeJson(res, Serial);
    Serial.println();
    return;
  }

  if (strcmp(cmd, "init_stepper") == 0) {
    int id = doc["id"];
    steppers[id].stepPin = doc["step_pin"];
    steppers[id].dirPin = doc["dir_pin"];
    steppers[id].limitA = doc["limit_a"];
    steppers[id].limitB = doc["limit_b"];
    steppers[id].home = doc["home"];
    steppers[id].minLimit = doc["min_limit"];
    steppers[id].maxLimit = doc["max_limit"];
    steppers[id].enableConfigured = doc.containsKey("enable_pin");
    if (steppers[id].enableConfigured) {
      steppers[id].enablePin = doc["enable_pin"];
      pinMode(steppers[id].enablePin, OUTPUT);
      digitalWrite(steppers[id].enablePin, HIGH);
    }
    pinMode(steppers[id].stepPin, OUTPUT);
    pinMode(steppers[id].dirPin, OUTPUT);
    pinMode(steppers[id].home, INPUT_PULLUP);
    pinMode(steppers[id].limitA, INPUT_PULLUP);
    pinMode(steppers[id].limitB, INPUT_PULLUP);
    steppers[id].position = 0;
    steppers[id].active = false;
    steppers[id].paused = false;
    steppers[id].homing = false;
    StaticJsonDocument<128> response;
    response["status"] = "stepper_initialized";
    response["id"] = id;
    serializeJson(response, Serial);
    Serial.println();
    return;
  }

  if (strcmp(cmd, "move_stepper") == 0) {
    int id = doc["id"];
    int steps = doc["steps"];
    int dir = doc["dir"];
    int speed = doc["speed"];
    if (id < MAX_STEPPERS) {
      steppers[id].target = steppers[id].position + (dir == 1 ? steps : -steps);
      steppers[id].speed = speed;
      steppers[id].direction = dir;
      steppers[id].homing = false;
      digitalWrite(steppers[id].dirPin, dir);
      if (steppers[id].enableConfigured) digitalWrite(steppers[id].enablePin, LOW);
      
      // Initialize acceleration if enabled (either acceleration or deceleration > 0)
      if (steppers[id].useAcceleration && (steppers[id].acceleration > 0 || steppers[id].deceleration > 0)) {
        startAcceleratedMove(id, steppers[id].target, speed);
      } else {
        // Use constant speed (existing behavior)
        steppers[id].active = true;
        steppers[id].paused = false;
        steppers[id].currentDelay = speed;
      }
      
      steppers[id].lastStepTime = micros();
    }
    return;
  }

  if (strcmp(cmd, "home_stepper") == 0) {
    int id = doc["id"];
    steppers[id].direction = 0;
    digitalWrite(steppers[id].dirPin, LOW);
    steppers[id].target = -999999;
    steppers[id].active = true;
    steppers[id].paused = false;
    steppers[id].homing = true;
    steppers[id].speed = doc.containsKey("speed") ? doc["speed"].as<int>() : 1000; // Default homing speed
    steppers[id].currentDelay = steppers[id].speed;
    if (steppers[id].enableConfigured) digitalWrite(steppers[id].enablePin, LOW);
    steppers[id].lastStepTime = micros();
    return;
  }

  if (strcmp(cmd, "set_stepper_acceleration") == 0) {
    int stepper_id = doc["id"].as<int>();
    int acceleration = doc["acceleration"].as<int>();
    
    if (stepper_id >= 0 && stepper_id < MAX_STEPPERS) {
      steppers[stepper_id].acceleration = acceleration;
      // Enable acceleration if either acceleration or deceleration is set
      steppers[stepper_id].useAcceleration = (steppers[stepper_id].acceleration > 0 || steppers[stepper_id].deceleration > 0);
      Serial.println("{\"status\":\"ok\",\"message\":\"acceleration_set\"}");
    } else {
      Serial.println("{\"status\":\"error\",\"message\":\"invalid_stepper_id\"}");
    }
    return;
  }

  if (strcmp(cmd, "set_stepper_deceleration") == 0) {
    int stepper_id = doc["id"].as<int>();
    int deceleration = doc["deceleration"].as<int>();
    
    if (stepper_id >= 0 && stepper_id < MAX_STEPPERS) {
      steppers[stepper_id].deceleration = deceleration;
      // Enable acceleration if either acceleration or deceleration is set
      steppers[stepper_id].useAcceleration = (steppers[stepper_id].acceleration > 0 || steppers[stepper_id].deceleration > 0);
      Serial.println("{\"status\":\"ok\",\"message\":\"deceleration_set\"}");
    } else {
      Serial.println("{\"status\":\"error\",\"message\":\"invalid_stepper_id\"}");
    }
    return;
  }

  if (strcmp(cmd, "set_stepper_speed_limits") == 0) {
    int stepper_id = doc["id"].as<int>();
    int minDelay = doc["min_delay"].as<int>();
    int maxDelay = doc["max_delay"].as<int>();
    
    if (stepper_id >= 0 && stepper_id < MAX_STEPPERS) {
      steppers[stepper_id].minDelay = minDelay;
      steppers[stepper_id].maxDelay = maxDelay;
      Serial.println("{\"status\":\"ok\",\"message\":\"speed_limits_set\"}");
    } else {
      Serial.println("{\"status\":\"error\",\"message\":\"invalid_stepper_id\"}");
    }
    return;
  }

  if (strcmp(cmd, "get_pin_states") == 0) {
    int id = doc["id"];
    if (id >= 0 && id < MAX_STEPPERS) {
      sendPinStates(id);
    } else {
      Serial.println("{\"status\":\"error\",\"message\":\"invalid_stepper_id\"}");
    }
    return;
  }

  if (strcmp(cmd, "get_status") == 0) {
    int id = doc.containsKey("id") ? doc["id"].as<int>() : 0;
    if (id >= 0 && id < MAX_STEPPERS) {
      sendPinStates(id);
    } else {
      Serial.println("{\"status\":\"error\",\"message\":\"invalid_stepper_id\"}");
    }
    return;
  }
  
  // Handle LED commands - support both direct "led" commands and WS2812B commands from Python
  if (strcmp(cmd, "led") == 0) {
    handleLedCommand(doc);
    return;
  }
  
  // Support for ws2812b_controller.py commands
  if (strcmp(cmd, "set_ws2812b_color") == 0) {
    uint8_t r = doc["r"];
    uint8_t g = doc["g"];
    uint8_t b = doc["b"];
    
    // Convert to LED command format and handle
    setLedColor(r, g, b, ledBrightness);
    
    StaticJsonDocument<128> response;
    response["status"] = "ok";
    response["message"] = "ws2812b_color_set";
    serializeJson(response, Serial);
    Serial.println();
    return;
  }
  
  if (strcmp(cmd, "set_ws2812b_brightness") == 0) {
    uint8_t brightness = doc["brightness"];
    
    // Map 0-100 to 0-255
    ledBrightness = map(brightness, 0, 100, 0, 255);
    FastLED.setBrightness(ledBrightness);
    FastLED.show();
    
    StaticJsonDocument<128> response;
    response["status"] = "ok";
    response["message"] = "ws2812b_brightness_set";
    serializeJson(response, Serial);
    Serial.println();
    return;
  }
  
  if (strcmp(cmd, "init_ws2812b") == 0) {
    // WS2812B is already initialized in setup(), just acknowledge
    StaticJsonDocument<128> response;
    response["status"] = "ok";
    response["message"] = "ws2812b_initialized";
    serializeJson(response, Serial);
    Serial.println();
    return;
  }
}

void updateSteppers() {
  unsigned long now = micros();
  for (int i = 0; i < MAX_STEPPERS; i++) {
    if (!steppers[i].active || steppers[i].paused) continue;

    // Check limit switches for safety during movement
    if (!steppers[i].homing) {
      checkLimitSwitches(i, steppers[i].direction);
      if (!steppers[i].active) continue; // Skip if movement was stopped by limit switch
    }

    int currentDelay = steppers[i].useAcceleration ? steppers[i].currentDelay : steppers[i].speed;
    
    if ((now - steppers[i].lastStepTime) >= currentDelay) {
      digitalWrite(steppers[i].stepPin, HIGH);
      delayMicroseconds(2);
      digitalWrite(steppers[i].stepPin, LOW);
      steppers[i].position += (steppers[i].direction == 1) ? 1 : -1;
      steppers[i].lastStepTime = now;

      // Handle homing
      if (steppers[i].homing && digitalRead(steppers[i].home) == LOW) {
        steppers[i].active = false;
        steppers[i].homing = false;
        steppers[i].position = 0;
        if (steppers[i].enableConfigured) digitalWrite(steppers[i].enablePin, HIGH);
        sendStepperDone(i);
        continue;
      }

      // Handle acceleration/deceleration
      if (steppers[i].useAcceleration && !steppers[i].homing) {
        steppers[i].stepsTaken++;
        
        // Update delay based on acceleration phase
        if (steppers[i].movePhase == 0) { // Acceleration phase
          if (steppers[i].stepsTaken < steppers[i].accelSteps) {
            steppers[i].currentDelay = calculateAccelDelay(i, steppers[i].stepsTaken, 
              steppers[i].accelSteps, steppers[i].maxDelay, steppers[i].speed);
          } else {
            steppers[i].movePhase = 1; // Switch to constant speed
            steppers[i].currentDelay = steppers[i].speed;
          }
        } else if (steppers[i].movePhase == 1) { // Constant speed phase
          long remainingSteps = steppers[i].totalSteps - steppers[i].stepsTaken;
          if (remainingSteps <= steppers[i].decelSteps) {
            steppers[i].movePhase = 2; // Switch to deceleration
          }
        } else if (steppers[i].movePhase == 2) { // Deceleration phase
          long decelStep = steppers[i].stepsTaken - (steppers[i].totalSteps - steppers[i].decelSteps);
          steppers[i].currentDelay = calculateDecelDelay(i, decelStep, 
            steppers[i].decelSteps, steppers[i].speed, steppers[i].maxDelay);
        }
      }

      // Check if move is complete
      if (!steppers[i].homing && steppers[i].position == steppers[i].target) {
        steppers[i].active = false;
        if (steppers[i].enableConfigured) digitalWrite(steppers[i].enablePin, HIGH);
        sendStepperDone(i);
      }
    }
  }
}

void sendStepperDone(int id) {
  StaticJsonDocument<128> doc;
  doc["event"] = "stepper_done";
  doc["id"] = id;
  doc["position"] = steppers[id].position;
  serializeJson(doc, Serial);
  Serial.println();
}

void startAcceleratedMove(int id, int targetPos, int moveSpeed) {
  steppers[id].totalSteps = abs(targetPos - steppers[id].position);
  steppers[id].stepsTaken = 0;
  steppers[id].speed = moveSpeed; // Ensure target speed is set
  
  // Calculate acceleration and deceleration steps
  steppers[id].accelSteps = calculateAccelSteps(id, steppers[id].totalSteps);
  steppers[id].decelSteps = calculateDecelSteps(id, steppers[id].totalSteps);
  
  // Debug output to see what's being calculated
  StaticJsonDocument<256> debug;
  debug["debug"] = "accel_setup";
  debug["id"] = id;
  debug["totalSteps"] = steppers[id].totalSteps;
  debug["accelSteps"] = steppers[id].accelSteps;
  debug["decelSteps"] = steppers[id].decelSteps;
  debug["acceleration"] = steppers[id].acceleration;
  debug["deceleration"] = steppers[id].deceleration;
  debug["speed"] = steppers[id].speed;
  debug["maxDelay"] = steppers[id].maxDelay;
  serializeJson(debug, Serial);
  Serial.println();
  
  // Ensure accel + decel doesn't exceed total steps
  if (steppers[id].accelSteps + steppers[id].decelSteps > steppers[id].totalSteps) {
    steppers[id].accelSteps = steppers[id].totalSteps / 2;
    steppers[id].decelSteps = steppers[id].totalSteps - steppers[id].accelSteps;
  }
  
  // Determine starting phase and delay
  if (steppers[id].accelSteps > 0) {
    steppers[id].movePhase = 0; // Start with acceleration
    steppers[id].currentDelay = steppers[id].maxDelay; // Start slow
  } else {
    steppers[id].movePhase = 1; // Start with constant speed
    steppers[id].currentDelay = steppers[id].speed; // Start at target speed
  }
  
  steppers[id].active = true;
  steppers[id].paused = false;
}

long calculateAccelSteps(int id, long totalSteps) {
  if (steppers[id].acceleration <= 0) return 0;
  
  // Simple direct scaling: acceleration value = percentage of total steps to use for acceleration
  // acceleration=100 means use ~100 steps for acceleration (minimum)
  // acceleration=1000 means use ~1000 steps for acceleration  
  long calculatedSteps = steppers[id].acceleration;
  
  // Limit to maximum 40% of total move for acceleration
  long maxAccelSteps = (totalSteps * 2) / 5;
  
  // Use the smaller of calculated steps or max allowed
  long finalSteps = min(maxAccelSteps, calculatedSteps);
  
  // Ensure minimum of 10 steps if acceleration is enabled
  return max(finalSteps, (long)10);
}

long calculateDecelSteps(int id, long totalSteps) {
  if (steppers[id].deceleration <= 0) return 0;
  
  // Simple direct scaling: deceleration value = number of steps to use for deceleration
  // deceleration=100 means use ~100 steps for deceleration (minimum)
  // deceleration=1000 means use ~1000 steps for deceleration
  long calculatedSteps = steppers[id].deceleration;
  
  // Limit to maximum 40% of total move for deceleration
  long maxDecelSteps = (totalSteps * 2) / 5;
  
  // Use the smaller of calculated steps or max allowed
  long finalSteps = min(maxDecelSteps, calculatedSteps);
  
  // Ensure minimum of 10 steps if deceleration is enabled
  return max(finalSteps, (long)10);
}

int calculateAccelDelay(int id, long currentStep, long totalAccelSteps, int startDelay, int endDelay) {
  if (totalAccelSteps == 0) return endDelay;
  
  // Linear interpolation for now to ensure it works
  float progress = (float)currentStep / (float)totalAccelSteps;
  
  // Make sure we're going from slow (high delay) to fast (low delay)
  return startDelay - (int)((startDelay - endDelay) * progress);
}

int calculateDecelDelay(int id, long currentStep, long totalDecelSteps, int startDelay, int endDelay) {
  if (totalDecelSteps == 0) return startDelay;
  
  // Linear interpolation for now to ensure it works
  float progress = (float)currentStep / (float)totalDecelSteps;
  
  // Make sure we're going from fast (low delay) to slow (high delay)
  return startDelay + (int)((endDelay - startDelay) * progress);
}

bool readLimitSwitch(int pin) {
  // Return true when switch is triggered (pin reads LOW due to pull-up)
  return digitalRead(pin) == LOW;
}

void checkLimitSwitches(int id, int direction) {
  // Check CW limit (Limit A) - stop if moving clockwise and switch triggered
  if (direction == 1 && readLimitSwitch(steppers[id].limitA)) {
    steppers[id].active = false;
    if (steppers[id].enableConfigured) digitalWrite(steppers[id].enablePin, HIGH);
    sendLimitHitEvent(id, "limit_a", steppers[id].position);
    return;
  }
  
  // Check CCW limit (Limit B) - stop if moving counter-clockwise and switch triggered  
  if (direction == 0 && readLimitSwitch(steppers[id].limitB)) {
    steppers[id].active = false;
    if (steppers[id].enableConfigured) digitalWrite(steppers[id].enablePin, HIGH);
    sendLimitHitEvent(id, "limit_b", steppers[id].position);
    return;
  }
}

void sendLimitHitEvent(int id, const char* limitName, int position) {
  StaticJsonDocument<128> doc;
  doc["event"] = "limit_hit";
  doc["limit"] = limitName;
  doc["position"] = position;
  doc["id"] = id;
  serializeJson(doc, Serial);
  Serial.println();
}

void sendPinStates(int id) {
  StaticJsonDocument<256> doc;
  JsonObject status = doc.createNestedObject("status");
  
  String stepperKey = "stepper_" + String(id);
  JsonObject stepperStatus = status.createNestedObject(stepperKey);
  
  stepperStatus["limit_a"] = readLimitSwitch(steppers[id].limitA);
  stepperStatus["limit_b"] = readLimitSwitch(steppers[id].limitB);
  stepperStatus["home"] = readLimitSwitch(steppers[id].home);
  stepperStatus["position"] = steppers[id].position;
  stepperStatus["moving"] = steppers[id].active && !steppers[id].paused;
  
  doc["id"] = id;
  serializeJson(doc, Serial);
  Serial.println();
}

// Set the LED color with given RGB values and optional brightness
void setLedColor(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) {
  if (!ledInitialized || NUM_LEDS == 0) return;
  
  // Safety check for array bounds
  if (NUM_LEDS < 1) return;
  
  // Set the color safely
  leds[0] = CRGB(r, g, b);
  
  // Apply brightness at the FastLED level if provided
  if (brightness != 255) {
    // Only update global brightness if it's different
    if (ledBrightness != brightness) {
      ledBrightness = brightness;
      FastLED.setBrightness(ledBrightness);
    }
  }
  
  // Show the LED safely
  FastLED.show();
  
  // Debug output (reduced frequency to prevent spam)
  static unsigned long lastDebugOutput = 0;
  if (millis() - lastDebugOutput > 1000) { // Only every second
    StaticJsonDocument<128> debug;
    debug["debug"] = "led_set";
    debug["r"] = r;
    debug["g"] = g;
    debug["b"] = b;
    debug["brightness"] = ledBrightness;
    serializeJson(debug, Serial);
    Serial.println();
    lastDebugOutput = millis();
  }
}

// Handle LED commands from JSON
void handleLedCommand(JsonDocument& doc) {
  if (!ledInitialized) {
    Serial.println("{\"status\":\"error\",\"message\":\"led_not_initialized\"}");
    return;
  }
  
  StaticJsonDocument<128> response;
  response["status"] = "ok";
  
  // Handle different subcommands
  if (doc.containsKey("subcommand")) {
    const char* subcmd = doc["subcommand"];
    
    if (strcmp(subcmd, "set_color") == 0) {
      uint8_t r = doc["r"];
      uint8_t g = doc["g"];
      uint8_t b = doc["b"];
      uint8_t brightness = doc.containsKey("brightness") ? doc["brightness"] : ledBrightness;
      
      // Update brightness if provided
      if (doc.containsKey("brightness")) {
        ledBrightness = brightness;
        FastLED.setBrightness(ledBrightness);
      }
      
      // Set animation mode to solid (0)
      ledAnimationMode = 0;
      
      // Set the color
      setLedColor(r, g, b, 255);
      
      response["message"] = "color_set";
    }
    else if (strcmp(subcmd, "set_animation") == 0) {
      ledAnimationMode = doc["mode"];
      if (doc.containsKey("speed")) {
        ledAnimationSpeed = doc["speed"];
      }
      
      // Get colors if provided
      if (doc.containsKey("r") && doc.containsKey("g") && doc.containsKey("b")) {
        uint8_t r = doc["r"];
        uint8_t g = doc["g"];
        uint8_t b = doc["b"];
        leds[0] = CRGB(r, g, b);
      }
      
      // Update brightness if provided
      if (doc.containsKey("brightness")) {
        ledBrightness = doc["brightness"];
        FastLED.setBrightness(ledBrightness);
      }
      
      // Reset animation parameters
      ledAnimationDirection = true;
      ledAnimationStep = 0;
      lastLedUpdate = millis();
      
      response["message"] = "animation_set";
    }
    else if (strcmp(subcmd, "off") == 0) {
      // Turn off LED by setting black color
      setLedColor(0, 0, 0, 255);
      ledAnimationMode = 0;
      
      response["message"] = "led_off";
    }
    else {
      response["status"] = "error";
      response["message"] = "unknown_subcommand";
    }
  }
  else {
    response["status"] = "error";
    response["message"] = "missing_subcommand";
  }
  
  serializeJson(response, Serial);
  Serial.println();
}

// Update LED animations based on current mode
void updateLedAnimations() {
  if (!ledInitialized || ledAnimationMode == 0 || NUM_LEDS == 0) {
    return; // No animation for solid color (mode 0) or if not initialized
  }
  
  unsigned long currentMillis = millis();
  if (currentMillis - lastLedUpdate < ledAnimationSpeed) {
    return; // Not time to update yet
  }
  
  lastLedUpdate = currentMillis;
  
  // Safety check for array bounds
  if (NUM_LEDS < 1) return;
  
  // Store current color safely
  CRGB currentColor = leds[0];
  
  switch (ledAnimationMode) {
    case 1: // Blinking
      {
        uint8_t luma = leds[0].getLuma();
        if (luma > 0) {
          leds[0] = CRGB::Black;
        } else {
          leds[0] = currentColor;
        }
      }
      break;
      
    case 2: // Breathing
      if (ledAnimationDirection) {
        // Increasing brightness
        ledAnimationStep += 5;
        if (ledAnimationStep >= 100) {
          ledAnimationStep = 100;
          ledAnimationDirection = false;
        }
      } else {
        // Decreasing brightness
        ledAnimationStep -= 5;
        if (ledAnimationStep <= 5) {
          ledAnimationStep = 5;
          ledAnimationDirection = true;
        }
      }
      // Apply breathing effect safely
      leds[0] = currentColor;
      leds[0].fadeToBlackBy(255 - (ledAnimationStep * 255 / 100));
      break;
      
    case 3: // Rotating colors (hue shift)
      leds[0].setHue(ledAnimationStep);
      ledAnimationStep = (ledAnimationStep + 5) % 256;
      break;
      
    case 4: // SOS pattern (3 short, 3 long, 3 short)
      // Implementation of SOS pattern - uses ledAnimationStep to track pattern position
      // This is a simplified version that alternates between on and off
      if ((ledAnimationStep / 2) % 2 == 0) {
        leds[0] = currentColor;
      } else {
        leds[0] = CRGB::Black;
      }
      ledAnimationStep = (ledAnimationStep + 1) % 20; // 10 steps for a complete cycle
      break;
      
    case 5: // Flash
      // Quick burst of 3 flashes then pause
      {
        int flashPhase = ledAnimationStep % 10;
        if (flashPhase < 1 || flashPhase == 2 || flashPhase == 4) {
          leds[0] = currentColor;
        } else {
          leds[0] = CRGB::Black;
        }
        ledAnimationStep = (ledAnimationStep + 1) % 20;
      }
      break;
      
    default:
      // Unknown animation mode, set to solid
      ledAnimationMode = 0;
      return;
  }
  
  // Show the LED safely
  FastLED.show();
}
