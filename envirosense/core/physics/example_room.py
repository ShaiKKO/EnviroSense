"""
EnviroSense Physics Engine - Example Room Simulation

This example demonstrates the use of the physical space modeling system,
including the spatial grid, room geometry, coordinate transformations,
and airflow modeling.
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from envirosense.core.physics.space import SpatialGrid
from envirosense.core.physics.geometry import Room, Material, GeometryLoader
from envirosense.core.physics.coordinates import Vector3D
from envirosense.core.physics.airflow import VentilationSource, AirflowModel, AirflowVisualizer


def create_example_room():
    """Create an example office room with standard dimensions."""
    # Load a template office room
    room = GeometryLoader.load_room_template("office")
    
    # Print room information
    print(f"Created room: {room.name}")
    print(f"Dimensions: {room.dimensions} meters")
    print(f"Objects: {len(room.get_all_objects())}")
    
    return room


def setup_spatial_grid(room):
    """Set up a spatial grid based on room dimensions."""
    # Convert room dimensions to grid cells (10cm resolution)
    cell_size = 0.1  # meters
    width = int(room.dimensions[0] / cell_size)
    length = int(room.dimensions[1] / cell_size)
    height = int(room.dimensions[2] / cell_size)
    
    # Create spatial grid
    grid = SpatialGrid((width, length, height), cell_size)
    
    print(f"Created spatial grid with dimensions: {grid.dimensions} cells")
    print(f"Cell size: {grid.cell_size} meters")
    print(f"Total cells: {width * length * height}")
    
    return grid


def setup_airflow_model(grid, room):
    """Set up an airflow model with ventilation sources."""
    # Create airflow model
    airflow = AirflowModel(grid, room)
    
    # Add a supply vent (HVAC inlet)
    vent_position = (0.5, 0.5, room.dimensions[2] - 0.2)  # Near ceiling
    vent_direction = (0.7, 0.7, -1.0)  # Diagonal downward
    supply_vent = VentilationSource(
        name="supply_vent",
        position=vent_position,
        direction=vent_direction,
        flow_rate=0.05,  # m³/s
        source_type=VentilationSource.TYPE_INLET,
        radius=0.15
    )
    airflow.add_source(supply_vent)
    
    # Add a return vent (HVAC outlet)
    return_position = (room.dimensions[0] - 0.5, room.dimensions[1] - 0.5, 0.3)  # Near floor, opposite corner
    return_direction = (0.0, 0.0, 1.0)  # Upward
    return_vent = VentilationSource(
        name="return_vent",
        position=return_position,
        direction=return_direction,
        flow_rate=0.05,  # m³/s
        source_type=VentilationSource.TYPE_OUTLET,
        radius=0.15
    )
    airflow.add_source(return_vent)
    
    # Add a window 
    # (Assuming we've added a window to the east wall already in the room template)
    window_center_x = 2.5
    window_center_y = 0.1  # Near south wall
    window_center_z = 1.5
    window_direction = (0.0, 1.0, 0.0)  # Northward (into room)
    window = VentilationSource(
        name="window",
        position=(window_center_x, window_center_y, window_center_z),
        direction=window_direction,
        flow_rate=0.01,  # m³/s (slight breeze)
        source_type=VentilationSource.TYPE_BIDIRECTIONAL,
        radius=0.2
    )
    airflow.add_source(window)
    
    # Set air exchange rate for the room
    airflow.set_air_exchange_rate(2.0)  # 2 air changes per hour
    
    print(f"Created airflow model with {len(airflow.get_sources())} sources")
    
    return airflow


def add_contaminant(grid, position, concentration):
    """Add a contaminant to the specified position in the grid."""
    # Convert physical position to grid coordinates
    x = int(position[0] / grid.cell_size)
    y = int(position[1] / grid.cell_size)
    z = int(position[2] / grid.cell_size)
    
    # Ensure position is within bounds
    x = max(0, min(x, grid.dimensions[0] - 1))
    y = max(0, min(y, grid.dimensions[1] - 1))
    z = max(0, min(z, grid.dimensions[2] - 1))
    
    # Add contaminant
    grid.set_parameter_at((x, y, z), "voc_concentration", concentration)
    print(f"Added contaminant at position ({x}, {y}, {z}) with concentration {concentration}")


def visualize_airflow(airflow_model):
    """Visualize airflow patterns using streamlines."""
    # Create figure
    fig, axs = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Airflow Patterns in Room")
    
    # xy plane (horizontal slice)
    X, Y, U, V = AirflowVisualizer.create_streamlines(
        airflow_model, plane='xy', offset=airflow_model.grid.dimensions[2] // 2
    )
    axs[0].set_title("Horizontal Slice (Middle Height)")
    axs[0].set_xlabel("X (meters)")
    axs[0].set_ylabel("Y (meters)")
    AirflowVisualizer.plot_streamlines(axs[0], X, Y, U, V, density=1.5)
    
    # xz plane (vertical slice)
    X, Z, U, V = AirflowVisualizer.create_streamlines(
        airflow_model, plane='xz', offset=airflow_model.grid.dimensions[1] // 2
    )
    axs[1].set_title("Vertical Slice (Middle Width)")
    axs[1].set_xlabel("X (meters)")
    axs[1].set_ylabel("Z (meters)")
    AirflowVisualizer.plot_streamlines(axs[1], X, Z, U, V, density=1.5)
    
    # yz plane (vertical slice)
    Y, Z, U, V = AirflowVisualizer.create_streamlines(
        airflow_model, plane='yz', offset=airflow_model.grid.dimensions[0] // 2
    )
    axs[2].set_title("Vertical Slice (Middle Length)")
    axs[2].set_xlabel("Y (meters)")
    axs[2].set_ylabel("Z (meters)")
    AirflowVisualizer.plot_streamlines(axs[2], Y, Z, U, V, density=1.5)
    
    plt.tight_layout()
    plt.savefig("airflow_streamlines.png")
    plt.close()
    print("Visualization saved to 'airflow_streamlines.png'")


def visualize_contaminant_spread(grid, parameter_name="voc_concentration"):
    """Visualize the spread of a contaminant through the room."""
    # Create 3D heatmap of parameter distribution
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Get grid dimensions
    width, length, height = grid.dimensions
    
    # Create meshgrid for all positions
    x, y, z = np.meshgrid(
        np.arange(0, width), 
        np.arange(0, length), 
        np.arange(0, height)
    )
    
    # Collect parameter values
    values = np.zeros((length, width, height))
    for i in range(width):
        for j in range(length):
            for k in range(height):
                values[j, i, k] = grid.get_parameter_at((i, j, k), parameter_name)
    
    # Filter points with significant concentration
    threshold = 0.01
    mask = values > threshold
    
    # Plot only points above threshold
    scatter = ax.scatter(
        x[mask], y[mask], z[mask],
        c=values[mask], cmap='hot',
        alpha=0.5, s=30
    )
    
    # Add colorbar
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label('Concentration')
    
    # Set labels
    ax.set_xlabel('X (cells)')
    ax.set_ylabel('Y (cells)')
    ax.set_zlabel('Z (cells)')
    ax.set_title(f'Contaminant Distribution ({parameter_name})')
    
    plt.savefig("contaminant_distribution.png")
    plt.close()
    print("Visualization saved to 'contaminant_distribution.png'")


def run_simulation():
    """Run a full example simulation of a room with airflow and contaminant."""
    print("Starting EnviroSense Physical Space Modeling example...")
    
    # Create room geometry
    room = create_example_room()
    
    # Set up spatial grid
    grid = setup_spatial_grid(room)
    
    # Set up airflow model
    airflow = setup_airflow_model(grid, room)
    
    # Calculate initial velocity field
    airflow.calculate_velocity_field()
    print("Calculated initial velocity field")
    
    # Add a contaminant source
    contaminant_position = (2.0, 1.0, 0.5)  # Middle of room, near floor
    add_contaminant(grid, contaminant_position, 10.0)
    
    # Visualize initial airflow
    visualize_airflow(airflow)
    
    # Run simulation for 5 minutes
    print("Running simulation for 5 minutes of room time...")
    simulation_duration = 300  # seconds
    airflow.simulate(["voc_concentration"], simulation_duration)
    
    # Visualize contaminant spread
    visualize_contaminant_spread(grid)
    
    print("Simulation complete!")


if __name__ == "__main__":
    try:
        run_simulation()
    except Exception as e:
        print(f"Error in simulation: {str(e)}")
