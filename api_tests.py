#!/usr/bin/env python
"""
API Test Suite for LCleanerController

This module tests all API endpoints defined in api_routes.py to ensure proper functionality.
Tests both successful and error responses for each endpoint.

Usage:
    python api_tests.py

Requirements:
    requests, pytest

Example:
    $ python api_tests.py
    Testing API: /integration/api/auth... OK
    Testing API: /integration/api/node_status... OK
    ...
    All tests passed!
"""
import os
import sys
import json
import time
import unittest
import requests
from datetime import datetime, timedelta

# Configuration
DEFAULT_API_URL = "http://localhost:5000"
DEFAULT_API_KEY = "test_api_key_for_development_only"

class APITester:
    """Test runner for API endpoints"""
    
    def __init__(self, base_url=None, api_key=None):
        """
        Initialize the API tester
        
        Args:
            base_url: Base URL for the API (default: http://localhost:5000)
            api_key: API key for authentication (default: test_api_key_for_development_only)
        """
        self.base_url = base_url or os.environ.get('API_BASE_URL', DEFAULT_API_URL)
        self.api_key = api_key or os.environ.get('API_KEY', DEFAULT_API_KEY)
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
        self.success_count = 0
        self.failure_count = 0
        self.error_details = []
        
    def run_test(self, endpoint, method='GET', data=None, params=None, expected_status=200,
                expected_keys=None, description=None):
        """
        Run a single API test
        
        Args:
            endpoint: API endpoint to test (e.g., '/auth')
            method: HTTP method (GET, POST, etc.)
            data: Data to send in the request body
            params: URL parameters
            expected_status: Expected HTTP status code
            expected_keys: List of keys expected in the response
            description: Description of the test
            
        Returns:
            bool: True if test passes, False otherwise
        """
        url = f"{self.base_url}{endpoint}"
        test_name = description or f"{method} {endpoint}"
        
        print(f"Testing API: {endpoint}... ", end="", flush=True)
        
        try:
            # Make request
            if method.upper() == 'GET':
                response = self.session.get(url, params=params)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, params=params)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, params=params)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, json=data, params=params)
            else:
                print(f"FAIL (Unsupported method: {method})")
                self.failure_count += 1
                self.error_details.append({
                    'test': test_name,
                    'error': f"Unsupported method: {method}"
                })
                return False
            
            # Check status code
            if response.status_code != expected_status:
                print(f"FAIL (Status code: {response.status_code}, expected: {expected_status})")
                self.failure_count += 1
                self.error_details.append({
                    'test': test_name,
                    'error': f"Status code: {response.status_code}, expected: {expected_status}",
                    'response': response.text
                })
                return False
            
            # For successful responses, check if response contains expected keys
            if expected_keys and response.status_code < 400:
                try:
                    resp_json = response.json()
                    missing_keys = [key for key in expected_keys if key not in resp_json]
                    if missing_keys:
                        print(f"FAIL (Missing keys: {', '.join(missing_keys)})")
                        self.failure_count += 1
                        self.error_details.append({
                            'test': test_name,
                            'error': f"Missing keys: {', '.join(missing_keys)}",
                            'response': resp_json
                        })
                        return False
                except ValueError:
                    print("FAIL (Response not valid JSON)")
                    self.failure_count += 1
                    self.error_details.append({
                        'test': test_name,
                        'error': "Response not valid JSON",
                        'response': response.text
                    })
                    return False
            
            print("OK")
            self.success_count += 1
            return True
            
        except Exception as e:
            print(f"ERROR ({str(e)})")
            self.failure_count += 1
            self.error_details.append({
                'test': test_name,
                'error': str(e)
            })
            return False
            
    def print_summary(self):
        """Print test summary"""
        print("\n=== Test Summary ===")
        print(f"Total tests: {self.success_count + self.failure_count}")
        print(f"Successes: {self.success_count}")
        print(f"Failures: {self.failure_count}")
        
        if self.error_details:
            print("\n=== Error Details ===")
            for i, error in enumerate(self.error_details, 1):
                print(f"\n{i}. Test: {error['test']}")
                print(f"   Error: {error['error']}")
                if 'response' in error:
                    print(f"   Response: {json.dumps(error['response'], indent=2)}" 
                          if isinstance(error['response'], dict) 
                          else f"   Response: {error['response']}")


