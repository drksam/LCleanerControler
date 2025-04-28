import time
import gpiod
from gpioctrl import GPIOController

# === Step 1: Initialize ESP32 Controller ===
gpio = GPIOController(port="/dev/ttyUSB0")

# Init stepper
gpio.init_stepper(
    id=0,
    step_pin=25,
    dir_pin=26,
    limit_a=0,
    limit_b=0,
    home=0,
    min_limit=-500,
    max_limit=500,
    enable_pin=0
)

# === Step 2: Run Stepper 400 steps forward ===
print("Running stepper forward 400 steps")
gpio.move_stepper(id=0, steps=400, direction=1, speed=1000)
time.sleep(1)
# === Step 3: Move Servo to 90° ===
print("Setting servo to 90°")
gpio.set_servo(pin=12, angle=90)
time.sleep(1)

# === Step 4: Local GPIO 26 LOW for 1s then HIGH ===
chip = gpiod.Chip('gpiochip4')  # RPi5 GPIO 26 and 16 are on gpiochip4
line26 = chip.get_line(26)
line26.request(consumer="gpioctrl-local", type=gpiod.LINE_REQ_DIR_OUT)

print("Setting GPIO 26 HIGH for 1s")
line26.set_value(1)
time.sleep(1)
print("Setting GPIO 26 LOW")
line26.set_value(0)

# === Step 5: GPIO 16 PWM from 0-100% over 2.5s and back ===
line16 = chip.get_line(16)
line16.request(consumer="gpioctrl-pwm", type=gpiod.LINE_REQ_DIR_OUT)

print("PWM GPIO 16 0% -> 100%")
for duty in range(0, 101, 5):
    line16.set_value(1)
    time.sleep((duty / 100.0) * 0.025)
    line16.set_value(0)
    time.sleep((1 - duty / 100.0) * 0.025)

print("PWM GPIO 16 100% -> 0%")
for duty in reversed(range(0, 101, 5)):
    line16.set_value(1)
    time.sleep((duty / 100.0) * 0.025)
    line16.set_value(0)
    time.sleep((1 - duty / 100.0) * 0.025)

# === Step 6: Move Servo to 0° ===
print("Returning servo to 0°")
gpio.set_servo(pin=12, angle=0)
time.sleep(1)

# === Step 7: Return Stepper to Position 0 ===
print("Returning stepper to 0")
gpio.move_stepper(id=0, steps=400, direction=0, speed=1000)
time.sleep(1)

# Cleanup
gpio.stop()
line26.release()
line16.release()
chip.close()
print("Done!")
