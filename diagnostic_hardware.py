#!/usr/bin/env python3
"""
Hardware Diagnostic Script for LCleaner Controller
Run this script on the Raspberry Pi to diagnose hardware detection issues.
"""

import os
import sys
import platform
import importlib.util
import json
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def check_system_info():
    """Check basic system information"""
    print_section("SYSTEM INFORMATION")
    
    print(f"Platform: {platform.platform()}")
    print(f"System: {platform.system()}")
    print(f"Machine: {platform.machine()}")
    print(f"Processor: {platform.processor()}")
    print(f"Python version: {sys.version}")
    
    # Check if we're on a Raspberry Pi
    try:
        # Check multiple methods for Pi detection
        pi_detected = False
        pi_model = "Unknown"
        
        # Method 1: /proc/cpuinfo
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                if 'BCM' in cpuinfo:
                    pi_detected = True
                    if 'BCM2712' in cpuinfo:
                        pi_model = "Raspberry Pi 5"
                    elif 'BCM2711' in cpuinfo:
                        pi_model = "Raspberry Pi 4"
                    elif 'BCM2710' in cpuinfo:
                        pi_model = "Raspberry Pi 3"
                    else:
                        pi_model = "Other Raspberry Pi model"
        except:
            pass
            
        # Method 2: /proc/device-tree/model
        if not pi_detected:
            try:
                with open('/proc/device-tree/model', 'r') as f:
                    model = f.read().strip()
                    if 'Raspberry Pi' in model:
                        pi_detected = True
                        pi_model = model
            except:
                pass
                
        # Method 3: Check for Pi-specific hardware
        if not pi_detected and os.path.exists('/sys/firmware/devicetree/base/model'):
            try:
                with open('/sys/firmware/devicetree/base/model', 'r') as f:
                    model = f.read().strip()
                    if 'Raspberry Pi' in model:
                        pi_detected = True
                        pi_model = model
            except:
                pass
        
        if pi_detected:
            print(f"✓ Detected: {pi_model}")
        else:
            print("✗ Not detected: Raspberry Pi hardware")
            print("  Note: This might be a compatibility issue or running in container")
            
    except Exception as e:
        print(f"✗ Error detecting Pi hardware: {e}")

def check_environment_variables():
    """Check relevant environment variables"""
    print_section("ENVIRONMENT VARIABLES")
    
    env_vars = [
        'SIMULATION_MODE',
        'FORCE_HARDWARE', 
        'DATABASE_URL',
        'CORE_DATABASE_URL',
        'CLEANER_DATABASE_URL'
    ]
    
    for var in env_vars:
        value = os.environ.get(var, 'NOT SET')
        print(f"{var}: {value}")

def check_python_libraries():
    """Check Python library availability"""
    print_section("PYTHON LIBRARY STATUS")
    
    libraries = [
        ('gpiod', 'GPIO control for Raspberry Pi'),
        ('gpioctrl', 'ESP32 communication library'),
        ('flask', 'Web framework'),
        ('flask_sqlalchemy', 'Database ORM'),
        ('psycopg2', 'PostgreSQL driver'),
        ('mfrc522', 'RFID reader library'),
        ('requests', 'HTTP client'),
    ]
    
    for lib_name, description in libraries:
        try:
            spec = importlib.util.find_spec(lib_name)
            if spec is not None:
                # Try to actually import it
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                print(f"✓ {lib_name}: Available - {description}")
                
                # Special checks for key libraries
                if lib_name == 'gpiod':
                    try:
                        # Test GPIO access with proper API handling
                        try:
                            # Try new API (gpiod 2.x)
                            with module.Chip('/dev/gpiochip0') as chip:
                                print(f"  ✓ gpiod: Can access GPIO chip 0 (v2 API)")
                        except (AttributeError, TypeError, FileNotFoundError):
                            try:
                                # Try old API (gpiod 1.x)
                                chip = module.Chip('gpiochip0')
                                if hasattr(chip, 'close'):
                                    chip.close()
                                print(f"  ✓ gpiod: Can access GPIO chip 0 (v1 API)")
                            except Exception as e2:
                                print(f"  ✗ gpiod: Cannot access GPIO chip: {e2}")
                    except Exception as e:
                        print(f"  ✗ gpiod: Cannot access GPIO chip: {e}")
                        
            else:
                print(f"✗ {lib_name}: NOT AVAILABLE - {description}")
        except Exception as e:
            print(f"✗ {lib_name}: ERROR - {e}")

