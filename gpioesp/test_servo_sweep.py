import time
from gpioctrl import GPIOController

# Initialize controller
gpio = GPIOController(port="/dev/ttyUSB0")  # Adjust if needed

# Sweep pattern in degrees
angles = [0, 90, 180]

try:
    while True:
        for angle in angles:
            print(f"Setting servo on pin 12 to {angle}°")
            gpio.set_servo(pin=12, angle=angle)
            time.sleep(1)  # Wait 1 second at each position
except KeyboardInterrupt:
    print("Servo sweep stopped by user.")
    gpio.stop()
