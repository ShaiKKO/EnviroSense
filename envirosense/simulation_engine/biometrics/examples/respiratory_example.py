"""
Respiratory Model Example

This script demonstrates the use of the RespiratoryModel to simulate respiratory
responses to environmental factors, exercise, stress, and chemical exposures.
"""

import numpy as np
import matplotlib.pyplot as plt
import os
import time

from envirosense.core.biometrics.respiratory import RespiratoryModel


def simulate_normal_breathing(model, duration=60, time_step=0.5):
    """Simulate normal breathing pattern.
    
    Args:
        model: The respiratory model instance
        duration: Duration of the simulation in seconds
        time_step: Time step between measurements in seconds
        
    Returns:
        Tuple of (time_points, respiratory_values)
    """
    print(f"Simulating normal breathing for {duration} seconds...")
    model.reset()
    
    time_points = np.arange(0, duration, time_step)
    respiratory_values = []
    
    for t in time_points:
        # No exposures or special conditions
        resp = model.generate_signal(t)
        respiratory_values.append(resp)
    
    return time_points, respiratory_values


def simulate_exercise(model, duration=60, time_step=0.5, exercise_pattern="steady"):
    """Simulate breathing during exercise.
    
    Args:
        model: The respiratory model instance
        duration: Duration of the simulation in seconds
        time_step: Time step between measurements in seconds
        exercise_pattern: Type of exercise pattern ("steady", "increasing", or "interval")
        
    Returns:
        Tuple of (time_points, respiratory_values)
    """
    print(f"Simulating {exercise_pattern} exercise for {duration} seconds...")
    model.reset()
    
    time_points = np.arange(0, duration, time_step)
    respiratory_values = []
    
    for t in time_points:
        # Calculate exercise level based on pattern
        if exercise_pattern == "steady":
            exercise = 0.6  # Moderate steady exercise
        elif exercise_pattern == "increasing":
            exercise = min(0.85, t / duration)  # Gradually increase to high intensity
        elif exercise_pattern == "interval":
            # High-intensity interval training pattern
            cycle = int(t / 10) % 3
            if cycle == 0:  # High intensity
                exercise = 0.8
            elif cycle == 1:  # Medium intensity
                exercise = 0.4
            else:  # Recovery
                exercise = 0.2
        else:
            exercise = 0.0
        
        resp = model.generate_signal(t, exercise_level=exercise)
        respiratory_values.append(resp)
    
    return time_points, respiratory_values


def simulate_chemical_exposure(model, duration=60, time_step=0.5, chemical="carbon_monoxide", concentration=5.0):
    """Simulate breathing during chemical exposure.
    
    Args:
        model: The respiratory model instance
        duration: Duration of the simulation in seconds
        time_step: Time step between measurements in seconds
        chemical: Chemical agent to simulate exposure to
        concentration: Concentration of the chemical
        
    Returns:
        Tuple of (time_points, respiratory_values)
    """
    print(f"Simulating {chemical} exposure ({concentration} units) for {duration} seconds...")
    model.reset()
    
    time_points = np.arange(0, duration, time_step)
    respiratory_values = []
    
    for t in time_points:
        # Add chemical exposure
        exposures = {chemical: concentration}
        resp = model.generate_signal(t, exposures=exposures)
        respiratory_values.append(resp)
    
    return time_points, respiratory_values


def simulate_altitude(model, duration=60, time_step=0.5, altitude=3000):
    """Simulate breathing at high altitude.
    
    Args:
        model: The respiratory model instance
        duration: Duration of the simulation in seconds
        time_step: Time step between measurements in seconds
        altitude: Altitude in meters
        
    Returns:
        Tuple of (time_points, respiratory_values)
    """
    print(f"Simulating breathing at {altitude}m altitude for {duration} seconds...")
    model.reset()
    
    time_points = np.arange(0, duration, time_step)
    respiratory_values = []
    
    for t in time_points:
        # Set altitude in environmental conditions
        environmental_conditions = {"altitude": altitude}
        resp = model.generate_signal(t, environmental_conditions=environmental_conditions)
        respiratory_values.append(resp)
    
    return time_points, respiratory_values


def simulate_distress(model, duration=60, time_step=0.5, level=0.6):
    """Simulate breathing during respiratory distress.
    
    Args:
        model: The respiratory model instance
        duration: Duration of the simulation in seconds
        time_step: Time step between measurements in seconds
        level: Respiratory distress level (0.0 to 1.0)
        
    Returns:
        Tuple of (time_points, respiratory_values)
    """
    print(f"Simulating respiratory distress (level {level}) for {duration} seconds...")
    model.reset()
    
    time_points = np.arange(0, duration, time_step)
    respiratory_values = []
    
    for t in time_points:
        resp = model.generate_signal(t, distress_level=level)
        respiratory_values.append(resp)
    
    return time_points, respiratory_values


