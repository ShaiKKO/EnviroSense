"""
Skin Conductance Model Example

This script demonstrates the use of the SkinConductanceModel to simulate skin conductance 
(electrodermal activity) responses to environmental factors, stress, and chemical exposures.
"""

import numpy as np
import matplotlib.pyplot as plt
import os
import time

from envirosense.core.biometrics.skin_conductance import SkinConductanceModel


def simulate_normal_conditions(model, duration=60, time_step=0.5):
    """Simulate skin conductance under normal conditions.
    
    Args:
        model: The skin conductance model instance
        duration: Duration of the simulation in seconds
        time_step: Time step between measurements in seconds
        
    Returns:
        Tuple of (time_points, conductance_values)
    """
    print(f"Simulating normal conditions for {duration} seconds...")
    model.reset()
    
    time_points = np.arange(0, duration, time_step)
    conductance_values = []
    
    for t in time_points:
        # No exposures, environmental stress, or psychological stress
        sc = model.generate_signal(t)
        conductance_values.append(sc)
    
    return time_points, np.array(conductance_values)


def simulate_stress_response(model, duration=60, time_step=0.5, stress_pattern="steady"):
    """Simulate skin conductance during stress.
    
    Args:
        model: The skin conductance model instance
        duration: Duration of the simulation in seconds
        time_step: Time step between measurements in seconds
        stress_pattern: Type of stress pattern ("steady", "increasing", or "pulsed")
        
    Returns:
        Tuple of (time_points, conductance_values)
    """
    print(f"Simulating {stress_pattern} stress for {duration} seconds...")
    model.reset()
    
    time_points = np.arange(0, duration, time_step)
    conductance_values = []
    
    for t in time_points:
        # Calculate stress level based on pattern
        if stress_pattern == "steady":
            stress = 0.7  # Constant moderate-high stress
        elif stress_pattern == "increasing":
            stress = min(0.9, t / duration)  # Gradually increase to high stress
        elif stress_pattern == "pulsed":
            # Alternating stress levels every 10 seconds
            stress = 0.8 if int(t / 10) % 2 == 0 else 0.2
        else:
            stress = 0.0
        
        sc = model.generate_signal(t, stress_level=stress)
        conductance_values.append(sc)
    
    return time_points, np.array(conductance_values)


def simulate_chemical_exposure(model, duration=60, time_step=0.5, chemical="carbon_monoxide", concentration=5.0):
    """Simulate skin conductance during chemical exposure.
    
    Args:
        model: The skin conductance model instance
        duration: Duration of the simulation in seconds
        time_step: Time step between measurements in seconds
        chemical: Chemical agent to simulate exposure to
        concentration: Concentration of the chemical
        
    Returns:
        Tuple of (time_points, conductance_values)
    """
    print(f"Simulating {chemical} exposure ({concentration} units) for {duration} seconds...")
    model.reset()
    
    time_points = np.arange(0, duration, time_step)
    conductance_values = []
    
    for t in time_points:
        # Add chemical exposure
        exposures = {chemical: concentration}
        sc = model.generate_signal(t, exposures=exposures)
        conductance_values.append(sc)
    
    return time_points, np.array(conductance_values)


def simulate_environmental_stress(model, duration=60, time_step=0.5, temp=35.0, humidity=85.0):
    """Simulate skin conductance during environmental stress.
    
    Args:
        model: The skin conductance model instance
        duration: Duration of the simulation in seconds
        time_step: Time step between measurements in seconds
        temp: Temperature in Celsius
        humidity: Relative humidity in percentage
        
    Returns:
        Tuple of (time_points, conductance_values)
    """
    print(f"Simulating environmental stress (Temp: {temp}°C, Humidity: {humidity}%) for {duration} seconds...")
    model.reset()
    
    time_points = np.arange(0, duration, time_step)
    conductance_values = []
    
    for t in time_points:
        # Add environmental stress
        environmental_conditions = {
            "temperature": temp,
            "humidity": humidity
        }
        sc = model.generate_signal(t, environmental_conditions=environmental_conditions)
        conductance_values.append(sc)
    
    return time_points, np.array(conductance_values)


