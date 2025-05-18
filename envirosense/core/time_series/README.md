# EnviroSense Time Series Generation System

## Overview

The EnviroSense Time Series Generation System provides a comprehensive framework for generating realistic time-based data for environmental parameters and physiological responses. This system is a core component of the EnviroSense simulation environment, enabling the generation of synthetic sensor data with configurable patterns, relationships, and constraints.

## Architecture

The system consists of three main components:

1. **Parameters** (`parameters.py`): Defines parameters with constraints, distributions, and metadata
2. **Patterns** (`patterns.py`): Implements various time-based patterns like diurnal and seasonal cycles
3. **Generator** (`generator.py`): Orchestrates parameter generation with relationships and time progression

```
+-------------------+     +--------------------+     +--------------------+
| Parameter System  |<--->| Pattern System     |<--->| Time Series        |
| - Types           |     | - Diurnal          |     | Generator          |
| - Constraints     |     | - Seasonal         |     | - Relationships    |
| - Distributions   |     | - Weekly           |     | - Data Series      |
+-------------------+     +--------------------+     +--------------------+
```

## Key Features

- **Parameter Types**: Support for continuous, discrete, categorical, and boolean parameters
- **Statistical Distributions**: Uniform, normal, exponential, Poisson, binomial, and custom distributions
- **Time-Based Patterns**: Diurnal (day/night), seasonal, weekly, monthly, annual, and custom cycles
- **Parameter Relationships**: Define functional relationships between parameters
- **Bidirectional Relationships**: Parameters can mutually influence each other
- **Composite Patterns**: Combine multiple patterns (e.g., diurnal + seasonal)
- **Constraints**: Min/max values, rate of change, allowed values
- **Data Export**: Export to CSV and JSON formats
- **Visualization**: Built-in plotting capabilities
- **Configurability**: Initialize via code or from configuration dictionaries

## Usage Examples

### Basic Parameter Creation

```python
from envirosense.core.time_series.parameters import Parameter, ParameterType
from envirosense.core.time_series.generator import TimeSeriesGenerator

# Create a generator
generator = TimeSeriesGenerator()

# Add parameters
generator.create_parameter(
    name="temperature",
    parameter_type=ParameterType.CONTINUOUS,
    initial_value=25.0,
    units="°C",
    min_value=0.0,
    max_value=50.0
)

generator.create_parameter(
    name="humidity",
    parameter_type=ParameterType.CONTINUOUS,
    initial_value=50.0,
    units="%",
    min_value=0.0,
    max_value=100.0
)
```

### Defining Parameter Relationships

```python
from envirosense.core.time_series.parameters import ParameterRelationship

# Create a relationship: humidity = 0.5 * temperature + 30
relationship = ParameterRelationship(
    source_parameter="temperature",
    target_parameter="humidity",
    relationship_function=linear_relationship,
    params={
        "slope": 0.5,
        "offset": 30.0
    }
)

# Add the relationship
generator.add_relationship(relationship)
```

### Applying Patterns

```python
from envirosense.core.time_series.patterns import Pattern, PatternType

# Create a diurnal pattern for temperature
diurnal_pattern = Pattern(
    pattern_type=PatternType.DIURNAL,
    base_value=25.0,
    amplitude=5.0,  # +/- 5°C variation
    period=24.0,    # 24-hour cycle
    phase_shift=14.0  # Peak at 2 PM
)

# Apply pattern to parameter
temp_param = generator.get_parameter("temperature")
temp_param.pattern = diurnal_pattern
```

### Generating Time Series Data

```python
# Generate 24 hours of data with 1-hour steps
series = generator.generate_series(duration=24.0, time_delta=1.0)

# Export to CSV
generator.export_to_csv("environmental_data.csv", series)

# Visualize the data
generator.plot(series, title="Environmental Parameters")
```

### Creating from Configuration