def simulate_breath_hold(model, duration=60, time_step=0.5, hold_start=10, hold_duration=15):
    """Simulate breathing with a breath hold.
    
    Args:
        model: The respiratory model instance
        duration: Duration of the simulation in seconds
        time_step: Time step between measurements in seconds
        hold_start: Time point to start holding breath (seconds)
        hold_duration: How long to hold breath (seconds)
        
    Returns:
        Tuple of (time_points, respiratory_values)
    """
    print(f"Simulating breath hold from {hold_start}s to {hold_start + hold_duration}s...")
    model.reset()
    
    time_points = np.arange(0, duration, time_step)
    respiratory_values = []
    
    for t in time_points:
        if abs(t - hold_start) < time_step/2:
            model.start_breath_hold(t, hold_duration)
        
        resp = model.generate_signal(t)
        respiratory_values.append(resp)
    
    return time_points, respiratory_values


def plot_comparison(results, labels, parameter="rate", title="Respiratory Response Comparison", output_path=None):
    """Plot a comparison of respiratory parameters.
    
    Args:
        results: List of (time_points, respiratory_values) tuples
        labels: List of labels for each result
        parameter: Which respiratory parameter to plot ('rate', 'volume', 'minute_volume')
        title: Plot title
        output_path: Optional path to save the plot image
        
    Returns:
        The matplotlib figure
    """
    fig, ax = plt.subplots(figsize=(12, 8))
    
    for i, (time_points, resp_values) in enumerate(results):
        # Extract the specified parameter from each respiratory value dictionary
        values = [rv[parameter] for rv in resp_values]
        ax.plot(time_points, values, label=labels[i])
    
    # Set labels based on parameter
    if parameter == "rate":
        ylabel = "Breathing Rate (breaths/min)"
    elif parameter == "volume":
        ylabel = "Tidal Volume (L)"
    elif parameter == "minute_volume":
        ylabel = "Minute Ventilation (L/min)"
    else:
        ylabel = parameter.capitalize()
    
    ax.set_title(title)
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path)
        print(f"Plot saved to {output_path}")
    
    return fig


def plot_breathing_waveforms(model, time_points, values, time_range=None, title="Breathing Waveform", output_path=None):
    """Plot respiratory waveforms showing the breathing cycle.
    
    Args:
        model: The respiratory model
        time_points: Array of time points
        values: List of respiratory value dictionaries
        time_range: Optional tuple of (start_time, end_time) to zoom in on a specific range
        title: Plot title
        output_path: Optional path to save the plot image
        
    Returns:
        The matplotlib figure
    """
    # Extract phases and rates from the respiratory values
    phases = [v["phase"] for v in values]
    rates = [v["rate"] for v in values]
    volumes = [v["volume"] for v in values]
    
    # Calculate instantaneous flow
    # Flow is proportional to sin(phase) * volume * rate
    # (positive during inspiration, negative during expiration)
    flows = [np.sin(phase) * volume * rate / 60.0 for phase, volume, rate in zip(phases, volumes, rates)]
    
    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # If time range specified, filter data to that range
    if time_range:
        start_idx = np.where(time_points >= time_range[0])[0][0]
        end_idx = np.where(time_points <= time_range[1])[0][-1]
        
        plot_times = time_points[start_idx:end_idx+1]
        plot_flows = flows[start_idx:end_idx+1]
        plot_volumes_cumulative = np.cumsum(plot_flows) * (time_points[1] - time_points[0])
        plot_volumes_cumulative -= np.min(plot_volumes_cumulative)  # Normalize
    else:
        plot_times = time_points
        plot_flows = flows
        plot_volumes_cumulative = np.cumsum(plot_flows) * (time_points[1] - time_points[0])
        plot_volumes_cumulative -= np.min(plot_volumes_cumulative)  # Normalize
    
    # Plot flow rate
    ax1.plot(plot_times, plot_flows, 'b-')
    ax1.set_title(f"Air Flow vs Time - {title}")
    ax1.set_xlabel("Time (seconds)")
    ax1.set_ylabel("Flow Rate (L/s)")
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color='k', linestyle='-', alpha=0.2)
    
    # Plot cumulative volume (simulating spirometer)
    ax2.plot(plot_times, plot_volumes_cumulative, 'g-')
    ax2.set_title(f"Breathing Volume vs Time - {title}")
    ax2.set_xlabel("Time (seconds)")
    ax2.set_ylabel("Volume (arbitrary units)")
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path)
        print(f"Plot saved to {output_path}")
    
    return fig


