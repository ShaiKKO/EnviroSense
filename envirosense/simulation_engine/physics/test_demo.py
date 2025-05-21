"""
EnviroSense Diffusion Test Data Demo

This script demonstrates how to use the test data setup and validation framework
for diffusion modeling.
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Add the parent directory to sys.path if needed
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from envirosense.core.physics.test_data_setup import TestDataManager
from envirosense.core.physics.validation import DiffusionValidator, validate_model, list_available_datasets


def demo_data_generation():
    """Generate synthetic test data for diffusion modeling."""
    print("\n=== Generating Synthetic Test Data ===")
    
    manager = TestDataManager()
    
    # Generate synthetic Gaussian plume data
    print("\nGenerating Gaussian plume test data...")
    success = manager.download_dataset("envirosense_synthetic_basic")
    print(f"Generation {'successful' if success else 'failed'}")
    
    # Generate synthetic indoor diffusion data
    print("\nGenerating indoor diffusion test data...")
    success = manager.download_dataset("envirosense_synthetic_multiroom")
    print(f"Generation {'successful' if success else 'failed'}")
    
    # Generate metadata
    manager.generate_metadata()
    
    print("\nTest data generation complete!")


def sample_gaussian_plume_model(x, y, z, params):
    """
    Sample Gaussian plume model implementation for demonstration.
    
    Args:
        x: Downwind distance (m)
        y: Crosswind distance (m)
        z: Vertical distance (m)
        params: Dictionary of model parameters
        
    Returns:
        float: Concentration at point (x, y, z)
    """
    # Extract parameters
    Q = params.get('source_strength', 1.0)  # emission rate (g/s)
    u = params.get('wind_speed', 1.0)       # wind speed (m/s)
    stability = params.get('stability_class', 'C')
    
    # Map stability class to dispersion parameters
    if stability == 'A':
        a_y, b_y, a_z, b_z = 0.22, 0.92, 0.20, 1.1
    elif stability == 'B':
        a_y, b_y, a_z, b_z = 0.16, 0.92, 0.12, 1.0
    elif stability == 'C':
        a_y, b_y, a_z, b_z = 0.11, 0.92, 0.08, 0.93
    elif stability == 'D':
        a_y, b_y, a_z, b_z = 0.08, 0.92, 0.06, 0.85
    elif stability == 'E':
        a_y, b_y, a_z, b_z = 0.06, 0.92, 0.03, 0.8
    else:  # F
        a_y, b_y, a_z, b_z = 0.04, 0.91, 0.016, 0.7
    
    # Calculate dispersion coefficients
    sigma_y = a_y * x ** b_y
    sigma_z = a_z * x ** b_z
    
    # Calculate effective stack height (simplified)
    H = 10.0  # m
    
    # Calculate concentration using Gaussian plume equation
    term1 = Q / (2 * np.pi * u * sigma_y * sigma_z)
    term2 = np.exp(-0.5 * (y / sigma_y) ** 2)
    term3 = np.exp(-0.5 * ((z - H) / sigma_z) ** 2) + np.exp(-0.5 * ((z + H) / sigma_z) ** 2)
    
    return term1 * term2 * term3


def sample_indoor_diffusion_model(time, room_config, params):
    """
    Sample indoor diffusion model implementation for demonstration.
    
    Args:
        time: Array of time values (hours)
        room_config: Room configuration data
        params: Additional model parameters
        
    Returns:
        Dict[str, np.ndarray]: Dictionary mapping room_id to concentration time series
    """
    # Extract configuration
    rooms = room_config.get('rooms', [])
    connections = room_config.get('connections', [])
    source_strength = room_config.get('source_strength', 1.0)  # g/h
    source_duration = room_config.get('source_duration', 1.0)  # hours
    
    # Initialize result dictionary
    result = {}
    
    # Time step
    if len(time) > 1:
        dt = time[1] - time[0]
    else:
        dt = 0.1
    
    # Calculate concentration for each room
    for room in rooms:
        room_id = room['id']
        volume = room.get('volume', 50.0)  # m³
        air_exchange = room.get('air_exchange_rate', 1.0)  # air changes per hour
        has_source = room.get('has_source', False)
        
        # Initialize concentration array
        concentration = np.zeros_like(time)
        
        # Source room calculation
        if has_source:
            for t in range(1, len(time)):
                source_term = source_strength if time[t] < source_duration else 0
                decay_term = air_exchange * concentration[t-1]
                
                concentration[t] = concentration[t-1] + (source_term - decay_term) * dt / volume
        
        # Non-source room calculation
        else:
            # Find incoming connections
            inflow_rooms = [c for c in connections if c.get('to', '') == room_id]
            
            for t in range(1, len(time)):
                inflow_term = 0
                
                # Calculate inflow from connected rooms
                for connection in inflow_rooms:
                    source_room = connection.get('from', '')
                    flow_rate = connection.get('flow_rate', 10.0)  # m³/h
                    
                    # Get source room concentration with time delay
                    delay_steps = max(1, int(volume / flow_rate / dt))
                    if t >= delay_steps and source_room in result:
                        source_conc = result[source_room][t-delay_steps]
                        inflow_term += source_conc * flow_rate / volume
                
                decay_term = air_exchange * concentration[t-1]
                concentration[t] = concentration[t-1] + (inflow_term - decay_term) * dt
        
        # Store result for this room
        result[room_id] = concentration
    
    return result


def demo_validation():
    """Demonstrate model validation against test data."""
    print("\n=== Demonstrating Model Validation ===")
    
    # List available datasets
    print("\nListing available datasets...")
    datasets = list_available_datasets()
    
    if not datasets:
        print("No datasets available. Please run demo_data_generation() first.")
        return
    
    print(f"Found {len(datasets)} datasets:")
    for dataset in datasets:
        dataset_type = "Generated" if dataset.get('generated', False) else "Downloaded"
        print(f"  - {dataset['id']}: {dataset['description']} [{dataset_type}]")
    
    # Validate Gaussian plume model
    print("\nValidating Gaussian plume model...")
    plume_results = validate_model(
        model_type='gaussian_plume',
        model_func=sample_gaussian_plume_model,
        dataset_id='envirosense_synthetic_basic'
    )
    
    if plume_results.get("validated", False):
        print("Gaussian plume validation completed successfully.")
        agg_metrics = plume_results.get("aggregated_metrics", {})
        if "rmse" in agg_metrics:
            print(f"  Average RMSE: {agg_metrics['rmse']['mean']:.6f}")
        if "r_squared" in agg_metrics:
            print(f"  Average R²: {agg_metrics['r_squared']['mean']:.6f}")
    else:
        print(f"Gaussian plume validation failed: {plume_results.get('error', 'Unknown error')}")
    
    # Validate indoor diffusion model
    print("\nValidating indoor diffusion model...")
    indoor_results = validate_model(
        model_type='indoor',
        model_func=sample_indoor_diffusion_model,
        dataset_id='envirosense_synthetic_multiroom'
    )
    
    if indoor_results.get("validated", False):
        print("Indoor diffusion validation completed successfully.")
        agg_metrics = indoor_results.get("aggregated_metrics", {})
        if "rmse" in agg_metrics:
            print(f"  Average RMSE: {agg_metrics['rmse']['mean']:.6f}")
        if "r_squared" in agg_metrics:
            print(f"  Average R²: {agg_metrics['r_squared']['mean']:.6f}")
    else:
        print(f"Indoor diffusion validation failed: {indoor_results.get('error', 'Unknown error')}")


def main():
    """Main function to run the demonstration."""
    print("EnviroSense Diffusion Test Data Framework Demo")
    print("=" * 45)
    
    # Generate test data
    demo_data_generation()
    
    # Validate models
    demo_validation()
    
    print("\nDemonstration completed successfully!")
    print("\nGenerated datasets are stored in: envirosense/test_data/diffusion")
    print("Validation results are stored in: envirosense/test_results/diffusion_validation")


if __name__ == "__main__":
    main()
