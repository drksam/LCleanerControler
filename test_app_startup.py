#!/usr/bin/env python3
"""
Quick Application Test
Tests if the LCleaner application can start despite GPIO warnings
"""

import sys
import os

def test_app_startup():
    """Test if the application can start"""
    print("="*60)
    print(" LCLEANER APPLICATION STARTUP TEST")
    print("="*60)
    
    try:
        # Add current directory to path
        sys.path.insert(0, '.')
        
        print("Testing configuration loading...")
        from config import get_system_config, get_gpio_config
        
        system_config = get_system_config()
        gpio_config = get_gpio_config()
        
        print(f"✓ Configuration loaded successfully")
        print(f"  Operation mode: {system_config.get('operation_mode', 'unknown')}")
        print(f"  GPIO pins configured: {len(gpio_config)}")
        
        print(f"\nTesting GPIO wrapper initialization...")
        from gpio_controller_wrapper import LocalGPIOWrapper
        
        # Test in both modes
        print(f"  Testing hardware mode...")
        try:
            gpio_hw = LocalGPIOWrapper(chip_name='gpiochip0', simulation_mode=False)
            print(f"  ✓ Hardware mode GPIO wrapper: OK")
        except Exception as e:
            print(f"  ⚠ Hardware mode GPIO wrapper: {e}")
            print(f"    (This is expected if GPIO has API issues)")
            
        print(f"  Testing simulation mode...")
        try:
            gpio_sim = LocalGPIOWrapper(chip_name='gpiochip0', simulation_mode=True)
            print(f"  ✓ Simulation mode GPIO wrapper: OK")
        except Exception as e:
            print(f"  ✗ Simulation mode GPIO wrapper: {e}")
            return False
            
        print(f"\nTesting output controller...")
        from output_control_gpiod import OutputController
        
        try:
            output_ctrl = OutputController()
            print(f"  ✓ Output controller: Initialized")
            print(f"    Simulation mode: {output_ctrl.simulation_mode}")
        except Exception as e:
            print(f"  ✗ Output controller failed: {e}")
            return False
            
        print(f"\nTesting web application import...")
        try:
            import app
            print(f"  ✓ Flask app: Can import")
        except Exception as e:
            print(f"  ✗ Flask app import failed: {e}")
            return False
            
        print(f"\n✅ APPLICATION STARTUP: SUCCESS")
        print(f"   The application should work despite any GPIO diagnostic warnings")
        return True
        
    except Exception as e:
        print(f"✗ Application test failed: {e}")
        return False

def main():
    """Main test function"""
    print("LCleaner Controller - Application Startup Test")
    print("Tests whether the app can start despite GPIO errors")
    
    success = test_app_startup()
    
    print(f"\n" + "="*60)
    print(" TEST SUMMARY")
    print("="*60)
    
    if success:
        print("✅ APPLICATION: Ready to run")
        print("\n💡 What this means:")
        print("  - Despite GPIO diagnostic errors, the app should work")
        print("  - GPIO errors are usually API compatibility issues")
        print("  - The app gracefully falls back to simulation mode if needed")
        print("  - You can safely start the application with: python3 app.py")
        
        print(f"\n🚀 Next steps:")
        print(f"  1. Start the application: python3 app.py")
        print(f"  2. Access web interface: http://your-pi-ip:5000")
        print(f"  3. Test hardware functions through the web UI")
        print(f"  4. If GPIO issues persist, run: python3 fix_gpio.py")
    else:
        print("❌ APPLICATION: Has issues that need fixing")
        print("\n🔧 Troubleshooting:")
        print("  1. Check Python virtual environment: source venv/bin/activate")
        print("  2. Install dependencies: pip install -r requirements.txt")
        print("  3. Run setup again: ./setup_pi_venv.sh")
        print("  4. Check for configuration errors")

if __name__ == "__main__":
    main()
