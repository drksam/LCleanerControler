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

# Get pin lists from config using get_gpio_config() and gpio_pin_types
OUTPUT_PINS = []
INPUT_PINS = []
gpio_config = None
gpio_pin_types = None
try:
    if hasattr(config, 'get_gpio_config'):
        gpio_config = config.get_gpio_config()
        print(f"gpio_config: {gpio_config}")
        logging.info(f"gpio_config: {gpio_config}")
        # Try to get pin types from config (from machine_config.json)
        if hasattr(config, 'config') and 'gpio_pin_types' in config.config:
            gpio_pin_types = config.config['gpio_pin_types']
            print(f"gpio_pin_types: {gpio_pin_types}")
            logging.info(f"gpio_pin_types: {gpio_pin_types}")
            for pin_name, pin_type in gpio_pin_types.items():
                if pin_name in gpio_config:
                    if pin_type == 'OUT':
                        OUTPUT_PINS.append(gpio_config[pin_name])
                    elif pin_type == 'IN':
                        INPUT_PINS.append(gpio_config[pin_name])
        else:
            print("gpio_pin_types not found in config.config!")
            logging.error("gpio_pin_types not found in config.config!")
    else:
        print("config.get_gpio_config() not found!")
        logging.error("config.get_gpio_config() not found!")
except Exception as e:
    logging.error(f"Error extracting pin lists from get_gpio_config and gpio_pin_types: {e}")
    print(f"Error extracting pin lists from get_gpio_config and gpio_pin_types: {e}")
    exit(1)
print(f"Detected OUTPUT_PINS: {OUTPUT_PINS}")
print(f"Detected INPUT_PINS: {INPUT_PINS}")
logging.info(f"Detected OUTPUT_PINS: {OUTPUT_PINS}")
logging.info(f"Detected INPUT_PINS: {INPUT_PINS}")

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
        gpio.write(pin, 1)
        time.sleep(2)
        gpio.write(pin, 0)
        time.sleep(0.5)
    except Exception as e:
        logging.error(f"Error testing output pin {pin}: {e}")

# Test inputs: wait for state change
for pin in INPUT_PINS:
    try:
        gpio.setup_input(pin)
        initial = gpio.read(pin)
        logging.info(f"Testing INPUT pin {pin}: waiting for state change (current state: {initial})...")
        print(f"Press/release button on INPUT pin {pin} to continue...")
        while True:
            val = gpio.read(pin)
            if val != initial:
                logging.info(f"Detected state change on INPUT pin {pin} (from {initial} to {val})")
                break
            time.sleep(0.05)
        time.sleep(0.5)
    except Exception as e:
        logging.error(f"Error testing input pin {pin}: {e}")

logging.info("GPIO test complete.")
print("GPIO test complete.")
