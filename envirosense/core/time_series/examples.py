"""
Usage examples for the TimeSeriesGenerator.

This module provides examples of how to use the TimeSeriesGenerator
to create and manage time series data for environmental parameters.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

from envirosense.core.time_series.generator import TimeSeriesGenerator
from envirosense.core.time_series.parameters import (
    Parameter,
    ParameterType,
    Distribution,
    Pattern,
    PatternType,
    ParameterRelationship,
    linear_relationship,
    exponential_relationship,
    logistic_relationship,
    threshold_relationship
)


def create_environmental_generator():
    """
    Create a generator with environmental parameters.
    
    This example creates a generator with temperature, humidity, CO2, and
    other environmental parameters with realistic relationships and patterns.
    
    Returns:
        TimeSeriesGenerator: A generator configured with environmental parameters
    """
    # Create the generator with a fixed seed for reproducibility
    generator = TimeSeriesGenerator({"seed": 42})
    
    # Add temperature parameter with a diurnal pattern
    temp = Parameter(
        name="temperature",
        parameter_type=ParameterType.CONTINUOUS,
        initial_value=25.0,
        units="°C",
        description="Ambient temperature",
        min_value=-10.0,
        max_value=45.0,
        distribution=Distribution.NORMAL,
        distribution_params={"mean": 0.0, "std_dev": 0.5}
    )
    
    # Create a diurnal pattern for temperature
    temp_pattern = Pattern(
        pattern_type=PatternType.DIURNAL,
        base_value=25.0,
        amplitude=8.0,      # 8°C variation
        period=24.0,        # 24-hour cycle
        phase_shift=14.0    # Peak at 2 PM
    )
    
    # Set the pattern on the parameter
    temp.pattern = temp_pattern
    
    # Add the parameter to the generator
    generator.add_parameter(temp)
    
    # Add humidity parameter
    humidity = Parameter(
        name="humidity",
        parameter_type=ParameterType.CONTINUOUS,
        initial_value=50.0,
        units="%",
        description="Relative humidity",
        min_value=0.0,
        max_value=100.0,
        distribution=Distribution.NORMAL,
        distribution_params={"mean": 0.0, "std_dev": 1.0}
    )
    
    # Add the parameter to the generator
    generator.add_parameter(humidity)
    
    # Add CO2 parameter
    co2 = Parameter(
        name="co2",
        parameter_type=ParameterType.CONTINUOUS,
        initial_value=400.0,
        units="ppm",
        description="Carbon dioxide concentration",
        min_value=300.0,
        max_value=2000.0,
        distribution=Distribution.NORMAL,
        distribution_params={"mean": 0.0, "std_dev": 5.0}
    )
    
    # Create a diurnal pattern for CO2 (higher during the day)
    co2_pattern = Pattern(
        pattern_type=PatternType.DIURNAL,
        base_value=400.0,
        amplitude=100.0,     # 100 ppm variation
        period=24.0,         # 24-hour cycle
        phase_shift=12.0     # Peak at noon
    )
    
    # Set the pattern on the parameter
    co2.pattern = co2_pattern
    
    # Add the parameter to the generator
    generator.add_parameter(co2)
    
    # Add particulate matter (PM2.5) parameter
    pm25 = Parameter(
        name="pm25",
        parameter_type=ParameterType.CONTINUOUS,
        initial_value=15.0,
        units="µg/m³",
        description="Particulate matter (2.5 µm)",
        min_value=0.0,
        max_value=100.0,
        distribution=Distribution.NORMAL,
        distribution_params={"mean": 0.0, "std_dev": 2.0}
    )
    
    # Add the parameter to the generator
    generator.add_parameter(pm25)
    
    # Add volatile organic compounds (VOC) parameter
    voc = Parameter(
        name="voc",
        parameter_type=ParameterType.CONTINUOUS,
        initial_value=200.0,
        units="ppb",
        description="Volatile organic compounds",
        min_value=0.0,
        max_value=1000.0,
        distribution=Distribution.NORMAL,
        distribution_params={"mean": 0.0, "std_dev": 10.0}
    )
    
    # Add the parameter to the generator
    generator.add_parameter(voc)
    
    # Add air quality index parameter
    aqi = Parameter(
        name="aqi",
        parameter_type=ParameterType.DISCRETE,
        initial_value=2,
        units="AQI level",
        description="Air Quality Index (1-5)",
        min_value=1,
        max_value=5,
        allowed_values=[1, 2, 3, 4, 5]
    )
    
    # Add the parameter to the generator
    generator.add_parameter(aqi)
    
    # Add alert parameter
    alert = Parameter(
        name="alert",
        parameter_type=ParameterType.BOOLEAN,
        initial_value=False,
        description="Environmental alert status"
    )
    
    # Add the parameter to the generator
    generator.add_parameter(alert)
    
    # Create relationships between parameters
    
    # 1. Temperature affects humidity (inverse relationship)
    # Higher temperature generally means lower humidity
    temp_humidity_rel = ParameterRelationship(
        source_parameter="temperature",
        target_parameter="humidity",
        relationship_function=linear_relationship,
        params={
            "slope": -1.5,     # Negative slope
            "offset": 80.0      # Baseline
        },
        description="Temperature affects humidity (inverse relationship)"
    )
    
    # Add the relationship
    generator.add_relationship(temp_humidity_rel)
    
    # 2. Temperature and humidity affect PM2.5
    # PM2.5 tends to be higher when it's hot and humid
    def temp_humidity_to_pm25(temp_value, params):
        humidity = params.get("humidity", 50.0)
        # Higher temperature and humidity tend to increase PM2.5
        multiplier = 1.0 + (temp_value - 20.0) / 50.0 + (humidity - 40.0) / 100.0
        return params.get("base_pm25", 15.0) * multiplier
    
    # This relationship will be updated dynamically in the step function
    
    # 3. CO2, PM2.5, and VOC affect AQI
    def calculate_aqi(co2_value, params):
        pm25 = params.get("pm25", 15.0)
        voc = params.get("voc", 200.0)
        
        # Calculate an AQI score based on these values
        score = 0
        
        # CO2 contribution (300-500: good, 500-1000: moderate, 1000+: poor)
        if co2_value < 500:
            score += 1
        elif co2_value < 1000:
            score += 2
        else:
            score += 3
        
        # PM2.5 contribution (0-12: good, 12-35: moderate, 35+: poor)
        if pm25 < 12:
            score += 1
        elif pm25 < 35:
            score += 2
        else:
            score += 3
        
        # VOC contribution (0-200: good, 200-500: moderate, 500+: poor)
        if voc < 200:
            score += 1
        elif voc < 500:
            score += 2
        else:
            score += 3
        
        # Convert score to AQI (1-5)
        # Score range: 3-9
        # Convert to AQI: score/9*5 rounded to nearest integer
        aqi = max(1, min(5, round(score / 9 * 5)))
        return aqi
    
    # This relationship will be updated dynamically in the step function
    
    # 4. AQI affects alert status
    aqi_alert_rel = ParameterRelationship(
        source_parameter="aqi",
        target_parameter="alert",
        relationship_function=threshold_relationship,
        params={
            "threshold": 4,       # AQI >= 4 triggers an alert
            "low_value": False,
            "high_value": True
        },
        description="High AQI triggers an alert"
    )
    
    # Add the relationship
    generator.add_relationship(aqi_alert_rel)
    
    # Define a custom step function to handle more complex relationships
    def custom_step(time_delta=1.0):
        # Original step function for base parameters
        values = generator.step(time_delta)
        
        # Update PM2.5 based on temperature and humidity
        temp_value = values["temperature"]
        humidity_value = values["humidity"]
        
        pm25_value = temp_humidity_to_pm25(
            temp_value, 
            {"humidity": humidity_value, "base_pm25": 15.0}
        )
        
        # Apply some random variation
        pm25_value += np.random.normal(0, 2.0)
        
        # Ensure within bounds
        pm25_value = max(0.0, min(100.0, pm25_value))
        
        # Update the value
        generator.set_parameter_value("pm25", pm25_value)
        
        # Update AQI based on CO2, PM2.5, and VOC
        co2_value = values["co2"]
        voc_value = values["voc"]
        
        aqi_value = calculate_aqi(
            co2_value, 
            {"pm25": pm25_value, "voc": voc_value}
        )
        
        # Update the value
        generator.set_parameter_value("aqi", aqi_value)
        
        # Return updated values
        return generator.get_current_values()
    
    # Attach the custom step function to the generator
    generator.custom_step = custom_step
    
    return generator


def run_environmental_example():
    """
    Run an example with the environmental generator.
    
    This generates time series data for environmental parameters,
    plots the results, and exports the data to files.
    """
    # Create the generator
    generator = create_environmental_generator()
    
    # Generate a time series for 48 hours
    duration = 48.0   # hours
    time_delta = 0.5  # 30 minutes
    
    # Initialize result dictionary
    result = {
        "timestamp": [],
        "temperature": [],
        "humidity": [],
        "co2": [],
        "pm25": [],
        "voc": [],
        "aqi": [],
        "alert": []
    }
    
    # Generate the time series
    start_time = generator.current_time
    
    while generator.current_time < start_time + duration:
        # Record the current time
        result["timestamp"].append(
            generator.start_time + timedelta(hours=generator.current_time)
        )
        
        # If we have a custom step function, use it
        if hasattr(generator, "custom_step"):
            current_values = generator.custom_step(time_delta)
        else:
            # Otherwise use the standard step function
            current_values = generator.step(time_delta)
        
        # Record the current values
        for name, value in current_values.items():
            if name in result:
                result[name].append(value)
    
    # Create plots directory if it doesn't exist
    os.makedirs("plots", exist_ok=True)
    
    # Plot the results (continuous parameters)
    plt.figure(figsize=(12, 8))
    
    # Convert timestamps to hours from start for x-axis
    hours = [(ts - result["timestamp"][0]).total_seconds() / 3600 for ts in result["timestamp"]]
    
    # Plot continuous parameters
    plt.subplot(2, 2, 1)
    plt.plot(hours, result["temperature"], label="Temperature (°C)")
    plt.xlabel("Hours")
    plt.ylabel("Temperature (°C)")
    plt.title("Temperature")
    plt.grid(True)
    
    plt.subplot(2, 2, 2)
    plt.plot(hours, result["humidity"], label="Humidity (%)")
    plt.xlabel("Hours")
    plt.ylabel("Humidity (%)")
    plt.title("Humidity")
    plt.grid(True)
    
    plt.subplot(2, 2, 3)
    plt.plot(hours, result["co2"], label="CO2 (ppm)")
    plt.xlabel("Hours")
    plt.ylabel("CO2 (ppm)")
    plt.title("Carbon Dioxide")
    plt.grid(True)
    
    plt.subplot(2, 2, 4)
    plt.plot(hours, result["pm25"], label="PM2.5 (µg/m³)")
    plt.xlabel("Hours")
    plt.ylabel("PM2.5 (µg/m³)")
    plt.title("Particulate Matter (2.5 µm)")
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig("plots/environmental_continuous.png")
    
    # Plot the discrete parameters
    plt.figure(figsize=(12, 6))
    
    plt.subplot(2, 1, 1)
    plt.plot(hours, result["aqi"], label="AQI Level")
    plt.xlabel("Hours")
    plt.ylabel("AQI Level")
    plt.title("Air Quality Index")
    plt.yticks([1, 2, 3, 4, 5])
    plt.grid(True)
    
    plt.subplot(2, 1, 2)
    plt.plot(hours, [int(a) for a in result["alert"]], label="Alert Status")
    plt.xlabel("Hours")
    plt.ylabel("Alert Status")
    plt.title("Environmental Alert")
    plt.yticks([0, 1], ["False", "True"])
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig("plots/environmental_discrete.png")
    
    # Export the data to CSV and JSON
    os.makedirs("data", exist_ok=True)
    
    # Convert timestamps to strings for JSON export
    json_result = {k: v if k != "timestamp" else [str(ts) for ts in v] for k, v in result.items()}
    
    # Export to CSV
    generator.export_to_csv("data/environmental_data.csv", result)
    
    # Export to JSON
    generator.export_to_json("data/environmental_data.json", json_result)
    
    print("Environmental example completed successfully.")
    print("Data exported to data/ directory.")
    print("Plots saved to plots/ directory.")
    
    return result


if __name__ == "__main__":
    run_environmental_example()
