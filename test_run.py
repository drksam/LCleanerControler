#!/usr/bin/env python3
"""
NooyenLaserRoom Control System Test Script
-----------------------------------------

This script allows you to quickly test the NooyenLaserRoom system 
without setting up the systemd service, ideal for hardware testing.

Usage:
  python3 test_run.py [options]

Options:
  --simulation       Run in simulation mode (no hardware required)
  --prototype        Run in prototype mode (hardware with debug logs)
  --normal           Run in normal production mode
  --port PORT        Specify port to run on (default: 5000)
  --debug            Enable Flask debug mode
  --help             Show this help message
"""

import os
import sys
import argparse
import json
import logging
import shutil
import subprocess
from pathlib import Path

def setup_parser():
    """Set up command line argument parser"""
    parser = argparse.ArgumentParser(description='Run NooyenLaserRoom Control System for testing')
    parser.add_argument('--simulation', action='store_true', help='Run in simulation mode (no hardware required)')
    parser.add_argument('--prototype', action='store_true', help='Run in prototype mode (hardware with debug logs)')
    parser.add_argument('--normal', action='store_true', help='Run in normal production mode')
    parser.add_argument('--port', type=int, default=5000, help='Port to run on (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Enable Flask debug mode')
    parser.add_argument('--debug-level', choices=['debug', 'info', 'warning', 'error'], 
                        default='info', help='Set logging level')
    return parser

