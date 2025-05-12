# LCleanerController Testing Documentation

## Overview

This document outlines the testing strategy and procedures for the LCleanerController project. The testing framework is designed to ensure the reliability and correctness of the system across different components and integration points.

## Testing Framework

The testing framework is organized into several categories to cover all aspects of the system:

1. **Unit Tests** - Testing individual functions and classes
2. **Hardware Tests** - Testing hardware components using mock interfaces
3. **Sequence Tests** - Testing sequence execution and error handling
4. **Integration Tests** - Testing interactions between components
5. **API Tests** - Testing API endpoints

## Directory Structure

```
tests/
├── test_base.py          # Base test class with common functionality
├── test_config.py        # Test configuration settings
├── run_tests.py          # Main test runner script
├── README.md             # Testing framework documentation
├── hardware/             # Hardware component tests
│   ├── mock_hardware.py  # Mock hardware implementations
│   └── test_*.py         # Hardware test files
├── unit/                 # Unit tests
│   └── test_*.py         # Unit test files
├── sequences/            # Sequence runner tests
│   └── test_*.py         # Sequence test files
└── integration/          # Integration tests
    └── test_*.py         # Integration test files
```

## Running Tests

You can run tests using the `run_tests.py` script:

```bash
# Run all tests
python tests/run_tests.py

# Run specific test categories
python tests/run_tests.py unit
python tests/run_tests.py hardware
python tests/run_tests.py sequences
python tests/run_tests.py integration
python tests/run_tests.py api
```

## Test Coverage

### 1. Hardware Component Testing

Hardware tests use mock implementations to verify correct behavior without requiring physical hardware:

- **Stepper Motors**: Movement, position tracking, error handling
- **Servos**: Angle movement, position control
- **Laser**: Firing, duration control, emergency stopping
- **GPIOs**: State changes, input/output operations

Hardware tests also verify error conditions and recovery mechanisms.

### 2. Sequence Runner Testing

Sequence tests verify the sequence execution engine:

- Basic sequence execution
- Error handling and recovery
- Step-by-step execution flow
- Emergency stop handling
- Status reporting

### 3. Authentication Testing

Authentication tests verify the RFID control system:

- User authentication via RFID cards
- Permission checking
- Access control for different operations
- User session management

### 4. API Testing

API tests verify the external interfaces:

- Authentication endpoints
- Node status APIs
- User management APIs
- Alert management APIs
- Machine usage data APIs

### 5. Utility Function Testing

Unit tests for utility functions verify:

- Error handling utilities
- String manipulation functions
- Configuration management
- Temperature conversion utilities
- Simulation mode detection

## Mocking Strategy

The testing framework uses a comprehensive mocking system to simulate hardware and external dependencies:

- **Mock Hardware Controller**: Centralized manager for all mock hardware components
- **Mock Stepper**: Simulates stepper motor behavior including movement and positioning
- **Mock Servo**: Simulates servo movement and angle positioning
- **Mock Laser**: Simulates laser firing with duration control
- **Mock GPIO**: Simulates GPIO pin state changes
- **Mock RFID Reader**: Simulates RFID card reading

Each mock component can simulate normal operation and error conditions to test recovery mechanisms.

## Continuous Integration

The test framework integrates with CI/CD pipelines:

- All tests run automatically on code commits
- Exit codes indicate test success or failure
- Test results are reported to the CI system

## Test Data Management

Test data is centralized in `test_config.py`:

- Sample sequences for testing sequence execution
- Hardware configuration data
- Test user profiles with different permission levels
- Environment-specific configuration

## Adding New Tests

To add new tests:

1. Create a new test file in the appropriate directory (unit, hardware, sequences, or integration)
2. Name the file with a `test_` prefix
3. Create a test class that inherits from `BaseTestCase`
4. Add test methods that start with `test_`
5. Run the new tests using the test runner

## Best Practices

1. **Always run tests before committing changes**
2. **Write tests for new features**
3. **Keep tests independent and idempotent**
4. **Use descriptive test names**
5. **Use mocks for external dependencies**
6. **Avoid hardcoded paths or configuration values**
7. **Clean up resources after tests**