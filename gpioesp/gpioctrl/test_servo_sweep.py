import time
from gpioctrl import GPIOController

# Initialize the GPIO controller
gpio = GPIOController(port="/dev/ttyUSB0")  # Change if needed

try:
    while True:
        for angle in [0, 90, 180, 90]:
            print(f"Setting servo to {angle}°")
            gpio.set_servo(pin=12, angle=angle)
            time.sleep(1)
except KeyboardInterrupt:
    print("Servo test interrupted by user.")
finally:
    gpio.stop()
