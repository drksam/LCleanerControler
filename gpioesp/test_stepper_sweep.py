import time
from gpioctrl import GPIOController

gpio = GPIOController(port="/dev/ttyUSB0")  # Adjust if needed

# Initialize stepper without physical limits
gpio.init_stepper(
    id=0,
    step_pin=25,
    dir_pin=26,
    limit_a=0,     # dummy unused pin
    limit_b=0,     # dummy unused pin
    home=0,        # dummy unused pin
    min_limit=-50,
    max_limit=250
)

try:
    while True:
        print("Moving forward 400 steps")
        gpio.move_stepper(id=0, steps=400, direction=1, speed=1000)
        time.sleep(1)

        print("Moving backward 400 steps")
        gpio.move_stepper(id=0, steps=400, direction=0, speed=1000)
        time.sleep(1)
except KeyboardInterrupt:
    print("Stepper test interrupted by user.")
    gpio.stop()
