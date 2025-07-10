#!/usr/bin/env python3
"""
Pin Configuration Analyzer
Compares pin assignments between different configuration sources
"""

import json
import os

def load_machine_config():
    """Load machine_config.json"""
    try:
        with open('machine_config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading machine_config.json: {e}")
        return None

def parse_pinout_txt():
    """Parse Default pinout.txt"""
    pinout_data = {}
    
    try:
        with open('Default pinout.txt', 'r') as f:
            content = f.read()
            
        # Parse the pinout file
        lines = content.split('\n')
        current_device = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if 'ESP32' in line:
                current_device = 'ESP32'
                continue
            elif 'Raspberry Pi5' in line:
                current_device = 'RaspberryPi'
                continue
                
            # Parse pin assignments
            if current_device == 'RaspberryPi':
                if 'FW (Physical pin' in line:
                    # Extract BCM pin
                    bcm_part = line.split('BCM ')[1].split(',')[0]
                    pinout_data['table_forward_pin'] = int(bcm_part)
                elif 'RV (Physical pin' in line:
                    bcm_part = line.split('BCM ')[1].split(',')[0]
                    pinout_data['table_backward_pin'] = int(bcm_part)
                elif 'Fan (Physical pin' in line:
                    bcm_part = line.split('BCM ')[1].split(',')[0]
                    pinout_data['fan_pin'] = int(bcm_part)
                elif 'Red Lights (Physical pin' in line:
                    bcm_part = line.split('BCM ')[1].split(',')[0]
                    pinout_data['red_lights_pin'] = int(bcm_part)
                elif 'FIRE (Physical pin' in line:
                    bcm_part = line.split('BCM ')[1].split(',')[0]
                    pinout_data['fire_button_pin'] = int(bcm_part)
                elif 'In (Physical pin' in line and 'button' not in line.lower():
                    bcm_part = line.split('BCM ')[1].split(',')[0]
                    pinout_data['button_in_pin'] = int(bcm_part)
                elif 'OUT (Physical pin' in line:
                    bcm_part = line.split('BCM ')[1].split(',')[0]
                    pinout_data['button_out_pin'] = int(bcm_part)
                    
    except Exception as e:
        print(f"Error parsing Default pinout.txt: {e}")
        
    return pinout_data

def compare_configurations():
    """Compare pin configurations between sources"""
    print("="*70)
    print(" PIN CONFIGURATION ANALYSIS")
    print("="*70)
    
    # Load configurations
    machine_config = load_machine_config()
    pinout_config = parse_pinout_txt()
    
    if not machine_config or not pinout_config:
        print("Cannot load configuration files!")
        return
    
    gpio_config = machine_config.get('gpio', {})
    
    print(f"\n{'Pin Name':<25} {'machine_config.json':<20} {'Default pinout.txt':<20} {'Status'}")
    print("-" * 70)
    
    # Compare key pins
    key_pins = [
        'table_forward_pin',
        'table_backward_pin', 
        'fan_pin',
        'red_lights_pin',
        'fire_button_pin',
        'button_in_pin',
        'button_out_pin'
    ]
    
    conflicts = []
    
    for pin_name in key_pins:
        machine_pin = gpio_config.get(pin_name, 'NOT SET')
        pinout_pin = pinout_config.get(pin_name, 'NOT SET')
        
        if machine_pin == 'NOT SET' or pinout_pin == 'NOT SET':
            status = "MISSING"
        elif machine_pin == pinout_pin:
            status = "✓ MATCH"
        else:
            status = "✗ CONFLICT"
            conflicts.append((pin_name, machine_pin, pinout_pin))
            
        print(f"{pin_name:<25} {str(machine_pin):<20} {str(pinout_pin):<20} {status}")
    
    # Summary
    print("\n" + "="*70)
    print(" SUMMARY")
    print("="*70)
    
    if conflicts:
        print(f"⚠ Found {len(conflicts)} pin conflicts that need resolution:")
        for pin_name, machine_pin, pinout_pin in conflicts:
            print(f"  {pin_name}: machine_config={machine_pin} vs pinout={pinout_pin}")
        
        print(f"\n🔧 NEXT STEPS:")
        print(f"1. Verify actual hardware connections on the Pi")
        print(f"2. Update the incorrect configuration file")
        print(f"3. Test hardware after fixing conflicts")
    else:
        print("✓ All pin configurations match!")
    
    # Show ESP32 pins for reference
    esp32_config = gpio_config
    print(f"\n📡 ESP32 PINS (for reference):")
    esp32_pins = ['esp_step_pin', 'esp_dir_pin', 'esp_enable_pin', 'esp_servo_pwm_pin']
    for pin in esp32_pins:
        if pin in esp32_config:
            print(f"  {pin}: {esp32_config[pin]}")

def main():
    """Main function"""
    compare_configurations()
    
    print(f"\n💡 RECOMMENDATIONS:")
    print(f"1. Run this script on the Raspberry Pi after deployment")
    print(f"2. Use diagnostic_hardware.py on the Pi to test hardware detection") 
    print(f"3. Verify physical wire connections match the chosen configuration")
    print(f"4. Test each GPIO pin individually before running full system")

if __name__ == "__main__":
    main()
