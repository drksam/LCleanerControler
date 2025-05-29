#!/usr/bin/env python
"""
Test Configuration for LCleanerController

This module provides configuration for test suites.
"""
import os
import sys
import json
from pathlib import Path

# Add project root directory to Python path to allow proper imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Define test environment constants
TEST_ENVIRONMENT = os.environ.get('TEST_ENV', 'development')
TEST_API_URL = os.environ.get('TEST_API_URL', 'http://localhost:5000')
TEST_API_KEY = os.environ.get('TEST_API_KEY', 'test_api_key_for_development_only')
HARDWARE_SIMULATION = os.environ.get('HARDWARE_SIMULATION', 'True').lower() in ('true', '1', 't')

# Sample test sequences
SAMPLE_SEQUENCES = {
    "basic_sequence": {
        "name": "Basic Test Sequence",
        "description": "A simple test sequence with common operations",
        "steps": [
            {
                "action": "stepper_move",
                "direction": "forward",
                "steps": 100
            },
            {
                "action": "fire",
                "duration": 0.5
            },
            {
                "action": "stepper_move",
                "direction": "backward",
                "steps": 100
            }
        ]
    },
    "complex_sequence": {
        "name": "Complex Test Sequence",
        "description": "A test sequence with error handling configuration",
        "steps": [
            {
                "action": "stepper_move",
                "direction": "forward",
                "steps": 200
            },
            {
                "action": "fire",
                "duration": 1.0
            },
            {
                "action": "delay",
                "seconds": 1.5
            },
            {
                "action": "stepper_move",
                "direction": "backward",
                "steps": 200,
                "error_recovery": {
                    "max_retries": 3,
                    "recovery_by_type": {
                        "hardware_failure": "retry"
                    }
                }
            }
        ],
        "error_recovery": {
            "max_retries": 2,
            "retry_delay": 0.5,
            "exponential_backoff": True,
            "recovery_by_type": {
                "hardware_failure": "retry",
                "hardware_not_available": "abort"
            }
        }
    }
}

# Hardware configuration for testing
HARDWARE_TEST_CONFIG = {
    "steppers": {
        "default": {
            "steps_per_rev": 200,
            "max_speed": 1000,
            "acceleration": 500
        },
        "cleaning_head": {
            "steps_per_rev": 200,
            "max_speed": 800,
            "acceleration": 400
        }
    },
    "servos": {
        "default": {
            "min_pulse_width": 500,
            "max_pulse_width": 2500,
            "default_angle": 90
        },
        "aim": {
            "min_pulse_width": 600,
            "max_pulse_width": 2400,
            "default_angle": 90
        }
    },
    "gpios": {
        "laser_trigger": {
            "pin": 18,
            "active_high": True
        },
        "emergency_stop": {
            "pin": 12,
            "active_high": False
        }
    }
}

# Test user data
TEST_USERS = {
    "admin": {
        "id": 1,
        "username": "admin",
        "card_id": "0123456789",
        "permissions": ["admin", "laser_operate", "machine_monitor"]
    },
    "operator": {
        "id": 2,
        "username": "operator",
        "card_id": "9876543210",
        "permissions": ["laser_operate"]
    },
    "invalid": {
        "id": 999,
        "username": "invalid",
        "card_id": "invalid_card",
        "permissions": []
    }
}

# Load and update config from local test_local_config.py if available
try:
    from tests.test_local_config import *
    print("Loaded local test configuration overrides")
except ImportError:
    pass