def run_all_tests():
    """Run all API tests"""
    tester = APITester()
    
    print("\n=== Authentication API Tests ===")
    
    # Test successful authentication
    tester.run_test(
        endpoint='/integration/api/auth',
        method='POST',
        data={
            'card_id': '0123456789',
            'machine_id': 'W1'
        },
        expected_status=200,
        expected_keys=['success', 'authorized', 'user'],
        description='Auth endpoint - Successful authentication'
    )
    
    # Test invalid card ID
    tester.run_test(
        endpoint='/integration/api/auth',
        method='POST',
        data={
            'card_id': 'invalid_card',
            'machine_id': 'W1'
        },
        expected_status=200,  # Note: Auth errors return 200 with authorized=false
        expected_keys=['success', 'authorized', 'reason'],
        description='Auth endpoint - Invalid card ID'
    )
    
    # Test missing parameters
    tester.run_test(
        endpoint='/integration/api/auth',
        method='POST',
        data={
            'card_id': '0123456789'
            # machine_id missing
        },
        expected_status=400,
        expected_keys=['success', 'error', 'code'],
        description='Auth endpoint - Missing required parameters'
    )
    
    # Test invalid API key (temporarily modify session)
    original_auth_header = tester.session.headers['Authorization']
    tester.session.headers['Authorization'] = 'Bearer invalid_api_key'
    
    tester.run_test(
        endpoint='/integration/api/auth',
        method='POST',
        data={
            'card_id': '0123456789',
            'machine_id': 'W1'
        },
        expected_status=401,
        expected_keys=['success', 'error', 'code'],
        description='Auth endpoint - Invalid API key'
    )
    
    # Restore valid API key
    tester.session.headers['Authorization'] = original_auth_header
    
    print("\n=== Node Status API Tests ===")
    
    # Test node status endpoint
    tester.run_test(
        endpoint='/integration/api/node_status',
        method='GET',
        expected_status=200,
        expected_keys=['nodes', 'timestamp'],
        description='Node status endpoint'
    )
    
    print("\n=== User Management API Tests ===")
    
    # Test available users endpoint
    tester.run_test(
        endpoint='/integration/api/users/available',
        method='GET',
        expected_status=200,
        expected_keys=['success', 'users'],
        description='Available users endpoint'
    )
    
    # Test user sync endpoint - import direction
    tester.run_test(
        endpoint='/integration/api/users/sync',
        method='POST',
        data={
            'external_id': 1,
            'direction': 'import',
            'overwrite_permissions': True
        },
        expected_status=200,
        expected_keys=['success', 'user'],
        description='User sync endpoint - Import direction'
    )
    
    # Test user sync endpoint - export direction
    tester.run_test(
        endpoint='/integration/api/users/sync',
        method='POST',
        data={
            'external_id': 1,
            'direction': 'export',
            'overwrite_permissions': False
        },
        expected_status=200,
        expected_keys=['success', 'user'],
        description='User sync endpoint - Export direction'
    )
    
    # Test user sync endpoint - user not found
    tester.run_test(
        endpoint='/integration/api/users/sync',
        method='POST',
        data={
            'external_id': 9999,  # Non-existent user ID
            'direction': 'export'
        },
        expected_status=404,
        expected_keys=['success', 'error', 'code'],
        description='User sync endpoint - User not found'
    )
    
    # Test user permissions endpoint - GET
    tester.run_test(
        endpoint='/integration/api/users/1/permissions',
        method='GET',
        expected_status=200,
        expected_keys=['success', 'user', 'permissions', 'machines'],
        description='User permissions endpoint - GET'
    )
    
    # Test user permissions endpoint - POST
    tester.run_test(
        endpoint='/integration/api/users/1/permissions',
        method='POST',
        data={
            'permissions': [1, 2, 3]
        },
        expected_status=200,
        expected_keys=['success', 'message', 'user', 'permissions'],
        description='User permissions endpoint - POST'
    )
    
    # Test user permissions endpoint - User not found
    tester.run_test(
        endpoint='/integration/api/users/9999/permissions',
        method='GET',
        expected_status=404,
        expected_keys=['success', 'error', 'code'],
        description='User permissions endpoint - User not found'
    )
    
    print("\n=== Alert Management API Tests ===")
    
    # Test send alert endpoint
    tester.run_test(
        endpoint='/integration/api/alerts',
        method='POST',
        data={
            'id': 1,
            'machineId': 'W1',
            'senderId': 1,
            'message': 'Machine requires maintenance',
            'alertType': 'warning',
            'status': 'pending',
            'origin': 'machine',
            'createdAt': datetime.utcnow().isoformat()
        },
        expected_status=200,
        expected_keys=['success', 'message', 'local_alert_id', 'external_alert_id'],
        description='Send alert endpoint'
    )
    
    # Test acknowledge alert endpoint
    tester.run_test(
        endpoint='/integration/api/alerts/1/acknowledge',
        method='POST',
        expected_status=200,
        expected_keys=['success', 'message', 'alert'],
        description='Acknowledge alert endpoint'
    )
    
    # Test acknowledge alert endpoint - Alert not found
    tester.run_test(
        endpoint='/integration/api/alerts/0/acknowledge',  # Invalid alert ID
        method='POST',
        expected_status=404,
        expected_keys=['success', 'error', 'code'],
        description='Acknowledge alert endpoint - Alert not found'
    )
    
    # Test resolve alert endpoint
    tester.run_test(
        endpoint='/integration/api/alerts/1/resolve',
        method='POST',
        expected_status=200,
        expected_keys=['success', 'message', 'alert'],
        description='Resolve alert endpoint'
    )
    
    # Test resolve alert endpoint - Alert not found
    tester.run_test(
        endpoint='/integration/api/alerts/0/resolve',  # Invalid alert ID
        method='POST',
        expected_status=404,
        expected_keys=['success', 'error', 'code'],
        description='Resolve alert endpoint - Alert not found'
    )
    
    print("\n=== Machine Usage API Tests ===")
    
    # Calculate date range for usage tests
    today = datetime.utcnow()
    start_date = (today - timedelta(days=30)).isoformat()
    end_date = today.isoformat()
    
    # Test machine usage endpoint - All machines
    tester.run_test(
        endpoint='/integration/api/machines/usage',
        method='GET',
        params={
            'start_date': start_date,
            'end_date': end_date
        },
        expected_status=200,
        expected_keys=['success', 'total_usage_hours', 'machines'],
        description='Machine usage endpoint - All machines'
    )
    
    # Test machine usage endpoint - Specific machine
    tester.run_test(
        endpoint='/integration/api/machines/usage',
        method='GET',
        params={
            'start_date': start_date,
            'end_date': end_date,
            'machine_id': 'laser_room_1'
        },
        expected_status=200,
        expected_keys=['success', 'total_usage_hours', 'machines'],
        description='Machine usage endpoint - Specific machine'
    )
    
    # Test machine usage endpoint - Missing date parameters
    tester.run_test(
        endpoint='/integration/api/machines/usage',
        method='GET',
        params={
            # Missing date parameters
            'machine_id': 'laser_room_1'
        },
        expected_status=400,
        expected_keys=['success', 'error', 'code'],
        description='Machine usage endpoint - Missing date parameters'
    )
    
    # Test machine usage endpoint - Invalid date format
    tester.run_test(
        endpoint='/integration/api/machines/usage',
        method='GET',
        params={
            'start_date': '2025-13-01',  # Invalid date format
            'end_date': end_date,
            'machine_id': 'laser_room_1'
        },
        expected_status=400,
        expected_keys=['success', 'error', 'code'],
        description='Machine usage endpoint - Invalid date format'
    )
    
    # Test rate limiting (send many requests quickly)
    print("\n=== Rate Limiting Test ===")
    print("Sending 5 requests in quick succession...")
    
    for i in range(5):
        tester.run_test(
            endpoint='/integration/api/node_status',
            method='GET',
            expected_status=200,
            description=f'Rate limit test request {i+1}'
        )
        time.sleep(0.1)  # Brief pause between requests
    
    # Print test summary
    tester.print_summary()
    
    # Return success or failure
    return tester.failure_count == 0

