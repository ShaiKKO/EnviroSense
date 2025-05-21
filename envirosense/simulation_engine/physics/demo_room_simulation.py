"""
EnviroSense Physics Engine - Room Simulation Demo

This script demonstrates the physics engine capabilities by:
1. Creating a room with standard walls, door, and window
2. Setting up a spatial grid for parameter tracking
3. Adding ventilation sources (inlet and outlet)
4. Adding a contaminant source
5. Running a simulation to show how the contaminant spreads
6. Visualizing the results using matplotlib

The simulation shows how airflow from ventilation affects the spread of a contaminant.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.animation as animation
from datetime import datetime

from envirosense.core.physics.space import SpatialGrid
from envirosense.core.physics.geometry import Room, Material, Wall, GeometryLoader
from envirosense.core.physics.coordinates import Vector3D
from envirosense.core.physics.airflow import AirflowModel, VentilationSource

# Create output directory if it doesn't exist
output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "plots")
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def create_office_room():
    """Create a standard office room with furniture."""
    # Create a room
    room = Room("office", (5.0, 4.0, 3.0))
    
    # Add walls with standard materials
    wall_material = Material.from_library("drywall")
    
    # Add walls (floor and ceiling included)
    walls = [
        # Floor
        Wall("floor", Material.from_library("concrete"), 
             (0, 0, 0), (5, 4, 0), 0.2),
        # Ceiling
        Wall("ceiling", wall_material, 
             (0, 0, 3), (5, 4, 3), 0.1),
        # Walls
        Wall("north_wall", wall_material, 
             (0, 4, 0), (5, 4, 3), 0.1),
        Wall("south_wall", wall_material, 
             (0, 0, 0), (5, 0, 3), 0.1),
        Wall("east_wall", wall_material, 
             (5, 0, 0), (5, 4, 3), 0.1),
        Wall("west_wall", wall_material, 
             (0, 0, 0), (0, 4, 3), 0.1),
    ]
    
    for wall in walls:
        room.add_object(wall)
    
    # Add a window on the east wall
    window = Wall("window", Material.from_library("glass"), 
                 (5, 1.5, 1.2), (5, 2.5, 2.2), 0.05)
    window.material.permeability = 0.0  # Window is closed
    room.add_object(window)
    
    # Add a door on the south wall
    door = Wall("door", Material.from_library("wood"), 
               (2, 0, 0), (3, 0, 2.1), 0.05)
    door.material.permeability = 0.05  # Door slightly open
    room.add_object(door)
    
    return room

def run_simulation(visualize=True, save_plots=True):
    """Run a simulation of contaminant spread in a room with ventilation."""
    print("Creating room...")
    room = create_office_room()
    
    # Create a spatial grid with 20cm resolution
    print("Setting up spatial grid...")
    grid_cell_size = 0.2  # meters
    width = int(room.dimensions[0] / grid_cell_size)
    length = int(room.dimensions[1] / grid_cell_size)
    height = int(room.dimensions[2] / grid_cell_size)
    grid = SpatialGrid((width, length, height), grid_cell_size)
    
    # Initialize parameters
    for x in range(width):
        for y in range(length):
            for z in range(height):
                # Set initial temperature
                grid.set_parameter_at((x, y, z), "temperature", 22.0)  # 22°C
                # Set initial VOC concentration
                grid.set_parameter_at((x, y, z), "voc", 0.0)  # ppm
    
    # Create airflow model
    print("Setting up airflow model...")
    airflow = AirflowModel(grid, room)
    
    # Add ventilation sources
    # Supply vent on the ceiling
    supply_vent = VentilationSource(
        name="supply_vent",
        position=(2.5, 2.0, 3.0),  # Center of ceiling
        direction=(0, 0, -1),      # Blowing down
        flow_rate=0.5,             # m³/s (relatively strong)
        source_type=VentilationSource.TYPE_INLET,
        radius=0.2
    )
    airflow.add_source(supply_vent)
    
    # Return vent near floor on west wall
    return_vent = VentilationSource(
        name="return_vent",
        position=(0.2, 2.0, 0.3),  # Near floor on west wall
        direction=(1, 0, 0),       # Pulling air toward west wall
        flow_rate=0.5,             # m³/s (matching supply)
        source_type=VentilationSource.TYPE_OUTLET,
        radius=0.2
    )
    airflow.add_source(return_vent)
    
    # VOC source near east wall (e.g., a cleaning product)
    # Add a concentrated source of VOC
    voc_source_x = int(4.5 / grid_cell_size)
    voc_source_y = int(2.0 / grid_cell_size)
    voc_source_z = int(1.0 / grid_cell_size)
    
    # Place a strong VOC concentration
    grid.set_parameter_at((voc_source_x, voc_source_y, voc_source_z), "voc", 100.0)
    
    # Calculate initial velocity field
    print("Calculating airflow patterns...")
    velocity_field = airflow.calculate_velocity_field()
    
    # Storage for simulation data
    voc_data = []
    
    # Record initial state
    voc_snapshot = np.zeros((width, length, height))
    for x in range(width):
        for y in range(length):
            for z in range(height):
                voc_snapshot[x, y, z] = grid.get_parameter_at((x, y, z), "voc")
    voc_data.append(voc_snapshot.copy())
    
    # Run simulation for several steps
    print("Running simulation steps...")
    num_steps = 50
    for step in range(num_steps):
        print(f"Step {step+1}/{num_steps}", end="\r")
        
        # Apply airflow effects to parameters
        airflow.apply_airflow_step(["voc"])
        
        # Diffuse parameters naturally
        grid.diffuse_parameter("voc", 0.1)  # Diffusion coefficient
        
        # Record state
        voc_snapshot = np.zeros((width, length, height))
        for x in range(width):
            for y in range(length):
                for z in range(height):
                    voc_snapshot[x, y, z] = grid.get_parameter_at((x, y, z), "voc")
        voc_data.append(voc_snapshot.copy())
    
    print("\nSimulation complete!")
    
    if visualize:
        # Create visualizations
        print("Generating visualizations...")
        
        # Visualization parameters
        timesteps = [0, 5, 15, 30, 49]  # Initial, early, middle, late steps
        heights = [0.4, 1.5, 2.5]  # Floor level, mid-level, ceiling level
        
        # Create a figure and subplots grid
        fig, axes = plt.subplots(nrows=len(heights), ncols=len(timesteps), figsize=(15, 10))
        
        # Function to create a slice plot at different heights
        def plot_slice(step, z_level, title, ax):
            z_idx = int(z_level / grid_cell_size)
            
            # Create a slice at the specified height
            slice_data = voc_data[step][:, :, z_idx].transpose()
            
            # Create the heatmap
            im = ax.imshow(slice_data, cmap='hot', 
                       extent=(0, room.dimensions[0], 0, room.dimensions[1]), 
                       origin='lower',
                       vmin=0, vmax=25)  # Set reasonable limits for color scale
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label('VOC Concentration (ppm)')
            
            # Mark ventilation positions
            vent_y = supply_vent.position.y / grid_cell_size
            vent_x = supply_vent.position.x / grid_cell_size
            if abs(z_idx - supply_vent.position.z / grid_cell_size) < 2:
                ax.plot(supply_vent.position.x, supply_vent.position.y, 'bo', markersize=10, label='Supply Vent')
            
            if abs(z_idx - return_vent.position.z / grid_cell_size) < 2:
                ax.plot(return_vent.position.x, return_vent.position.y, 'go', markersize=10, label='Return Vent')
            
            # Mark VOC source
            voc_x = voc_source_x * grid_cell_size
            voc_y = voc_source_y * grid_cell_size
            if abs(z_idx - voc_source_z) < 2:
                ax.plot(voc_x, voc_y, 'ro', markersize=10, label='VOC Source')
            
            # Configure the plot
            ax.set_title(title)
            ax.set_xlabel('X (meters)')
            ax.set_ylabel('Y (meters)')
            ax.grid(True)
            ax.legend(loc='upper right')
        
        # Create a grid of plots showing different times and heights
        for j, height in enumerate(heights):
            for i, step in enumerate(timesteps):
                title = f"Step {step} - Height {height}m"
                plot_slice(step, height, title, axes[j, i])
        
        plt.tight_layout()
        
        if save_plots:
            # Save the visualization
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(output_dir, f"physics_simulation_{timestamp}.png")
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"Visualization saved to {filename}")
        
        plt.show()
    
    return grid, airflow, voc_data

if __name__ == "__main__":
    # Run the simulation
    grid, airflow, voc_data = run_simulation(visualize=True, save_plots=True)
    print("Demo completed successfully")
