"""
Heart Rate Model Example

This script demonstrates the use of the HeartRateModel to simulate heart rate responses
to environmental factors and chemical exposures.
"""

import numpy as np
import matplotlib.pyplot as plt
import os
import time

from envirosense.core.biometrics.heart_rate import HeartRateModel


def simulate_normal_conditions(model, duration=60, time_step=1.0):
    """Simulate heart rate under normal conditions.
    
    Args:
        model: The heart rate model instance
        duration: Duration of the simulation in seconds
        time_step: Time step between measurements in seconds
        
    Returns:
        Tuple of (time_points, heart_rates)
    """
    print(f"Simulating normal conditions for {duration} seconds...")
    model.reset()
    
    time_points = np.arange(0, duration, time_step)
    heart_rates = []
    
    for t in time_points:
        # No exposures or environmental stress
        hr = model.generate_signal(t)
        heart_rates.append(hr)
    
    return time_points, np.array(heart_rates)


def simulate_co_exposure(model, duration=60, time_step=1.0, co_concentration=5.0):
    """Simulate heart rate during carbon monoxide exposure.
    
    Args:
        model: The heart rate model instance
        duration: Duration of the simulation in seconds
        time_step: Time step between measurements in seconds
        co_concentration: Carbon monoxide concentration in ppm
        
    Returns:
        Tuple of (time_points, heart_rates)
    """
    print(f"Simulating CO exposure ({co_concentration} ppm) for {duration} seconds...")
    model.reset()
    
    time_points = np.arange(0, duration, time_step)
    heart_rates = []
    
    for t in time_points:
        # Add carbon monoxide exposure
        exposures = {"carbon_monoxide": co_concentration}
        hr = model.generate_signal(t, exposures=exposures)
        heart_rates.append(hr)
    
    return time_points, np.array(heart_rates)


def simulate_environmental_stress(model, duration=60, time_step=1.0, temp=32.0, humidity=80.0, noise=85.0):
    """Simulate heart rate during environmental stress.
    
    Args:
        model: The heart rate model instance
        duration: Duration of the simulation in seconds
        time_step: Time step between measurements in seconds
        temp: Temperature in Celsius
        humidity: Relative humidity in percentage
        noise: Noise level in decibels
        
    Returns:
        Tuple of (time_points, heart_rates)
    """
    print(f"Simulating environmental stress (Temp: {temp}°C, Humidity: {humidity}%, Noise: {noise} dB) for {duration} seconds...")
    model.reset()
    
    time_points = np.arange(0, duration, time_step)
    heart_rates = []
    
    for t in time_points:
        # Add environmental stress
        environmental_conditions = {
            "temperature": temp,
            "humidity": humidity,
            "noise": noise
        }
        hr = model.generate_signal(t, environmental_conditions=environmental_conditions)
        heart_rates.append(hr)
    
    return time_points, np.array(heart_rates)


def simulate_combined_stressors(model, duration=60, time_step=1.0):
    """Simulate heart rate with combined stressors that change over time.
    
    Args:
        model: The heart rate model instance
        duration: Duration of the simulation in seconds
        time_step: Time step between measurements in seconds
        
    Returns:
        Tuple of (time_points, heart_rates)
    """
    print(f"Simulating combined stressors for {duration} seconds...")
    model.reset()
    
    time_points = np.arange(0, duration, time_step)
    heart_rates = []
    
    for t in time_points:
        # Gradually increase temperature and add chemical exposure midway
        temp = 25.0 + (t / duration) * 10.0  # Temperature increases from 25°C to 35°C
        humidity = 60.0 + (t / duration) * 20.0  # Humidity increases from 60% to 80%
        
        environmental_conditions = {
            "temperature": temp,
            "humidity": humidity,
            "noise": 70.0  # Constant noise level
        }
        
        # Add chemical exposure midway through the simulation
        exposures = {}
        if t > duration / 2:
            co_level = 2.0 + (t - duration / 2) / (duration / 2) * 4.0  # CO increases from 2 to 6 ppm
            exposures["carbon_monoxide"] = co_level
        
        hr = model.generate_signal(t, exposures=exposures, environmental_conditions=environmental_conditions)
        heart_rates.append(hr)
    
    return time_points, np.array(heart_rates)


