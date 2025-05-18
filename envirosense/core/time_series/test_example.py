"""
Quick test script for the TimeSeriesGenerator.

Run this script to verify the TimeSeriesGenerator implementation.
"""

import sys
import os
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from envirosense.core.time_series import (
    TimeSeriesGenerator,
    Parameter,
    ParameterType,
    Distribution,
    Pattern,
    PatternType,
    ParameterRelationship,
    linear_relationship
)


def create_simple_generator():
    """Create a simple generator with temperature and humidity parameters."""
    # Create a generator with a fixed seed
    generator = TimeSeriesGenerator({"seed": 42})
    
    # Add temperature parameter with normal distribution
    generator.create_parameter(
        name="temperature",
        parameter_type=ParameterType.CONTINUOUS,
        initial_value=25.0,
        units="°C",
        description="Ambient temperature",
        min_value=0.0,
        max_value=50.0,
        distribution=Distribution.NORMAL,
        distribution_params={"mean": 25.0, "std_dev": 5.0}
    )
    
    # Add humidity parameter
    generator.create_parameter(
        name="humidity",
        parameter_type=ParameterType.CONTINUOUS,
        initial_value=50.0,
        units="%",
        description="Relative humidity",
        min_value=0.0,
        max_value=100.0
    )
    
    # Create a relationship: humidity = -1.5 * temperature + 90
    # (Higher temperature -> lower humidity, simple inverse relationship)
    relationship = ParameterRelationship(
        source_parameter="temperature",
        target_parameter="humidity",
        relationship_function=linear_relationship,
        params={
            "slope": -1.5,
            "offset": 90.0
        }
    )
    
    # Add the relationship
    generator.add_relationship(relationship)
    
    return generator


def run_simple_test():
    """Run a simple test of the TimeSeriesGenerator."""
    print("Creating generator...")
    generator = create_simple_generator()
    
    print("Initial values:")
    print(f"  Temperature: {generator.get_parameter_value('temperature')} °C")
    print(f"  Humidity: {generator.get_parameter_value('humidity')} %")
    
    print("\nGenerating time series for 24 hours...")
    series = generator.generate_series(24.0, 1.0)
    
    print(f"Generated {len(series['temperature'])} data points")
    
    print("\nPlotting results...")
    plt.figure(figsize=(10, 6))
    
    # Create a time axis in hours
    hours = range(len(series["temperature"]))
    
    # Plot temperature
    plt.subplot(2, 1, 1)
    plt.plot(hours, series["temperature"], 'r-', label="Temperature (°C)")
    plt.xlabel("Hours")
    plt.ylabel("Temperature (°C)")
    plt.title("Temperature over Time")
    plt.grid(True)
    plt.legend()
    
    # Plot humidity
    plt.subplot(2, 1, 2)
    plt.plot(hours, series["humidity"], 'b-', label="Humidity (%)")
    plt.xlabel("Hours")
    plt.ylabel("Humidity (%)")
    plt.title("Humidity over Time")
    plt.grid(True)
    plt.legend()
    
    plt.tight_layout()
    
    # Create directory if it doesn't exist
    os.makedirs("test_results", exist_ok=True)
    
    # Save the plot
    plt.savefig("test_results/simple_test.png")
    print("Plot saved to test_results/simple_test.png")
    
    # Export the data
    generator.export_to_csv("test_results/simple_test.csv", series)
    print("Data exported to test_results/simple_test.csv")
    
    print("\nTest completed successfully!")


if __name__ == "__main__":
    run_simple_test()