def analyze_respiratory_patterns(results, labels):
    """Analyze respiratory patterns in the results.
    
    Args:
        results: List of (time_points, respiratory_values) tuples
        labels: List of labels for each result
        
    Returns:
        Dictionary of respiratory statistics
    """
    statistics = {}
    
    for i, (time_points, resp_values) in enumerate(results):
        label = labels[i]
        
        # Extract values for each parameter
        rates = [rv["rate"] for rv in resp_values]
        volumes = [rv["volume"] for rv in resp_values]
        minute_volumes = [rv["minute_volume"] for rv in resp_values]
        distress_levels = [rv["distress"] for rv in resp_values]
        
        # Count pattern types
        patterns = [rv["pattern"] for rv in resp_values]
        pattern_counts = {}
        for pattern in patterns:
            if pattern not in pattern_counts:
                pattern_counts[pattern] = 0
            pattern_counts[pattern] += 1
        
        # Calculate dominant pattern
        dominant_pattern = max(pattern_counts.items(), key=lambda x: x[1])[0]
        
        # Store statistics
        statistics[label] = {
            "rate_mean": np.mean(rates),
            "rate_min": np.min(rates),
            "rate_max": np.max(rates),
            "rate_std": np.std(rates),
            "volume_mean": np.mean(volumes),
            "volume_min": np.min(volumes),
            "volume_max": np.max(volumes),
            "volume_std": np.std(volumes),
            "minute_volume_mean": np.mean(minute_volumes),
            "minute_volume_min": np.min(minute_volumes),
            "minute_volume_max": np.max(minute_volumes),
            "minute_volume_std": np.std(minute_volumes),
            "distress_mean": np.mean(distress_levels),
            "dominant_pattern": dominant_pattern,
            "pattern_counts": pattern_counts
        }
    
    return statistics


def print_statistics(stats):
    """Print statistics for each simulation.
    
    Args:
        stats: Dictionary of statistics
    """
    print("\nRespiratory Statistics:")
    print("-" * 120)
    print(f"{'Scenario':<20} {'Rate Mean':<10} {'Rate Min':<10} {'Rate Max':<10} {'Volume Mean':<12} {'Min Vol':<10} {'Minute Vol':<12} {'Pattern':<15} {'Distress':<10}")
    print("-" * 120)
    
    for label, stat in stats.items():
        print(f"{label:<20} {stat['rate_mean']:<10.2f} {stat['rate_min']:<10.2f} {stat['rate_max']:<10.2f} {stat['volume_mean']:<12.3f} {stat['volume_min']:<10.3f} {stat['minute_volume_mean']:<12.2f} {stat['dominant_pattern']:<15} {stat['distress_mean']:<10.3f}")


