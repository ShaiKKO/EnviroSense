# EnviroSense™ - TeraFlux Studios

Environmental Monitoring and Health Alert System

## Overview

EnviroSense™ is a sophisticated platform for monitoring environmental chemical triggers and physiological responses, providing early warnings for potential health reactions. This system is built around a three-tier architecture:

1. **EnviroSense Simulation Engine** - A standalone library focused on modeling environmental conditions, exposures, and physiological responses with no dependencies on web frameworks, APIs, or deployment considerations.

2. **EnviroSense Core Platform** - The infrastructure, APIs, and user interfaces that build upon the simulation engine, providing scenario management, visualization, data integration, and developer tools.

3. **Grid Guardian Hardware/Firmware** - The physical hardware, firmware, and backend integration that brings EnviroSense capabilities into the field with specialized utility monitoring capabilities.

## Current Status

As of May 2025:
- **Simulation Engine**: ✓ COMPLETED
- **Core Platform**: ⧗ IN PROGRESS (Currently at Platform 1.2 - Temporal Correlation System)
- **Grid Guardian**: ⧖ PLANNED

## Project Structure

```
envirosense/
  ├── core/                              # Simulation Engine components
  │    ├── time_series/                  # Time series generation
  │    ├── physics/                      # Environmental physics engine
  │    ├── chemical/                     # Chemical behavior models
  │    ├── exposure/                     # Exposure tracking and response
  │    ├── physiological/                # Physiological response models
  │    └── biometrics/                   # Biometric signal generation
  │
  ├── platform/                          # Core Platform components
  │    ├── api/                          # API server
  │    ├── web/                          # Web interface
  │    ├── streamer/                     # Real-time data streaming
  │    ├── correlation/                  # Advanced correlation analysis
  │    ├── scenario/                     # Scenario management
  │    └── visualization/                # Data visualization
  │
  ├── grid_guardian/                     # Grid Guardian components
  │    ├── firmware/                     # Device firmware
  │    ├── hardware/                     # Hardware specifications
  │    └── integration/                  # Backend integration
  │
  ├── configuration/                     # Configuration and control
  │    ├── scenario/                     # Scenario management
  │    └── parameters/                   # Parameter control
  │
  ├── data/                              # Data services
  │    ├── export/                       # Data export services
  │    ├── storage/                      # Data storage
  │    └── api/                          # API layer
  │
  ├── ui/                                # User interface
  │    ├── control/                      # Simulation control UI
  │    └── visualization/                # Visualization components
  │
  ├── utils/                             # Utility functions
  │
  ├── testing/                           # Testing framework
  │    ├── generators/                   # Test data generators
  │    ├── scenarios/                    # Test scenarios
  │    ├── validation/                   # Validation tools
  │    └── runners/                      # Test runners
  │
  ├── references/                        # Research references
  │
  └── state/                             # Development state management
```

## Three-Tier Architecture Benefits

The EnviroSense™ system is built with a clear separation of concerns:

1. **Simulation Engine Benefits**:
   - Standalone library with no external dependencies
   - Full simulation capabilities without web infrastructure
   - Suitable for embedded deployment
   - Clean, physics-focused API

2. **Core Platform Benefits**:
   - Builds on simulation engine for sophisticated data analysis
   - Provides user interfaces and visualization
   - Handles real-time data streaming and API access
   - Manages scenarios and configuration

3. **Grid Guardian Benefits**:
   - Specialized hardware for utility infrastructure monitoring
   - Field-deployable with robust environmental protection
   - Integrates with Core Platform for comprehensive analysis
   - Specialized fire-precursor detection capabilities

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

The development of EnviroSense™ follows a phased approach aligned with our three-tier architecture:

1. **Phase 1: Simulation Engine** (COMPLETED)
   - Time Series Generator: Create realistic environmental and physiological data patterns
   - Environmental Physics Engine: Model physical environmental processes
   - Physiological Response Engine: Simulate health responses to environmental conditions
   - Correlation Framework: Connect environmental factors to physiological responses

2. **Phase 2: Core Platform** (IN PROGRESS)
   - Simulation Engine Integration: Connect platform to simulation capabilities
   - Temporal Correlation System: Analyze time-based relationships in data
   - Analysis and Insight Generation: Extract meaningful conclusions from data
   - Multi-signal Correlation: Connect diverse data types for comprehensive analysis
   - Scenario Management: Create and execute simulation scenarios
   - Parameter Control System: Manage simulation parameters
   - API Server: Provide programmatic access to platform capabilities
   - Real-time Data Streamer: Enable live data streaming

3. **Phase 3: Grid Guardian Implementation** (PLANNED)
   - Hardware Architecture: Design specialized utility monitoring hardware
   - Firmware Development: Create embedded software for device operation
   - Backend Integration: Connect hardware to Core Platform
   - Field Deployment: Prepare for and execute real-world deployment

## License

Proprietary - TeraFlux Studios
