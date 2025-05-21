"""
EnviroSense Chemical Sources Test Script

This script demonstrates the functionality of various chemical source types and
the chemical source manager. It creates different sources, runs a simulation over
time, and visualizes the emission patterns.

The demonstration includes:
1. Creating various chemical sources with different emission patterns
2. Simulating emissions over time with environmental variations
3. Visualizing the emission rates and cumulative amounts
"""

import os
import math
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

from envirosense.core.physics.coordinates import Vector3D
from envirosense.core.chemical.chemical_properties import (
    ChemicalCategory,
    CHEMICAL_PROPERTIES,
    get_chemical_property
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


def simulate_and_plot():
    """Run a simulation of different chemical sources and visualize the results."""
    # Create chemical sources
    sources = []
    
    # 1. Constant formaldehyde source (e.g., fresh furniture)
    sources.append(
        ConstantSource(
            source_id="furniture_formaldehyde",
            position=(2.5, 2.0, 1.0),  # Middle of room
            chemical_id="formaldehyde",
            initial_strength=0.05,  # g/s
            properties={
                "description": "New furniture emitting formaldehyde",
                "temperature_sensitive": True,
                "total_capacity": 50.0  # g (finite source)
            }
        )
    )
    
    # 2. Pulsed benzene source (e.g., intermittent vehicle exhaust)
    sources.append(
        PulsedSource(
            source_id="vehicle_benzene",
            position=(0.5, 0.0, 0.5),  # Near room entrance
            chemical_id="benzene",
            initial_strength=0.2,  # g/s when active
            pulse_period=300.0,    # 5 minutes cycle
            duty_cycle=0.2,        # Active 20% of the time
            properties={
                "description": "Vehicle exhaust entering through door",
                "temperature_sensitive": False,
            }
        )
    )
    
    # 3. Decaying ethanol source (e.g., hand sanitizer)
    sources.append(
        DecayingSource(
            source_id="sanitizer_ethanol",
            position=(1.0, 1.0, 1.0),  # On a desk
            chemical_id="ethanol",
            initial_strength=0.3,  # g/s
            half_life=600.0,       # 10 minutes half-life
            properties={
                "description": "Hand sanitizer with ethanol",
                "temperature_sensitive": True,
                "humidity_sensitive": True,
            }
        )
    )
    
    # 4. Diurnal nitrogen dioxide source (e.g., outdoor pollution)
    sources.append(
        DiurnalSource(
            source_id="outdoor_no2",
            position=(5.0, 2.0, 1.5),  # At window
            chemical_id="nitrogen_dioxide",
            initial_strength=0.02,  # g/s at peak
            peak_hour=16,           # 4 PM peak (rush hour)
            trough_hour=4,          # 4 AM trough
            min_factor=0.1,         # 10% of peak at trough
            properties={
                "description": "Outdoor NO2 pollution through window",
                "temperature_sensitive": True,
            }
        )
    )
    
    # 5. Event-triggered CO source (e.g., cooking event)
    sources.append(
        EventTriggeredSource(
            source_id="cooking_co",
            position=(4.0, 3.0, 1.2),  # Kitchen area
            chemical_id="carbon_monoxide",
            initial_strength=0.15,     # g/s
            emission_duration=1200.0,  # 20 minutes
            pattern="decay",           # Decaying pattern after trigger
            properties={
                "description": "Carbon monoxide from cooking",
                "decay_half_life": 300.0,  # 5 minutes half-life
                "temperature_sensitive": True,
            }
        )
    )
    
    # Create a source manager and add the sources
    manager = ChemicalSourceManager()
    for source in sources:
        manager.add_source(source)
    
    # Trigger the event-triggered source at a certain point
    trigger_time = 1800  # 30 minutes into simulation
    
    # Set up simulation parameters
    simulation_duration = 3600.0  # 1 hour in seconds
    time_step = 60.0  # 1 minute time step
    
    # Prepare storage for results
    times = np.arange(0, simulation_duration + time_step, time_step)
    emission_data = {source.source_id: np.zeros_like(times) for source in sources}
    cumulative_data = {source.source_id: np.zeros_like(times) for source in sources}
    
    # Temperature and humidity variations over time (simplified)
    def get_environment_at_time(t: float) -> Dict[str, float]:
        """Generate environment conditions at a given time."""
        # Temperature varies between 20-26°C in a sinusoidal pattern
        temperature = 23.0 + 3.0 * math.sin(2 * math.pi * t / (24 * 3600))
        
        # Humidity varies between 40-60% in a different pattern
        humidity = 50.0 + 10.0 * math.sin(2 * math.pi * t / (12 * 3600) + math.pi/4)
        
        return {
            "temperature": temperature,
            "relative_humidity": humidity
        }
    
    # Run simulation
    print(f"Starting simulation for {simulation_duration/3600:.1f} hours with {len(sources)} chemical sources")
    for i, t in enumerate(times):
        # Get current environment conditions
        env = get_environment_at_time(t)
        
        # Trigger the cooking event at the specified time
        if i > 0 and times[i-1] < trigger_time <= t:
            print(f"Triggering cooking event at t={t/60:.1f} minutes")
            manager.trigger_source("cooking_co", 1.0)
        
        # Apply emissions for each source individually for this demo
        for source in sources:
            emission_rate = source.emit(time_step, env)
            emission_data[source.source_id][i] = emission_rate
            
            if i > 0:
                # Calculate cumulative amount
                cumulative_data[source.source_id][i] = (
                    cumulative_data[source.source_id][i-1] + emission_rate * time_step
                )
        
        # Print status at regular intervals
        if i % 10 == 0:
            print(f"  Simulation time: {t/60:.1f} minutes, Temperature: {env['temperature']:.1f}°C, "
                  f"Humidity: {env['relative_humidity']:.1f}%")
    
    print("Simulation complete")
    
    # Create visualizations
    output_dir = create_output_directory()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Plot emission rates over time
    plt.figure(figsize=(12, 8))
    for source in sources:
        plt.plot(times/60, emission_data[source.source_id], label=f"{source.source_id} ({source.chemical_id})")
    
    plt.xlabel("Time (minutes)")
    plt.ylabel("Emission Rate (g/s)")
    plt.title("Chemical Source Emission Rates Over Time")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    
    # Save plot
    emission_plot_path = os.path.join(output_dir, f"chemical_emissions_{timestamp}.png")
    plt.savefig(emission_plot_path, dpi=300)
    print(f"Emission rate plot saved to {emission_plot_path}")
    
    # Plot cumulative emissions over time
    plt.figure(figsize=(12, 8))
    for source in sources:
        plt.plot(times/60, cumulative_data[source.source_id], label=f"{source.source_id} ({source.chemical_id})")
    
    plt.xlabel("Time (minutes)")
    plt.ylabel("Cumulative Emission (g)")
    plt.title("Cumulative Chemical Emissions Over Time")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    
    # Save plot
    cumulative_plot_path = os.path.join(output_dir, f"cumulative_emissions_{timestamp}.png")
    plt.savefig(cumulative_plot_path, dpi=300)
    print(f"Cumulative emissions plot saved to {cumulative_plot_path}")
    
    # Show specific source patterns with environmental factors
    plt.figure(figsize=(15, 10))
    
    # Plot sources
    plt.subplot(3, 1, 1)
    for source in sources:
        plt.plot(times/60, emission_data[source.source_id], label=f"{source.source_id} ({source.chemical_id})")
    plt.xlabel("Time (minutes)")
    plt.ylabel("Emission Rate (g/s)")
    plt.title("Chemical Source Emission Rates")
    plt.grid(True)
    plt.legend()
    
    # Plot temperature
    plt.subplot(3, 1, 2)
    temps = [get_environment_at_time(t)["temperature"] for t in times]
    plt.plot(times/60, temps, 'r-')
    plt.xlabel("Time (minutes)")
    plt.ylabel("Temperature (°C)")
    plt.title("Temperature Variation")
    plt.grid(True)
    
    # Plot humidity
    plt.subplot(3, 1, 3)
    humidities = [get_environment_at_time(t)["relative_humidity"] for t in times]
    plt.plot(times/60, humidities, 'b-')
    plt.xlabel("Time (minutes)")
    plt.ylabel("Relative Humidity (%)")
    plt.title("Humidity Variation")
    plt.grid(True)
    
    plt.tight_layout()
    
    # Save plot
    env_plot_path = os.path.join(output_dir, f"emissions_with_environment_{timestamp}.png")
    plt.savefig(env_plot_path, dpi=300)
    print(f"Environmental factors plot saved to {env_plot_path}")
    
    # Display statistics
    stats = manager.get_emission_statistics()
    print("\nEmission Statistics:")
    for chemical_id, chem_stats in stats.items():
        chem_name = CHEMICAL_PROPERTIES[chemical_id]["name"]
        print(f"  {chem_name} ({chemical_id}):")
        print(f"    Total sources: {chem_stats['total_sources']}")
        print(f"    Active sources: {chem_stats['active_sources']}")
        print(f"    Total emitted: {chem_stats['total_emitted']:.3f} g")
        print(f"    Current strength sum: {chem_stats['current_strength_sum']:.3f} g/s")
        print(f"    Average strength: {chem_stats['average_strength']:.3f} g/s")
    
    # Return for interactive use
    return {
        "sources": sources,
        "manager": manager, 
        "times": times,
        "emission_data": emission_data,
        "cumulative_data": cumulative_data
    }


if __name__ == "__main__":
    results = simulate_and_plot()
    plt.show()
    print("Demonstration completed successfully")
