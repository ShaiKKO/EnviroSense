# EnviroSense System Organization

Following the three-tier architecture defined in the Master Development Plan v2.1:

## 1. Simulation Engine (`/simulation_engine`)
The standalone library focused on modeling environmental conditions, exposures, and physiological responses.

- Time Series Generation (`/simulation_engine/time_series`)
- Environmental Physics (`/simulation_engine/physics`)
- Chemical Modeling (`/simulation_engine/chemical`)
- Exposure Tracking (`/simulation_engine/exposure`)
- Physiological Response (`/simulation_engine/physiological`)
- Biometrics (`/simulation_engine/biometrics`)
- Correlation Framework (`/simulation_engine/correlation`)

## 2. Core Platform (`/core_platform`)
The infrastructure, APIs, and user interfaces that build upon the simulation engine.

- Temporal Correlation System (`/core_platform/temporal_correlation`)
- Visualization Components (`/core_platform/visualization`)
- Planned: Analysis and Insight Generation
- Planned: Multi-signal Correlation
- Planned: Scenario Management
- Planned: Parameter Control System
- Planned: API Server
- Planned: Real-time Data Streamer

## 3. Grid Guardian Hardware (`/grid_guardian`)
The physical hardware, firmware, and backend integration.

- Hardware Interfaces
- Firmware
- Device Management
- Communication Protocols

## Support and Infrastructure

- Data Handling (`/data_handling`)
- Common Utilities (`/common`)
- Testing Framework (`/testing_framework`)
- Platform Core (`/platform`)

## Current Status

The organization is being consolidated to match the architecture in the master plan:

1. Simulation Engine: ✓ COMPLETED (Components migrated from `/core` to `/simulation_engine`)
2. Core Platform: ⧗ IN PROGRESS (Temporal Correlation system implementation)
3. Grid Guardian Hardware: ⧖ PLANNED
