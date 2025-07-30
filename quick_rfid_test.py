#!/usr/bin/env python3
"""
Quick RFID Test - Simple test to verify RFID reader is working
"""
import sys
import time
from datetime import datetime

def quick_rfid_test():
    """Quick test of RFID reader functionality"""
    print("🔍 Quick RFID Reader Test")
    print("="*40)
    
    # Test 1: Import library
    print("1. Testing MFRC522 library...")
    try:
        import mfrc522
        print("   ✅ Library imported successfully")
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        print("   📥 Install with: pip install mfrc522")
        return False
    
    # Test 2: Initialize reader
    print("\\n2. Initializing RFID reader...")
    try:
        reader = mfrc522.SimpleMFRC522()
        print("   ✅ Reader initialized")
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        print("   💡 Check SPI enable and wiring")
        return False
    
    # Test 3: Card detection
    print("\\n3. Testing card detection...")
    print("   📋 Place an RFID card near the reader (20s timeout)")
    
    start_time = time.time()
    card_detected = False
    
    try:
        while time.time() - start_time < 20:
            try:
                id, text = reader.read_no_block()
                if id is not None:
                    print(f"   ✅ Card detected!")
                    print(f"      ID: {id}")
                    print(f"      Text: '{text.strip()}'")
                    card_detected = True
                    break
            except:
                pass
            time.sleep(0.2)
        
        if not card_detected:
            print("   ⏰ No card detected in 20 seconds")
            print("   💡 Try different card or check reader position")
    
    except KeyboardInterrupt:
        print("\\n   🛑 Test stopped by user")
    
    print("\\n" + "="*40)
    if card_detected:
        print("🎉 RFID reader is working!")
    else:
        print("⚠️  Reader initialized but no card detected")
    
    return True

if __name__ == "__main__":
    try:
        quick_rfid_test()
    except KeyboardInterrupt:
        print("\\n🛑 Test interrupted")
    except Exception as e:
        print(f"\\n❌ Test error: {e}")
