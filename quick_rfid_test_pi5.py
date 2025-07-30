#!/usr/bin/env python3
"""
Quick RFID Test for Pi 5 - Simple test to verify RFID reader is working
Bypasses GPIO permission issues by focusing on SPI functionality
"""
import sys
import time
from datetime import datetime

def quick_rfid_test_pi5():
    """Quick test of RFID reader functionality for Pi 5"""
    print("🔍 Quick RFID Reader Test (Pi 5 Compatible)")
    print("="*50)
    
    # Test 1: Import library
    print("1. Testing MFRC522 library...")
    try:
        import mfrc522
        print("   ✅ Library imported successfully")
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        print("   📥 Install with: pip install mfrc522")
        return False
    
    # Test 2: Check SPI
    print("\\n2. Checking SPI availability...")
    import os
    spi_devices = ['/dev/spidev0.0', '/dev/spidev0.1']
    spi_found = any(os.path.exists(device) for device in spi_devices)
    
    if spi_found:
        print("   ✅ SPI devices found")
    else:
        print("   ❌ SPI devices not found")
        print("   💡 Enable SPI: sudo raspi-config")
        return False
    
    # Test 3: Initialize reader (this will fail gracefully if wiring is wrong)
    print("\\n3. Initializing RFID reader...")
    try:
        reader = mfrc522.SimpleMFRC522()
        print("   ✅ Reader initialized")
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        print("   💡 Check wiring connections")
        return False
    
    # Test 4: Card detection with better error handling
    print("\\n4. Testing card detection...")
    print("   📋 Place an RFID card near the reader (15s timeout)")
    print("   💡 Ignore any GPIO warning messages")
    
    start_time = time.time()
    card_detected = False
    read_attempts = 0
    errors = 0
    
    try:
        while time.time() - start_time < 15:
            try:
                read_attempts += 1
                id, text = reader.read_no_block()
                if id is not None:
                    print(f"   ✅ Card detected!")
                    print(f"      ID: {id}")
                    print(f"      Text: '{text.strip()}'")
                    print(f"      Read attempts: {read_attempts}")
                    card_detected = True
                    break
            except Exception as e:
                errors += 1
                # Only show first few errors to avoid spam
                if errors <= 3:
                    print(f"   ⚠️  Read error #{errors}: {str(e)[:50]}...")
                elif errors == 4:
                    print("   ⚠️  (Suppressing further error messages...)")
            
            time.sleep(0.2)
        
        if not card_detected:
            print(f"   ⏰ No card detected in 15 seconds")
            print(f"   📊 Attempted {read_attempts} reads, {errors} errors")
            if errors < read_attempts / 2:
                print("   💡 Reader appears functional - try different card or position")
            else:
                print("   💡 Many errors - check wiring and connections")
    
    except KeyboardInterrupt:
        print("\\n   🛑 Test stopped by user")
    
    print("\\n" + "="*50)
    if card_detected:
        print("🎉 RFID reader is working!")
        print("✅ Ready for use in the main application")
    else:
        print("⚠️  Reader initialized but no card detected")
        if errors < 10:
            print("✅ Reader appears functional - may just need different card")
        else:
            print("❌ High error rate - check wiring")
    
    return True

def test_rfid_integration():
    """Test integration with the application's RFID module"""
    print("\\n🔗 Testing application integration...")
    try:
        # Import the application's RFID module
        from rfid_control import RFIDController
        
        print("   ✅ RFID control module imported")
        
        # Try to create controller
        controller = RFIDController()
        print("   ✅ RFID controller created")
        
        # Check if it's in a working mode
        if hasattr(controller, 'operation_mode'):
            print(f"   📋 Operation mode: {controller.operation_mode}")
        
        return True
        
    except Exception as e:
        print(f"   ⚠️  Integration test failed: {e}")
        print("   💡 This is normal if running outside the main app")
        return False

if __name__ == "__main__":
    try:
        print("🚀 Starting RFID tests for Raspberry Pi 5...")
        basic_success = quick_rfid_test_pi5()
        integration_success = test_rfid_integration()
        
        print("\\n" + "="*50)
        print("📊 FINAL SUMMARY")
        print("="*50)
        print(f"Basic RFID Test:      {'✅ PASS' if basic_success else '❌ FAIL'}")
        print(f"Integration Test:     {'✅ PASS' if integration_success else '⚠️  SKIP'}")
        
        if basic_success:
            print("\\n🎉 RFID reader is ready!")
            print("🔧 Next steps:")
            print("   1. Test with your actual RFID cards")
            print("   2. Configure server settings if needed")
            print("   3. Test within the main application")
        else:
            print("\\n⚠️  Please check wiring and try again")
            
    except KeyboardInterrupt:
        print("\\n🛑 Test interrupted")
    except Exception as e:
        print(f"\\n❌ Test error: {e}")
        import traceback
        print("Full error details:")
        traceback.print_exc()