def create_api_test_postman_collection():
    """
    Create a Postman collection file for API testing
    
    Returns:
        dict: Postman collection data
    """
    base_url = "{{baseUrl}}"
    
    collection = {
        "info": {
            "name": "LCleanerController API Tests",
            "description": "API tests for LCleanerController integration APIs",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": [
            # Authentication API
            {
                "name": "Authentication",
                "item": [
                    {
                        "name": "Verify Machine Access",
                        "request": {
                            "method": "POST",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{apiKey}}",
                                    "type": "text"
                                },
                                {
                                    "key": "Content-Type",
                                    "value": "application/json",
                                    "type": "text"
                                }
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": "{\n    \"card_id\": \"0123456789\",\n    \"machine_id\": \"W1\"\n}"
                            },
                            "url": {
                                "raw": "{{baseUrl}}/integration/api/auth",
                                "host": ["{{baseUrl}}"],
                                "path": ["integration", "api", "auth"]
                            },
                            "description": "Verify if a user has permission to access a specific machine"
                        }
                    }
                ]
            },
            # Node Status API
            {
                "name": "Node Status",
                "item": [
                    {
                        "name": "Get Node Status",
                        "request": {
                            "method": "GET",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{apiKey}}",
                                    "type": "text"
                                }
                            ],
                            "url": {
                                "raw": "{{baseUrl}}/integration/api/node_status",
                                "host": ["{{baseUrl}}"],
                                "path": ["integration", "api", "node_status"]
                            },
                            "description": "Get status of all nodes and connected machines"
                        }
                    }
                ]
            },
            # User Management APIs
            {
                "name": "User Management",
                "item": [
                    {
                        "name": "Get Available Users",
                        "request": {
                            "method": "GET",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{apiKey}}",
                                    "type": "text"
                                }
                            ],
                            "url": {
                                "raw": "{{baseUrl}}/integration/api/users/available",
                                "host": ["{{baseUrl}}"],
                                "path": ["integration", "api", "users", "available"]
                            },
                            "description": "Get list of available users"
                        }
                    },
                    {
                        "name": "Sync User",
                        "request": {
                            "method": "POST",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{apiKey}}",
                                    "type": "text"
                                },
                                {
                                    "key": "Content-Type",
                                    "value": "application/json",
                                    "type": "text"
                                }
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": "{\n    \"external_id\": 1,\n    \"direction\": \"import\",\n    \"overwrite_permissions\": true\n}"
                            },
                            "url": {
                                "raw": "{{baseUrl}}/integration/api/users/sync",
                                "host": ["{{baseUrl}}"],
                                "path": ["integration", "api", "users", "sync"]
                            },
                            "description": "Synchronize user between systems"
                        }
                    },
                    {
                        "name": "Get User Permissions",
                        "request": {
                            "method": "GET",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{apiKey}}",
                                    "type": "text"
                                }
                            ],
                            "url": {
                                "raw": "{{baseUrl}}/integration/api/users/1/permissions",
                                "host": ["{{baseUrl}}"],
                                "path": ["integration", "api", "users", "1", "permissions"]
                            },
                            "description": "Get permissions for a specific user"
                        }
                    },
                    {
                        "name": "Update User Permissions",
                        "request": {
                            "method": "POST",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{apiKey}}",
                                    "type": "text"
                                },
                                {
                                    "key": "Content-Type",
                                    "value": "application/json",
                                    "type": "text"
                                }
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": "{\n    \"permissions\": [1, 2, 3]\n}"
                            },
                            "url": {
                                "raw": "{{baseUrl}}/integration/api/users/1/permissions",
                                "host": ["{{baseUrl}}"],
                                "path": ["integration", "api", "users", "1", "permissions"]
                            },
                            "description": "Update permissions for a specific user"
                        }
                    }
                ]
            },
            # Alert Management APIs
            {
                "name": "Alert Management",
                "item": [
                    {
                        "name": "Send Alert",
                        "request": {
                            "method": "POST",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{apiKey}}",
                                    "type": "text"
                                },
                                {
                                    "key": "Content-Type",
                                    "value": "application/json",
                                    "type": "text"
                                }
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": "{\n    \"id\": 1,\n    \"machineId\": \"W1\",\n    \"senderId\": 1,\n    \"message\": \"Machine requires maintenance\",\n    \"alertType\": \"warning\",\n    \"status\": \"pending\",\n    \"origin\": \"machine\",\n    \"createdAt\": \"{{$isoTimestamp}}\"\n}"
                            },
                            "url": {
                                "raw": "{{baseUrl}}/integration/api/alerts",
                                "host": ["{{baseUrl}}"],
                                "path": ["integration", "api", "alerts"]
                            },
                            "description": "Send an alert from ShopTracker to RFID Machine Monitor"
                        }
                    },
                    {
                        "name": "Acknowledge Alert",
                        "request": {
                            "method": "POST",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{apiKey}}",
                                    "type": "text"
                                }
                            ],
                            "url": {
                                "raw": "{{baseUrl}}/integration/api/alerts/1/acknowledge",
                                "host": ["{{baseUrl}}"],
                                "path": ["integration", "api", "alerts", "1", "acknowledge"]
                            },
                            "description": "Acknowledge an alert"
                        }
                    },
                    {
                        "name": "Resolve Alert",
                        "request": {
                            "method": "POST",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{apiKey}}",
                                    "type": "text"
                                }
                            ],
                            "url": {
                                "raw": "{{baseUrl}}/integration/api/alerts/1/resolve",
                                "host": ["{{baseUrl}}"],
                                "path": ["integration", "api", "alerts", "1", "resolve"]
                            },
                            "description": "Resolve an alert"
                        }
                    }
                ]
            },
            # Machine Usage API
            {
                "name": "Machine Usage",
                "item": [
                    {
                        "name": "Get Machine Usage",
                        "request": {
                            "method": "GET",
                            "header": [
                                {
                                    "key": "Authorization",
                                    "value": "Bearer {{apiKey}}",
                                    "type": "text"
                                }
                            ],
                            "url": {
                                "raw": "{{baseUrl}}/integration/api/machines/usage?start_date={{$isoTimestamp}}+00:00&end_date={{$isoTimestamp}}+00:00&machine_id=laser_room_1",
                                "host": ["{{baseUrl}}"],
                                "path": ["integration", "api", "machines", "usage"],
                                "query": [
                                    {
                                        "key": "start_date",
                                        "value": "{{$isoTimestamp}}+00:00"
                                    },
                                    {
                                        "key": "end_date",
                                        "value": "{{$isoTimestamp}}+00:00"
                                    },
                                    {
                                        "key": "machine_id",
                                        "value": "laser_room_1"
                                    }
                                ]
                            },
                            "description": "Get usage statistics for machines"
                        }
                    }
                ]
            }
        ],
        "variable": [
            {
                "key": "baseUrl",
                "value": "http://localhost:5000",
                "type": "string"
            },
            {
                "key": "apiKey",
                "value": "test_api_key_for_development_only",
                "type": "string"
            }
        ]
    }
    
    return collection

def save_postman_collection(filename='LCleanerController_API_Tests.postman_collection.json'):
    """Save the Postman collection to a file"""
    try:
        collection = create_api_test_postman_collection()
        with open(filename, 'w') as f:
            json.dump(collection, f, indent=2)
        print(f"\nPostman collection saved to {filename}")
        return True
    except Exception as e:
        print(f"\nError saving Postman collection: {e}")
        return False

if __name__ == '__main__':
    print("\n=== LCleanerController API Test Suite ===")
    success = run_all_tests()
    
    # Generate Postman collection for manual testing
    save_postman_collection()
    
    if success:
        print("\n✅ All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. See details above.")
        sys.exit(1)