def update_config(mode, debug_level):
    """Update configuration with the specified mode and debug level"""
    print(f"[DEBUG] update_config called with mode={mode}, debug_level={debug_level}")
    try:
        # Load current config
        with open('machine_config.json', 'r') as f:
            config = json.load(f)
        
        # Update system section
        if 'system' not in config:
            config['system'] = {}
        
        config['system']['operation_mode'] = mode
        config['system']['debug_level'] = debug_level
        
        # Make sure gpioctrl is always used for stepper and servo
        config['system']['use_gpioctrl'] = True
        
        # Write updated config
        with open('machine_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"Configuration updated: operation_mode={mode}, debug_level={debug_level}")
        print(f"[DEBUG] config['system']['debug_level'] after update: {config['system']['debug_level']}")
        return True
    except Exception as e:
        print(f"Error updating configuration: {e}")
        return False

def install_gpioctrl_package():
    """Install the local gpioctrl package"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    gpioesp_dir = os.path.join(current_dir, 'gpioesp')
    
    if not os.path.exists(gpioesp_dir):
        print("Warning: gpioesp directory not found, cannot install gpioctrl")
        return False
    
    # Check if pip is available
    pip_path = shutil.which('pip') or shutil.which('pip3')
    
    if not pip_path:
        print("Error: pip not found. Please install pip first.")
        return False
    
    print("Installing gpioctrl package from local directory...")
    try:
        # Install the package in development mode
        result = subprocess.run(
            [pip_path, 'install', '-e', gpioesp_dir],
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        print("gpioctrl package installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing gpioctrl package: {e}")
        print(f"Error details: {e.stderr}")
        return False

def check_gpioctrl_installed():
    """Check if gpioctrl is already installed"""
    try:
        import gpioctrl
        return True
    except ImportError:
        return False

def main():
    """Main entry point"""
    parser = setup_parser()
    args = parser.parse_args()
    
    # Determine mode
    mode = 'simulation'  # Default mode
    if args.prototype:
        mode = 'prototype'
    elif args.normal:
        mode = 'normal'
    elif args.simulation:
        mode = 'simulation'
    
    # Update configuration
    if not update_config(mode, args.debug_level):
        sys.exit(1)
    
    # Set environment variables based on mode
    if mode == 'simulation':
        os.environ['SIMULATION_MODE'] = 'True'
    elif mode == 'prototype':
        # CRITICAL: In prototype mode, we NEVER want to fall back to simulation
        # mode regardless of IO issues, so we explicitly set SIMULATION_MODE to 'False'
        os.environ['SIMULATION_MODE'] = 'False'
        os.environ['PROTOTYPE_MODE'] = 'True'
        os.environ['FORCE_HARDWARE'] = 'True'  # Additional flag to force hardware use
        print("PROTOTYPE MODE: Forcing hardware access regardless of I/O issues")
        
        # In prototype mode, ensure gpioctrl is installed
        if not check_gpioctrl_installed():
            if not install_gpioctrl_package():
                print("Error: Failed to install gpioctrl package. Hardware access will not work correctly.")
                sys.exit(1)
    else:
        # Normal mode
        os.environ.pop('SIMULATION_MODE', None)
        os.environ.pop('FORCE_HARDWARE', None)
        
        # Normal mode still requires gpioctrl for stepper and servo
        if not check_gpioctrl_installed():
            if not install_gpioctrl_package():
                print("Warning: Failed to install gpioctrl package. Using with limited functionality.")
    
    # Configure basic logging
    log_level = getattr(logging, args.debug_level.upper())
    logging.basicConfig(level=log_level,
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                       stream=sys.stdout)
    
    print(f"\n{'='*80}")
    print(f"Starting NooyenLaserRoom Control System in {mode.upper()} mode")
    print(f"Debug level: {args.debug_level.upper()}")
    print(f"Access the interface at: http://localhost:{args.port} or http://<your-ip-address>:{args.port}")
    print(f"Press Ctrl+C to stop the server")
    print(f"{'='*80}\n")
    
    # Import and run the application
    try:
        # Add the current directory to the path to ensure imports work
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # Check if main.py exists in the current directory
        if not os.path.exists(os.path.join(current_dir, 'main.py')):
            # Try to find main.py in subdirectories
            found = False
            for root, dirs, files in os.walk(current_dir):
                if 'main.py' in files:
                    # Add this directory to path
                    if root not in sys.path:
                        sys.path.insert(0, root)
                    os.chdir(root)  # Change to the directory containing main.py
                    found = True
                    print(f"Found main.py in {root}")
                    break
            
            if not found:
                print("Error: Could not find main.py in the application directory or subdirectories.")
                sys.exit(1)
        
        # Try to use gunicorn if available, otherwise install required dependencies
        try:
            # Check if the requirements file exists
            req_file = os.path.join(current_dir, 'requirements.txt')
            if not os.path.exists(req_file):
                # Search for requirements.txt in parent and subdirectories
                for root, _, files in os.walk(os.path.dirname(current_dir)):
                    if 'requirements.txt' in files:
                        req_file = os.path.join(root, 'requirements.txt')
                        print(f"Found requirements.txt at {req_file}")
                        break
            
            # Check if pip is available
            pip_path = shutil.which('pip') or shutil.which('pip3')
            
            if not pip_path:
                print("Error: pip not found. Please install pip first.")
                sys.exit(1)
            
            # Check if gunicorn is available
            gunicorn_path = shutil.which('gunicorn')
            
            # If gunicorn is not available and we have a requirements file, ask to install dependencies
            if not gunicorn_path and os.path.exists(req_file):
                print("Gunicorn not found. Would you like to install the required dependencies?")
                response = input("This will run 'pip install -r requirements.txt' [y/N]: ")
                
                if response.lower() in ['y', 'yes']:
                    print("Installing dependencies...")
                    try:
                        # Check if pip is available
                        pip_path = shutil.which('pip') or shutil.which('pip3')
                        
                        if not pip_path:
                            print("Error: pip not found. Please install pip first.")
                            sys.exit(1)
                            
                        # Install requirements
                        # subprocess is already imported at the top level, no need to import again
                        result = subprocess.run([pip_path, 'install', '-r', req_file], 
                                               stdout=subprocess.PIPE, 
                                               stderr=subprocess.PIPE,
                                               text=True,
                                               check=True)
                        print("Dependencies installed successfully! Please run the script again.")
                        sys.exit(0)
                    except Exception as install_error:
                        print(f"Error installing dependencies: {install_error}")
                else:
                    print("Continuing without installing dependencies...")
            
            # Start the application with gunicorn if available, otherwise use Flask
            if gunicorn_path:
                print(f"Starting application with Gunicorn on port {args.port}...")
                cmd = [
                    gunicorn_path,
                    '--bind', f'0.0.0.0:{args.port}',
                    '--reuse-port',
                    '--reload',
                    'main:app'
                ]
                
                # Execute the command
                subprocess.run(cmd)
            else:
                # Gunicorn not found, use Flask's development server
                print(f"Starting application with Flask's built-in server on port {args.port}...")
                print("Note: For production use, it's recommended to install gunicorn:")
                print("      pip install gunicorn")
                
                # Import Flask app and run it
                from main import app
                app.run(host='0.0.0.0', port=args.port, debug=args.debug)
                
        except ImportError as e:
            # If we failed importing modules for the app, offer to install dependencies
            print(f"Error importing application modules: {e}")
            
            # Look for requirements.txt
            req_file = os.path.join(current_dir, 'requirements.txt')
            if not os.path.exists(req_file):
                # Search for requirements.txt in parent and subdirectories
                for root, _, files in os.walk(os.path.dirname(current_dir)):
                    if 'requirements.txt' in files:
                        req_file = os.path.join(root, 'requirements.txt')
                        break
            
            if os.path.exists(req_file):
                print(f"Found requirements file at {req_file}")
                response = input("Would you like to install the required dependencies? [y/N]: ")
                
                if response.lower() in ['y', 'yes']:
                    print("Installing dependencies...")
                    try:
                        # Check if pip is available
                        pip_path = shutil.which('pip') or shutil.which('pip3')
                        
                        if not pip_path:
                            print("Error: pip not found. Please install pip first.")
                            sys.exit(1)
                            
                        # Install requirements
                        # subprocess is already imported at the top level, no need to import again
                        result = subprocess.run([pip_path, 'install', '-r', req_file], 
                                               stdout=subprocess.PIPE, 
                                               stderr=subprocess.PIPE,
                                               text=True,
                                               check=True)
                        print("Dependencies installed successfully! Please run the script again.")
                        sys.exit(0)
                    except Exception as install_error:
                        print(f"Error installing dependencies: {install_error}")
            
            # If we couldn't install or user declined, show error message
            try:
                from flask import Flask
                app = Flask(__name__)
                
                @app.route('/')
                def home():
                    return """
                    <html>
                        <head><title>NooyenLaserRoom - Setup Required</title></head>
                        <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
                            <h1>NooyenLaserRoom - Setup Required</h1>
                            <p>The application could not be started due to missing dependencies.</p>
                            <p>Please install the required dependencies:</p>
                            <pre>pip install -r requirements.txt</pre>
                            <p>If you're still having issues, check that all required Python modules are installed.</p>
                        </body>
                    </html>
                    """
                
                print("Starting minimal error application to show setup instructions...")
                app.run(host='0.0.0.0', port=args.port, debug=True)
            except ImportError:
                print("Error: Flask is not installed. Please install the required dependencies:")
                print("pip install -r requirements.txt")
                sys.exit(1)
        
    except ImportError as e:
        print(f"Error importing modules: {e}")
        print("Make sure you have installed all required dependencies:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error running application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()