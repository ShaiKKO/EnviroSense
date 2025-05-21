# EnviroSense Biometric Signal System

## Overview

The Biometric Signal System provides realistic physiological response modeling for different environmental exposures, physical conditions, and psychological states. This system enables simulation of how human biometric signals respond to various stimuli including chemical exposures, environmental conditions, exercise, and stress factors.

## Key Components

### Base Signal Models

- **HeartRateModel**: Simulates heart rate responses with configurable baseline rate, variability, recovery dynamics, and age/fitness adjustments
- **SkinConductanceModel**: Simulates electrodermal activity (skin conductance) with stress response patterns, environmental effects, and recovery dynamics
- **RespiratoryModel**: Simulates breathing patterns including rate, volume, and breathing pattern changes in response to various stimuli

### Integrated Biometric Profile

The `BiometricProfile` class combines all three base signal models into a coordinated physiological system that ensures realistic cross-signal interactions. It offers:

- Individualized sensitivity factors for different stimuli
- Demographic variation through the `create_demographic_variant` method
- Pattern detection to identify underlying physiological states
- Energy expenditure (MET) calculation
- Integrated stress index calculation
- Historical data tracking for time-series analysis
- Serialization/deserialization for profile storage and sharing

## Key Features

1. **Realistic Physiological Interaction**
   - Changes in respiratory patterns affect heart rate and skin conductance
   - Heart rate responses influence respiratory patterns
   - Stress affects all physiological systems in coordinated ways

2. **Comprehensive Response Modeling**
   - Chemical exposure effects with compound-specific patterns
   - Environmental condition responses (temperature, humidity)
   - Exercise response with fitness-dependent adaptation
   - Psychological stress response

3. **Individual Variation Modeling**
   - Age-based physiological differences
   - Fitness level adjustments to baseline and response
   - Chemical sensitivity variations
   - Stress sensitivity factors

4. **Pattern Recognition**
   - Automatic detection of physical exertion
   - Identification of acute stress response
   - Recognition of chemical exposure patterns
   - Detection of respiratory distress
   - Identification of recovery phase

## Usage Examples

### Basic Usage

```python
from envirosense.core.biometrics.biometric_profile import BiometricProfile

# Create a default biometric profile
profile = BiometricProfile(
    name="Default Profile",
    description="Standard adult profile with average physiological parameters"
)

# Generate biometric signals at a specific time point with no special conditions
baseline_signals = profile.generate_signals(time_point=0.0)

# Generate signals during exercise
exercise_signals = profile.generate_signals(
    time_point=1.0,
    exercise_level=0.7  # 0.0 to 1.0 scale
)

# Generate signals during chemical exposure
exposure_signals = profile.generate_signals(
    time_point=2.0,
    exposures={"carbon_monoxide": 5.0}
)

# Generate signals with multiple factors
combined_signals = profile.generate_signals(
    time_point=3.0,
    exposures={"formaldehyde": 2.0},
    environmental_conditions={"temperature": 32.0, "humidity": 80.0},
    exercise_level=0.3,
    stress_level=0.4
)

# Calculate integrated stress index
stress_index = profile.calculate_stress_index()

# Calculate energy expenditure
met_value = profile.calculate_energy_expenditure()

# Detect physiological patterns
patterns = profile.detect_biometric_pattern()
```

### Demographic Variants

```python
# Create an athletic young adult profile
athlete = profile.create_demographic_variant(
    age=25,
    fitness_level=0.9,
    stress_sensitivity=0.8,
    name="Athletic Young Adult"
)

# Create an older adult with higher chemical sensitivity
older_adult = profile.create_demographic_variant(
    age=68,
    fitness_level=0.4,
    chemical_sensitivity=1.3,
    name="Older Adult"
)
```

## See Also

- [Biometric Profile Example](./examples/biometric_profile_example.py) - Comprehensive demonstration of all features
- [Heart Rate Example](./examples/heart_rate_example.py) - Focused example of heart rate response modeling
- [Respiratory Example](./examples/respiratory_example.py) - Focused example of respiratory pattern modeling
- [Skin Conductance Example](./examples/skin_conductance_example.py) - Focused example of skin conductance response

## Integration Points

- **Exposure Tracking System**: Biometric profiles can be linked to exposure histories to show physiological responses to exposures over time
- **Sensitivity Profiles**: Can be incorporated into biometric profiles for personalized response modeling
- **Correlation Engine**: Provides temporal correlation between exposure events and physiological responses
- **Visualization Dashboard**: Visualizes biometric signals and their changes in response to stimuli
