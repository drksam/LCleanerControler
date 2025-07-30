#!/usr/bin/env python3
"""
RFID Wiring Guide and Verification
Shows expected wiring connections and tests basic GPIO functionality
"""
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_gpio_config

def show_wiring_guide():
    """Display the RFID wiring guide based on configuration"""
    gpio_config = get_gpio_config()
    
    # Get RFID pin configuration
    mosi_pin = gpio_config.get('rfid_mosi_pin', 10)
    miso_pin = gpio_config.get('rfid_miso_pin', 9)
    sclk_pin = gpio_config.get('rfid_sclk_pin', 11)
    ce0_pin = gpio_config.get('rfid_ce0_pin', 8)
    
    print("🔌 RFID READER WIRING GUIDE")
    print("="*50)
    print("Based on your machine_config.json settings:")
    print()
    
    print("MFRC522 Module    →    Raspberry Pi")
    print("-"*40)
    print(f"VCC (3.3V)        →    Pin 1  (3.3V)")
    print(f"RST               →    Pin 22 (GPIO 25) - Not used")
    print(f"GND               →    Pin 6  (GND)")
    print(f"MISO              →    Pin 21 (GPIO {miso_pin})")
    print(f"MOSI              →    Pin 19 (GPIO {mosi_pin})")
    print(f"SCK               →    Pin 23 (GPIO {sclk_pin})")
    print(f"SDA/SS            →    Pin 24 (GPIO {ce0_pin})")
    print()
    
    print("🔧 PHYSICAL PIN LAYOUT (Raspberry Pi GPIO Header)")
    print("="*50)
    print("    3.3V  [1] [2]  5V")
    print("   GPIO2  [3] [4]  5V")
    print("   GPIO3  [5] [6]  GND     ← Connect RFID GND here")
    print("   GPIO4  [7] [8]  GPIO14")
    print("     GND  [9][10]  GPIO15")
    print("  GPIO17 [11][12]  GPIO18")
    print("  GPIO27 [13][14]  GND")
    print("  GPIO22 [15][16]  GPIO23")
    print("    3.3V [17][18]  GPIO24")
    print(f"  GPIO{mosi_pin:2d} [19][20]  GND")
    print(f"  GPIO{miso_pin:2d} [21][22]  GPIO25")
    print(f"  GPIO{sclk_pin:2d} [23][24]  GPIO{ce0_pin:2d}    ← Connect RFID SDA here")
    print("     GND [25][26]  GPIO7")
    print()
    
    print("⚠️  IMPORTANT NOTES:")
    print("1. Use 3.3V power, NOT 5V (can damage the module)")
    print("2. Make sure SPI is enabled: sudo raspi-config")
    print("3. Ensure good connections (no loose wires)")
    print("4. Keep wires short to avoid interference")
    print()
    
    return {
        'mosi_pin': mosi_pin,
        'miso_pin': miso_pin,
        'sclk_pin': sclk_pin,
        'ce0_pin': ce0_pin
    }

def test_spi_enabled():
    """Check if SPI is enabled"""
    print("🔍 CHECKING SPI STATUS")
    print("="*30)
    
    # Check SPI device files
    spi_devices = ['/dev/spidev0.0', '/dev/spidev0.1']
    spi_found = False
    
    for device in spi_devices:
        if os.path.exists(device):
            print(f"✅ Found: {device}")
            spi_found = True
        else:
            print(f"❌ Missing: {device}")
    
    if spi_found:
        print("✅ SPI appears to be enabled")
    else:
        print("❌ SPI not enabled")
        print("💡 Enable with: sudo raspi-config")
        print("   Interface Options → SPI → Yes")
        print("   Then reboot: sudo reboot")
    
    return spi_found

def test_gpio_access():
    """Test basic GPIO access"""
    print("\\n🔍 TESTING GPIO ACCESS")
    print("="*30)
    
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        
        # Test a safe pin (not used by RFID)
        test_pin = 18  # Safe test pin
        GPIO.setup(test_pin, GPIO.OUT)
        GPIO.output(test_pin, GPIO.HIGH)
        GPIO.output(test_pin, GPIO.LOW)
        GPIO.cleanup(test_pin)
        
        print("✅ GPIO access working")
        return True
        
    except Exception as e:
        print(f"❌ GPIO access failed: {e}")
        print("💡 Try adding user to gpio group:")
        print("   sudo usermod -a -G gpio $USER")
        print("   Then logout and login again")
        return False

def check_rfid_library():
    """Check if RFID library is installed"""
    print("\\n🔍 CHECKING RFID LIBRARY")
    print("="*30)
    
    try:
        import mfrc522
        print("✅ mfrc522 library is installed")
        return True
    except ImportError:
        print("❌ mfrc522 library not found")
        print("📥 Install with:")
        print("   pip install mfrc522")
        print("   # or")
        print("   sudo pip install mfrc522")
        return False

def main():
    """Main verification function"""
    print("🔌 RFID SETUP VERIFICATION TOOL")
    print("="*50)
    
    # Show wiring guide
    pins = show_wiring_guide()
    
    # Run checks
    spi_ok = test_spi_enabled()
    gpio_ok = test_gpio_access()
    lib_ok = check_rfid_library()
    
    # Summary
    print("\\n📊 SETUP VERIFICATION SUMMARY")
    print("="*40)
    print(f"SPI Enabled:      {'✅ Yes' if spi_ok else '❌ No'}")
    print(f"GPIO Access:      {'✅ Yes' if gpio_ok else '❌ No'}")
    print(f"RFID Library:     {'✅ Yes' if lib_ok else '❌ No'}")
    
    if all([spi_ok, gpio_ok, lib_ok]):
        print("\\n🎉 All checks passed! Ready to test RFID reader.")
        print("\\nNext steps:")
        print("1. Run: python quick_rfid_test.py")
        print("2. Or run: python test_rfid.py (full test)")
    else:
        print("\\n⚠️  Some checks failed. Fix the issues above first.")
    
    print("="*50)

if __name__ == "__main__":
    main()