def main():
    """Main function to run the respiratory example."""
    # Create output directory for plots if it doesn't exist
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'output', 'biometrics')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a timestamp for unique filenames
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # Create a respiratory model with custom parameters
    model = RespiratoryModel(
        baseline_rate=14.0,            # Baseline of 14 breaths per minute
        baseline_volume=0.5,           # 0.5 L tidal volume
        rate_variability=0.5,          # Relatively low variability for visualization
        volume_variability=0.02,
        recovery_rate=0.08,            # Moderate recovery rate
        max_rate=35.0,                 # Maximum rate (breaths per minute)
        min_rate=6.0,                  # Minimum rate (breaths per minute)
        max_volume=1.2,                # Maximum tidal volume (liters)
        min_volume=0.2,                # Minimum tidal volume (liters)
        chemical_sensitivity=1.2       # Slight sensitivity increase
    )
    
    # Run different simulations
    duration = 120  # 2 minutes of data
    
    # Basic simulations
    normal_results = simulate_normal_breathing(model, duration=duration)
    moderate_exercise = simulate_exercise(model, duration=duration, exercise_pattern="steady")
    interval_exercise = simulate_exercise(model, duration=duration, exercise_pattern="interval")
    
    # Compare basic scenarios (rate)
    results_basic = [normal_results, moderate_exercise, interval_exercise]
    labels_basic = ["Normal Breathing", "Moderate Exercise", "Interval Training"]
    
    output_path = os.path.join(output_dir, f"respiratory_basic_rate_{timestamp}.png")
    plot_comparison(results_basic, labels_basic, parameter="rate", 
                   title="Breathing Rate Comparison - Basic Scenarios", 
                   output_path=output_path)
    
    # Compare basic scenarios (volume)
    output_path = os.path.join(output_dir, f"respiratory_basic_volume_{timestamp}.png")
    plot_comparison(results_basic, labels_basic, parameter="volume", 
                   title="Tidal Volume Comparison - Basic Scenarios", 
                   output_path=output_path)
    
    # Compare basic scenarios (minute volume)
    output_path = os.path.join(output_dir, f"respiratory_basic_minute_volume_{timestamp}.png")
    plot_comparison(results_basic, labels_basic, parameter="minute_volume", 
                   title="Minute Ventilation Comparison - Basic Scenarios", 
                   output_path=output_path)
    
    # Stress scenarios
    co_exposure = simulate_chemical_exposure(model, duration=duration, chemical="carbon_monoxide", concentration=7.0)
    formaldehyde = simulate_chemical_exposure(model, duration=duration, chemical="formaldehyde", concentration=2.0)
    smoke_exposure = simulate_chemical_exposure(model, duration=duration, chemical="smoke", concentration=3.0)
    high_altitude = simulate_altitude(model, duration=duration, altitude=3500)
    distress_moderate = simulate_distress(model, duration=duration, level=0.5)
    breath_hold = simulate_breath_hold(model, duration=duration, hold_start=30, hold_duration=20)
    
    # Compare chemical exposures
    results_exposures = [normal_results, co_exposure, formaldehyde, smoke_exposure]
    labels_exposures = ["Normal Breathing", "CO Exposure", "Formaldehyde Exposure", "Smoke Exposure"]
    
    output_path = os.path.join(output_dir, f"respiratory_exposures_rate_{timestamp}.png")
    plot_comparison(results_exposures, labels_exposures, parameter="rate", 
                   title="Breathing Rate Response to Chemical Exposures", 
                   output_path=output_path)
    
    # Compare special conditions
    results_special = [normal_results, high_altitude, distress_moderate, breath_hold]
    labels_special = ["Normal Breathing", "High Altitude", "Moderate Distress", "Breath Hold"]
    
    output_path = os.path.join(output_dir, f"respiratory_special_rate_{timestamp}.png")
    plot_comparison(results_special, labels_special, parameter="rate", 
                   title="Breathing Rate Response to Special Conditions", 
                   output_path=output_path)
    
    # Plot breathing waveforms for a few interesting cases
    # Normal breathing
    output_path = os.path.join(output_dir, f"respiratory_waveform_normal_{timestamp}.png")
    plot_breathing_waveforms(model, normal_results[0], normal_results[1], 
                           time_range=(30, 40),  # 10-second window
                           title="Normal Breathing", 
                           output_path=output_path)
    
    # Exercise breathing
    output_path = os.path.join(output_dir, f"respiratory_waveform_exercise_{timestamp}.png")
    plot_breathing_waveforms(model, moderate_exercise[0], moderate_exercise[1], 
                           time_range=(60, 70),  # 10-second window
                           title="During Exercise", 
                           output_path=output_path)
    
    # Breath hold
    output_path = os.path.join(output_dir, f"respiratory_waveform_breathhold_{timestamp}.png")
    plot_breathing_waveforms(model, breath_hold[0], breath_hold[1], 
                           time_range=(25, 55),  # 30-second window around breath hold
                           title="Breath Hold", 
                           output_path=output_path)
    
    # Calculate and print statistics
    all_results = [normal_results, moderate_exercise, interval_exercise, co_exposure, 
                  formaldehyde, smoke_exposure, high_altitude, distress_moderate, breath_hold]
    all_labels = ["Normal", "Moderate Exercise", "Interval Exercise", "CO Exposure", 
                 "Formaldehyde", "Smoke", "High Altitude", "Distress", "Breath Hold"]
    
    stats = analyze_respiratory_patterns(all_results, all_labels)
    print_statistics(stats)
    
    # Calculate respiratory efficiency for various conditions
    print("\nRespiratory Efficiency:")
    print("-" * 50)
    
    for label, (time_points, resp_values) in zip(all_labels, all_results):
        # Take the last values (steady state)
        model.reset()
        model.current_rate = resp_values[-1]["rate"]
        model.current_volume = resp_values[-1]["volume"]
        model.distress_level = resp_values[-1]["distress"]
        efficiency = model.calculate_respiratory_efficiency()
        capacity = model.calculate_lung_capacity_used()
        
        print(f"{label:<20} Efficiency: {efficiency:.2f}  Lung Capacity: {capacity:.2f}")
    
    print("\nRespiratory simulation complete!")


if __name__ == "__main__":
    main()
