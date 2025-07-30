#include <Arduino.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <FastLED.h>

// Undefine and redefine MAX_SERVOS to avoid conflict with ESP32Servo library
#undef MAX_SERVOS
#define MAX_SERVOS 4
#define MAX_STEPPERS 2
#define WS2812B_PIN 23       // LED data pin for WS2812B
#define NUM_LEDS 2           // Number of WS2812B LEDs
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

// FastLED WS2812B LED variables
CRGB leds[NUM_LEDS];
bool ledInitialized = false;
int ledAnimationMode = 0;  // 0=solid, 1=blinking, 2=breathing, 3=rotating
uint8_t ledBrightness = LED_BRIGHTNESS;
unsigned long lastLedUpdate = 0;
unsigned long ledAnimationSpeed = 100; // Animation speed in ms
bool ledAnimationDirection = true;     // For breathing effect
int ledAnimationStep = 0;              // For animation progress
bool ledState = false;                 // Current LED on/off state
uint8_t currentR = 0, currentG = 0, currentB = 50; // Current color (default blue)
uint8_t targetR = 0, targetG = 0, targetB = 50;    // Target color for animations

// Function declarations for WS2812B (FastLED)
void setLedColor(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness = 255);
void setIndividualLedColor(int ledIndex, uint8_t r, uint8_t g, uint8_t b, uint8_t brightness = 255);
void simpleLedOn();
void simpleLedOff();

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

void setup() {
  Serial.begin(115200);
  
  // Print startup information
  Serial.println();
  Serial.println("ESP32 LCleaner Controller Starting (Simple LED)...");
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
  
  // Initialize FastLED WS2812B LEDs
  FastLED.addLeds<WS2812B, WS2812B_PIN, GRB>(leds, NUM_LEDS);
  FastLED.setBrightness(LED_BRIGHTNESS);
  FastLED.clear();
  FastLED.show();
  
  ledInitialized = true;
  
  // Test LED functionality at startup
  Serial.println("Testing FastLED WS2812B LEDs...");
  
  // Test red
  setLedColor(255, 0, 0, 255);
  delay(500);
  
  // Test green  
  setLedColor(0, 255, 0, 255);
  delay(500);
  
  // Test blue
  setLedColor(0, 0, 255, 255);
  delay(500);
  
  // Set default color (dim blue)
  setLedColor(0, 0, 50, 255);
  
  Serial.println("FastLED WS2812B initialized successfully");
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
    
    // Reset animation mode to solid when setting color directly
    ledAnimationMode = 0;
    
    // Set the color with improved handling
    setLedColor(r, g, b, ledBrightness);
    
    StaticJsonDocument<128> response;
    response["status"] = "ok";
    response["message"] = "enhanced_color_set";
    response["r"] = r;
    response["g"] = g; 
    response["b"] = b;
    serializeJson(response, Serial);
    Serial.println();
    return;
  }
  
  // New command for individual LED control
  if (strcmp(cmd, "set_individual_led") == 0) {
    int ledIndex = doc["led"];
    uint8_t r = doc["r"];
    uint8_t g = doc["g"];
    uint8_t b = doc["b"];
    uint8_t brightness = doc.containsKey("brightness") ? doc["brightness"] : ledBrightness;
    
    setIndividualLedColor(ledIndex, r, g, b, brightness);
    
    StaticJsonDocument<128> response;
    response["status"] = "ok";
    response["message"] = "individual_led_set";
    response["led"] = ledIndex;
    response["r"] = r;
    response["g"] = g;
    response["b"] = b;
    response["brightness"] = brightness;
    serializeJson(response, Serial);
    Serial.println();
    return;
  }
  
  if (strcmp(cmd, "set_ws2812b_brightness") == 0) {
    uint8_t brightness = doc["brightness"];
    
    // Map 0-100 to 0-255 and store
    ledBrightness = map(brightness, 0, 100, 0, 255);
    
    // Re-apply current color with new brightness
    setLedColor(currentR, currentG, currentB, ledBrightness);
    
    StaticJsonDocument<128> response;
    response["status"] = "ok";
    response["message"] = "enhanced_brightness_set";
    response["brightness_input"] = brightness;
    response["brightness_mapped"] = ledBrightness;
    serializeJson(response, Serial);
    Serial.println();
    return;
  }
  
  if (strcmp(cmd, "init_ws2812b") == 0) {
    // Simple LED is already initialized in setup(), just acknowledge
    StaticJsonDocument<128> response;
    response["status"] = "ok";
    response["message"] = "ws2812b_initialized";
    serializeJson(response, Serial);
    Serial.println();
    return;
  }
}

