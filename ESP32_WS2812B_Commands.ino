/*
This is a sketch for the ESP32 that will be uploaded to the ESP32 board.
It receives commands from the Raspberry Pi over Serial to control WS2812B LEDs.

Commands:
- Initialize WS2812B: {"cmd": "init_ws2812b", "pin": 23, "num_leds": 1}
- Set LED color: {"cmd": "set_ws2812b_color", "r": 255, "g": 0, "b": 0}
- Set LED brightness: {"cmd": "set_ws2812b_brightness", "brightness": 50}

This should be added to the existing ESP32 firmware.
*/

#include <FastLED.h>

// WS2812B LED configuration
#define MAX_LEDS 16  // Maximum number of LEDs supported
CRGB leds[MAX_LEDS];
uint8_t numLeds = 1;
uint8_t ledPin = 23;  // Default pin
uint8_t brightness = 128;  // Default brightness (0-255)
bool ledsInitialized = false;

// Function to handle WS2812B LED commands
void handleLEDCommands(JsonObject& json) {
  String cmd = json["cmd"].as<String>();
  
  if (cmd == "init_ws2812b") {
    // Initialize WS2812B LEDs
    if (ledsInitialized) {
      // Clean up previous initialization
      FastLED.clear();
      FastLED.show();
    }
    
    ledPin = json["pin"] | 23;
    numLeds = json["num_leds"] | 1;
    
    if (numLeds > MAX_LEDS) {
      numLeds = MAX_LEDS;
    }
    
    // Initialize FastLED
    FastLED.addLeds<WS2812B, ledPin, GRB>(leds, numLeds);
    FastLED.setBrightness(brightness);
    FastLED.clear();
    FastLED.show();
    
    ledsInitialized = true;
    
    // Send response
    StaticJsonDocument<200> response;
    response["status"] = "ok";
    response["message"] = "WS2812B initialized";
    response["pin"] = ledPin;
    response["num_leds"] = numLeds;
    
    serializeJson(response, Serial);
    Serial.println();
    
  } else if (cmd == "set_ws2812b_color") {
    if (!ledsInitialized) {
      // Initialize with defaults if not done yet
      FastLED.addLeds<WS2812B, 23, GRB>(leds, 1);
      FastLED.setBrightness(brightness);
      ledsInitialized = true;
    }
    
    // Set LED color
    uint8_t r = json["r"] | 0;
    uint8_t g = json["g"] | 0;
    uint8_t b = json["b"] | 0;
    
    // Set the color for all LEDs
    for (int i = 0; i < numLeds; i++) {
      leds[i] = CRGB(r, g, b);
    }
    
    FastLED.show();
    
  } else if (cmd == "set_ws2812b_brightness") {
    if (!ledsInitialized) {
      // Initialize with defaults if not done yet
      FastLED.addLeds<WS2812B, 23, GRB>(leds, 1);
      ledsInitialized = true;
    }
    
    // Set brightness (0-100 input mapped to 0-255)
    uint8_t bright = json["brightness"] | 50;
    brightness = map(bright, 0, 100, 0, 255);
    
    FastLED.setBrightness(brightness);
    FastLED.show();
  }
}
