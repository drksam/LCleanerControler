"""
Test all GPIO outputs and inputs using pin numbers from config.py.
- Blinks each output (LED) for 2 seconds.
- For each input (button), waits for a state change before moving to the next.
- Designed for use on real hardware (not simulation).
"""
import time
import logging
import importlib

# Import config and GPIO wrapper
def import_config():
    try:
        config = importlib.import_module('config')
        return config
    except Exception as e:
        print(f"Failed to import config.py: {e}")
        exit(1)

def import_gpio_wrapper():
    try:
        wrapper = importlib.import_module('gpio_controller_wrapper')
        return wrapper
    except Exception as e:
        print(f"Failed to import gpio_controller_wrapper.py: {e}")
        exit(1)

config = import_config()
gpio_module = import_gpio_wrapper()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

# Get pin lists from config
OUTPUT_PINS = []
INPUT_PINS = []

# Try to get pin lists from config.py (adapt as needed for your config structure)
try:
    if hasattr(config, 'OUTPUT_PINS'):
        OUTPUT_PINS = list(config.OUTPUT_PINS)
    if hasattr(config, 'INPUT_PINS'):
        INPUT_PINS = list(config.INPUT_PINS)
    # Fallback: try to collect pins from known config attributes
    if not OUTPUT_PINS:
        OUTPUT_PINS = [
            getattr(config, k) for k in dir(config)
            if k.startswith('OUT_') or k.startswith('OUTPUT_')
            and isinstance(getattr(config, k), int)
        ]
    if not INPUT_PINS:
        INPUT_PINS = [
            getattr(config, k) for k in dir(config)
            if k.startswith('IN_') or k.startswith('INPUT_')
            and isinstance(getattr(config, k), int)
        ]
except Exception as e:
    logging.error(f"Error extracting pin lists from config: {e}")
    exit(1)

logging.info(f"Output pins: {OUTPUT_PINS}")
logging.info(f"Input pins: {INPUT_PINS}")

# Initialize GPIO wrapper
try:
    gpio = gpio_module.LocalGPIOWrapper()
except Exception as e:
    logging.error(f"Failed to initialize GPIO wrapper: {e}")
    exit(1)

# Test outputs: blink each LED
for pin in OUTPUT_PINS:
    try:
        logging.info(f"Testing OUTPUT pin {pin}: ON for 2s, then OFF.")
        gpio.setup_output(pin)
        gpio.write_output(pin, 1)
        time.sleep(2)
        gpio.write_output(pin, 0)
        time.sleep(0.5)
    except Exception as e:
        logging.error(f"Error testing output pin {pin}: {e}")

# Test inputs: wait for state change
for pin in INPUT_PINS:
    try:
        gpio.setup_input(pin)
        initial = gpio.read_input(pin)
        logging.info(f"Testing INPUT pin {pin}: waiting for state change (current state: {initial})...")
        print(f"Press/release button on INPUT pin {pin} to continue...")
        while True:
            val = gpio.read_input(pin)
            if val != initial:
                logging.info(f"Detected state change on INPUT pin {pin} (from {initial} to {val})")
                break
            time.sleep(0.05)
        time.sleep(0.5)
    except Exception as e:
        logging.error(f"Error testing input pin {pin}: {e}")

logging.info("GPIO test complete.")
print("GPIO test complete.")
