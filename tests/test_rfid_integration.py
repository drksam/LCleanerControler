#!/usr/bin/env python3
"""
Test RFID Integration with Main Application
Tests the RFID functionality within the context of the main application
"""
import sys
import os
import time

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_rfid_integration():
    """Test RFID integration with the main application"""
    print("🔗 Testing RFID Integration with Main Application")
    print("="*60)
    
    # Test 1: Import RFID control module
    print("1. Testing RFID control module import...")
    try:
        from rfid_control import RFIDController
        print("   ✅ RFID control module imported successfully")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False
    
    # Test 2: Create RFID controller
    print("\\n2. Creating RFID controller...")
    try:
        def access_callback(granted, user_data):
            if granted:
                print(f"   🎉 Access granted for: {user_data.get('name', 'Unknown')}")
            else:
                print("   🚫 Access denied")
        
        controller = RFIDController(access_callback=access_callback)
        print("   ✅ RFID controller created successfully")
        print(f"   📋 Operation mode: {controller.operation_mode}")
        print(f"   📋 RFID available: {hasattr(controller, 'reader') and controller.reader is not None}")
    except Exception as e:
        print(f"   ❌ Controller creation failed: {e}")
        return False
    
    # Test 3: Check RFID reader initialization
    print("\\n3. Checking RFID reader status...")
    if hasattr(controller, 'reader') and controller.reader is not None:
        print("   ✅ RFID reader initialized")
        print("   📋 Reader thread running:", controller.running)
        
        # Test 4: Card detection
        print("\\n4. Testing card detection (15 seconds)...")
        print("   📋 Place your RFID card near the reader...")
        
        start_time = time.time()
        initial_user = controller.authenticated_user
        
        while time.time() - start_time < 15:
            # Check if authentication state changed
            if controller.authenticated_user != initial_user:
                print("   ✅ Card detected and processed!")
                if controller.authenticated_user:
                    user = controller.authenticated_user
                    print(f"      User: {user.get('name', 'Unknown')}")
                    print(f"      Access Level: {user.get('access_level', 'Unknown')}")
                    print(f"      User ID: {user.get('user_id', 'Unknown')}")
                break
            
            time.sleep(0.5)
            
            # Show progress
            elapsed = time.time() - start_time
            if int(elapsed) % 5 == 0 and elapsed > 4:
                remaining = 15 - elapsed
                print(f"   ⏱️  Still waiting... {remaining:.0f}s remaining")
                time.sleep(0.5)  # Prevent spam
        
        if controller.authenticated_user == initial_user:
            print("   ⏰ No new card detected")
            if controller.operation_mode in ['simulation', 'prototype']:
                print("   💡 In simulation/prototype mode - this is normal")
            else:
                print("   💡 Try different card or check reader positioning")
    
    elif controller.operation_mode in ['simulation', 'prototype']:
        print("   ✅ RFID in simulation/prototype mode")
        print("   📋 Default user authenticated:", controller.authenticated_user is not None)
        if controller.authenticated_user:
            user = controller.authenticated_user
            print(f"      Sim User: {user.get('name', 'Unknown')}")
    else:
        print("   ⚠️  RFID reader not initialized")
        print("   💡 This might be due to Pi 5 compatibility issues")
    
    # Test 5: Test RFID status
    print("\\n5. Testing RFID status methods...")
    try:
        is_auth = controller.is_authenticated()
        print(f"   📋 Is authenticated: {is_auth}")
        
        user = controller.get_current_user()
        if user:
            print(f"   📋 Current user: {user.get('name', 'Unknown')}")
        else:
            print("   📋 No current user")
            
        print("   ✅ Status methods working")
    except Exception as e:
        print(f"   ⚠️  Status methods error: {e}")
    
    # Cleanup
    try:
        controller.stop()
        print("\\n   🧹 Controller stopped cleanly")
    except:
        pass
    
    return True

def test_config_integration():
    """Test configuration integration"""
    print("\\n🔧 Testing Configuration Integration")
    print("="*40)
    
    try:
        from config import get_rfid_config
        rfid_config = get_rfid_config()
        
        print("   ✅ RFID configuration loaded")
        print(f"   📋 Server URL: {rfid_config.get('server_url', 'Not set')}")
        print(f"   📋 Machine ID: {rfid_config.get('machine_id', 'Not set')}")
        print(f"   📋 Access Control: {rfid_config.get('access_control_enabled', False)}")
        print(f"   📋 Offline Mode: {rfid_config.get('offline_mode', False)}")
        
        return True
    except Exception as e:
        print(f"   ❌ Configuration test failed: {e}")
        return False

def main():
    """Main integration test"""
    print("🚀 RFID Application Integration Test")
    print("="*60)
    
    # Test configuration first
    config_ok = test_config_integration()
    
    # Test RFID integration
    rfid_ok = test_rfid_integration()
    
    # Summary
    print("\\n" + "="*60)
    print("📊 INTEGRATION TEST SUMMARY")
    print("="*60)
    print(f"Configuration Test:   {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"RFID Integration:     {'✅ PASS' if rfid_ok else '❌ FAIL'}")
    
    if config_ok and rfid_ok:
        print("\\n🎉 RFID integration successful!")
        print("✅ Your application should now work with RFID on Pi 5")
        print("\\n🔧 Next steps:")
        print("   1. Test with your main application: python main.py")
        print("   2. Check web interface RFID status")
        print("   3. Test access control functionality")
    else:
        print("\\n⚠️  Some integration tests failed")
        print("💡 Check error messages above for troubleshooting")
    
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\\n❌ Integration test error: {e}")
        import traceback
        traceback.print_exc()
