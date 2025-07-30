import time
import logging
from gpio_controller_wrapper import LocalGPIOWrapper

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

def main():
    print("Starting minimal LocalGPIOWrapper test...")
    wrapper = LocalGPIOWrapper(simulation_mode=False)
    test_pin_out = 26  # Use a safe output pin
    test_pin_in = 12   # Use a safe input pin (wired to GND or 3.3V for test)

    # Test output setup and write
    print("Setting up output pin {}...".format(test_pin_out))
    wrapper.setup_output(test_pin_out, initial_value=0)
    for i in range(5):
        print(f"Setting pin {test_pin_out} HIGH")
        wrapper.write(test_pin_out, 1)
        time.sleep(0.5)
        print(f"Setting pin {test_pin_out} LOW")
        wrapper.write(test_pin_out, 0)
        time.sleep(0.5)

    # Test input setup and read
    print("Setting up input pin {}...".format(test_pin_in))
    wrapper.setup_input(test_pin_in, pull_up=True)
    for i in range(10):
        val = wrapper.read(test_pin_in)
        print(f"Read pin {test_pin_in}: {val}")
        time.sleep(0.2)

    # Test cleanup
    print("Cleaning up pins...")
    wrapper.cleanup(test_pin_out)
    wrapper.cleanup(test_pin_in)
    print("Test complete.")

if __name__ == "__main__":
    main()
