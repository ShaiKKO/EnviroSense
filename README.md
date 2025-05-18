# EnviroSense™ - TeraFlux Studios

Environmental Monitoring and Health Alert System

## Overview

EnviroSense™ is a sophisticated platform for monitoring environmental chemical triggers and physiological responses, providing early warnings for potential health reactions. This system includes sensor arrays, wearable devices, edge computing hubs, mobile applications, and cloud infrastructure.

This repository contains the implementation of the EnviroSense™ platform following a phased development approach:

1. **Simulation Environment**: Sensor Simulator, Mobile App, Minimal Cloud Backend
2. **Core Infrastructure**: Edge Hub Core, Data Analytics Pipeline, ML Training System
3. **Hardware Implementation**: Sensor Array Firmware, Wearable Component Firmware, Edge Hub Hardware

## Project Structure

```
envirosense/
  ├── core/                # Core simulation engine
  │    ├── time_series/    # Time series generation
  │    ├── physics/        # Environmental physics engine
  │    ├── chemical/       # Chemical behavior models
  │    └── physiological/  # Physiological response models
  │
  ├── configuration/       # Configuration and control
  │    ├── scenario/       # Scenario management
  │    └── parameters/     # Parameter control
  │
  ├── data/                # Data services
  │    ├── export/         # Data export services
  │    ├── storage/        # Data storage
  │    └── api/            # API layer
  │
  ├── ui/                  # User interface
  │    ├── control/        # Simulation control UI
  │    └── visualization/  # Visualization components
  │
  ├── utils/               # Utility functions
  │
  └── state/               # Development state management
```

## Development State Management

The EnviroSense™ project includes a sophisticated state management system to help track development progress, component status, and session information. This system helps maintain context between development sessions and makes it easier to pick up where you left off.

### Key Features

- Component tracking with dependencies, tags, and status
- Development session recording
- Checkpoint creation for milestone tracking
- CLI for interacting with the state management system
- Component status visualization

### Installation

```bash
# Install the package in development mode
pip install -e .
```

### Using the State Management System

#### Initialize the Development State

```bash
# Initialize the state with EnviroSense components
python -m envirosense.state.initialize
```

Or using the CLI:

```bash
envirosense-state init
```

#### Initialize the Master Development Plan Tasks

```bash
# Initialize tasks from the master development plan
envirosense-state init-plan
```

#### View Development Status

```bash
envirosense-state summary
```

#### Start a Development Session

```bash
# Start a session focused on specific components
envirosense-state start --focus TimeSeriesGenerator EnvironmentalPhysicsEngine
```

#### Record Changes

```bash
# Record a change to a component
envirosense-state change TimeSeriesGenerator "Implemented Gaussian noise generator" --files envirosense/core/time_series/gaussian.py envirosense/core/time_series/noise.py
```

#### Update Component Status

```bash
# Update the status of a component
envirosense-state component-status TimeSeriesGenerator implemented
```

#### Create a Checkpoint

```bash
# Create a checkpoint to mark a milestone
envirosense-state checkpoint phase1_milestone1 "Completed basic time series generation"
```

#### End a Development Session

```bash
# End the current development session
envirosense-state end --notes "Completed implementation of Gaussian noise generator"
```

#### List Components by Tag

```bash
# List all components with a specific tag
envirosense-state list-components --tag physics
```

#### Work with Development Tasks

```bash
# List all tasks
envirosense-state list-tasks

# List tasks by type
envirosense-state list-tasks --type mini_task

# List tasks for a specific component
envirosense-state list-tasks --component TimeSeriesGenerator

# View task details
envirosense-state task 1.1.1

# Set the current task
envirosense-state set-task 1.1.1

# Update task status
envirosense-state task-status 1.1.1 completed

# Add a note to a task
envirosense-state task-note 1.1.1 "Implemented parameter constraint system"

# Add a blocker to a task
envirosense-state task-blocker 1.1.1 "Need to define parameter relationships schema"

# Resolve a blocker
envirosense-state resolve-blocker 1.1.1 0 "Created JSON schema for parameter relationships"
```

### Programmatic Usage

You can also use the state management system programmatically:

```python
from envirosense.state.utils import (
    get_state, 
    save_state, 
    start_development_session,
    record_change,
    update_component_status
)

# Get the current state
state = get_state()

# Start a development session
start_development_session(["TimeSeriesGenerator"])

# Record changes
record_change(
    "TimeSeriesGenerator",
    "Implemented Gaussian noise generator",
    ["envirosense/core/time_series/gaussian.py"]
)

# Update component status
component = state.get_component("TimeSeriesGenerator")
component.update_status(ComponentStatus.IMPLEMENTED)

# Save changes
save_state()
```

## Development Process

The development of EnviroSense™ follows a phased approach:

1. **Phase 1: Simulation Environment** (Weeks 1-8)
   - Sensor Simulator: Generate realistic environmental and physiological data
   - Mobile Application: User interface for monitoring and alerts
   - Minimal Cloud Backend: Essential cloud services for data storage and APIs

2. **Phase 2: Core Infrastructure** (Weeks 9-16)
   - Edge Hub Core: Central processing for sensor fusion and local analysis
   - Data Analytics Pipeline: Process and analyze sensor data
   - ML Training System: Train and deploy models for detection and prediction

3. **Phase 3: Hardware Implementation** (Weeks 17-24)
   - Sensor Array Firmware: Control environmental sensor operation
   - Wearable Component Firmware: Monitor physiological responses
   - Edge Hub Hardware Integration: Integrate software with hardware components

## License

Proprietary - TeraFlux Studios
