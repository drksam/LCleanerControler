# Sequence Format Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Sequence Structure](#sequence-structure)
3. [Step Types](#step-types)
   - [Stepper Movement](#stepper-movement)
   - [Fire Actions](#fire-actions)
   - [Table Movement](#table-movement)
   - [Waiting and Input](#waiting-and-input)
   - [Fan Control](#fan-control)
   - [Lights Control](#lights-control)
4. [Error Recovery Configuration](#error-recovery-configuration)
5. [Operation Modes](#operation-modes)
6. [Sequence Examples](#sequence-examples)
7. [Sequence Flow](#sequence-flow)

## Introduction

Sequences in the LCleanerController define ordered series of actions to be performed by the laser cleaning system. They allow for automated control of all hardware components including stepper motors, servos, table movement, fans, and lights. This document details the format and structure of these sequences, their error handling capabilities, and provides examples for typical usage patterns.

## Sequence Structure

A sequence is defined as a JSON object with the following top-level structure:

```json
{
  "id": "unique-sequence-id",
  "name": "Sequence Name",
  "description": "Detailed description of what this sequence does",
  "created_by": "username",
  "created_at": "2025-05-09T12:00:00Z",
  "updated_at": "2025-05-09T13:30:00Z",
  "steps": [
    // Array of step objects - see step types below
  ],
  "error_recovery": {
    // Optional error recovery configuration - see error recovery section
  }
}
```

### Required Properties

- **id**: Unique identifier for the sequence
- **name**: Human-readable name for the sequence
- **steps**: Array of step objects that define the actions to be performed

### Optional Properties

- **description**: Detailed description of the sequence purpose
- **created_by**: Username of sequence creator
- **created_at**: ISO timestamp of creation
- **updated_at**: ISO timestamp of last update
- **error_recovery**: Configuration for error handling behaviors

## Step Types

Each step in the sequence is represented as a JSON object with required and optional properties depending on the type of action. All steps must have an `action` property that defines the type of action to perform.

Common properties for all steps:

- **action**: (required) The type of action to perform
- **delay_after**: (optional) Time in milliseconds to wait after completing this step before starting the next
- **comment**: (optional) Human-readable comment about this step
- **error_recovery**: (optional) Step-specific error recovery configuration that overrides the sequence defaults

### Stepper Movement

Moves the stepper motor that controls the laser head position.

```json
{
  "action": "stepper_move",
  "direction": "in",        // "in" or "out"
  "steps": 100,             // Number of steps to move
  "delay_after": 500        // Optional: Wait 500ms after move
}
```

#### Parameters

- **direction**: (required) Direction to move the stepper
  - `"in"`: Move the laser head closer to the table
  - `"out"`: Move the laser head away from the table
- **steps**: (required) Number of steps to move

### Fire Actions

Control the servo for laser operation.

#### Start Firing

```json
{
  "action": "fire",
  "duration": 2000           // Fire for 2000ms (optional)
}
```

#### Start Fiber Sequence (A-B-A-B pattern)

```json
{
  "action": "fire_fiber"      // No additional parameters needed
}
```

#### Stop Firing

```json
{
  "action": "stop_fire"       // No additional parameters needed
}
```

### Table Movement

Control the table movement forwards or backwards.

#### Move Table Forward

```json
{
  "action": "table_forward",
  "duration": 1000           // Move for 1000ms
}
```

#### Move Table Backward

```json
{
  "action": "table_backward",
  "duration": 1000           // Move for 1000ms
}
```

#### Parameters

- **duration**: (required) Time in milliseconds to run the table motor

### Waiting and Input

Wait for a specific time or user input before continuing.

#### Wait for Time

```json
{
  "action": "wait",
  "duration": 1000           // Wait for 1000ms
}
```

#### Wait for Input

```json
{
  "action": "wait_input",
  "input_type": "button_in", // Type of input to wait for
  "timeout": 10000           // Optional: Timeout in ms (0 = wait forever)
}
```

#### Parameters for wait_input

- **input_type**: (required) Type of input to wait for:
  - `"button_in"`: Wait for IN button press
  - `"button_out"`: Wait for OUT button press
  - `"fire_button"`: Wait for FIRE button press
  - `"table_front_limit"`: Wait for front limit switch activation
  - `"table_back_limit"`: Wait for back limit switch activation
- **timeout**: (optional) Maximum time in milliseconds to wait (0 or omitted means wait indefinitely)

### Fan Control

Control the cooling fan.

#### Turn Fan On

```json
{
  "action": "fan_on"          // No additional parameters needed
}
```

#### Turn Fan Off

```json
{
  "action": "fan_off"         // No additional parameters needed
}
```

### Lights Control

Control the red indicator lights.

#### Turn Lights On

```json
{
  "action": "lights_on"       // No additional parameters needed
}
```

#### Turn Lights Off

```json
{
  "action": "lights_off"      // No additional parameters needed
}
```

## Error Recovery Configuration

Sequences can define how errors should be handled during execution. This can be configured at the sequence level (applying to all steps) and/or at the individual step level.

### Sequence-Level Error Configuration

```json
{
  "error_recovery": {
    "max_retries": 3,                 // Maximum retry attempts
    "retry_delay": 1.0,               // Seconds between retries
    "exponential_backoff": true,      // Increase delay with each retry
    "recovery_by_type": {
      "hardware_not_available": "abort",
      "hardware_failure": "retry",
      "timeout": "retry",
      "invalid_step": "abort",
      "unexpected": "abort"
    },
    "recovery_by_step": {
      "stepper_move": {
        "hardware_failure": "retry"
      },
      "fire": {
        "hardware_failure": "retry"
      }
    }
  }
}
```

### Step-Level Error Configuration

Individual steps can override the sequence-level error configuration:

```json
{
  "action": "stepper_move",
  "direction": "in",
  "steps": 100,
  "error_recovery": {
    "max_retries": 5,                 // Override max_retries for this step
    "recovery_by_type": {
      "hardware_failure": "skip"      // Skip instead of retry for this step
    }
  }
}
```

### Error Types

The system recognizes several error types:

- `hardware_not_available`: The required hardware component is not available
- `hardware_failure`: The hardware component is available but failed to perform the action
- `timeout`: The operation timed out
- `invalid_step`: The step configuration is invalid
- `unexpected`: An unexpected error occurred

### Recovery Actions

The following recovery actions can be specified:

- `abort`: Abort the sequence (default for most errors)
- `retry`: Retry the operation (up to max_retries)
- `skip`: Skip this step and continue with the next
- `simulate`: Use simulation instead of hardware
- `pause`: Pause for user intervention

## Operation Modes

The system supports three operation modes that affect how hardware errors are handled:

1. **Simulation Mode (`simulation`)**: 
   - Simulation is expected behavior
   - No hardware errors are generated

2. **Normal Mode (`normal`)**: 
   - Hardware is preferred
   - Simulation is NOT a fallback for hardware errors
   - Hardware errors are displayed in the UI

3. **Prototype Mode (`prototype`)**:
   - Hardware is required
   - Errors are returned when hardware is unavailable
   - No simulation fallback

The operation mode is configured in `config.py` or `machine_config.json`.

## Sequence Examples

### Basic Cleaning Cycle

```json
{
  "id": "basic-clean",
  "name": "Basic Cleaning Cycle",
  "description": "A simple cleaning sequence with stepper movement and firing",
  "steps": [
    {
      "action": "wait_input",
      "input_type": "button_in",
      "comment": "Wait for start button"
    },
    {
      "action": "fan_on",
      "comment": "Turn on cooling fan"
    },
    {
      "action": "stepper_move",
      "direction": "in",
      "steps": 500,
      "comment": "Move laser head closer to target"
    },
    {
      "action": "wait",
      "duration": 1000,
      "comment": "Brief pause before firing"
    },
    {
      "action": "lights_on",
      "comment": "Turn on warning lights"
    },
    {
      "action": "fire",
      "comment": "Activate laser"
    },
    {
      "action": "wait",
      "duration": 5000,
      "comment": "Fire for 5 seconds"
    },
    {
      "action": "stop_fire",
      "comment": "Stop the laser"
    },
    {
      "action": "lights_off",
      "comment": "Turn off warning lights"
    },
    {
      "action": "stepper_move",
      "direction": "out",
      "steps": 500,
      "comment": "Move laser head back to safe position"
    },
    {
      "action": "fan_off",
      "comment": "Turn off cooling fan"
    }
  ]
}
```

### Fiber Cleaning Pattern

```json
{
  "id": "fiber-clean",
  "name": "Fiber Cleaning Pattern",
  "description": "Uses the A-B-A-B fiber sequence pattern for more thorough cleaning",
  "steps": [
    {
      "action": "fan_on"
    },
    {
      "action": "lights_on"
    },
    {
      "action": "stepper_move",
      "direction": "in",
      "steps": 300
    },
    {
      "action": "fire_fiber",
      "comment": "Start the A-B-A-B fiber cleaning pattern"
    },
    {
      "action": "wait",
      "duration": 20000,
      "comment": "Let fiber sequence run for 20 seconds"
    },
    {
      "action": "stop_fire"
    },
    {
      "action": "stepper_move",
      "direction": "out",
      "steps": 300
    },
    {
      "action": "lights_off"
    },
    {
      "action": "fan_off"
    }
  ],
  "error_recovery": {
    "max_retries": 2,
    "recovery_by_type": {
      "hardware_failure": "pause"
    }
  }
}
```

### Table Movement Cycle

```json
{
  "id": "table-cycle",
  "name": "Table Movement Cycle",
  "description": "Moves the table back and forth while cleaning",
  "steps": [
    {
      "action": "fan_on"
    },
    {
      "action": "table_forward",
      "duration": 2000,
      "comment": "Move table to front position"
    },
    {
      "action": "wait_input",
      "input_type": "table_front_limit",
      "timeout": 5000,
      "comment": "Wait for table to reach front limit"
    },
    {
      "action": "stepper_move",
      "direction": "in",
      "steps": 500
    },
    {
      "action": "lights_on"
    },
    {
      "action": "fire"
    },
    {
      "action": "table_backward",
      "duration": 5000,
      "comment": "Slowly move table backward while firing"
    },
    {
      "action": "stop_fire"
    },
    {
      "action": "lights_off"
    },
    {
      "action": "stepper_move",
      "direction": "out",
      "steps": 500
    },
    {
      "action": "fan_off"
    }
  ]
}
```

## Sequence Flow

The sequence execution follows these steps:

1. **Sequence Loading**: 
   - Sequence data is loaded from JSON
   - Error recovery configuration is processed
   - Step queue is initialized

2. **Execution Start**:
   - Hardware state is captured
   - Operation mode is checked
   - Hardware requirements are verified
   - Sequence thread is started

3. **Step Execution Loop**:
   - Each step is fetched from the queue
   - Pre-step hardware state is captured
   - Step execution is logged
   - Action is executed with error handling
   - Post-step hardware state is captured
   - Delay after step is processed
   - Progress is updated
   - Next step is fetched

4. **Error Handling**:
   - Error type is determined
   - Recovery action is selected based on configuration
   - Recovery is applied (retry, skip, abort, simulate, pause)
   - Errors are logged with hardware state

5. **Sequence Completion/Termination**:
   - Final hardware state is captured
   - Execution statistics are recorded
   - Status is updated to COMPLETED, ERROR, or IDLE

### Structured Logging

Each step and action generates structured logs containing:

- Step information (index, action)
- Hardware state snapshots (before/after)
- Execution times
- Error details and recovery actions

These logs can be used for troubleshooting and analysis.

---

*This documentation was last updated: May 10, 2025*