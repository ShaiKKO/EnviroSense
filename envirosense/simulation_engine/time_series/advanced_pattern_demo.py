"""
EnviroSense Advanced Pattern Generation Demonstration

This module demonstrates the advanced pattern generation capabilities
including waveform types, correlation matrices, and stochastic elements.
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
    ParameterRelationship
)
from envirosense.core.time_series.patterns import (
    Pattern,
    PatternType,
    WaveformType,
    CompositePattern
)
from envirosense.core.time_series.correlation import (
    CorrelationMatrix,
    StochasticElementGenerator
)


def demonstrate_waveforms():
    """Demonstrate different waveform types for patterns."""
    # Create a timeframe for the demonstration
    hours = np.linspace(0, 48, 1000)  # 48 hours with 1000 points
    
    # Define the base settings for all waveforms
    base_value = 20.0
    amplitude = 5.0
    period = 24.0  # 24-hour cycle
    phase_shift = 14.0  # Peak at 2 PM
    
    # Create patterns with different waveform types
    waveforms = {
        "Sine": Pattern.create_diurnal(
            base_value=base_value,
            amplitude=amplitude,
            phase_shift=phase_shift,
            waveform=WaveformType.SINE
        ),
        "Cosine": Pattern.create_diurnal(
            base_value=base_value,
            amplitude=amplitude,
            phase_shift=phase_shift,
            waveform=WaveformType.COSINE
        ),
        "Square": Pattern.create_diurnal(
            base_value=base_value,
            amplitude=amplitude,
            phase_shift=phase_shift,
            waveform=WaveformType.SQUARE
        ),
        "Triangle": Pattern.create_diurnal(
            base_value=base_value,
            amplitude=amplitude,
            phase_shift=phase_shift,
            waveform=WaveformType.TRIANGLE
        ),
        "Sawtooth": Pattern.create_diurnal(
            base_value=base_value,
            amplitude=amplitude,
            phase_shift=phase_shift,
            waveform=WaveformType.SAWTOOTH
        ),
        "Reverse Sawtooth": Pattern.create_diurnal(
            base_value=base_value,
            amplitude=amplitude,
            phase_shift=phase_shift,
            waveform=WaveformType.REVERSE_SAWTOOTH
        )
    }
    
    # Direct creation of wave patterns
    custom_waves = {
        "Square Wave": Pattern.create_square_wave(
            base_value=base_value,
            amplitude=amplitude,
            period=period,
            duty_cycle=0.3  # 30% on, 70% off
        ),
        "Triangle Wave": Pattern.create_triangle_wave(
            base_value=base_value,
            amplitude=amplitude,
            period=period,
            duty_cycle=0.7  # 70% rise, 30% fall
        ),
        "Sawtooth Wave": Pattern.create_sawtooth_wave(
            base_value=base_value,
            amplitude=amplitude,
            period=period
        )
    }
    
    # Generate values for each pattern
    waveform_values = {name: [pattern.get_value(h) for h in hours] 
                      for name, pattern in {**waveforms, **custom_waves}.items()}
    
    # Create plots directory if it doesn't exist
    os.makedirs("plots", exist_ok=True)
    
    # Plot the waveforms
    plt.figure(figsize=(15, 10))
    
    # Plot standard waveform implementations
    plt.subplot(2, 1, 1)
    for name, values in {k: v for k, v in waveform_values.items() if k in waveforms}.items():
        plt.plot(hours, values, label=name)
    
    plt.xlabel("Hours")
    plt.ylabel("Value")
    plt.title("Standard Waveform Patterns (Using WaveformType)")
    plt.grid(True)
    plt.legend()
    
    # Plot custom wave pattern implementations
    plt.subplot(2, 1, 2)
    for name, values in {k: v for k, v in waveform_values.items() if k in custom_waves}.items():
        plt.plot(hours, values, label=name)
    
    plt.xlabel("Hours")
    plt.ylabel("Value")
    plt.title("Custom Wave Patterns (Using Pattern Factory Methods)")
    plt.grid(True)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig("plots/waveform_examples.png")
    plt.close()
    
    print("Waveform example completed. Plot saved to plots/waveform_examples.png")
    return waveform_values


def demonstrate_noise_and_interruptions():
    """Demonstrate noise addition and pattern interruptions."""
    # Create a timeframe for the demonstration
    hours = np.linspace(0, 96, 1000)  # 96 hours with 1000 points
    
    # Create base diurnal patterns with different noise levels
    base_value = 25.0
    amplitude = 8.0
    noise_patterns = {
        "No Noise": Pattern.create_diurnal(
            base_value=base_value,
            amplitude=amplitude,
            noise_level=0.0
        ),
        "Low Noise (5%)": Pattern.create_diurnal(
            base_value=base_value,
            amplitude=amplitude,
            noise_level=0.05
        ),
        "Medium Noise (15%)": Pattern.create_diurnal(
            base_value=base_value,
            amplitude=amplitude,
            noise_level=0.15
        ),
        "High Noise (30%)": Pattern.create_diurnal(
            base_value=base_value,
            amplitude=amplitude,
            noise_level=0.30
        )
    }
    
    # Create an interrupted pattern
    # Define the base pattern
    base_pattern = {
        "pattern_type": PatternType.DIURNAL,
        "base_value": base_value,
        "amplitude": amplitude,
        "period": 24.0,
        "phase_shift": 14.0
    }
    
    # Define interruptions
    interruptions = [
        # Flat line interruption
        {
            "start_time": 24.0,  # Start at hour 24
            "end_time": 36.0,    # End at hour 36
            "value": base_value  # Flat at the base value
        },
        # Different pattern interruption
        {
            "start_time": 60.0,  # Start at hour 60
            "end_time": 72.0,    # End at hour 72
            "pattern": {
                "pattern_type": PatternType.SQUARE_WAVE,
                "base_value": base_value,
                "amplitude": amplitude * 0.5,  # Half the amplitude
                "period": 4.0,                # 4-hour period
                "duty_cycle": 0.5
            }
        }
    ]
    
    # Create the interrupted pattern
    interrupted_pattern = Pattern.create_interrupted_pattern(
        base_pattern=base_pattern,
        interruptions=interruptions
    )
    
    # Generate values for each pattern
    noise_values = {name: [pattern.get_value(h) for h in hours] 
                   for name, pattern in noise_patterns.items()}
    
    interrupted_values = [interrupted_pattern.get_value(h) for h in hours]
    
    # Create plots directory if it doesn't exist
    os.makedirs("plots", exist_ok=True)
    
    # Plot the noise patterns
    plt.figure(figsize=(15, 10))
    
    plt.subplot(2, 1, 1)
    for name, values in noise_values.items():
        plt.plot(hours, values, label=name)
    
    plt.xlabel("Hours")
    plt.ylabel("Value")
    plt.title("Diurnal Patterns with Different Noise Levels")
    plt.grid(True)
    plt.legend()
    
    # Plot the interrupted pattern
    plt.subplot(2, 1, 2)
    plt.plot(hours, interrupted_values, label="Interrupted Pattern")
    
    # Highlight the interruption periods
    plt.axvspan(24.0, 36.0, alpha=0.2, color='red', label="Flat Interruption")
    plt.axvspan(60.0, 72.0, alpha=0.2, color='green', label="Square Wave Interruption")
    
    plt.xlabel("Hours")
    plt.ylabel("Value")
    plt.title("Pattern with Interruptions")
    plt.grid(True)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig("plots/noise_and_interruptions.png")
    plt.close()
    
    print("Noise and interruptions example completed. Plot saved to plots/noise_and_interruptions.png")
    return noise_values, interrupted_values


def demonstrate_stochastic_elements():
    """Demonstrate various stochastic elements."""
    # Create a timeframe for the demonstration
    hours = np.linspace(0, 24, 1000)  # 24 hours with 1000 points
    
    # Generate different types of noise
    stochastic_gen = StochasticElementGenerator()
    size = len(hours)
    
    # Generate noise elements
    noise_elements = {
        "White Noise": stochastic_gen.white_noise(size, scale=1.0),
        "Pink Noise": stochastic_gen.pink_noise(size, scale=1.0),
        "Brown Noise": stochastic_gen.brown_noise(size, scale=1.0),
        "Autocorrelated Noise (φ=0.9)": stochastic_gen.autocorrelated_noise(size, phi=0.9, scale=1.0),
        "Autocorrelated Noise (φ=0.7)": stochastic_gen.autocorrelated_noise(size, phi=0.7, scale=1.0),
        "Random Events": stochastic_gen.generate_random_events(
            size, 
            event_probability=0.03, 
            event_magnitude=(1.0, 3.0),
            event_duration=(5, 20)
        )
    }
    
    # Create a base pattern
    base_pattern = Pattern.create_diurnal(
        base_value=25.0,
        amplitude=5.0
    )
    
    # Generate the base pattern values
    base_values = [base_pattern.get_value(h) for h in hours]
    
    # Add anomalies to the base pattern
    base_with_anomalies = stochastic_gen.add_anomalies(
        np.array(base_values),
        anomaly_probability=0.01,
        anomaly_scale=(2.0, 4.0)
    )
    
    # Create plots directory if it doesn't exist
    os.makedirs("plots", exist_ok=True)
    
    # Plot the stochastic elements
    plt.figure(figsize=(15, 15))
    
    # Plot the noise types
    plt.subplot(3, 1, 1)
    for name, values in {k: v for k, v in noise_elements.items() if k not in ["Random Events"]}.items():
        plt.plot(hours, values, label=name)
    
    plt.xlabel("Hours")
    plt.ylabel("Value")
    plt.title("Different Types of Noise")
    plt.grid(True)
    plt.legend()
    
    # Plot the random events
    plt.subplot(3, 1, 2)
    plt.plot(hours, noise_elements["Random Events"], label="Random Events")
    
    plt.xlabel("Hours")
    plt.ylabel("Value")
    plt.title("Random Events")
    plt.grid(True)
    plt.legend()
    
    # Plot the pattern with anomalies
    plt.subplot(3, 1, 3)
    plt.plot(hours, base_values, label="Original Pattern")
    plt.plot(hours, base_with_anomalies, label="Pattern with Anomalies")
    
    plt.xlabel("Hours")
    plt.ylabel("Value")
    plt.title("Pattern with Anomalies")
    plt.grid(True)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig("plots/stochastic_elements.png")
    plt.close()
    
    print("Stochastic elements example completed. Plot saved to plots/stochastic_elements.png")
    return noise_elements, base_values, base_with_anomalies


def demonstrate_correlation_matrix():
    """Demonstrate correlation matrix functionality."""
    # Create a correlation matrix for environmental parameters
    corr_matrix = CorrelationMatrix()
    
    # Define correlations between parameters
    corr_matrix.add_correlation("temperature", "humidity", -0.7)  # Negative correlation
    corr_matrix.add_correlation("temperature", "pressure", -0.3)
    corr_matrix.add_correlation("temperature", "co2", 0.4)
    corr_matrix.add_correlation("humidity", "pressure", 0.2)
    corr_matrix.add_correlation("humidity", "co2", -0.1)
    corr_matrix.add_correlation("pressure", "co2", -0.2)
    
    # Generate relationships based on correlation matrix
    relationships = corr_matrix.generate_relationships(threshold=0.3)
    
    # Check for cycles in the relationships
    cycles = corr_matrix.detect_cycles(relationships)
    
    print("Correlation Matrix:")
    for param1 in corr_matrix.parameters:
        for param2 in corr_matrix.parameters:
            if param1 <= param2:  # Only show one side of the matrix
                print(f"{param1} - {param2}: {corr_matrix.get_correlation(param1, param2):.2f}")
    
    print("\nGenerated Relationships (threshold=0.3):")
    for source, target, params in relationships:
        print(f"{source} -> {target}: slope={params['slope']:.2f}")
    
    print("\nDetected Cycles:", cycles if cycles else "None")
    
    # Create a TimeSeriesGenerator with correlation-based relationships
    generator = TimeSeriesGenerator({"seed": 42})
    
    # Add parameters to the generator
    params = {
        "temperature": Parameter(
            name="temperature",
            parameter_type=ParameterType.CONTINUOUS,
            initial_value=25.0,
            units="°C",
            description="Ambient temperature",
            min_value=-10.0,
            max_value=45.0,
            distribution=Distribution.NORMAL,
            distribution_params={"mean": 0.0, "std_dev": 0.5}
        ),
        "humidity": Parameter(
            name="humidity",
            parameter_type=ParameterType.CONTINUOUS,
            initial_value=50.0,
            units="%",
            description="Relative humidity",
            min_value=0.0,
            max_value=100.0,
            distribution=Distribution.NORMAL,
            distribution_params={"mean": 0.0, "std_dev": 1.0}
        ),
        "pressure": Parameter(
            name="pressure",
            parameter_type=ParameterType.CONTINUOUS,
            initial_value=1013.0,
            units="hPa",
            description="Atmospheric pressure",
            min_value=950.0,
            max_value=1050.0,
            distribution=Distribution.NORMAL,
            distribution_params={"mean": 0.0, "std_dev": 1.0}
        ),
        "co2": Parameter(
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
    }
    
    # Add diurnal pattern to temperature
    temp_pattern = Pattern.create_diurnal(
        base_value=25.0,
        amplitude=8.0,
        phase_shift=14.0,
        waveform=WaveformType.COSINE,
        noise_level=0.05
    )
    params["temperature"].pattern = temp_pattern
    
    # Add pressure pattern (slight diurnal variation)
    pressure_pattern = Pattern.create_diurnal(
        base_value=1013.0,
        amplitude=2.0,
        phase_shift=10.0,  # Peak at 10 AM
        waveform=WaveformType.COSINE,
        noise_level=0.02
    )
    params["pressure"].pattern = pressure_pattern
    
    # Add parameters to the generator
    for _, param in params.items():
        generator.add_parameter(param)
    
    # Add relationships from the correlation matrix
    # To avoid cycles, we'll keep track of which parameters have relationships
    processed_pairs = set()
    
    for source, target, rel_params in relationships:
        # Skip if we already have a relationship between these parameters (in reverse)
        pair = tuple(sorted([source, target]))
        if pair in processed_pairs:
            continue
        
        # Mark this parameter pair as processed
        processed_pairs.add(pair)
        
        # Calculate an appropriate offset to maintain the current values
        source_value = params[source].value
        target_value = params[target].value
        offset = target_value - rel_params["slope"] * source_value
        rel_params["offset"] = offset
        
        # For the demo, only add one direction of the relationship to avoid cycles
        try:
            relationship = ParameterRelationship(
                source_parameter=source,
                target_parameter=target,
                relationship_function=lambda x, p: p["slope"] * x + p["offset"],
                params=rel_params,
                description=f"Correlation-based relationship from {source} to {target}"
            )
            
            generator.add_relationship(relationship)
            print(f"Added relationship: {source} → {target}")
        except ValueError as e:
            print(f"Skipped relationship {source} → {target}: {str(e)}")
    
    # Generate a time series
    duration = 48.0  # hours
    time_delta = 0.5  # 30 minutes
    
    # Initialize result dictionary
    result = {param_name: [] for param_name in params.keys()}
    result["time"] = []
    
    # Generate the time series
    current_time = 0.0
    while current_time < duration:
        result["time"].append(current_time)
        
        # Get the current values
        current_values = generator.step(time_delta)
        
        # Record the values
        for name, value in current_values.items():
            result[name].append(value)
        
        current_time += time_delta
    
    # Create plots directory if it doesn't exist
    os.makedirs("plots", exist_ok=True)
    
    # Plot the correlated parameters
    plt.figure(figsize=(15, 10))
    
    plt.subplot(2, 2, 1)
    plt.plot(result["time"], result["temperature"], label="Temperature (°C)")
    plt.xlabel("Hours")
    plt.ylabel("Temperature (°C)")
    plt.title("Temperature")
    plt.grid(True)
    
    plt.subplot(2, 2, 2)
    plt.plot(result["time"], result["humidity"], label="Humidity (%)")
    plt.xlabel("Hours")
    plt.ylabel("Humidity (%)")
    plt.title("Humidity")
    plt.grid(True)
    
    plt.subplot(2, 2, 3)
    plt.plot(result["time"], result["pressure"], label="Pressure (hPa)")
    plt.xlabel("Hours")
    plt.ylabel("Pressure (hPa)")
    plt.title("Pressure")
    plt.grid(True)
    
    plt.subplot(2, 2, 4)
    plt.plot(result["time"], result["co2"], label="CO2 (ppm)")
    plt.xlabel("Hours")
    plt.ylabel("CO2 (ppm)")
    plt.title("Carbon Dioxide")
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig("plots/correlated_parameters.png")
    plt.close()
    
    print("Correlation matrix example completed. Plot saved to plots/correlated_parameters.png")
    return result


def run_advanced_demos():
    """Run all advanced pattern generation demonstrations."""
    print("\n=== Running Advanced Pattern Generation Demonstrations ===\n")
    
    print("\n--- Waveforms Demonstration ---")
    demonstrate_waveforms()
    
    print("\n--- Noise and Interruptions Demonstration ---")
    demonstrate_noise_and_interruptions()
    
    print("\n--- Stochastic Elements Demonstration ---")
    demonstrate_stochastic_elements()
    
    print("\n--- Correlation Matrix Demonstration ---")
    demonstrate_correlation_matrix()
    
    print("\n=== All demonstrations completed ===")


if __name__ == "__main__":
    run_advanced_demos()