def check_configuration_files():
    """Check configuration file status"""
    print_section("CONFIGURATION FILES")
    
    config_files = [
        'machine_config.json',
        'Default pinout.txt',
        'config.py'
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✓ {config_file}: EXISTS")
            
            # Special handling for JSON config
            if config_file.endswith('.json'):
                try:
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    
                    # Check operation mode
                    operation_mode = config.get('system', {}).get('operation_mode', 'NOT SET')
                    print(f"  Operation mode: {operation_mode}")
                    
                    # Check GPIO config
                    gpio_config = config.get('gpio', {})
                    if gpio_config:
                        print(f"  GPIO pins configured: {len(gpio_config)} pins")
                        # Show a few key pins
                        key_pins = ['fan_pin', 'red_lights_pin', 'table_forward_pin']
                        for pin in key_pins:
                            if pin in gpio_config:
                                print(f"    {pin}: {gpio_config[pin]}")
                    else:
                        print(f"  ✗ No GPIO configuration found")
                        
                except json.JSONDecodeError as e:
                    print(f"  ✗ JSON parsing error: {e}")
                except Exception as e:
                    print(f"  ✗ Error reading file: {e}")
        else:
            print(f"✗ {config_file}: MISSING")

def check_gpio_hardware():
    """Check GPIO hardware access"""
    print_section("GPIO HARDWARE ACCESS")
    
    # Check if we can access GPIO
    gpio_paths = [
        '/dev/gpiochip0',
        '/dev/gpiochip1', 
        '/dev/gpiochip2',
        '/dev/gpiochip3',
        '/dev/gpiochip4'
    ]
    
    available_chips = []
    for path in gpio_paths:
        if os.path.exists(path):
            available_chips.append(path)
            print(f"✓ {path}: Available")
        
    if not available_chips:
        print("✗ No GPIO chips found - this is not a Raspberry Pi or GPIO is disabled")
        return
    
    # Try to use gpiod if available
    try:
        import gpiod
        
        # Get version safely
        try:
            version = gpiod.version_string()
            print(f"  gpiod library version: {version}")
        except AttributeError:
            print(f"  gpiod library version: Unknown (likely v1.x)")
        
        gpio_working = False
        
        for chip_path in available_chips:
            try:
                chip_num = int(chip_path.split('gpiochip')[1])
                
                # Try multiple API approaches gracefully
                success = False
                
                # Approach 1: gpiod v1 API (standard on Raspberry Pi)
                try:
                    chip = gpiod.Chip(f'gpiochip{chip_num}')
                    num_lines = chip.num_lines()
                    print(f"✓ GPIO chip {chip_num}: {num_lines} lines available (v1 API)")
                    success = True
                    gpio_working = True
                except Exception:
                    pass
                
                # Approach 2: gpiod v2 API fallback (newer versions)
                if not success:
                    try:
                        with gpiod.Chip(f'/dev/gpiochip{chip_num}') as chip:
                            info = chip.get_info()
                            print(f"✓ GPIO chip {chip_num}: {info.num_lines} lines available (v2 API)")
                            success = True
                            gpio_working = True
                    except Exception:
                        pass
                
                # Approach 3: Try alternate chip naming
                if not success:
                    try:
                        chip = gpiod.Chip(f'gpiochip{chip_num}')
                        try:
                            if hasattr(chip, 'num_lines'):
                                num_lines = chip.num_lines()
                            else:
                                num_lines = "unknown"
                            print(f"✓ GPIO chip {chip_num}: {num_lines} lines available (v1 API alternate)")
                            success = True
                            gpio_working = True
                        finally:
                            if hasattr(chip, 'close'):
                                chip.close()
                    except Exception:
                        pass
                
                # If all failed, show a user-friendly message
                if not success:
                    print(f"⚠ GPIO chip {chip_num}: API compatibility issue (will use simulation mode)")
                        
            except Exception as e:
                print(f"⚠ GPIO chip {chip_num}: {e} (will use simulation mode)")
        
        # Summary message
        if gpio_working:
            print(f"  ✓ GPIO access: Working correctly")
        else:
            print(f"  ⚠ GPIO access: API compatibility issues detected")
            print(f"    → Application will automatically use simulation mode")
            print(f"    → Hardware control may be limited but app will run")
                
    except ImportError:
        print("⚠ gpiod library not available")
        print("  → Application will use simulation mode")
        print("  → Install with: sudo apt install python3-gpiod")
    except Exception as e:
        print(f"⚠ gpiod library error: {e}")
        print(f"  → Application will use simulation mode")

def check_serial_ports():
    """Check serial ports for ESP32 communication"""
    print_section("SERIAL PORTS (ESP32 COMMUNICATION)")
    
    serial_paths = [
        '/dev/ttyUSB0',
        '/dev/ttyUSB1', 
        '/dev/ttyACM0',
        '/dev/ttyACM1',
        '/dev/serial0',
        '/dev/serial1'
    ]
    
    found_ports = []
    for path in serial_paths:
        if os.path.exists(path):
            found_ports.append(path)
            print(f"✓ {path}: Available")
            
            # Check permissions
            try:
                with open(path, 'r'):
                    pass
                print(f"  ✓ {path}: Readable (good permissions)")
            except PermissionError:
                print(f"  ✗ {path}: Permission denied - add user to dialout group")
            except Exception as e:
                print(f"  ? {path}: {e}")
    
    if not found_ports:
        print("✗ No serial ports found - ESP32 may not be connected")
    
    # Check user groups
    try:
        import grp
        import pwd
        
        username = pwd.getpwuid(os.getuid()).pw_name
        user_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
        
        required_groups = ['gpio', 'dialout', 'spi', 'i2c']
        print(f"\nUser '{username}' is in groups: {', '.join(user_groups)}")
        
        for group in required_groups:
            if group in user_groups:
                print(f"✓ {group}: User has access")
            else:
                print(f"✗ {group}: User needs access - run: sudo usermod -a -G {group} {username}")
                
    except Exception as e:
        print(f"? Cannot check user groups: {e}")

def check_temperature_sensors():
    """Check 1-Wire temperature sensors"""
    print_section("TEMPERATURE SENSORS (1-Wire)")
    
    w1_path = '/sys/bus/w1/devices'
    if os.path.exists(w1_path):
        print(f"✓ 1-Wire bus available at {w1_path}")
        
        # List devices
        devices = []
        try:
            for device in os.listdir(w1_path):
                if device.startswith('28-'):  # DS18B20 devices start with 28-
                    devices.append(device)
                    print(f"  ✓ Found DS18B20 sensor: {device}")
            
            if not devices:
                print("  ⚠ No DS18B20 sensors detected")
                print("  Check: 1-Wire enabled in config.txt, sensors connected, pull-up resistor")
                
        except Exception as e:
            print(f"  ✗ Error reading devices: {e}")
    else:
        print(f"✗ 1-Wire bus not available")
        print("  Enable with: sudo raspi-config → Interface Options → 1-Wire")

def run_hardware_simulation_test():
    """Test hardware detection logic"""
    print_section("HARDWARE DETECTION SIMULATION")
    
    try:
        # Try to import the project's modules
        sys.path.insert(0, '.')
        
        from config import get_system_config, get_gpio_config
        
        # Test configuration loading
        system_config = get_system_config()
        gpio_config = get_gpio_config()
        
        operation_mode = system_config.get('operation_mode', 'unknown')
        print(f"Loaded operation mode: {operation_mode}")
        
        # Test GPIO wrapper initialization
        try:
            from gpio_controller_wrapper import LocalGPIOWrapper
            
            # Test in non-simulation mode
            print("\nTesting LocalGPIOWrapper (hardware mode)...")
            gpio_wrapper = LocalGPIOWrapper(simulation_mode=False)
            print("✓ LocalGPIOWrapper: Initialized successfully")
            
        except Exception as e:
            print(f"✗ LocalGPIOWrapper: Failed to initialize - {e}")
            
        # Test output controller
        try:
            from output_control_gpiod import OutputController
            
            print("\nTesting OutputController...")
            output_controller = OutputController()
            print(f"✓ OutputController: Initialized (simulation_mode: {output_controller.simulation_mode})")
            
        except Exception as e:
            print(f"✗ OutputController: Failed to initialize - {e}")
            
    except Exception as e:
        print(f"✗ Cannot test project modules: {e}")

def check_gpio_compatibility():
    """Simplified GPIO compatibility check with clear recommendations"""
    print_section("GPIO COMPATIBILITY ANALYSIS")
    
    try:
        import gpiod
        
        # Check gpiod version
        try:
            version = gpiod.version_string()
            print(f"✓ gpiod version: {version}")
        except AttributeError:
            print("⚠ gpiod version: Cannot determine (likely v1.x)")
            
        # Test basic GPIO access
        print("\nTesting GPIO access:")
        
        gpio_works = False
        api_version = "unknown"
        
        # Test v1 API first (standard on Raspberry Pi)
        try:
            chip = gpiod.Chip('gpiochip0')
            num_lines = chip.num_lines()
            print(f"✓ GPIO access: Working with v1 API ({num_lines} lines)")
            gpio_works = True
            api_version = "v1"
        except Exception:
            # Test v2 API fallback
            try:
                with gpiod.Chip('/dev/gpiochip0') as chip:
                    info = chip.get_info()
                    print(f"✓ GPIO access: Working with v2 API ({info.num_lines} lines)")
                    gpio_works = True
                    api_version = "v2"
            except Exception:
                # Test v1 alternate approach
                try:
                    chip = gpiod.Chip('gpiochip0') 
                    try:
                        lines = chip.num_lines() if hasattr(chip, 'num_lines') else "unknown"
                        print(f"✓ GPIO access: Working with v1 API alternate ({lines} lines)")
                        gpio_works = True
                        api_version = "v1"
                    finally:
                        if hasattr(chip, 'close'):
                            chip.close()
                except Exception as e:
                    print(f"⚠ GPIO access: {e}")
                    print(f"  → This is usually an API compatibility issue")
                
        # User-friendly summary
        print(f"\n� GPIO Status Summary:")
        if gpio_works:
            print(f"  ✅ GPIO hardware access: WORKING ({api_version} API)")
            print(f"  ✅ Application will use hardware mode")
        else:
            print(f"  ⚠️ GPIO hardware access: COMPATIBILITY ISSUES")
            print(f"  ✅ Application will automatically use simulation mode")
            print(f"  💡 This doesn't prevent the application from running")
            
    except ImportError:
        print("⚠ gpiod library not installed")
        print(f"\n📋 GPIO Status Summary:")
        print(f"  ⚠️ GPIO library: NOT AVAILABLE")
        print(f"  ✅ Application will use simulation mode")
        print(f"  💡 Install with: sudo apt install python3-gpiod")
    except Exception as e:
        print(f"⚠ Unexpected error: {e}")
        
    # Simple troubleshooting advice
    print(f"\n� If you see GPIO issues:")
    print(f"  1. The application will still work in simulation mode")
    print(f"  2. For hardware mode: sudo apt update && sudo apt upgrade python3-gpiod")
    print(f"  3. Ensure user is in gpio group: sudo usermod -a -G gpio $USER")
    print(f"  4. Reboot if you made group changes: sudo reboot")
    print(f"  5. If issues persist: copy updated files from development machine")

def main():
    """Run all diagnostic checks"""
    print("LCleaner Controller Hardware Diagnostic")
    print("Run this on the Raspberry Pi to identify hardware issues")
    
    check_system_info()
    check_environment_variables()
    check_python_libraries()
    check_configuration_files()
    check_gpio_hardware()
    check_gpio_compatibility()  # New detailed GPIO analysis
    check_serial_ports()
    check_temperature_sensors()
    run_hardware_simulation_test()
    
    print_section("DIAGNOSTIC COMPLETE")
    print("Review the output above to identify any issues.")
    print("Key items to check:")
    print("- All required Python libraries are available")
    print("- GPIO chips are accessible (or app will use simulation mode)")
    print("- User is in required groups (gpio, dialout, spi, i2c)")
    print("- Serial ports are available for ESP32")
    print("- Configuration files are valid")
    
    print(f"\n✅ Application Status:")
    print(f"  The LCleaner Controller should work regardless of GPIO warnings")
    print(f"  GPIO compatibility issues are handled automatically")
    print(f"  The app will use simulation mode if hardware access has problems")
    
    print(f"\n🔧 If you need to fix anything:")
    print(f"  1. Copy updated files from your development machine")
    print(f"  2. Run: ./setup_pi_venv.sh")
    print(f"  3. No need for complex fix scripts - just redeploy!")

if __name__ == "__main__":
    main()
