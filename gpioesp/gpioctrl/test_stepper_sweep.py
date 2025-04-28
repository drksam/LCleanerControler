import time
from gpioctrl import GPIOController

# Initialize controller
gpio = GPIOController(port="/dev/ttyUSB0")  # Adjust if needed

# Stepper configuration
STEP_PIN = 25
DIR_PIN = 26
HOME_PIN = 0     # unused
LIMIT_A = 0      # unused
LIMIT_B = 0      # unused
ENABLE_PIN = 27
MIN_LIMIT = -50
MAX_LIMIT = 250
SPEED = 200       # microseconds per step

# Init stepper motor
gpio.init_stepper(
    id=0,
    step_pin=STEP_PIN,
    dir_pin=DIR_PIN,
    limit_a=LIMIT_A,
    limit_b=LIMIT_B,
    home=HOME_PIN,
    min_limit=MIN_LIMIT,
    max_limit=MAX_LIMIT,
    enable_pin=ENABLE_PIN
)

try:
    while True:
        print("?? Forward 200 steps")
        result = gpio.move_stepper(id=0, steps=2, direction=1, speed=SPEED, wait=True)
        print("? Done:", result)

        time.sleep(1)

        print("?? Backward 200 steps")
        result = gpio.move_stepper(id=0, steps=2, direction=0, speed=SPEED, wait=True)
        print("? Done:", result)

        time.sleep(1)

except KeyboardInterrupt:
    print("Stepper test interrupted.")
    gpio.stop()
