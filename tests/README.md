# LCleanerController Testing Framework

This directory contains the testing framework for the LCleanerController project.

## Overview

The testing framework is organized into several categories:

- **Unit Tests**: Tests for individual functions and classes
- **Hardware Tests**: Tests for hardware components using mock interfaces
- **Sequence Tests**: Tests for sequence runner functionality
- **Integration Tests**: Tests for interactions between multiple components
- **API Tests**: Tests for API endpoints

## Directory Structure

```
tests/
├── test_base.py          # Base test class with common functionality
├── test_config.py        # Test configuration settings
├── run_tests.py          # Main test runner script
├── README.md             # This file
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

You can run tests using the `run_tests.py` script. The script supports running all tests or specific categories:

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

## Writing New Tests

### 1. Unit Tests

Unit tests should be placed in the `tests/unit/` directory and should follow this naming pattern:

```
test_module_name.py
```

Each test file should contain one or more test classes that inherit from `BaseTestCase`:

```python
from tests.test_base import BaseTestCase

class YourModuleTest(BaseTestCase):
    def test_your_function(self):
        # Test code here
        self.assertEqual(expected, actual)
```

### 2. Hardware Tests

Hardware tests should use the mock hardware implementations from `tests/hardware/mock_hardware.py`:

```python
from tests.test_base import BaseTestCase
from tests.hardware.mock_hardware import MockHardwareController

class YourHardwareTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.controller = MockHardwareController()
        self.component = self.controller.add_component('test_component')
        
    def test_hardware_function(self):
        # Test code here
        self.assertTrue(self.component.do_something())
```

### 3. Sequence Tests

Sequence tests should test sequence execution with various configurations:

```python
from tests.test_base import BaseTestCase
from tests.hardware.mock_hardware import MockHardwareController
from your_sequence_runner import SequenceRunner

class YourSequenceTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.controller = MockHardwareController()
        self.sequence = self.create_test_sequence('test_sequence')
        
    def test_sequence_execution(self):
        # Test code here
        runner = SequenceRunner(self.sequence, self.controller)
        self.assertTrue(runner.execute())
```

### 4. Integration Tests

Integration tests should test interactions between multiple components:

```python
from tests.test_base import BaseTestCase

class YourIntegrationTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Initialize components
        
    def test_component_interaction(self):
        # Test interaction between components
        self.assertTrue(result)
```

### 5. API Tests

API tests are managed in the root `api_tests.py` file. You can add new API tests by adding test cases to that file.

## Mock Hardware

The `tests/hardware/mock_hardware.py` file provides mock implementations of hardware components for testing, including:

- `MockStepper`: Mock stepper motor
- `MockServo`: Mock servo motor
- `MockLaser`: Mock laser
- `MockGPIO`: Mock GPIO pins
- `MockHardwareController`: Controller for all mock hardware components

These mock implementations simulate the behavior of real hardware and can be configured to return specific results or simulate errors.

## Test Configuration

The `tests/test_config.py` file contains configuration settings for tests, including:

- Sample test sequences
- Hardware configuration
- Test user data
- Environment settings

You can modify this file to add new test configurations or override existing ones.

## Best Practices

1. **Always run tests before committing changes**
2. **Write tests for new features**
3. **Keep tests independent and idempotent**
4. **Use descriptive test names**
5. **Use mocks for external dependencies**
6. **Avoid hardcoded paths or configuration values**
7. **Clean up resources after tests**

## Continuous Integration

The test framework is designed to work with continuous integration systems. The `run_tests.py` script returns appropriate exit codes (0 for success, 1 for failure) that can be used in CI pipelines.