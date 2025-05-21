# Physiological Response Modeling Framework

The Physiological Response module provides a comprehensive framework for modeling the effects of chemical exposures on different physiological systems, with capabilities for simulating immediate, delayed, chronic, and cascading responses.

## Core Components

### Base Framework
- `PhysiologicalResponseSystem`: Abstract base class for all physiological systems
- `SystemOutput`: Response output data structure
- `ResponseSeverityLevel`: Enumeration for severity classification
- `PhysiologicalSystemSet`: Collection of systems with interaction matrices

### Standard Systems
- `RespiratoryResponseSystem`: Models respiratory effects
- `NeurologicalResponseSystem`: Models neurological effects

### Temporal Framework (New)
- `TemporalResponseMixin`: Enhances systems with temporal response capabilities
- `TemporalParameters`: Parameters for controlling time-course effects
- `TemporalPattern`: Enumerated patterns (IMMEDIATE, DELAYED, BIPHASIC, CHRONIC, RECURRENT)
- `PhysiologicalEffectGraph`: Directed graph for modeling cascading effects
- `TemporalSystemSet`: Enhanced system set with cascade analysis capabilities

### Temporal Systems (New)
- `TemporalRespiratorySystem`: Respiratory system with temporal capabilities
- `TemporalNeurologicalSystem`: Neurological system with temporal capabilities

## Key Features

### 1. Time-Based Response Patterns

The framework can model different temporal patterns:
- **Immediate**: Fast onset, rapid recovery
- **Delayed**: Delayed onset, variable recovery
- **Biphasic**: Initial response followed by delayed secondary response
- **Chronic**: Ongoing effects from cumulative exposure
- **Recurrent**: Effects that cycle through periods of intensity

### 2. Cascade Effects Between Systems

Model how effects in one system propagate to others over time with:
- Configurable interaction factors
- Temporal delays between systems
- System-specific propagation characteristics

### 3. Temporal Projections and Predictions

- Project response values over specified time periods
- Predict when responses will reach severity thresholds
- Calculate confidence intervals for predictions

## Usage Examples

### Basic Response Calculation

```python
from envirosense.core.exposure.physiological_response import (
    RespiratoryResponseSystem, 
    SystemOutput
)

# Create a respiratory system
respiratory = RespiratoryResponseSystem()

# Define an exposure
exposure = {
    "chemical_id": "formaldehyde",
    "concentration": 20.0,  # ppm
    "duration": 1.0         # hours
}

# Calculate immediate response
response = respiratory.calculate_response(exposure)

print(f"Response value: {response.response_value}")
print(f"Severity: {response.severity_level.name}")
```

### Temporal Response Calculation

```python
from envirosense.core.exposure.physiological_response import (
    TemporalRespiratorySystem
)

# Create a temporal respiratory system
temporal_respiratory = TemporalRespiratorySystem()

# Define exposure same as above
exposure = {...}  # Same as previous example

# Calculate response with temporal effects
temporal_response = temporal_respiratory.calculate_delayed_response(
    exposure_history=exposure,
    reference_time=datetime.datetime.now() + datetime.timedelta(hours=4)  # 4 hours later
)

print(f"Temporal response value: {temporal_response.response_value}")
print(f"Severity: {temporal_response.severity_level.name}")
```

### Projecting Responses Over Time

```python
import datetime

# Create time points for projection
start_time = datetime.datetime.now()
time_points = [
    start_time + datetime.timedelta(hours=h)
    for h in [0, 1, 2, 4, 8, 12, 24]
]

# Project responses at each time point
projections = temporal_respiratory.project_response_over_time(
    exposure_history=exposure,
    time_points=time_points
)

# Print results
for time, response in projections.items():
    hours = (time - start_time).total_seconds() / 3600
    print(f"At {hours:.1f} hours: {response.response_value:.2f} ({response.severity_level.name})")
```

### Modeling System Cascades

```python
from envirosense.core.exposure.physiological_response import (
    PhysiologicalSystemSet, 
    TemporalSystemSet,
    TemporalRespiratorySystem, 
    TemporalNeurologicalSystem
)

# Create system set
system_set = PhysiologicalSystemSet()

# Add systems
respiratory = TemporalRespiratorySystem()
neurological = TemporalNeurologicalSystem()
system_set.add_system(respiratory)
system_set.add_system(neurological)

# Configure interactions
system_set.set_interaction("Respiratory System", "Neurological System", 0.4)
system_set.set_interaction("Neurological System", "Respiratory System", 0.3)

# Create temporal set
temporal_set = TemporalSystemSet(system_set)

# Calculate cascade effects
cascade_results = temporal_set.calculate_temporal_cascade(
    initial_system="Respiratory System",
    exposure_history=exposure,
    time_points=time_points
)

# Process cascade results for each time point
for time, responses in cascade_results.items():
    hours = (time - start_time).total_seconds() / 3600
    print(f"\nTime: {hours:.1f} hours")
    
    for system_name, response in responses.items():
        print(f"  {system_name}: {response.response_value:.2f} ({response.severity_level.name})")
```

## Additional Examples

For more detailed examples, see the example scripts in `envirosense/core/exposure/physiological_response/examples/`:

- `integrated_example.py`: Demonstrates integrated use of multiple systems
- `temporal_cascade_example.py`: Demonstrates temporal response patterns and cascade effects

## References

- Cohen et al. (2023): "Delayed Onset of Chemical Effects in Biological Systems"
- WHO (2024): "Time-Course Dynamics of Toxicant Exposures"
- EPA (2023): "Chronic Exposure Assessment Guidelines"
