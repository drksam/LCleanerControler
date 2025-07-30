#!/usr/bin/env python3
"""
RFID Reader Test Script
Tests the MFRC522 RFID reader hardware and software functionality.
"""
import os
import sys
import time
import logging
import threading
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

class RFIDTester:
    """Test class for RFID functionality"""
    
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
        print("RFID READER TEST SCRIPT")
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
    
    def test_spi_initialization(self):
        """Test SPI interface initialization"""
        print("\\n2. Testing SPI initialization...")
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
            print("     - GPIO permissions")
            return False
    
    def test_card_detection(self, timeout=30):
        """Test card detection functionality"""
        print(f"\\n3. Testing card detection (timeout: {timeout}s)...")
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
            return False
            
        except Exception as e:
            print(f"   ❌ Error during card detection: {e}")
            return False
    
    def test_card_reading_continuous(self, duration=60):
        """Test continuous card reading"""
        print(f"\\n4. Testing continuous card reading ({duration}s)...")
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
                    if id is not None and id != last_card_id:
                        card_count += 1
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"   [{timestamp}] Card #{card_count}: ID={id}, Text='{text.strip()}'")
                        last_card_id = id
                    
                    # Reset last_card_id if no card present for a while
                    if id is None and last_card_id is not None:
                        # Small delay before resetting to avoid flicker
                        time.sleep(0.5)
                        id2, _ = self.reader.read_no_block()
                        if id2 is None:
                            last_card_id = None
                    
                except Exception as e:
                    # Ignore individual read errors
                    pass
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\\n   🛑 Test stopped by user")
        
        print(f"   📊 Total unique cards detected: {card_count}")
        return card_count > 0
    
    def test_gpio_permissions(self):
        """Test GPIO permissions"""
        print("\\n5. Testing GPIO permissions...")
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            
            # Test setting up one of the RFID pins
            test_pin = self.ce0_pin
            GPIO.setup(test_pin, GPIO.OUT)
            GPIO.output(test_pin, GPIO.HIGH)
            time.sleep(0.1)
            GPIO.output(test_pin, GPIO.LOW)
            GPIO.cleanup(test_pin)
            
            print("   ✅ GPIO permissions OK")
            return True
        except Exception as e:
            print(f"   ❌ GPIO permission error: {e}")
            print("   💡 Try running with sudo or add user to gpio group:")
            print("     sudo usermod -a -G gpio $USER")
            return False
    
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
                import spidev
                spi = spidev.SpiDev()
                spi.open(0, 0)  # Bus 0, Device 0
                spi.close()
                print("   ✅ SPI interface accessible")
                return True
            else:
                print("   ❌ SPI device files not found")
                print("   💡 Enable SPI with: sudo raspi-config")
                print("     Interface Options -> SPI -> Enable")
                return False
                
        except ImportError:
            print("   ❌ spidev module not available")
            print("   📥 Install with: pip install spidev")
            return False
        except Exception as e:
            print(f"   ❌ SPI interface error: {e}")
            return False
    
    def run_full_test(self):
        """Run the complete RFID test suite"""
        print("Starting comprehensive RFID test...")
        
        tests = [
            ("Library Import", self.test_mfrc522_import),
            ("GPIO Permissions", self.test_gpio_permissions),
            ("SPI Interface", self.test_spi_interface),
            ("SPI Initialization", self.test_spi_initialization),
            ("Card Detection", lambda: self.test_card_detection(30)),
            ("Continuous Reading", lambda: self.test_card_reading_continuous(30))
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
        elif passed > 0:
            print("⚠️  Some tests failed. Check connections and configuration.")
        else:
            print("❌ All tests failed. Check hardware setup and dependencies.")
        
        print("="*60)
        
        return passed == total

def main():
    """Main test function"""
    tester = RFIDTester()
    
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
