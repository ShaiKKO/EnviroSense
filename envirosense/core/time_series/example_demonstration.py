"""
Example demonstration of the EnviroSense Time Series Generator system.
This script creates a simple environmental parameter set with relationships
and patterns, then generates and plots a 24-hour dataset.
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add the parent directory to sys.path to allow imports
script_dir = Path(__file__).resolve().parent
if str(script_dir.parent.parent) not in sys.path:
    sys.path.append(str(script_dir.parent.parent))

from envirosense.core.time_series.generator import TimeSeriesGenerator
from envirosense.core.time_series.parameters import (
    Parameter,
    ParameterType,
    Distribution,
    Pattern,
    PatternType,
    ParameterRelationship
)

def main():
    # Create a generator with a fixed seed for reproducibility
    generator = TimeSeriesGenerator({"seed": 42})
    
    # Create temperature parameter with a diurnal pattern
    generator.create_parameter(
        name="temperature",
        parameter_type=ParameterType.CONTINUOUS,
        initial_value=25.0,
        units="°C",
        description="Ambient temperature",
        min_value=10.0,
        max_value=40.0
    )
    
    # Add a diurnal pattern to temperature (day/night cycle)
    temp_param = generator.get_parameter("temperature")
    temp_param.pattern = Pattern(
        pattern_type=PatternType.DIURNAL,
        base_value=25.0,
        amplitude=5.0,  # +/- 5°C variation
        period=24.0,    # 24-hour cycle
        phase_shift=14.0  # Peak at 2 PM
    )
    
    # Create humidity parameter
    generator.create_parameter(
        name="humidity",
        parameter_type=ParameterType.CONTINUOUS,
        initial_value=50.0,
        units="%",
        description="Relative humidity",
        min_value=20.0,
        max_value=90.0
    )
    
    # Define a relationship: humidity is inversely related to temperature
    # When temperature goes up, humidity goes down
    def inverse_temp_humidity(temp, params):
        # Simple inverse relationship with scaling
        base = params.get('base', 100.0)
        factor = params.get('factor', 1.5)
        return base - factor * temp
    
    relationship = ParameterRelationship(
        source_parameter="temperature",
        target_parameter="humidity",
        relationship_function=inverse_temp_humidity,
        params={
            "base": 100.0,
            "factor": 1.5
        }
    )
    
    # Add the relationship
    generator.add_relationship(relationship)
    
    # Create VOC parameter with random variations
    generator.create_parameter(
        name="voc",
        parameter_type=ParameterType.CONTINUOUS,
        initial_value=200.0,
        units="ppb",
        description="Volatile Organic Compounds",
        min_value=50.0,
        max_value=1000.0,
        distribution=Distribution.NORMAL,
        distribution_params={"mean": 0.0, "std_dev": 20.0}
    )
    
    # Create air quality index (discrete parameter)
    generator.create_parameter(
        name="air_quality",
        parameter_type=ParameterType.DISCRETE,
        initial_value=2,
        units="AQI",
        description="Air Quality Index (1-5)",
        min_value=1,
        max_value=5
    )
    
    # Relate VOC to air quality
    def voc_to_aqi(voc, params):
        # Convert VOC level to air quality index
        thresholds = params.get('thresholds', [100, 200, 300, 500])
        
        if voc < thresholds[0]:
            return 1  # Excellent
        elif voc < thresholds[1]:
            return 2  # Good
        elif voc < thresholds[2]:
            return 3  # Moderate
        elif voc < thresholds[3]:
            return 4  # Poor
        else:
            return 5  # Hazardous
    
    relationship = ParameterRelationship(
        source_parameter="voc",
        target_parameter="air_quality",
        relationship_function=voc_to_aqi,
        params={
            "thresholds": [100, 200, 300, 500]
        }
    )
    
    # Add the relationship
    generator.add_relationship(relationship)
    
    # Generate 24 hours of data with 15-minute intervals
    hours = 24
    interval = 0.25  # 15 minutes
    series = generator.generate_series(
        duration=hours, 
        time_delta=interval,
        include_timestamps=True
    )
    
    # Create plots directory if it doesn't exist
    plots_dir = script_dir.parent / "plots"
    plots_dir.mkdir(exist_ok=True)
    
    # Plot the data
    # Continuous parameters
    plt.figure(figsize=(12, 8))
    
    # Create x-axis with hour labels
    x = range(len(series["timestamp"]))
    hour_labels = [f"{i%24:02d}:00" for i in range(0, hours+1, 2)]
    hour_positions = [i * int(1/interval) for i in range(0, hours+1, 2)]
    
    # Set up primary axis for temperature
    ax1 = plt.gca()
    ax1.plot(x, series["temperature"], 'r-', label="Temperature (°C)")
    ax1.set_xlabel("Time (hours)")
    ax1.set_ylabel("Temperature (°C)", color='r')
    ax1.tick_params(axis='y', labelcolor='r')
    ax1.set_xticks(hour_positions)
    ax1.set_xticklabels(hour_labels, rotation=45)
    
    # Set up secondary y-axis for humidity
    ax2 = ax1.twinx()
    ax2.plot(x, series["humidity"], 'b-', label="Humidity (%)")
    ax2.set_ylabel("Humidity (%)", color='b')
    ax2.tick_params(axis='y', labelcolor='b')
    
    # Add VOC as a third line with its own scale
    ax3 = ax1.twinx()
    ax3.spines["right"].set_position(("axes", 1.1))  # Offset the right spine
    ax3.plot(x, series["voc"], 'g-', label="VOC (ppb)")
    ax3.set_ylabel("VOC (ppb)", color='g')
    ax3.tick_params(axis='y', labelcolor='g')
    
    # Add legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    lines3, labels3 = ax3.get_legend_handles_labels()
    
    ax1.legend(lines1 + lines2 + lines3, labels1 + labels2 + labels3, loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=3)
    
    plt.title("EnviroSense Continuous Environmental Parameters (24 Hours)")
    plt.tight_layout()
    plt.savefig(str(plots_dir / "environmental_continuous.png"))
    
    # Plot the discrete parameter
    plt.figure(figsize=(12, 4))
    plt.step(x, series["air_quality"], 'k-', where='post', linewidth=2)
    plt.xlabel("Time (hours)")
    plt.ylabel("Air Quality Index (1-5)")
    plt.yticks([1, 2, 3, 4, 5], ["Excellent", "Good", "Moderate", "Poor", "Hazardous"])
    plt.ylim(0.5, 5.5)
    plt.title("EnviroSense Air Quality Index (24 Hours)")
    plt.grid(True, axis='y')
    plt.xticks(hour_positions, hour_labels, rotation=45)
    
    plt.tight_layout()
    plt.savefig(str(plots_dir / "environmental_discrete.png"))
    
    # Export to CSV
    csv_path = script_dir.parent / "data"
    csv_path.mkdir(exist_ok=True)
    generator.export_to_csv(str(csv_path / "environmental_data.csv"), series)
    
    print("Demonstration complete!")
    print(f"Plots saved to: {plots_dir}")
    print(f"Data saved to: {csv_path / 'environmental_data.csv'}")

if __name__ == "__main__":
    main()
