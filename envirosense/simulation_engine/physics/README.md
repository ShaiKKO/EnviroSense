# EnviroSense Physics Engine - Physical Space Modeling

This module provides the core components for 3D spatial modeling, room geometry definition, coordinate transformations, and airflow simulation in the EnviroSense environment monitoring system.

## Overview

The Physical Space Modeling system enables EnviroSense to simulate how environmental parameters (such as VOCs, particulates, temperature, etc.) distribute and evolve within indoor environments. The system combines a 3D spatial grid, geometric objects representing the physical space, and airflow modeling to create realistic simulations of parameter propagation.

## Core Components

### Spatial Grid System (`space.py`)

The spatial grid discretizes 3D space into a collection of cells, each capable of storing environmental parameter values.

- `SpatialGrid`: Implements a 3D discretized space with configurable resolution
- `GridCell`: Represents a discrete cell in the grid with parameter storage and neighbor relationships
- Features include grid-based parameter diffusion, boundary conditions, and coordinate transformation

### Room Geometry Framework (`geometry.py`)

Defines geometric objects that represent physical elements of indoor environments.

- `Material`: Represents physical and chemical properties of materials
- `GeometryObject`: Base class for all physical objects 
- `Wall`, `Window`, `Door`: Specific implementations of common room elements
- `Room`: Container for geometric objects with helper methods for standard room creation
- `GeometryLoader`: Utility for loading room configurations from templates or files

### Coordinate Transformation Utilities (`coordinates.py`)

Provides utilities for transforming between different coordinate systems and performing spatial operations.

- `Vector3D`: Represents a 3D vector with common operations
- `CoordinateSystem`: Handles conversions between Cartesian, cylindrical, and spherical coordinates
- `Transform`: Represents a hierarchical transformation in 3D space (translation, rotation, scaling)

### Airflow Modeling System (`airflow.py`)

Models airflow patterns in enclosed spaces to simulate how parameters propagate through air.

- `VentilationSource`: Represents sources of airflow like vents, fans, or openings
- `AirflowModel`: Manages the simulation of airflow patterns and parameter advection
- `AirflowVisualizer`: Utilities for visualizing airflow patterns

## Example Usage

### Basic Room Setup

```python
from envirosense.core.physics.space import SpatialGrid
from envirosense.core.physics.geometry import GeometryLoader
from envirosense.core.physics.airflow import AirflowModel, VentilationSource

# Create a room from a template
room = GeometryLoader.load_room_template("office")

# Create a spatial grid with 10cm resolution
width = int(room.dimensions[0] / 0.1)
length = int(room.dimensions[1] / 0.1)
height = int(room.dimensions[2] / 0.1)
grid = SpatialGrid((width, length, height), 0.1)

# Create airflow model
airflow = AirflowModel(grid, room)

# Add a vent
supply_vent = VentilationSource(
    name="supply_vent",
    position=(0.5, 0.5, 2.5),
    direction=(0, 0, -1),
    flow_rate=0.05,
    source_type=VentilationSource.TYPE_INLET
)
airflow.add_source(supply_vent)

# Add a parameter source
grid.set_parameter_at((10, 10, 5), "voc_concentration", 10.0)

# Run simulation for 5 minutes
airflow.simulate(["voc_concentration"], 300)
```

### Full Example

See `example_room.py` for a complete demonstration of all components working together, including visualization of airflow patterns and contaminant spread.

## Testing

Unit tests are provided in `test_physics_core.py` to verify the functionality of each component. These tests serve as additional examples of how to use the API.

## Performance Considerations

- The system is designed for computational efficiency with a balance of accuracy and speed
- For large simulations, consider adjusting grid resolution to balance detail and performance
- Visualizations can be memory-intensive; use selectively for large simulations
