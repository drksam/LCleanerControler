#!/usr/bin/env python3
"""
RFID Library Compatibility Test for Pi 5
Tests different RFID libraries to find Pi 5 compatible options
"""
import sys
import subprocess
import importlib

def test_library_import(library_name, install_command=None):
    """Test if a library can be imported"""
    try:
        importlib.import_module(library_name)
        print(f"   ✅ {library_name} - Available")
        return True
    except ImportError:
        print(f"   ❌ {library_name} - Not available")
        if install_command:
            print(f"      📥 Install: {install_command}")
        return False

def test_mfrc522_alternatives():
    """Test alternative RFID libraries"""
    print("🔍 Testing RFID Library Compatibility")
    print("="*50)
    
    libraries = [
        ("mfrc522", "pip install mfrc522"),
        ("pi-rc522", "pip install pi-rc522"),
        ("pn532", "pip install pn532"),
        ("nfcpy", "pip install nfcpy"),
        ("spidev", "pip install spidev"),
        ("gpiod", "pip install gpiod")
    ]
    
    available_libs = []
    
    for lib_name, install_cmd in libraries:
        if test_library_import(lib_name, install_cmd):
            available_libs.append(lib_name)
    
    print(f"\\n📊 Available libraries: {len(available_libs)}/{len(libraries)}")
    return available_libs

def test_pi_rc522():
    """Test pi-rc522 library (potentially Pi 5 compatible)"""
    print("\\n🔧 Testing pi-rc522 library...")
    try:
        from pirc522 import RFID
        
        print("   ✅ pi-rc522 imported successfully")
        
        # Try to initialize
        rdr = RFID()
        print("   ✅ RFID reader initialized")
        
        # Quick test
        print("   📋 Quick card detection test (5s)...")
        import time
        start_time = time.time()
        
        while time.time() - start_time < 5:
            rdr.wait_for_tag()
            (error, tag_type) = rdr.request()
            if not error:
                print("   ✅ Card detected with pi-rc522!")
                (error, uid) = rdr.anticoll()
                if not error:
                    print(f"      Card UID: {uid}")
                return True
            time.sleep(0.1)
        
        print("   ⏰ No card detected (normal)")
        return True  # Library works even if no card
        
    except ImportError:
        print("   ❌ pi-rc522 not available")
        print("   📥 Install: pip install pi-rc522")
        return False
    except Exception as e:
        print(f"   ⚠️  pi-rc522 error: {e}")
        return False

def check_system_info():
    """Check system information"""
    print("\\n💻 System Information")
    print("="*30)
    
    try:
        # Check Pi model
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if 'Model' in line:
                    print(f"   {line.strip()}")
                elif 'Revision' in line:
                    print(f"   {line.strip()}")
        
        # Check kernel version
        with open('/proc/version', 'r') as f:
            version = f.read().strip()
            print(f"   Kernel: {version.split()[2]}")
        
        # Check if gpiochip4 exists (Pi 5 indicator)
        import os
        if os.path.exists('/dev/gpiochip4'):
            print("   ✅ gpiochip4 detected (Pi 5)")
        else:
            print("   ❌ gpiochip4 not found")
            
    except Exception as e:
        print(f"   ⚠️  Could not read system info: {e}")

def suggest_solutions():
    """Suggest solutions for Pi 5 RFID compatibility"""
    print("\\n💡 Pi 5 RFID Solutions")
    print("="*30)
    
    print("1. 🔧 Try pi-rc522 library:")
    print("   pip install pi-rc522")
    print("   (May have better Pi 5 support)")
    
    print("\\n2. 🔧 Use direct SPI communication:")
    print("   python test_rfid_direct_spi.py")
    print("   (Bypasses GPIO library issues)")
    
    print("\\n3. 🔧 Use lgpio instead of RPi.GPIO:")
    print("   pip install lgpio")
    print("   (Modern GPIO library for Pi 5)")
    
    print("\\n4. 🔧 Try different MFRC522 library:")
    print("   pip uninstall mfrc522")
    print("   pip install mfrc522-python")
    
    print("\\n5. 🔧 Check for library updates:")
    print("   pip install --upgrade mfrc522")
    print("   (Newer versions may support Pi 5)")

def install_pi_rc522():
    """Try to install pi-rc522 automatically"""
    print("\\n📦 Installing pi-rc522...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pi-rc522"])
        print("   ✅ pi-rc522 installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Installation failed: {e}")
        return False

def main():
    """Main compatibility test"""
    print("🔍 RFID Pi 5 Compatibility Checker")
    print("="*50)
    
    # Check system
    check_system_info()
    
    # Test current libraries
    available = test_mfrc522_alternatives()
    
    # Test alternatives
    if "pi-rc522" in available:
        pi_rc522_works = test_pi_rc522()
    else:
        print("\\n📦 pi-rc522 not found, attempting installation...")
        if install_pi_rc522():
            pi_rc522_works = test_pi_rc522()
        else:
            pi_rc522_works = False
    
    # Test direct SPI if spidev available
    if "spidev" in available:
        print("\\n🔧 Direct SPI communication is possible")
        print("   Run: python test_rfid_direct_spi.py")
    
    # Summary and suggestions
    print("\\n" + "="*50)
    print("📊 COMPATIBILITY SUMMARY")
    print("="*50)
    
    if "pi-rc522" in available and pi_rc522_works:
        print("🎉 Recommended: Use pi-rc522 library")
        print("✅ This should work on Pi 5")
    elif "spidev" in available:
        print("🔧 Recommended: Use direct SPI communication")
        print("✅ This bypasses GPIO library issues")
    else:
        print("⚠️  Limited options available")
    
    suggest_solutions()
    print("="*50)

if __name__ == "__main__":
    main()
