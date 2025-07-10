#!/usr/bin/env python3
"""
GPIO Test and Fix Script
Specifically designed to diagnose and fix the gpiod API issues
"""

import os
import sys
import subprocess

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def test_gpiod_versions():
    """Test different gpiod API versions and recommend fixes"""
    print_section("GPIOD API COMPATIBILITY TEST")
    
    try:
        import gpiod
        print(f"✓ gpiod library imported successfully")
        
        # Get version if possible
        try:
            version = gpiod.version_string()
            print(f"  Version: {version}")
        except AttributeError:
            print(f"  Version: Unknown (likely v1.x)")
            
        # Test APIs
        print(f"\nTesting API compatibility:")
        
        # Test v2 API
        v2_success = False
        try:
            with gpiod.Chip('/dev/gpiochip0') as chip:
                info = chip.get_info()
                print(f"✓ gpiod v2 API: SUCCESS ({info.num_lines} lines)")
                v2_success = True
        except Exception as e:
            print(f"✗ gpiod v2 API: {e}")
            
        # Test v1 API
        v1_success = False
        try:
            chip = gpiod.Chip('gpiochip0')
            try:
                if hasattr(chip, 'num_lines'):
                    lines = chip.num_lines()
                    print(f"✓ gpiod v1 API: SUCCESS ({lines} lines)")
                    v1_success = True
                else:
                    print(f"✓ gpiod v1 API: SUCCESS (lines unknown)")
                    v1_success = True
            finally:
                if hasattr(chip, 'close'):
                    chip.close()
        except Exception as e:
            print(f"✗ gpiod v1 API: {e}")
            
        # Recommendations
        print(f"\n🔧 RECOMMENDATIONS:")
        if v2_success:
            print(f"  ✓ gpiod v2 API works - application should use this")
        elif v1_success:
            print(f"  ⚠ Only gpiod v1 API works - update recommended")
            print(f"    sudo apt update && sudo apt upgrade python3-gpiod")
        else:
            print(f"  ❌ Neither API works - gpiod needs fixing")
            print(f"    sudo apt install --reinstall python3-gpiod")
            return False
            
        return True
        
    except ImportError:
        print(f"✗ gpiod library not found")
        print(f"  Install: sudo apt install python3-gpiod")
        return False
    except Exception as e:
        print(f"✗ gpiod test failed: {e}")
        return False

def check_gpio_permissions():
    """Check GPIO device permissions"""
    print_section("GPIO PERMISSIONS CHECK")
    
    import pwd
    import grp
    
    username = os.getenv('USER', 'unknown')
    try:
        user_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
        primary_group = grp.getgrgid(pwd.getpwnam(username).pw_gid).gr_name
        if primary_group not in user_groups:
            user_groups.append(primary_group)
            
        print(f"User '{username}' groups: {', '.join(user_groups)}")
        
        # Check required groups
        required = ['gpio', 'dialout']
        missing = [g for g in required if g not in user_groups]
        
        if missing:
            print(f"✗ Missing groups: {missing}")
            print(f"  Fix: sudo usermod -a -G {','.join(missing)} {username}")
            print(f"  Then logout/login or reboot")
            return False
        else:
            print(f"✓ All required groups present")
            
    except Exception as e:
        print(f"? Cannot check groups: {e}")
        
    # Check device permissions
    gpio_devices = ['/dev/gpiochip0', '/dev/gpiochip4']
    for device in gpio_devices:
        if os.path.exists(device):
            stat = os.stat(device)
            print(f"{device}: mode {oct(stat.st_mode)}")
            
            # Check if readable
            if os.access(device, os.R_OK):
                print(f"  ✓ Readable by current user")
            else:
                print(f"  ✗ Not readable by current user")
                
    return True

def fix_common_issues():
    """Attempt to fix common GPIO issues"""
    print_section("AUTOMATED FIXES")
    
    fixes_applied = []
    
    # Fix 1: Update gpiod library
    print("Attempting to update gpiod library...")
    try:
        result = subprocess.run(['sudo', 'apt', 'update'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            result = subprocess.run(['sudo', 'apt', 'install', '--reinstall', 'python3-gpiod'], 
                                  capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                print("✓ gpiod library reinstalled")
                fixes_applied.append("Reinstalled python3-gpiod")
            else:
                print(f"✗ Failed to reinstall gpiod: {result.stderr}")
        else:
            print(f"✗ Failed to update packages: {result.stderr}")
    except Exception as e:
        print(f"? Cannot update packages: {e}")
        
    # Fix 2: Add user to groups
    username = os.getenv('USER', 'unknown')
    try:
        for group in ['gpio', 'dialout']:
            result = subprocess.run(['sudo', 'usermod', '-a', '-G', group, username],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ Added {username} to {group} group")
                fixes_applied.append(f"Added to {group} group")
    except Exception as e:
        print(f"? Cannot modify user groups: {e}")
        
    if fixes_applied:
        print(f"\n✅ Applied fixes: {', '.join(fixes_applied)}")
        print(f"⚠ Logout/login or reboot required for group changes")
    else:
        print(f"\n⚠ No fixes could be applied automatically")
        
    return len(fixes_applied) > 0

def main():
    """Main diagnostic and fix routine"""
    print("LCleaner Controller - GPIO Diagnostic & Fix Tool")
    print("Specifically addresses the GPIO access errors you're seeing")
    
    # Test gpiod compatibility
    gpiod_ok = test_gpiod_versions()
    
    # Check permissions
    perms_ok = check_gpio_permissions()
    
    # Offer to fix issues
    if not gpiod_ok or not perms_ok:
        print(f"\n❓ Attempt automatic fixes? (y/n): ", end="")
        response = input().lower().strip()
        if response.startswith('y'):
            fixes_applied = fix_common_issues()
            
            print(f"\n🔄 Retesting after fixes...")
            gpiod_ok = test_gpiod_versions()
            
    print_section("SUMMARY")
    if gpiod_ok:
        print("✅ GPIO library compatibility: GOOD")
    else:
        print("❌ GPIO library compatibility: NEEDS FIXING")
        
    print(f"\n💡 Next steps:")
    if gpiod_ok:
        print("  - GPIO library is working correctly")
        print("  - The errors in diagnostic_hardware.py should be resolved")
        print("  - Try running: python3 app.py")
    else:
        print("  - GPIO library needs attention")
        print("  - Follow the recommendations above")
        print("  - Rerun this script after fixes")
        print("  - Consider rebooting the Pi")

if __name__ == "__main__":
    main()