def simulate_scr_events(model, duration=60, time_step=0.5, event_times=None):
    """Simulate skin conductance with specific SCR events at given times.
    
    Args:
        model: The skin conductance model instance
        duration: Duration of the simulation in seconds
        time_step: Time step between measurements in seconds
        event_times: List of time points (in seconds) when SCR events occur
        
    Returns:
        Tuple of (time_points, conductance_values)
    """
    event_times = event_times or [10, 25, 40]
    print(f"Simulating SCR events at times {event_times} for {duration} seconds...")
    model.reset()
    
    time_points = np.arange(0, duration, time_step)
    conductance_values = []
    
    for t in time_points:
        # Check if we're at an event time (with some tolerance)
        trigger_scr = any(abs(t - event_time) < time_step/2 for event_time in event_times)
        
        # Generate signal, triggering SCR if at an event time
        if trigger_scr:
            sc = model.generate_scr_response(t, intensity=1.5)
        else:
            sc = model.generate_signal(t)
            
        conductance_values.append(sc)
    
    return time_points, np.array(conductance_values)


def plot_comparison(results, labels, title="Skin Conductance Comparison", output_path=None):
    """Plot a comparison of skin conductance results.
    
    Args:
        results: List of (time_points, conductance_values) tuples
        labels: List of labels for each result
        title: Plot title
        output_path: Optional path to save the plot image
        
    Returns:
        The matplotlib figure
    """
    fig, ax = plt.subplots(figsize=(12, 8))
    
    for i, (time_points, conductance_values) in enumerate(results):
        ax.plot(time_points, conductance_values, label=labels[i])
    
    ax.set_title(title)
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Skin Conductance (µS)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path)
        print(f"Plot saved to {output_path}")
    
    return fig


def analyze_scr_responses(results, labels):
    """Analyze SCR responses in the results.
    
    Args:
        results: List of (time_points, conductance_values) tuples
        labels: List of labels for each result
        
    Returns:
        Dictionary of SCR statistics
    """
    statistics = {}
    
    for i, (time_points, conductance_values) in enumerate(results):
        label = labels[i]
        
        # Calculate first derivative to find SCRs
        dvalues = np.diff(conductance_values)
        dtimes = np.diff(time_points)
        derivatives = dvalues / dtimes
        
        # Identify SCRs (where derivative exceeds threshold)
        threshold = 0.1  # µS/second
        scr_indices = np.where(derivatives > threshold)[0]
        
        # Group adjacent indices to find unique SCRs
        if len(scr_indices) > 0:
            unique_scrs = [[scr_indices[0]]]
            for idx in scr_indices[1:]:
                if idx - unique_scrs[-1][-1] <= 2:  # If within 2 samples, part of same SCR
                    unique_scrs[-1].append(idx)
                else:
                    unique_scrs.append([idx])
            
            scr_count = len(unique_scrs)
            
            # Calculate SCR amplitudes
            scr_amplitudes = []
            for scr_group in unique_scrs:
                start_idx = max(0, min(scr_group) - 1)
                end_idx = min(len(conductance_values) - 1, max(scr_group) + 4)  # Look a bit after onset for peak
                amplitude = max(conductance_values[start_idx:end_idx+1]) - conductance_values[start_idx]
                scr_amplitudes.append(amplitude)
        else:
            scr_count = 0
            scr_amplitudes = []
        
        # Store statistics
        statistics[label] = {
            "scr_count": scr_count,
            "scr_frequency": scr_count / (time_points[-1] / 60),  # SCRs per minute
            "mean_amplitude": np.mean(scr_amplitudes) if scr_amplitudes else 0,
            "max_amplitude": max(scr_amplitudes) if scr_amplitudes else 0,
            "min": np.min(conductance_values),
            "max": np.max(conductance_values),
            "mean": np.mean(conductance_values),
            "std_dev": np.std(conductance_values)
        }
    
    return statistics


