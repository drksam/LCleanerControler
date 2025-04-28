import serial
import json
import threading
import time

class GPIOController:
    def __init__(self, port="/dev/ttyUSB0", baudrate=115200):
        self.ser = serial.Serial(port, baudrate, timeout=1)
        self.lock = threading.Lock()
        self.running = True
        self.feedback = {}
        self.last_event = {}
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()

    def _listen(self):
        while self.running:
            try:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode().strip()
                    if line:
                        data = json.loads(line)
                        self._handle_feedback(data)
            except Exception as e:
                print("Error in _listen:", e)

    def _handle_feedback(self, data):
        with self.lock:
            self.feedback.update(data)
            if "event" in data:
                self.last_event = data

    def _send_cmd(self, cmd):
        with self.lock:
            self.ser.write((json.dumps(cmd) + "\n").encode())

    def set_servo(self, pin, angle):
        self._send_cmd({"cmd": "set_servo", "pin": pin, "angle": angle})

    def set_pin(self, pin, state):
        self._send_cmd({"cmd": "set_pin", "pin": pin, "state": state})

    def init_stepper(self, id, step_pin, dir_pin, limit_a, limit_b, home,
                     min_limit, max_limit, enable_pin=None):
        cmd = {
            "cmd": "init_stepper",
            "id": id,
            "step_pin": step_pin,
            "dir_pin": dir_pin,
            "limit_a": limit_a,
            "limit_b": limit_b,
            "home": home,
            "min_limit": min_limit,
            "max_limit": max_limit
        }
        if enable_pin is not None:
            cmd["enable_pin"] = enable_pin
        self._send_cmd(cmd)

    def move_stepper(self, id, steps, direction, speed, wait=False, timeout=10):
        self.last_event = {}
        self._send_cmd({
            "cmd": "move_stepper",
            "id": id,
            "steps": steps,
            "dir": direction,
            "speed": speed
        })
        if wait:
            return self.wait_for_stepper_done(id, timeout)

    def home_stepper(self, id, wait=False, timeout=10):
        self.last_event = {}
        self._send_cmd({"cmd": "home_stepper", "id": id})
        if wait:
            return self.wait_for_stepper_done(id, timeout)

    def pause_stepper(self, id):
        self._send_cmd({"cmd": "pause_stepper", "id": id})

    def resume_stepper(self, id):
        self._send_cmd({"cmd": "resume_stepper", "id": id})

    def stop_stepper(self, id):
        self._send_cmd({"cmd": "stop_stepper", "id": id})

    def get_status(self):
        self._send_cmd({"cmd": "get_status"})
        time.sleep(0.1)
        return self.get_feedback()

    def get_feedback(self):
        with self.lock:
            return self.feedback.copy()

    def wait_for_stepper_done(self, id, timeout=10):
        start = time.time()
        while time.time() - start < timeout:
            with self.lock:
                event = self.last_event.copy()
            if event.get("event") == "stepper_done" and event.get("id") == id:
                return event
            time.sleep(0.05)
        raise TimeoutError("Stepper did not complete within timeout.")

    def stop(self):
        self.running = False
        self.thread.join()
        self.ser.close()

# Example test
if __name__ == "__main__":
    gpio = GPIOController()
    gpio.set_servo(pin=12, angle=90)
    gpio.init_stepper(id=0, step_pin=25, dir_pin=26, limit_a=0, limit_b=0, home=0, min_limit=-50, max_limit=250, enable_pin=27)
    gpio.move_stepper(id=0, steps=200, direction=1, speed=10, wait=True)
    gpio.home_stepper(id=0, wait=True)
    gpio.stop()
