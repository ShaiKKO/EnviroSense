"""
Test script for Advanced Environmental Effects in the EnviroSense Physics Engine.

This script demonstrates the combined functionality of barriers, partitions,
and HVAC systems in affecting environmental parameter distribution.
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Dict, List, Tuple

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from envirosense.core.physics.space import SpatialGrid
from envirosense.core.physics.geometry import Room, Material
from envirosense.core.physics.airflow import AirflowModel, VentilationSource
from envirosense.core.physics.barriers import Barrier, BarrierHandler, PartitionedRoom
from envirosense.core.physics.hvac import HVACSystem, AirFilter
from envirosense.core.chemical.sources import ChemicalSource, ConstantSource, DiurnalSource
from envirosense.core.chemical.chemical_properties import CHEMICAL_PROPERTIES, get_chemical_property

# Create output directory for plots
PLOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "plots")
os.makedirs(PLOT_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


def setup_room_with_partition() -> Tuple[SpatialGrid, Room, BarrierHandler]:
    """Set up a room with a partition."""
    # Create a spatial grid for the room
    grid = SpatialGrid(
        dimensions=(20, 30, 10),  # Grid cells
        cell_size=0.2             # Meters per cell
    )
    
    # Set default parameters for all cells
    for pos, cell in grid.iterate_cells():
        cell.set_parameter("temperature", 22.0)
        cell.set_parameter("relative_humidity", 50.0)
    
    # Create a room
    room = Room(
        name="test_room",
        dimensions=(4, 6, 2.5),  # 4m x 6m x 2.5m room
        position=(0, 0, 0)
    )
    
    # Create standard materials
    drywall = Material.from_library("drywall")
    glass = Material.from_library("glass")
    
    # Create a barrier handler
    barrier_handler = BarrierHandler(grid)
    
    # Add a partition wall with a doorway 
    PartitionedRoom.create_room_divider(
        grid=grid,
        barrier_handler=barrier_handler,
        room_origin=(0, 0, 0),
        room_dimensions=(4, 6, 2.5),
        orientation='x',              # Partition along YZ plane
        position_ratio=0.5,           # In the middle of the room
        opening_start=0.4,            # Door starts at 40% of room width
        opening_width=0.2,            # Door is 20% of room width
        material_name="drywall"
    )
    
    # Add a glass barrier
    glass_barrier = Barrier(
        name="glass_divider",
        material=glass,
        start_point=(1.0, 4.0, 0.8),
        end_point=(3.0, 4.2, 2.0),
        thickness=0.01,
        permeability={"temperature": 0.7, "carbon_monoxide": 0.0, "voc_total": 0.0}
    )
    barrier_handler.add_barrier(glass_barrier)
    
    return grid, room, barrier_handler


def setup_hvac_system(grid: SpatialGrid) -> HVACSystem:
    """Set up an HVAC system for the room."""
    # Create an airflow model
    airflow_model = AirflowModel(grid)
    
    # Create an HVAC system
    hvac = HVACSystem(
        name="main_hvac",
        grid=grid,
        airflow_model=airflow_model
    )
    
    # Add supply vents
    hvac.add_supply_vent(
        vent_name="supply_1",
        position=(1.0, 1.0, 2.2),
        direction=(0, 0, -1)
    )
    hvac.add_supply_vent(
        vent_name="supply_2",
        position=(3.0, 5.0, 2.2),
        direction=(0, 0, -1)
    )
    
    # Add return vent
    hvac.add_return_vent(
        vent_name="return_1",
        position=(2.0, 3.0, 0.3)
    )
    
    # Add filters
    hvac.add_filter(
        filter_name="main_filter",
        filter_type="commercial",  # MERV 13-16
    )
    hvac.add_filter(
        filter_name="carbon_filter",
        filter_type="carbon",      # Specialized for gases/VOCs
    )
    
    # Configure HVAC settings
    hvac.set_temperature_setpoints(heating=21.0, cooling=24.0)
    hvac.set_outdoor_air_fraction(0.2)  # 20% fresh air
    
    # Create temperature zones
    zone1_positions = [(x, y, z) for x in range(10) for y in range(15) for z in range(10)]
    zone2_positions = [(x, y, z) for x in range(10, 20) for y in range(15) for z in range(10)]
    
    hvac.define_zone("zone1", zone1_positions)
    hvac.define_zone("zone2", zone2_positions)
    
    return hvac


def add_chemical_sources(grid: SpatialGrid) -> List[ChemicalSource]:
    """Add chemical sources to the environment."""
    sources = []
    
    # Add a constant CO source (simulating human occupancy)
    co2_source = ConstantSource(
        source_id="human_co2",
        position=(1.0, 2.0, 1.0),
        chemical_id="carbon_monoxide",
        initial_strength=0.04,  # kg/hour
        properties={
            "radius": 0.5,  # meters
            "temperature_sensitive": True,
            "humidity_sensitive": False
        }
    )
    sources.append(co2_source)
    
    # Add a formaldehyde source with diurnal variation (building materials off-gassing)
    formaldehyde_source = DiurnalSource(
        source_id="material_offgassing",
        position=(3.0, 5.0, 1.0),
        chemical_id="formaldehyde",
        initial_strength=0.005,  # kg/hour
        peak_hour=15,  # 3 PM peak
        trough_hour=3,  # 3 AM trough
        min_factor=0.2,  # 20% at minimum
        properties={
            "radius": 0.8,  # meters
            "temperature_sensitive": True,
            "humidity_sensitive": True
        }
    )
    sources.append(formaldehyde_source)
    
    return sources


def run_simulation(grid: SpatialGrid, hvac: HVACSystem, 
                  barrier_handler: BarrierHandler, 
                  sources: List[ChemicalSource],
                  time_steps: int, dt: float) -> Dict:
    """
    Run a simulation of the environmental effects.
    
    Args:
        grid: The spatial grid
        hvac: The HVAC system
        barrier_handler: The barrier handler
        sources: List of chemical sources
        time_steps: Number of time steps to simulate
        dt: Time step in seconds
        
    Returns:
        Dictionary with simulation results and metrics
    """
    # Initialize parameters to track
    parameters_to_track = ["temperature", "carbon_monoxide", "formaldehyde"]
    
    # Initialize HVAC
    hvac.set_mode(HVACSystem.MODE_AUTO)
    
    # Store results for plotting
    results = {
        "parameters": parameters_to_track,
        "time_points": np.arange(0, time_steps * dt, dt),
        "zone1_avg": {param: [] for param in parameters_to_track},
        "zone2_avg": {param: [] for param in parameters_to_track},
        "room_avg": {param: [] for param in parameters_to_track}
    }
    
    # Run simulation for specified time steps
    for i in range(time_steps):
        # Emit from sources
        for source in sources:
            # Get environmental conditions at source position
            pos = source.position
            grid_pos = grid.grid_coordinates((pos.x, pos.y, pos.z))
            
            # Make sure the position is within grid bounds
            if grid.is_position_valid(grid_pos):
                cell = grid.get_cell(grid_pos)
                env_data = {
                    "temperature": cell.get_parameter("temperature", 22.0),
                    "relative_humidity": cell.get_parameter("relative_humidity", 50.0)
                }
            else:
                # Use default values if outside grid
                env_data = {
                    "temperature": 22.0,
                    "relative_humidity": 50.0
                }
            
            # Call emit with proper parameters
            source.emit(dt, env_data)
        
        # Diffuse parameters through the grid, accounting for barriers
        for param in parameters_to_track:
            if param != "temperature":  # Temperature handled by HVAC
                # Diffuse with barriers affecting rates
                barrier_handler.diffuse_parameter_with_barriers(param, diffusion_rate=0.1)
        
        # Update HVAC system (heating, cooling, filtration)
        hvac.update_system(dt, parameters_to_track)
        
        # Record averages for each zone and the whole room
        for param in parameters_to_track:
            results["zone1_avg"][param].append(hvac.get_zone_temperature("zone1") if param == "temperature" 
                                            else grid.get_average_parameter(hvac.zones["zone1"], param))
            results["zone2_avg"][param].append(hvac.get_zone_temperature("zone2") if param == "temperature" 
                                            else grid.get_average_parameter(hvac.zones["zone2"], param))
            results["room_avg"][param].append(grid.get_average_parameter(None, param))
    
    return results


def plot_results(results: Dict, save_path: str) -> None:
    """
    Plot simulation results.
    
    Args:
        results: Simulation results
        save_path: Path to save the plot
    """
    # Create subplots for each parameter
    fig, axs = plt.subplots(len(results["parameters"]), 1, figsize=(12, 4 * len(results["parameters"])))
    
    for i, param in enumerate(results["parameters"]):
        ax = axs[i] if len(results["parameters"]) > 1 else axs
        
        # Plot parameter values for each zone and room average
        ax.plot(results["time_points"] / 60, results["zone1_avg"][param], 
                label=f"Zone 1 (Left of Partition)")
        ax.plot(results["time_points"] / 60, results["zone2_avg"][param], 
                label=f"Zone 2 (Right of Partition)")
        ax.plot(results["time_points"] / 60, results["room_avg"][param], 
                label="Room Average", linestyle="--")
        
        # Add labels and legend
        ax.set_xlabel("Time (minutes)")
        
        if param == "temperature":
            ax.set_ylabel("Temperature (°C)")
            ax.set_title("Temperature Variation with HVAC Control")
        elif param == "co2":
            ax.set_ylabel("CO2 (ppm)")
            ax.set_title("CO2 Concentration with Barriers and HVAC Filtration")
        elif param == "formaldehyde":
            ax.set_ylabel("Formaldehyde (ppm)")
            ax.set_title("Formaldehyde Concentration with Barriers and HVAC Filtration")
        else:
            ax.set_ylabel(f"{param.capitalize()}")
            ax.set_title(f"{param.capitalize()} Variation with Barriers and HVAC Control")
        
        ax.legend()
        ax.grid(True)
    
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()


def plot_spatial_snapshot(grid: SpatialGrid, parameter: str, z_level: int, 
                         time_point: str, save_path: str) -> None:
    """
    Plot a spatial snapshot of parameter distribution at a specific height.
    
    Args:
        grid: The spatial grid
        parameter: Parameter to plot
        z_level: Z-level to plot (grid coordinates)
        time_point: Description of the time point (for title)
        save_path: Path to save the plot
    """
    # Get dimensions
    nx, ny, _ = grid.dimensions
    
    # Create a 2D array to hold parameter values
    data = np.zeros((nx, ny))
    
    # Extract parameter values at the specified z-level
    for x in range(nx):
        for y in range(ny):
            cell = grid.get_cell((x, y, z_level))
            if cell:
                data[x, y] = cell.get_parameter(parameter, 0.0)
    
    # Plot heatmap
    plt.figure(figsize=(10, 8))
    
    # Create colormap based on parameter
    cmap = 'viridis'
    if parameter == "temperature":
        cmap = 'coolwarm'
    elif parameter in ["carbon_monoxide", "formaldehyde"]:
        cmap = 'YlOrRd'
    
    # Create the heatmap
    plt.imshow(data.T, origin='lower', cmap=cmap, interpolation='none')
    plt.colorbar(label=f"{parameter.capitalize()}")
    
    # Add labels and title
    plt.xlabel("X coordinate (grid cells)")
    plt.ylabel("Y coordinate (grid cells)")
    plt.title(f"{parameter.capitalize()} Distribution at Z={z_level} - {time_point}")
    
    # Mark partition locations (assuming barrier handler or room info available)
    plt.axvline(x=nx/2, color='black', linestyle='--', alpha=0.7, label="Partition")
    
    plt.legend()
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()


def main():
    """Run the environmental effects test."""
    print("Setting up environment...")
    grid, room, barrier_handler = setup_room_with_partition()
    hvac = setup_hvac_system(grid)
    sources = add_chemical_sources(grid)
    
    print("Running simulation...")
    results = run_simulation(
        grid=grid,
        hvac=hvac,
        barrier_handler=barrier_handler,
        sources=sources,
        time_steps=120,  # 120 steps
        dt=30            # 30 seconds per step = 1 hour total
    )
    
    print("Plotting results...")
    # Plot time series results
    plot_results(
        results=results,
        save_path=os.path.join(PLOT_DIR, f"environmental_effects_{timestamp}.png")
    )
    
    # Plot spatial snapshots for each parameter
    for param in results["parameters"]:
        plot_spatial_snapshot(
            grid=grid,
            parameter=param,
            z_level=5,  # Middle of the room height
            time_point="End of Simulation",
            save_path=os.path.join(PLOT_DIR, f"spatial_{param}_{timestamp}.png")
        )
    
    print(f"Test completed. Results saved to {PLOT_DIR}")
    print(f"• Time series plot: environmental_effects_{timestamp}.png")
    for param in results["parameters"]:
        print(f"• Spatial plot for {param}: spatial_{param}_{timestamp}.png")


if __name__ == "__main__":
    main()
