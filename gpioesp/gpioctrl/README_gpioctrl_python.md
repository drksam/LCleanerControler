
# GPIO Controller Python Module

This Python module (`gpioctrl`) allows control of an ESP32-based GPIO expansion device, designed for:

- 🚀 Offloading servo and stepper motor control to an ESP32
- ✅ Bidirectional serial communication (feedback, status, homing)
- ✅ Compatibility with Raspberry Pi 5 (BCM2712)

---

## 📦 Installation

### Using pip in development mode:

```bash
git clone <your-repo-url>
cd gpioctrl
pip install -e . --break-system-packages
```

Or if downloaded from zip:

```bash
unzip gpioctrl_python_package.zip
cd gpioctrl_python_package
pip install -e . --break-system-packages
```

> The `--break-system-packages` flag is required on Raspberry Pi OS Bookworm or newer.

---

## ⚙️ ESP32 Firmware Requirements

Ensure the ESP32 is flashed with the matching firmware provided in the `/firmware` folder or ZIP. It should support:

- Servo commands via `ESP32Servo`
- Stepper motor motion
- Enable pin and soft limits
- Homing and `"stepper_done"` event feedback

---

## 🧪 Usage Examples

### Initialize Controller

```python
from gpioctrl import GPIOController
gpio = GPIOController(port="/dev/ttyUSB0")  # or /dev/serial0, etc.
```

---

### Set Servo Angle

```python
gpio.set_servo(pin=12, angle=90)
```

---

### Initialize Stepper

```python
gpio.init_stepper(
    id=0,
    step_pin=25,
    dir_pin=26,
    limit_a=0,
    limit_b=0,
    home=0,
    min_limit=-100,
    max_limit=500,
    enable_pin=27
)
```

---

### Move Stepper and Wait for Done

```python
gpio.move_stepper(id=0, steps=200, direction=1, speed=1000, wait=True)
```

---

### Home Stepper

```python
gpio.home_stepper(id=0, wait=True)
```

---

### Pause / Resume / Stop Stepper

```python
gpio.pause_stepper(id=0)
gpio.resume_stepper(id=0)
gpio.stop_stepper(id=0)
```

---

### Get Last Feedback

```python
feedback = gpio.get_feedback()
print(feedback)
```

---

## 🔧 RPi5 GPIO + gpiod Integration (Example)

```python
import gpiod

chip = gpiod.Chip('gpiochip4')  # GPIO 16 and 26 on Pi 5
line26 = chip.get_line(26)
line26.request(consumer="example", type=gpiod.LINE_REQ_DIR_OUT)

line26.set_value(0)
time.sleep(1)
line26.set_value(1)
```

---

## 🧪 Test Scripts Included

- `test_servo_sweep.py`: Sweeps servo 0° → 90° → 180° → 0°
- `test_stepper_sweep.py`: Moves stepper 200 steps forward and back, waits for `stepper_done`
- `rpi5_dual_gpio_demo.py`: Full demo using ESP32 + Raspberry Pi 5 onboard GPIO (via `gpiod`)

---

## 🔌 Supported Python Versions

- Python 3.7+
- Raspberry Pi OS Bookworm (3.11+) ✅
- Compatible with `libgpiod` for Pi 5 GPIO access

---

## 📫 Feedback

Open issues or suggestions via GitHub or your support channel.
