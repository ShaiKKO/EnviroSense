# EnviroSense Chemical Module

This module provides the implementation for Task 1.2.2: Chemical Source Implementation of the EnviroSense project. It contains classes for simulating various chemical sources, a comprehensive chemical properties database, and utilities for modeling how chemicals interact with the environment.

## Components

### Chemical Properties Database

The `chemical_properties.py` file contains a database of chemical and particulate matter properties relevant to environmental monitoring, including:

- Physical properties (molecular weight, diffusion coefficients, density)
- Environmental behavior (volatility, reactivity, deposition rates)
- Temperature and humidity scaling factors
- Health-related thresholds and exposure limits
- Typical sources and concentrations

Each chemical is categorized into one of the following types:
- Volatile Organic Compounds (VOCs)
- Inorganic Gases
- Particulate Matter
- Bioaerosols
- Radiation
- Semi-Volatile Organic Compounds

### Chemical Sources

The `sources.py` file implements various chemical source types, each with different emission patterns:

1. **Base ChemicalSource Class**: Abstract base class that defines the common interface and functionality for all source types.

2. **ConstantSource**: Emits at a constant rate, though still affected by environmental factors like temperature and humidity.
   - Example use: Building materials continuously emitting formaldehyde

3. **PulsedSource**: Alternates between active and inactive states based on a defined pulse period and duty cycle.
   - Example use: Intermittent emissions like vehicle traffic or industrial processes

4. **DecayingSource**: Starts strong and decays over time following an exponential decay model.
   - Example use: Chemical spills, evaporating liquids, or other diminishing sources

5. **DiurnalSource**: Varies emission by time of day following a sinusoidal pattern.
   - Example use: Natural processes that follow day/night cycles or human activities with daily patterns

6. **EventTriggeredSource**: Remains inactive until triggered by an event, then emits according to a specified pattern.
   - Example use: Cooking, cleaning, or other episodic activities

### ChemicalSourceManager

The `sources.py` file also includes a `ChemicalSourceManager` class that provides:

- Source collection management (add, remove, lookup sources)
- Batch operations on sources (activate/deactivate all)
- Spatial queries (find sources in a radius)
- Batch emission calculations
- Source triggering
- Emission statistics

## Environmental Factors

Chemical emissions are affected by environmental factors:

1. **Temperature**: Emissions generally increase with temperature, modeled using:
   - Linear scaling
   - Arrhenius equation (for chemical reactions)
   - Complex reference curves

2. **Humidity**: Affects emission rates depending on the chemical's hygroscopic properties.

## Usage Example

```python
from envirosense.core.chemical import (
    ChemicalSource, ConstantSource, ChemicalSourceManager
)

# Create a source manager
manager = ChemicalSourceManager()

# Add a constant formaldehyde source (e.g., from furniture)
furniture_source = ConstantSource(
    source_id="furniture_formaldehyde",
    position=(2.5, 2.0, 1.0),  # 3D position in meters
    chemical_id="formaldehyde",
    initial_strength=0.05,  # g/s
    properties={
        "description": "New furniture emitting formaldehyde",
        "temperature_sensitive": True
    }
)
manager.add_source(furniture_source)

# Time-stepping simulation
def get_environment(position):
    # Return environmental conditions at this position
    return {"temperature": 25.0, "relative_humidity": 50.0}

def apply_emission(source, emission_rate):
    # Apply the emission to your environment model
    print(f"Source {source.source_id} emitted {emission_rate} g/s")

# Apply emissions for a single time step
emission_rates = manager.apply_emissions(
    time_step=60.0,  # seconds
    environment_function=get_environment,
    apply_function=apply_emission
)
```

## Demonstration

A demonstration script is provided in `test_chemical_sources.py`, which:

1. Creates various chemical sources with different emission patterns
2. Simulates emissions over time
3. Shows how environmental factors like temperature and humidity affect emission rates
4. Generates visualization plots of emission rates and cumulative emissions
5. Provides statistics about the emissions

Run the demonstration with:

```
python -m envirosense.core.chemical.test_chemical_sources
```

## Integration with Physics Engine

The chemical sources can be integrated with the EnviroSense Physics Engine (Task 1.2.1) to model how chemicals diffuse through space under the influence of airflow.