// FastLED WS2812B functions (much simpler and more reliable)
void setLedColor(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) {
  if (!ledInitialized) return;
  
  // Apply brightness scaling
  r = (r * brightness) / 255;
  g = (g * brightness) / 255;
  b = (b * brightness) / 255;
  
  // Store current color
  currentR = r;
  currentG = g;
  currentB = b;
  
  // Set all LEDs to the same color
  for (int i = 0; i < NUM_LEDS; i++) {
    leds[i] = CRGB(r, g, b);
  }
  
  FastLED.show();
  
  // Update LED state
  ledState = (r > 0 || g > 0 || b > 0);
  
  // Debug output (reduced frequency to prevent spam)
  static unsigned long lastDebugOutput = 0;
  if (millis() - lastDebugOutput > 2000) { // Only every 2 seconds
    StaticJsonDocument<128> debug;
    debug["debug"] = "fastled_set";
    debug["r"] = r;
    debug["g"] = g;
    debug["b"] = b;
    debug["brightness"] = brightness;
    debug["led_state"] = ledState;
    serializeJson(debug, Serial);
    Serial.println();
    lastDebugOutput = millis();
  }
}

// New function for individual LED control
void setIndividualLedColor(int ledIndex, uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) {
  if (!ledInitialized) return;
  if (ledIndex < 0 || ledIndex >= NUM_LEDS) return;
  
  // Apply brightness scaling
  r = (r * brightness) / 255;
  g = (g * brightness) / 255;
  b = (b * brightness) / 255;
  
  // Set specific LED color
  leds[ledIndex] = CRGB(r, g, b);
  
  FastLED.show();
  
  // Debug output (reduced frequency to prevent spam)
  static unsigned long lastDebugOutput = 0;
  if (millis() - lastDebugOutput > 2000) { // Only every 2 seconds
    StaticJsonDocument<128> debug;
    debug["debug"] = "individual_led_set";
    debug["led_index"] = ledIndex;
    debug["r"] = r;
    debug["g"] = g;
    debug["b"] = b;
    debug["brightness"] = brightness;
    serializeJson(debug, Serial);
    Serial.println();
    lastDebugOutput = millis();
  }
}

void simpleLedOn() {
  setLedColor(currentR, currentG, currentB, ledBrightness);
}

void simpleLedOff() {
  for (int i = 0; i < NUM_LEDS; i++) {
    leds[i] = CRGB::Black;
  }
  FastLED.show();
  ledState = false;
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
        currentR = doc["r"];
        currentG = doc["g"];
        currentB = doc["b"];
      }
      
      // Update brightness if provided
      if (doc.containsKey("brightness")) {
        ledBrightness = doc["brightness"];
      }
      
      // Reset animation parameters
      ledAnimationDirection = true;
      ledAnimationStep = 0;
      lastLedUpdate = millis();
      
      response["message"] = "animation_set";
    }
    else if (strcmp(subcmd, "off") == 0) {
      // Turn off LED
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

// Update LED animations based on current mode (WS2812B)
void updateLedAnimations() {
  if (!ledInitialized || ledAnimationMode == 0) {
    return; // No animation for solid color (mode 0) or if not initialized
  }
  
  unsigned long currentMillis = millis();
  if (currentMillis - lastLedUpdate < ledAnimationSpeed) {
    return; // Not time to update yet
  }
  
  lastLedUpdate = currentMillis;
  
  switch (ledAnimationMode) {
    case 1: // Blinking
      if (ledState) {
        simpleLedOff();
      } else {
        simpleLedOn();
      }
      break;
      
    case 2: // Breathing - smooth brightness changes
      {
        if (ledAnimationDirection) {
          ledAnimationStep += 3;
          if (ledAnimationStep >= 100) {
            ledAnimationStep = 100;
            ledAnimationDirection = false;
          }
        } else {
          ledAnimationStep -= 3;
          if (ledAnimationStep <= 10) {
            ledAnimationStep = 10;
            ledAnimationDirection = true;
          }
        }
        
        // Apply breathing effect by scaling the RGB values
        uint8_t r = (currentR * ledAnimationStep) / 100;
        uint8_t g = (currentG * ledAnimationStep) / 100;
        uint8_t b = (currentB * ledAnimationStep) / 100;
        
        setLedColor(r, g, b, 255);
      }
      break;
      
    case 3: // Rotating colors - cycle through RGB
      {
        uint8_t r = 0, g = 0, b = 0;
        int phase = ledAnimationStep % 300; // 300 steps for full cycle
        
        if (phase < 100) {
          // Red to Green
          r = 255 - (phase * 255 / 100);
          g = phase * 255 / 100;
          b = 0;
        } else if (phase < 200) {
          // Green to Blue
          r = 0;
          g = 255 - ((phase - 100) * 255 / 100);
          b = (phase - 100) * 255 / 100;
        } else {
          // Blue to Red
          r = (phase - 200) * 255 / 100;
          g = 0;
          b = 255 - ((phase - 200) * 255 / 100);
        }
        
        setLedColor(r, g, b, ledBrightness);
        ledAnimationStep = (ledAnimationStep + 5) % 300;
      }
      break;
      
    case 4: // SOS pattern
      {
        // SOS pattern timing: 3 short, 3 long, 3 short
        int pattern[] = {1,0,1,0,1,0,0,1,1,1,0,1,1,1,0,1,1,1,0,0,1,0,1,0,1,0,0,0}; 
        int patternLength = sizeof(pattern) / sizeof(pattern[0]);
        int currentStep = ledAnimationStep % patternLength;
        
        if (pattern[currentStep]) {
          setLedColor(255, 0, 0, ledBrightness); // Red for SOS
        } else {
          setLedColor(0, 0, 0, 255); // Off
        }
        ledAnimationStep = (ledAnimationStep + 1) % patternLength;
      }
      break;
      
    case 5: // Flash - quick bursts
      {
        int flashPhase = ledAnimationStep % 8;
        if (flashPhase < 2) {
          simpleLedOn();
        } else {
          simpleLedOff();
        }
        ledAnimationStep = (ledAnimationStep + 1) % 16;
      }
      break;
      
    default:
      // Unknown animation mode, set to solid
      ledAnimationMode = 0;
      simpleLedOn();
      return;
  }
}

// Include all the stepper motor functions (unchanged)
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
  
  // Calculate steps based on speed difference and acceleration setting
  int speedDiff = steppers[id].maxDelay - steppers[id].speed;
  long calculatedSteps = (speedDiff / 50) * steppers[id].acceleration; // More gradual
  
  // Limit acceleration to reasonable portion of total steps
  long maxAccelSteps = min((long)(totalSteps * 0.3), (long)200); // Max 30% or 200 steps
  long finalSteps = min(maxAccelSteps, calculatedSteps);
  return max(finalSteps, (long)20); // Minimum 20 steps for smooth acceleration
}