def plot_comparison(results, labels, title="Heart Rate Comparison", output_path=None):
    """Plot a comparison of heart rate results.
    
    Args:
        results: List of (time_points, heart_rates) tuples
        labels: List of labels for each result
        title: Plot title
        output_path: Optional path to save the plot image
        
    Returns:
        The matplotlib figure
    """
    fig, ax = plt.subplots(figsize=(12, 8))
    
    for i, (time_points, heart_rates) in enumerate(results):
        ax.plot(time_points, heart_rates, label=labels[i])
    
    ax.set_title(title)
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Heart Rate (BPM)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path)
        print(f"Plot saved to {output_path}")
    
    return fig


def calculate_statistics(results, labels):
    """Calculate statistics for each simulation.
    
    Args:
        results: List of (time_points, heart_rates) tuples
        labels: List of labels for each result
        
    Returns:
        Dictionary of statistics
    """
    stats = {}
    
    for i, (_, heart_rates) in enumerate(results):
        label = labels[i]
        stats[label] = {
            "mean": np.mean(heart_rates),
            "median": np.median(heart_rates),
            "min": np.min(heart_rates),
            "max": np.max(heart_rates),
            "std_dev": np.std(heart_rates),
            "variance": np.var(heart_rates)
        }
    
    return stats


def print_statistics(stats):
    """Print statistics for each simulation.
    
    Args:
        stats: Dictionary of statistics
    """
    print("\nHeart Rate Statistics:")
    print("-" * 80)
    print(f"{'Scenario':<25} {'Mean':<10} {'Median':<10} {'Min':<10} {'Max':<10} {'Std Dev':<10} {'Variance':<10}")
    print("-" * 80)
    
    for label, stat in stats.items():
        print(f"{label:<25} {stat['mean']:<10.2f} {stat['median']:<10.2f} {stat['min']:<10.2f} {stat['max']:<10.2f} {stat['std_dev']:<10.2f} {stat['variance']:<10.2f}")


def main():
    """Main function to run the heart rate model example."""
    # Create output directory for plots if it doesn't exist
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'output', 'biometrics')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a timestamp for unique filenames
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # Create a heart rate model with custom parameters
    model = HeartRateModel(
        baseline_heart_rate=65.0,  # Resting heart rate of 65 BPM
        variability=2.0,           # Lower variability for smoother curves
        recovery_rate=0.08,        # Slightly slower recovery rate
        max_heart_rate=180.0,      # Maximum possible heart rate
        stress_factor=1.5          # Higher stress factor for more pronounced effects
    )
    
    # Run different simulations
    duration = 120  # 2 minutes
    normal_results = simulate_normal_conditions(model, duration=duration)
    co_results = simulate_co_exposure(model, duration=duration, co_concentration=8.0)
    env_results = simulate_environmental_stress(model, duration=duration, temp=35.0, humidity=85.0, noise=90.0)
    combined_results = simulate_combined_stressors(model, duration=duration)
    
    # Compile results and labels
    results = [normal_results, co_results, env_results, combined_results]
    labels = [
        "Normal Conditions", 
        "CO Exposure (8 ppm)", 
        "Environmental Stress", 
        "Combined Stressors"
    ]
    
    # Plot comparison
    output_path = os.path.join(output_dir, f"heart_rate_comparison_{timestamp}.png")
    plot_comparison(results, labels, title="Heart Rate Response to Various Stressors", output_path=output_path)
    
    # Calculate and print statistics
    stats = calculate_statistics(results, labels)
    print_statistics(stats)
    
    print("\nHeart rate simulation complete!")


if __name__ == "__main__":
    main()