def print_statistics(stats):
    """Print statistics for each simulation.
    
    Args:
        stats: Dictionary of statistics
    """
    print("\nSkin Conductance Statistics:")
    print("-" * 100)
    print(f"{'Scenario':<20} {'Mean (µS)':<10} {'Min (µS)':<10} {'Max (µS)':<10} {'Std Dev':<10} {'SCRs':<10} {'SCR Freq':<10} {'Avg Amp':<10}")
    print("-" * 100)
    
    for label, stat in stats.items():
        print(f"{label:<20} {stat['mean']:<10.2f} {stat['min']:<10.2f} {stat['max']:<10.2f} {stat['std_dev']:<10.2f} {stat['scr_count']:<10d} {stat['scr_frequency']:<10.2f} {stat['mean_amplitude']:<10.2f}")


def main():
    """Main function to run the skin conductance example."""
    # Create output directory for plots if it doesn't exist
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'output', 'biometrics')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a timestamp for unique filenames
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # Create a skin conductance model with custom parameters
    model = SkinConductanceModel(
        baseline_conductance=2.5,    # Baseline of 2.5 µS
        variability=0.2,             # Relatively low variability for clearer visualization
        recovery_rate=0.05,          # Moderate recovery rate
        max_conductance=25.0,        # Maximum possible conductance
        stress_sensitivity=1.8       # Higher sensitivity to stress
    )
    
    # Run different simulations
    duration = 120  # 2 minutes of data
    
    # Compare different stress patterns
    normal_results = simulate_normal_conditions(model, duration=duration)
    steady_stress_results = simulate_stress_response(model, duration=duration, stress_pattern="steady")
    increasing_stress_results = simulate_stress_response(model, duration=duration, stress_pattern="increasing")
    pulsed_stress_results = simulate_stress_response(model, duration=duration, stress_pattern="pulsed")
    
    results_stress = [normal_results, steady_stress_results, increasing_stress_results, pulsed_stress_results]
    labels_stress = ["Normal Conditions", "Steady Stress", "Increasing Stress", "Pulsed Stress"]
    
    output_path = os.path.join(output_dir, f"skin_conductance_stress_comparison_{timestamp}.png")
    plot_comparison(results_stress, labels_stress, title="Skin Conductance Response to Different Stress Patterns", output_path=output_path)
    
    # Compare different environmental and chemical factors
    env_stress_results = simulate_environmental_stress(model, duration=duration, temp=36, humidity=90)
    co_exposure_results = simulate_chemical_exposure(model, duration=duration, chemical="carbon_monoxide", concentration=8.0)
    formaldehyde_results = simulate_chemical_exposure(model, duration=duration, chemical="formaldehyde", concentration=2.0)
    scr_events_results = simulate_scr_events(model, duration=duration, event_times=[20, 40, 60, 80, 100])
    
    results_factors = [normal_results, env_stress_results, co_exposure_results, formaldehyde_results, scr_events_results]
    labels_factors = ["Normal Conditions", "Environmental Stress", "CO Exposure", "Formaldehyde Exposure", "SCR Events"]
    
    output_path = os.path.join(output_dir, f"skin_conductance_factors_comparison_{timestamp}.png")
    plot_comparison(results_factors, labels_factors, title="Skin Conductance Response to Various Factors", output_path=output_path)
    
    # Analyze and print statistics
    stats = analyze_scr_responses(results_factors, labels_factors)
    print_statistics(stats)
    
    # Calculate SCR frequency for various conditions
    for label, (time_points, values) in zip(labels_factors, results_factors):
        model.reset()
        for t, v in zip(time_points, values):
            model.add_to_history(t, v)
        
        scr_freq = model.calculate_scr_frequency(window_size=60)
        print(f"SCR frequency for {label}: {scr_freq:.2f} responses/minute")
    
    print("\nSkin conductance simulation complete!")


if __name__ == "__main__":
    main()
