#!/usr/bin/env python3
"""
LCleaner Controller Test Script
-------------------------------

This script allows you to quickly test the LCleaner system with temporary database
and proper hardware mode (no simulation fallback).

Usage:
  python3 test_run.py [options]

Options:
  --hardware         Force hardware mode (default)
  --simulation       Run in simulation mode for testing
  --port PORT        Specify port to run on (default: 5000)
  --debug            Enable Flask debug mode
  --temp-db          Use temporary SQLite database (default)
  --help             Show this help message
"""

import os
import sys
import argparse
import json
import logging
import tempfile
import shutil
from pathlib import Path

def setup_parser():
    """Set up command line argument parser"""
    parser = argparse.ArgumentParser(description='Run LCleaner Controller for testing')
    parser.add_argument('--hardware', action='store_true', default=True, help='Force hardware mode (default)')
    parser.add_argument('--simulation', action='store_true', help='Run in simulation mode for testing')
    parser.add_argument('--port', type=int, default=5000, help='Port to run on (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Enable Flask debug mode')
    parser.add_argument('--temp-db', action='store_true', default=True, help='Use temporary SQLite database (default)')
    parser.add_argument('--debug-level', choices=['debug', 'info', 'warning', 'error'], 
                        default='info', help='Set logging level')
    return parser

def setup_temporary_database():
    """Setup temporary SQLite database for testing"""
    # Create temporary database file
    temp_dir = tempfile.gettempdir()
    db_path = os.path.join(temp_dir, 'lcleaner_test.db')
    
    # Set environment variable for SQLite database
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    
    print(f"Using temporary database: {db_path}")
    return db_path

def update_config(mode, debug_level):
    """Update configuration with the specified mode"""
    try:
        # Load current config
        with open('machine_config.json', 'r') as f:
            config = json.load(f)
        
        # Update system section
        if 'system' not in config:
            config['system'] = {}
        
        config['system']['operation_mode'] = mode
        config['system']['debug_level'] = debug_level
        
        # Write updated config
        with open('machine_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"Configuration updated: operation_mode={mode}, debug_level={debug_level}")
        return True
    except Exception as e:
        print(f"Error updating configuration: {e}")
        return False

def check_gpioctrl_installed():
    """Check if gpioctrl is already installed"""
    try:
        import gpioctrl
        print("✓ gpioctrl package is available")
        return True
    except ImportError:
        print("⚠ gpioctrl package not found")
        return False

def install_gpioctrl_package():
    """Install the local gpioctrl package"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    gpioesp_dir = os.path.join(current_dir, 'gpioesp')
    
    if not os.path.exists(gpioesp_dir):
        print("Warning: gpioesp directory not found, skipping gpioctrl installation")
        return False
    
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-e', gpioesp_dir
        ], check=True, capture_output=True, text=True)
        
        print("✓ gpioctrl package installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error installing gpioctrl package: {e}")
        return False

def main():
    """Main entry point"""
    parser = setup_parser()
    args = parser.parse_args()
    
    print("LCleaner Controller Test Runner")
    print("=" * 50)
    
    # Determine mode
    if args.simulation:
        mode = 'simulation'
        print("Mode: SIMULATION (no hardware required)")
    else:
        mode = 'hardware'
        print("Mode: HARDWARE (real GPIO control)")
    
    # Setup temporary database
    if args.temp_db:
        db_path = setup_temporary_database()
        print(f"Database: Temporary SQLite ({db_path})")
    else:
        print("Database: Using configured database")
    
    # Update configuration
    if not update_config(mode, args.debug_level):
        sys.exit(1)
    
    # Set environment variables
    if mode == 'simulation':
        os.environ['SIMULATION_MODE'] = 'True'
    else:
        # CRITICAL: Force hardware mode - no simulation fallback
        os.environ['SIMULATION_MODE'] = 'False'
        os.environ['FORCE_HARDWARE'] = 'True'
        print("⚠ IMPORTANT: Hardware mode - GPIO must work!")
        
        # Test GPIO availability before starting
        print("Testing GPIO access...")
        try:
            import gpiod
            chip = gpiod.Chip('gpiochip0')
            num_lines = chip.num_lines()
            print(f"✓ GPIO chip detected: {num_lines} lines available")
            print("✓ GPIO hardware ready for testing")
        except Exception as e:
            print(f"✗ GPIO test failed: {e}")
            print("✗ Hardware mode requires working GPIO!")
            print("Check that:")
            print("  - You're running on a Raspberry Pi")
            print("  - gpiod library is installed: sudo apt install python3-libgpiod")
            print("  - User has GPIO permissions: sudo usermod -a -G gpio $USER")
            sys.exit(1)
        
        # Ensure gpioctrl is installed for ESP32 control
        if not check_gpioctrl_installed():
            print("Installing gpioctrl package for ESP32 control...")
            if not install_gpioctrl_package():
                print("✗ Failed to install gpioctrl - ESP32 control may not work")
                print("Continuing anyway...")  # Don't fail completely for ESP32 issues
    
    # Configure logging
    log_level = getattr(logging, args.debug_level.upper())
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print(f"\nStarting LCleaner Controller:")
    print(f"  Port: {args.port}")
    print(f"  Debug: {args.debug}")
    print(f"  Log level: {args.debug_level.upper()}")
    print(f"  Access at: http://localhost:{args.port}")
    print(f"\nPress Ctrl+C to stop")
    print("=" * 50)
    
    # Import and run the application
    try:
        # Add current directory to path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # Import the Flask app
        from main import app
        
        # Initialize database tables if using temporary database
        if args.temp_db:
            with app.app_context():
                from models import db
                db.create_all()
                print("✓ Temporary database tables created")
        
        # Run the application
        app.run(
            host='0.0.0.0', 
            port=args.port, 
            debug=args.debug,
            use_reloader=False  # Disable reloader to avoid issues with GPIO
        )
        
    except ImportError as e:
        print(f"✗ Error importing application: {e}")
        print("Make sure you have installed all dependencies:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error running application: {e}")
        sys.exit(1)
    finally:
        # Cleanup temporary database if created
        if args.temp_db and 'DATABASE_URL' in os.environ:
            db_path = os.environ['DATABASE_URL'].replace('sqlite:///', '')
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                    print(f"✓ Cleaned up temporary database: {db_path}")
                except:
                    pass

if __name__ == '__main__':
    main()
