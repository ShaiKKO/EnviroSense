"""
EnviroSense Chemical-Physics Integration

This script demonstrates the integration between the Chemical Sources module (Task 1.2.2)
and the Physics Engine (Task 1.2.1). It shows how chemical sources can be incorporated
into a physical environment simulation to model the spread of chemicals in a room.

The integration demonstrates:
1. Creating a room with the Physics Engine
2. Adding various chemical sources to the room
3. Simulating how chemicals diffuse through the room under airflow influences
4. Visualizing chemical concentrations across the room over time
"""

import os
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

from envirosense.core.physics.coordinates import Vector3D
from envirosense.core.physics.space import SpatialGrid
from envirosense.core.physics.geometry import Room, Material, Wall
from envirosense.core.physics.airflow import AirflowModel, VentilationSource

from envirosense.core.chemical.chemical_properties import (
    ChemicalCategory,
    CHEMICAL_PROPERTIES,
    get_chemical_property,
    get_diffusion_coefficient
)
from envirosense.core.chemical.sources import (
    SourceStatus,
    ChemicalSource,
    ConstantSource,
    PulsedSource,
    DecayingSource,
    DiurnalSource,
    EventTriggeredSource,
    ChemicalSourceManager
)


def create_output_directory():
    """Create output directory for plots if it doesn't exist."""
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "plots")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return output_dir


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


def setup_sources(grid_cell_size: float) -> ChemicalSourceManager:
    """Set up chemical sources in the room."""
    manager = ChemicalSourceManager()
    
    # 1. Formaldehyde from new furniture (constant source)
    furniture_source = ConstantSource(
        source_id="furniture_formaldehyde",
        position=(2.5, 2.0, 0.8),  # Coffee table in center of room
        chemical_id="formaldehyde",
        initial_strength=0.01,  # g/s (lower than test case)
        properties={
            "description": "New furniture emitting formaldehyde",
            "temperature_sensitive": True,
            "radius": 0.5  # Apply within this radius
        }
    )
    manager.add_source(furniture_source)
    
    # 2. Nitrogen dioxide from outdoor pollution (near window, diurnal pattern)
    outdoor_no2 = DiurnalSource(
        source_id="outdoor_no2",
        position=(4.9, 2.0, 1.7),  # Near window
        chemical_id="nitrogen_dioxide",
        initial_strength=0.005,  # g/s at peak
        peak_hour=17,           # 5 PM peak (rush hour)
        trough_hour=4,          # 4 AM trough
        min_factor=0.1,         # 10% of peak at trough
        properties={
            "description": "Outdoor NO2 pollution entering through window gaps",
            "temperature_sensitive": True,
            "radius": 0.3  # Apply within this radius
        }
    )
    manager.add_source(outdoor_no2)
    
    # 3. Benzene source near entrance (car exhaust, pulsed)
    car_exhaust = PulsedSource(
        source_id="car_exhaust",
        position=(2.5, 0.1, 0.9),  # Near door
        chemical_id="benzene",
        initial_strength=0.015,  # g/s when active
        pulse_period=600.0,      # 10 minutes cycle
        duty_cycle=0.2,          # Active 20% of the time
        properties={
            "description": "Vehicle exhaust entering through doorway",
            "temperature_sensitive": False,
            "radius": 0.6  # Apply within this radius
        }
    )
    manager.add_source(car_exhaust)
    
    # 4. Ethanol from hand sanitizer (decaying source, near door)
    sanitizer = DecayingSource(
        source_id="hand_sanitizer",
        position=(3.5, 0.3, 1.2),  # Table near entrance
        chemical_id="ethanol",
        initial_strength=0.08,   # g/s
        half_life=1200.0,       # 20 minutes half-life
        properties={
            "description": "Hand sanitizer at entrance",
            "temperature_sensitive": True,
            "humidity_sensitive": True,
            "radius": 0.4  # Apply within this radius
        }
    )
    manager.add_source(sanitizer)
    
    # 5. Carbon monoxide for cooking event (to be triggered later)
    cooking_source = EventTriggeredSource(
        source_id="cooking_activity",
        position=(4.5, 3.5, 1.2),  # Kitchen area
        chemical_id="carbon_monoxide",
        initial_strength=0.05,     # g/s
        emission_duration=1800.0,  # 30 minutes
        pattern="decay",           # Decaying pattern after trigger
        properties={
            "description": "Carbon monoxide from cooking",
            "decay_half_life": 600.0,  # 10 minutes half-life
            "temperature_sensitive": True,
            "radius": 0.8  # Apply within this radius
        }
    )
    manager.add_source(cooking_source)
    
    return manager