```python
config = {
    "parameters": [
        {
            "name": "temperature",
            "type": "continuous",
            "current_value": 25.0,
            "units": "°C",
            "min_value": 0.0,
            "max_value": 50.0
        },
        {
            "name": "humidity",
            "type": "continuous",
            "current_value": 50.0,
            "units": "%",
            "min_value": 0.0,
            "max_value": 100.0
        }
    ],
    "relationships": [
        {
            "source_parameter": "temperature",
            "target_parameter": "humidity",
            "function": "linear_relationship",
            "params": {
                "slope": 0.5,
                "offset": 30.0
            }
        }
    ]
}

generator = TimeSeriesGenerator(config)
```

## Supported Pattern Types

1. **Constant**: No variation, constant value
2. **Diurnal**: Day/night cycle (24-hour period)
3. **Seasonal**: Annual cycle (365-day period)
4. **Weekly**: 7-day cycle for day-of-week patterns
5. **Monthly**: Monthly cycle for month-specific patterns
6. **Annual**: Year-long pattern with specific day values
7. **Custom Cycle**: User-defined cyclic pattern
8. **Trend**: Long-term trend (linear, exponential, etc.)
9. **Composite**: Combination of multiple patterns

## Relationship Functions

1. **Linear**: y = ax + b
2. **Exponential**: y = a * e^(bx)
3. **Power**: y = a * x^b
4. **Logarithmic**: y = a * log(x) + b
5. **Threshold**: Step function based on thresholds
6. **Custom**: User-defined formula

## Advanced Features

### Composite Patterns

Combine multiple patterns to create complex behaviors:

```python
from envirosense.core.time_series.patterns import CompositePattern

# Create individual patterns
diurnal = Pattern.create_diurnal(
    base_value=25.0,
    amplitude=5.0
)

seasonal = Pattern.create_seasonal(
    base_value=25.0,
    amplitude=10.0
)

# Combine patterns
composite = CompositePattern(
    base_value=25.0,
    patterns=[diurnal, seasonal],
    modulation_factors=[1.0, 0.5]  # Seasonal effect is half as strong
)
```

### Pattern Helpers

Use helper functions for common pattern combinations:

```python
from envirosense.core.time_series.patterns import create_diurnal_seasonal_composite

# Create a temperature pattern with both daily and yearly cycles
temp_pattern = create_diurnal_seasonal_composite(
    base_value=25.0,
    diurnal_amplitude=5.0,
    seasonal_amplitude=10.0
)
```

## Implementation Details

### Parameter Class

The `Parameter` class represents a variable in the system with properties like:

- `name`: Identifier for the parameter
- `parameter_type`: Continuous, discrete, categorical, or boolean
- `value`: Current value of the parameter
- `min_value`/`max_value`: Range constraints
- `allowed_values`: Set of allowed values (for discrete/categorical)
- `distribution`: Statistical distribution for random variation
- `rate_of_change`: Maximum change between consecutive values

### Pattern Class

The `Pattern` class defines time-based variation with properties:

- `pattern_type`: Type of pattern (diurnal, seasonal, etc.)
- `base_value`: Center value around which the pattern varies
- `amplitude`: Magnitude of the variation
- `period`: Length of the cycle in appropriate units
- `phase_shift`: Shift of the cycle peak

### TimeSeriesGenerator Class

The `TimeSeriesGenerator` class manages the generation process:

- Maintains a collection of parameters
- Tracks relationships between parameters
- Manages simulation time
- Provides methods for stepping through time
- Handles data export and visualization
- Supports saving/loading configurations

## Extensions

The system is designed to be extensible:

1. Add new `PatternType` values for additional patterns
2. Create custom relationship functions
3. Implement custom distributions
4. Add new parameter types
5. Create specialized pattern helper functions

## Testing

The system includes comprehensive tests for all components:

- `test_parameters.py`: Tests parameter functionality
- `test_patterns.py`: Tests pattern generation
- `test_generator.py`: Tests the generator and relationships

## Performance Considerations

- For large parameter sets, consider optimizing dependency order
- For long timescales, use appropriate time steps
- For high-frequency data, consider memory usage in series generation
- Use numpy for efficient array operations in custom functions
