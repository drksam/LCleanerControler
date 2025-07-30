#!/usr/bin/env python3
"""
RFID Test Script for Pi 5 - Using gpiod instead of RPi.GPIO
Tests the MFRC522 RFID reader hardware and software functionality.
"""
import os
import sys
import time
import logging
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_gpio_config, get_rfid_config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RFIDTesterPi5:
    """Test class for RFID functionality on Pi 5"""
    
    def __init__(self):
        """Initialize the RFID tester"""
        self.running = False
        self.gpio_config = get_gpio_config()
        self.rfid_config = get_rfid_config()
        self.reader = None
        
        # Get RFID pin configuration
        self.mosi_pin = self.gpio_config.get('rfid_mosi_pin', 10)
        self.miso_pin = self.gpio_config.get('rfid_miso_pin', 9)
        self.sclk_pin = self.gpio_config.get('rfid_sclk_pin', 11)
        self.ce0_pin = self.gpio_config.get('rfid_ce0_pin', 8)
        
        print("="*60)
        print("RFID READER TEST SCRIPT (Pi 5 Compatible)")
        print("="*60)
        print(f"Configuration:")
        print(f"  MOSI Pin: GPIO {self.mosi_pin}")
        print(f"  MISO Pin: GPIO {self.miso_pin}")
        print(f"  SCLK Pin: GPIO {self.sclk_pin}")
        print(f"  CE0 Pin:  GPIO {self.ce0_pin}")
        print(f"  Server URL: {self.rfid_config.get('server_url', 'Not configured')}")
        print(f"  Machine ID: {self.rfid_config.get('machine_id', 'Not configured')}")
        print("="*60)
    
    def test_mfrc522_import(self):
        """Test if the MFRC522 library can be imported"""
        print("\\n1. Testing MFRC522 library import...")
        try:
            import mfrc522
            print("   ✅ MFRC522 library imported successfully")
            return True
        except ImportError as e:
            print(f"   ❌ Failed to import MFRC522 library: {e}")
            print("   📥 Install with: pip install mfrc522")
            return False
    
    def test_gpiod_access(self):
        """Test gpiod library access (Pi 5 compatible)"""
        print("\\n2. Testing GPIO access (gpiod)...")
        try:
            import gpiod
            
            # Try to access GPIO chip
            chip = gpiod.Chip('gpiochip4')  # Pi 5 uses gpiochip4
            
            # Test access to one of the RFID pins
            test_pin = self.ce0_pin
            line = chip.get_line(test_pin)
            line.request(consumer="rfid_test", type=gpiod.LINE_REQ_DIR_OUT)
            line.set_value(1)
            time.sleep(0.01)
            line.set_value(0)
            line.release()
            chip.close()
            
            print("   ✅ GPIO access working (gpiod)")
            return True
        except ImportError:
            print("   ⚠️  gpiod library not available")
            print("   📥 Install with: pip install gpiod")
            return self.test_rpi_gpio_fallback()
        except Exception as e:
            print(f"   ⚠️  gpiod access failed: {e}")
            return self.test_rpi_gpio_fallback()
    
    def test_rpi_gpio_fallback(self):
        """Fallback test using RPi.GPIO"""
        print("   🔄 Trying RPi.GPIO fallback...")
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Test setting up one of the RFID pins
            test_pin = self.ce0_pin
            GPIO.setup(test_pin, GPIO.OUT)
            GPIO.output(test_pin, GPIO.HIGH)
            time.sleep(0.01)
            GPIO.output(test_pin, GPIO.LOW)
            GPIO.cleanup(test_pin)
            
            print("   ✅ GPIO access working (RPi.GPIO)")
            return True
        except Exception as e:
            print(f"   ❌ RPi.GPIO also failed: {e}")
            print("   💡 This might be a Pi 5 compatibility issue")
            print("   💡 RFID might still work if SPI is functioning")
            return False
    
    def test_spi_initialization(self):
        """Test SPI interface initialization"""
        print("\\n3. Testing SPI initialization...")
        try:
            import mfrc522
            
            # Initialize the RFID reader
            self.reader = mfrc522.SimpleMFRC522()
            print("   ✅ MFRC522 reader initialized successfully")
            return True
        except Exception as e:
            print(f"   ❌ Failed to initialize MFRC522 reader: {e}")
            print("   💡 Check:")
            print("     - SPI is enabled (raspi-config)")
            print("     - RFID module wiring")
            print("     - Power connections (3.3V not 5V)")
            return False
    
    def test_card_detection(self, timeout=30):
        """Test card detection functionality"""
        print(f"\\n4. Testing card detection (timeout: {timeout}s)...")
        if not self.reader:
            print("   ❌ Reader not initialized")
            return False
        
        print("   📋 Place an RFID card/tag near the reader...")
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                try:
                    # Try to read card (non-blocking)
                    id, text = self.reader.read_no_block()
                    if id is not None:
                        print(f"   ✅ Card detected!")
                        print(f"      Card ID: {id}")
                        print(f"      Card Text: '{text.strip()}'")
                        return True
                except Exception as e:
                    # Ignore read errors and continue trying
                    pass
                
                time.sleep(0.1)  # Small delay
                
                # Show progress every 5 seconds
                elapsed = time.time() - start_time
                if int(elapsed) % 5 == 0 and elapsed > 0:
                    remaining = timeout - elapsed
                    print(f"   ⏱️  Still waiting... {remaining:.0f}s remaining")
                    time.sleep(1)  # Prevent multiple prints per second
            
            print(f"   ⏰ Timeout after {timeout}s - no card detected")
            print("   💡 Try:")
            print("     - Moving card closer to reader")
            print("     - Different RFID card/tag")
            print("     - Check antenna connections")
            return False
            
        except Exception as e:
            print(f"   ❌ Error during card detection: {e}")
            return False
    
    def test_card_reading_loop(self, duration=60):
        """Test continuous card reading in a loop"""
        print(f"\\n5. Testing continuous card reading ({duration}s)...")
        if not self.reader:
            print("   ❌ Reader not initialized")
            return False
        
        print("   📋 Place and remove RFID cards to test continuous reading...")
        print("   📝 Press Ctrl+C to stop early")
        
        start_time = time.time()
        last_card_id = None
        card_count = 0
        
        try:
            while time.time() - start_time < duration:
                try:
                    id, text = self.reader.read_no_block()
                    current_time = time.time()
                    
                    if id is not None and id != last_card_id:
                        card_count += 1
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"   [{timestamp}] Card #{card_count}: ID={id}, Text='{text.strip()}'")
                        last_card_id = id
                        last_read_time = current_time
                    
                    # Reset last_card_id if no card present for a while
                    if id is None and last_card_id is not None:
                        if current_time - last_read_time > 1.0:  # 1 second delay
                            last_card_id = None
                    
                except Exception as e:
                    # Ignore individual read errors but count them
                    pass
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\\n   🛑 Test stopped by user")
        
        print(f"   📊 Total unique cards detected: {card_count}")
        return card_count > 0
    
    def test_spi_interface(self):
        """Test SPI interface availability"""
        print("\\n6. Testing SPI interface...")
        try:
            # Check if SPI device files exist
            spi_devices = ['/dev/spidev0.0', '/dev/spidev0.1']
            spi_found = any(os.path.exists(device) for device in spi_devices)
            
            if spi_found:
                print("   ✅ SPI device files found")
                
                # Try to access SPI
                try:
                    import spidev
                    spi = spidev.SpiDev()
                    spi.open(0, 0)  # Bus 0, Device 0
                    spi.close()
                    print("   ✅ SPI interface accessible")
                    return True
                except Exception as e:
                    print(f"   ⚠️  SPI access issue: {e}")
                    print("   💡 SPI devices exist but access failed")
                    return False
            else:
                print("   ❌ SPI device files not found")
                print("   💡 Enable SPI with: sudo raspi-config")
                print("     Interface Options -> SPI -> Enable")
                return False
                
        except ImportError:
            print("   ❌ spidev module not available")
            print("   📥 Install with: pip install spidev")
            return False
    
    def run_full_test(self):
        """Run the complete RFID test suite"""
        print("Starting comprehensive RFID test...")
        
        tests = [
            ("Library Import", self.test_mfrc522_import),
            ("SPI Interface", self.test_spi_interface),
            ("GPIO Access", self.test_gpiod_access),
            ("SPI Initialization", self.test_spi_initialization),
            ("Card Detection", lambda: self.test_card_detection(20)),
            ("Continuous Reading", lambda: self.test_card_reading_loop(30))
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                results[test_name] = result
                
                # Stop if critical tests fail
                if not result and test_name in ["Library Import", "SPI Interface"]:
                    print(f"\\n❌ Critical test '{test_name}' failed - stopping test suite")
                    break
                    
            except KeyboardInterrupt:
                print("\\n🛑 Test suite interrupted by user")
                break
            except Exception as e:
                print(f"\\n❌ Test '{test_name}' crashed: {e}")
                results[test_name] = False
        
        # Print summary
        print("\\n" + "="*60)
        print("TEST RESULTS SUMMARY")
        print("="*60)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:20} : {status}")
            if result:
                passed += 1
        
        print("-"*60)
        print(f"TOTAL: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! RFID reader is working correctly.")
        elif passed >= 4:  # If at least basic functionality works
            print("✅ RFID reader is functional! Some optional tests failed.")
        elif passed > 0:
            print("⚠️  Some tests failed. Check connections and configuration.")
        else:
            print("❌ All tests failed. Check hardware setup and dependencies.")
        
        print("="*60)
        
        return passed >= 4  # Consider success if core functionality works

def main():
    """Main test function"""
    tester = RFIDTesterPi5()
    
    try:
        success = tester.run_full_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\\n🛑 Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test script error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