def integrate_chemical_physics():
    """Run a simulation integrating chemicals and physics."""
    print("Setting up physical environment...")
    room = create_office_room()
    
    # Create a spatial grid with 25cm resolution
    print("Creating spatial grid...")
    grid_cell_size = 0.25  # meters
    width = int(room.dimensions[0] / grid_cell_size)
    length = int(room.dimensions[1] / grid_cell_size)
    height = int(room.dimensions[2] / grid_cell_size)
    grid = SpatialGrid((width, length, height), grid_cell_size)
    
    # Initialize environmental parameters
    print("Initializing grid parameters...")
    for x in range(width):
        for y in range(length):
            for z in range(height):
                # Set initial temperature (gradient with warmer at ceiling)
                temperature = 20.0 + (z * grid_cell_size / room.dimensions[2]) * 3.0
                grid.set_parameter_at((x, y, z), "temperature", temperature)
                
                # Set initial humidity
                grid.set_parameter_at((x, y, z), "relative_humidity", 50.0)
                
                # Initialize chemical concentrations to zero
                for chemical_id in ["formaldehyde", "nitrogen_dioxide", "benzene", "ethanol", "carbon_monoxide"]:
                    grid.set_parameter_at((x, y, z), chemical_id, 0.0)  # ppm
    
    # Create airflow model
    print("Setting up airflow model...")
    airflow = AirflowModel(grid, room)
    
    # Add ventilation sources
    # Supply vent on the ceiling
    supply_vent = VentilationSource(
        name="supply_vent",
        position=(2.5, 2.0, 3.0),  # Center of ceiling
        direction=(0, 0, -1),      # Blowing down
        flow_rate=0.3,             # m³/s (moderate airflow)
        source_type=VentilationSource.TYPE_INLET,
        radius=0.2
    )
    airflow.add_source(supply_vent)
    
    # Return vent near floor on west wall
    return_vent = VentilationSource(
        name="return_vent",
        position=(0.2, 2.0, 0.3),  # Near floor on west wall
        direction=(1, 0, 0),       # Pulling air toward west wall
        flow_rate=0.3,             # m³/s (matching supply)
        source_type=VentilationSource.TYPE_OUTLET,
        radius=0.2
    )
    airflow.add_source(return_vent)
    
    # Set up chemical sources
    print("Setting up chemical sources...")
    source_manager = setup_sources(grid_cell_size)
    
    # Calculate initial velocity field
    print("Calculating airflow patterns...")
    velocity_field = airflow.calculate_velocity_field()
    
    # Time parameters
    simulation_duration = 7200.0  # 2 hours in seconds
    time_step = 60.0  # 1 minute time step
    
    # Prepare to store data for visualization
    chemicals_to_track = ["formaldehyde", "nitrogen_dioxide", "benzene", "ethanol", "carbon_monoxide"]
    snapshot_times = [0, 900, 1800, 3600, 7140]  # Times to save snapshots (in seconds)
    snapshots = {chem: {t: np.zeros((width, length, height)) for t in snapshot_times} for chem in chemicals_to_track}
    
    # Trigger time for cooking event
    cooking_trigger_time = 1800  # 30 minutes into simulation
    
    # Helper function to get environment at a position
    def get_environment_at_position(position):
        """Get environmental conditions at a position."""
        # Convert from meters to grid coordinates
        x = int(position.x / grid_cell_size)
        y = int(position.y / grid_cell_size)
        z = int(position.z / grid_cell_size)
        
        # Ensure coordinates are within grid bounds
        x = max(0, min(x, width - 1))
        y = max(0, min(y, length - 1))
        z = max(0, min(z, height - 1))
        
        return {
            "temperature": grid.get_parameter_at((x, y, z), "temperature"),
            "relative_humidity": grid.get_parameter_at((x, y, z), "relative_humidity")
        }
    
    # Helper function to apply chemical emission to the grid
    def apply_emission_to_grid(source, emission_rate):
        """Apply chemical emission to grid cells within the source's radius."""
        if emission_rate <= 0:
            return
            
        # Get source position in grid coordinates
        source_x = int(source.position.x / grid_cell_size)
        source_y = int(source.position.y / grid_cell_size)
        source_z = int(source.position.z / grid_cell_size)
        
        # Get radius in grid cells
        radius_cells = int(source.properties.get("radius", 0.5) / grid_cell_size)
        
        # Calculate volume of a grid cell in m³
        cell_volume = grid_cell_size ** 3
        
        # Convert emission rate from g/s to concentration increase per cell
        # This is a simplification - in reality would need to account for 
        # molecular weight, temperature, pressure, etc.
        
        # Approximate conversion using typical molecular weights
        # Formula: ppm = (mg/m³) * (24.45 / molecular_weight) at 25°C and 1 atm
        molecular_weight = CHEMICAL_PROPERTIES[source.chemical_id].get("molecular_weight", 100.0)
        
        # Calculate mg/m³ from g/s spread over affected cells
        affected_cells = (2 * radius_cells + 1) ** 3  # Approximate cube of influence
        emission_mg_per_m3 = (emission_rate * 1000) / (affected_cells * cell_volume)
        
        # Convert to ppm
        emission_ppm = emission_mg_per_m3 * (24.45 / molecular_weight)
        
        # Apply to grid with distance-based falloff
        for dx in range(-radius_cells, radius_cells + 1):
            for dy in range(-radius_cells, radius_cells + 1):
                for dz in range(-radius_cells, radius_cells + 1):
                    x = source_x + dx
                    y = source_y + dy
                    z = source_z + dz
                    
                    # Skip if outside grid
                    if not (0 <= x < width and 0 <= y < length and 0 <= z < height):
                        continue
                    
                    # Calculate distance-based falloff (inverse square law)
                    distance = math.sqrt(dx**2 + dy**2 + dz**2) * grid_cell_size
                    if distance < 0.01:  # Avoid division by zero
                        distance = 0.01
                        
                    # Apply inverse square falloff with minimum threshold
                    falloff = min(1.0, (source.properties.get("radius", 0.5) / distance) ** 2)
                    
                    # Get current concentration and add emission
                    current = grid.get_parameter_at((x, y, z), source.chemical_id)
                    new_value = current + emission_ppm * falloff * (time_step / 60.0)  # Scale by time step 
                    
                    grid.set_parameter_at((x, y, z), source.chemical_id, new_value)
    
    # Run simulation
    print(f"Running integrated simulation for {simulation_duration/3600:.1f} hours...")
    current_time = 0.0
    
    while current_time < simulation_duration:
        # Print progress
        if int(current_time) % 600 == 0:  # Every 10 minutes
            print(f"  Simulation time: {current_time/60:.1f} minutes")
        
        # Check if we need to trigger the cooking event
        if current_time <= cooking_trigger_time < current_time + time_step:
            print(f"  Triggering cooking event at {current_time/60:.1f} minutes")
            source_manager.trigger_source("cooking_activity")
        
        # Apply emissions from all sources
        emission_rates = source_manager.apply_emissions(
            time_step=time_step,
            environment_function=get_environment_at_position,
            apply_function=apply_emission_to_grid
        )
        
        # Apply airflow effects
        airflow.apply_airflow_step(chemicals_to_track)
        
        # Apply natural diffusion for each chemical
        for chemical_id in chemicals_to_track:
            # Get base diffusion coefficient from database
            base_diffusion = get_chemical_property(chemical_id, "diffusion_coefficient") or 1e-5
            
            # Scale to appropriate units for the grid
            diffusion_coefficient = base_diffusion * (time_step / grid_cell_size**2) * 10
            
            # Apply diffusion
            grid.diffuse_parameter(chemical_id, diffusion_coefficient)
        
        # Update time
        current_time += time_step
        
        # Save snapshots at specific times
        if current_time in snapshot_times:
            print(f"  Saving snapshot at {current_time/60:.1f} minutes")
            for chemical_id in chemicals_to_track:
                for x in range(width):
                    for y in range(length):
                        for z in range(height):
                            snapshots[chemical_id][current_time][x, y, z] = grid.get_parameter_at((x, y, z), chemical_id)
    
    print("Simulation complete")
    
    # Create visualizations
    output_dir = create_output_directory()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Visualization for each chemical at different time points
    for chemical_id in chemicals_to_track:
        chemical_name = CHEMICAL_PROPERTIES[chemical_id]["name"]
        print(f"Generating visualizations for {chemical_name}...")
        
        plt.figure(figsize=(15, 10))
        subplot_count = 1
        
        for t in snapshot_times:
            if t == 0:
                continue  # Skip initial state which is all zeros
                
            # Create horizontal slices at different heights
            for height_fraction in [0.2, 0.5, 0.8]:
                z_idx = int(height * height_fraction)
                height_meters = z_idx * grid_cell_size
                
                plt.subplot(len(snapshot_times) - 1, 3, subplot_count)
                subplot_count += 1
                
                # Extract horizontal slice
                slice_data = snapshots[chemical_id][t][:, :, z_idx].transpose()
                
                # Determine max value for consistent color scaling
                max_val = np.max(snapshots[chemical_id][t])
                if max_val == 0:
                    max_val = 0.001  # Avoid divide by zero
                
                # Create heatmap
                im = plt.imshow(slice_data, 
                           cmap='hot', 
                           extent=(0, room.dimensions[0], 0, room.dimensions[1]),
                           origin='lower',
                           vmin=0, vmax=max_val)
                
                plt.colorbar(im, label=f'Concentration (ppm)')
                plt.title(f'{chemical_name} at t={t/60:.0f}min, h={height_meters:.1f}m')
                plt.xlabel('X (m)')
                plt.ylabel('Y (m)')
                plt.grid(True)
        
        plt.tight_layout()
        
        # Save the visualization
        filename = os.path.join(output_dir, f"chemical_physics_{chemical_id}_{timestamp}.png")
        plt.savefig(filename, dpi=300)
        print(f"Visualization saved to {filename}")
    
    # Create a summary visualization showing all chemicals at final time
    plt.figure(figsize=(15, 8))
    
    for i, chemical_id in enumerate(chemicals_to_track):
        chemical_name = CHEMICAL_PROPERTIES[chemical_id]["name"]
        
        plt.subplot(1, len(chemicals_to_track), i+1)
        
        # Use middle height
        z_idx = int(height * 0.5)
        
        # Extract horizontal slice
        slice_data = snapshots[chemical_id][snapshot_times[-1]][:, :, z_idx].transpose()
        
        # Create heatmap
        im = plt.imshow(slice_data, 
                   cmap='hot', 
                   extent=(0, room.dimensions[0], 0, room.dimensions[1]),
                   origin='lower')
        
        plt.colorbar(im, label=f'ppm')
        plt.title(f'{chemical_name}')
        plt.xlabel('X (m)')
        if i == 0:
            plt.ylabel('Y (m)')
        plt.grid(True)
    
    plt.tight_layout()
    
    # Save the summary visualization
    summary_filename = os.path.join(output_dir, f"chemical_physics_summary_{timestamp}.png")
    plt.savefig(summary_filename, dpi=300)
    print(f"Summary visualization saved to {summary_filename}")
    
    # Return results for further analysis
    return {
        "room": room,
        "grid": grid,
        "airflow": airflow,
        "source_manager": source_manager,
        "snapshots": snapshots
    }


if __name__ == "__main__":
    results = integrate_chemical_physics()
    print("Integration demonstration completed successfully")
