import sys
import subprocess
import importlib
import pkg_resources
import platform
import shutil

REQUIRED_PYTHON = (3, 7)
REQUIREMENTS_FILE = "requirements.txt"

# 1. Check Python version
def check_python_version():
    print(f"Python version: {platform.python_version()}")
    if sys.version_info < REQUIRED_PYTHON:
        print(f"[FAIL] Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+ required.")
        return False
    print("[OK] Python version is sufficient.")
    return True

# 2. Check Python packages
def check_python_packages():
    print("\nChecking Python packages from requirements.txt...")
    missing = []
    with open(REQUIREMENTS_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'): continue
            pkg = line.split('==')[0] if '==' in line else line
            try:
                pkg_resources.require(line)
                print(f"[OK] {line}")
            except pkg_resources.DistributionNotFound:
                print(f"[FAIL] {pkg} not installed.")
                missing.append(pkg)
            except pkg_resources.VersionConflict as e:
                print(f"[FAIL] {pkg} version conflict: {e}")
                missing.append(pkg)
    if missing:
        print("\nMissing or incompatible packages:", ", ".join(missing))
    else:
        print("All required Python packages are installed.")
    return not missing

# 3. Check for gpiod system dependency
def check_gpiod():
    print("\nChecking for gpiod system dependency...")
    gpiod_cmd = shutil.which("gpiodetect")
    if gpiod_cmd:
        print(f"[OK] gpiodetect found at {gpiod_cmd}")
    else:
        print("[FAIL] gpiodetect not found in PATH. libgpiod may not be installed.")
    return bool(gpiod_cmd)

# 4. Check for ESP32-based GPIO controller (gpioctrl)
def check_gpioctrl():
    print("\nChecking for ESP32-based GPIO controller Python package (gpioctrl)...")
    try:
        import gpioctrl
        print("[OK] gpioctrl package is importable.")
        return True
    except ImportError:
        print("[FAIL] gpioctrl package is not importable.")
        return False

# 5. Optionally check for serial ports (for ESP32 connection)
def check_serial_ports():
    print("\nChecking for available serial ports (ESP32 connection)...")
    try:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("[WARN] No serial ports found.")
        else:
            print("[OK] Serial ports found:")
            for port in ports:
                print(f"  - {port.device} ({port.description})")
        return True
    except ImportError:
        print("[FAIL] pyserial not installed. Cannot check serial ports.")
        return False

if __name__ == "__main__":
    print("=== ShopLaserRoom System Requirements Check ===\n")
    ok = check_python_version()
    ok &= check_python_packages()
    ok &= check_gpiod()
    ok &= check_gpioctrl()
    check_serial_ports()
    print("\n=== Check Complete ===")
    if not ok:
        print("\nSome requirements are missing or incompatible. Please review the output above.")
    else:
        print("\nAll critical requirements are satisfied.")
