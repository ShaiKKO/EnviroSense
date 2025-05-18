# EnviroSense™ Platform

## Project Overview

EnviroSense™ is TeraFlux Studios' platform for monitoring and alerting users to environmental chemical triggers that may cause adverse health reactions. This system integrates sensor arrays, wearable devices, edge computing, and cloud infrastructure to provide early warning of potential chemical sensitivity triggers.

## Current Development Status

The project is proceeding according to the phased development plan. Currently, we have completed:

### Time Series Generation System ✅

The core time series generation system has been successfully implemented with the following capabilities:

- **Parameter System**: Support for continuous, discrete, categorical, and boolean parameters with constraints
- **Pattern System**: Implementation of various time-based patterns (diurnal, seasonal, weekly, monthly, annual)
- **Generator System**: Orchestrating parameter generation with relationships and time progression

Key features include:
- Bidirectional parameter relationships
- Composite patterns combining multiple cycles
- Statistical distributions for natural variations
- Data export to CSV and JSON formats
- Visualization capabilities
- Configuration-based initialization

All tests for the time series system are passing, with comprehensive test coverage across all components.

## Project Structure

```
envirosense/
├── core/
│   ├── time_series/        # Time series generator system
│   │   ├── generator.py    # Main generator component
│   │   ├── parameters.py   # Parameter definitions and relationships
│   │   ├── patterns.py     # Time-based pattern implementations
│   │   ├── examples.py     # Example usages
│   │   ├── README.md       # Detailed documentation
│   │   └── tests/          # Unit tests for time series system
│   ├── plots/              # Generated visualization outputs
│   └── data/               # Sample data files
├── state/                  # Development state tracking system
└── docs/                   # Project documentation
```

## Getting Started

To run the time series demonstration:

```bash
cd envirosense
python core/time_series/example_demonstration.py
```

This will generate example environmental data with relationships and patterns, create visualization plots, and export the data to CSV.

## Sample Output

The time series system can generate realistic environmental data with natural patterns and relationships:

- **Continuous Parameters**: Temperature follows a diurnal pattern with a peak at 2 PM, humidity is inversely related to temperature, and VOC levels have random variations
- **Discrete Parameters**: Air quality index derived from VOC levels, categorized into 5 levels (Excellent to Hazardous)

## Next Development Steps

According to the development plan, upcoming work will focus on:

1. Scenario Manager system for predefined environmental scenarios
2. Data Export Service for integration with other components
3. API Endpoints for external access to the simulation system

## Development Tracking

Development progress is tracked in `dev_state.json`, which maintains the registry of components, their implementation status, and development notes.