long calculateDecelSteps(int id, long totalSteps) {
  if (steppers[id].deceleration <= 0) return 0;
  
  // Calculate steps based on speed difference and deceleration setting
  int speedDiff = steppers[id].maxDelay - steppers[id].speed;
  long calculatedSteps = (speedDiff / 50) * steppers[id].deceleration; // More gradual
  
  // Limit deceleration to reasonable portion of total steps
  long maxDecelSteps = min((long)(totalSteps * 0.3), (long)200); // Max 30% or 200 steps
  long finalSteps = min(maxDecelSteps, calculatedSteps);
  return max(finalSteps, (long)20); // Minimum 20 steps for smooth deceleration
}

int calculateAccelDelay(int id, long currentStep, long totalAccelSteps, int startDelay, int endDelay) {
  if (totalAccelSteps == 0) return endDelay;
  
  // Use smooth exponential curve for acceleration
  float progress = (float)currentStep / (float)totalAccelSteps;
  float smoothProgress = 1.0 - pow(1.0 - progress, 2.0); // Exponential ease-out
  int newDelay = startDelay - (int)((startDelay - endDelay) * smoothProgress);
  
  // Ensure minimum step size for smoothness
  int maxStep = max(1, (startDelay - endDelay) / 20);
  int prevDelay = steppers[id].currentDelay;
  if (abs(newDelay - prevDelay) > maxStep) {
    newDelay = prevDelay + (newDelay > prevDelay ? maxStep : -maxStep);
  }
  
  return max(newDelay, steppers[id].minDelay);
}

int calculateDecelDelay(int id, long currentStep, long totalDecelSteps, int startDelay, int endDelay) {
  if (totalDecelSteps == 0) return startDelay;
  
  // Use smooth exponential curve for deceleration
  float progress = (float)currentStep / (float)totalDecelSteps;
  float smoothProgress = pow(progress, 2.0); // Exponential ease-in
  int newDelay = startDelay + (int)((endDelay - startDelay) * smoothProgress);
  
  // Ensure minimum step size for smoothness
  int maxStep = max(1, (endDelay - startDelay) / 20);
  int prevDelay = steppers[id].currentDelay;
  if (abs(newDelay - prevDelay) > maxStep) {
    newDelay = prevDelay + (newDelay > prevDelay ? maxStep : -maxStep);
  }
  
  return min(newDelay, steppers[id].maxDelay);
}

bool readLimitSwitch(int pin) {
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
