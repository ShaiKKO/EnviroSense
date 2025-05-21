"""
Biometric Profile Example

This script demonstrates the use of the BiometricProfile class to simulate coordinated 
physiological responses to various stimuli including chemical exposures, environmental conditions,
exercise, and stress scenarios.
"""

import os
import time
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple, Any

from envirosense.core.biometrics.heart_rate import HeartRateModel
from envirosense.core.biometrics.skin_conductance import SkinConductanceModel
from envirosense.core.biometrics.respiratory import RespiratoryModel
from envirosense.core.biometrics.biometric_profile import BiometricProfile


def create_demographic_profiles() -> List[BiometricProfile]:
    """Create a set of demographic variants of biometric profiles.
    
    Returns:
        List of BiometricProfile instances for different demographics
    """
    # Create a base profile
    base_profile = BiometricProfile(
        name="Base Profile",
        description="Standard adult profile with average physiological parameters"
    )
    
    # Create demographic variants
    profiles = [
        base_profile,
        base_profile.create_demographic_variant(
            age=25, 
            fitness_level=0.8, 
            stress_sensitivity=0.8,
            name="Athletic Young Adult"
        ),
        base_profile.create_demographic_variant(
            age=65, 
            fitness_level=0.4, 
            stress_sensitivity=1.2,
            chemical_sensitivity=1.3,
            name="Older Adult"
        ),
        base_profile.create_demographic_variant(
            age=45, 
            fitness_level=0.2, 
            stress_sensitivity=1.1,
            name="Sedentary Middle Aged Adult"
        ),
        base_profile.create_demographic_variant(
            age=30, 
            fitness_level=0.6, 
            stress_sensitivity=1.4,
            chemical_sensitivity=1.5,
            name="Chemically Sensitive Adult"
        )
    ]
    
    return profiles


def simulate_scenario(
    profile: BiometricProfile,
    scenario_name: str,
    duration: float = 180.0,  # 3 minutes of data
    time_step: float = 1.0
) -> Tuple[np.ndarray, List[Dict[str, Dict]]]:
    """Simulate a standardized scenario for comparison between profiles.
    
    Args:
        profile: BiometricProfile to use for simulation
        scenario_name: Name of the scenario to simulate
        duration: Duration of simulation in seconds
        time_step: Time step between data points in seconds
        
    Returns:
        Tuple of (time_points, biometric_values)
    """
    profile.reset()
    
    time_points = np.arange(0, duration, time_step)
    biometric_values = []
    
    print(f"Simulating scenario: {scenario_name} for profile: {profile.name}")
    
    if scenario_name == "resting":
        # Resting baseline scenario
        for t in time_points:
            values = profile.generate_signals(t)
            biometric_values.append(values)
    
    elif scenario_name == "exercise":
        # Exercise scenario: gradual increase, plateau, recovery
        for t in time_points:
            if t < 60.0:  # First minute: increasing exercise
                exercise_level = min(0.8, t / 60.0)
            elif t < 120.0:  # Second minute: sustained exercise
                exercise_level = 0.8
            else:  # Third minute: recovery
                exercise_level = max(0.0, 0.8 - (t - 120.0) / 60.0)
                
            values = profile.generate_signals(t, exercise_level=exercise_level)
            biometric_values.append(values)
    
    elif scenario_name == "chemical_exposure":
        # Chemical exposure scenario (CO exposure)
        for t in time_points:
            if t < 30.0:  # First 30 seconds: no exposure
                exposures = {}
            elif t < 120.0:  # Next 90 seconds: increasing CO exposure
                concentration = min(10.0, (t - 30.0) / 9.0)
                exposures = {"carbon_monoxide": concentration}
            else:  # Last minute: decreasing exposure (ventilation)
                concentration = max(0.0, 10.0 - (t - 120.0) / 12.0)
                exposures = {"carbon_monoxide": concentration}
                
            values = profile.generate_signals(t, exposures=exposures)
            biometric_values.append(values)
    
    elif scenario_name == "stress_response":
        # Acute stress response scenario
        for t in time_points:
            if t < 30.0:  # First 30 seconds: baseline
                stress_level = 0.0
            elif t < 40.0:  # Quick stress onset (10 seconds)
                stress_level = min(0.9, (t - 30.0) / 10.0)
            elif t < 90.0:  # 50 seconds of high stress
                stress_level = 0.9
            else:  # Gradual recovery
                stress_level = max(0.0, 0.9 - (t - 90.0) / 90.0)
                
            values = profile.generate_signals(t, stress_level=stress_level)
            biometric_values.append(values)
    
    elif scenario_name == "environmental":
        # Environmental scenario (high temperature and humidity)
        for t in time_points:
            if t < 60.0:  # First minute: gradually increasing temperature
                temp = min(40.0, 25.0 + t / 4.0)
                humidity = min(85.0, 50.0 + t / 2.0)
            else:  # Next two minutes: sustained high temperature/humidity
                temp = 40.0
                humidity = 85.0
                
            environmental_conditions = {
                "temperature": temp,
                "humidity": humidity
            }
                
            values = profile.generate_signals(
                t, 
                environmental_conditions=environmental_conditions
            )
            biometric_values.append(values)
    
    elif scenario_name == "combined_stressors":
        # Multiple stressors combined
        for t in time_points:
            # Moderate exercise throughout
            exercise_level = 0.4
            
            # Increasing chemical exposure in middle section
            if t < 60.0:
                exposures = {}
            elif t < 120.0:
                concentration = min(5.0, (t - 60.0) / 12.0)
                exposures = {"formaldehyde": concentration}
            else:
                concentration = max(0.0, 5.0 - (t - 120.0) / 12.0)
                exposures = {"formaldehyde": concentration}
            
            # Environmental stress in later section
            if t < 90.0:
                environmental_conditions = {}
            else:
                temp = min(35.0, 25.0 + (t - 90.0) / 6.0)
                environmental_conditions = {"temperature": temp}
                
            # Psychological stress spike in the middle
            if 80.0 <= t < 100.0:
                stress_level = 0.6
            else:
                stress_level = 0.0
                
            values = profile.generate_signals(
                t, 
                exposures=exposures,
                environmental_conditions=environmental_conditions,
                exercise_level=exercise_level,
                stress_level=stress_level
            )
            biometric_values.append(values)
    
    else:
        raise ValueError(f"Unknown scenario: {scenario_name}")
    
    return time_points, biometric_values


def plot_profile_comparison(
    scenario_name: str,
    profiles: List[BiometricProfile],
    metric: str = "heart_rate",  # One of heart_rate, skin_conductance, respiratory_rate
    output_dir: str = None
) -> None:
    """Plot a comparison of different biometric profiles for the same scenario.
    
    Args:
        scenario_name: Name of the scenario to simulate
        profiles: List of BiometricProfile instances to compare
        metric: Which biometric metric to plot
        output_dir: Optional directory to save plots
    """
    fig, ax = plt.subplots(figsize=(12, 8))
    
    for profile in profiles:
        time_points, biometric_values = simulate_scenario(
            profile, scenario_name
        )
        
        # Extract the requested metric
        if metric == "heart_rate":
            values = [v["heart_rate"]["heart_rate"] for v in biometric_values]
            y_label = "Heart Rate (BPM)"
        elif metric == "skin_conductance":
            values = [v["skin_conductance"] for v in biometric_values]
            y_label = "Skin Conductance (µS)"
        elif metric == "respiratory_rate":
            values = [v["respiratory"]["rate"] for v in biometric_values]
            y_label = "Respiratory Rate (breaths/min)"
        else:
            raise ValueError(f"Unknown metric: {metric}")
        
        ax.plot(time_points, values, label=profile.name)
    
    ax.set_title(f"{scenario_name.capitalize()} Scenario - {metric.replace('_', ' ').title()}")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel(y_label)
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{scenario_name}_{metric}_comparison_{timestamp}.png"
        output_path = os.path.join(output_dir, filename)
        plt.savefig(output_path)
        print(f"Saved comparison plot to {output_path}")
    
    plt.close()


def plot_coordinated_response(
    profile: BiometricProfile,
    scenario_name: str,
    output_dir: str = None
) -> None:
    """Plot the coordinated biometric response for a specific profile and scenario.
    
    Args:
        profile: BiometricProfile to simulate
        scenario_name: Name of the scenario to simulate
        output_dir: Optional directory to save plots
    """
    time_points, biometric_values = simulate_scenario(
        profile, scenario_name
    )
    
    # Extract each biometric signal
    hr_values = [v["heart_rate"]["heart_rate"] for v in biometric_values]
    sc_values = [v["skin_conductance"] for v in biometric_values]
    resp_rate = [v["respiratory"]["rate"] for v in biometric_values]
    resp_volume = [v["respiratory"]["volume"] for v in biometric_values]
    
    # Create subplots showing all signals
    fig, axes = plt.subplots(4, 1, figsize=(12, 12), sharex=True)
    
    # Heart rate plot
    axes[0].plot(time_points, hr_values, 'r-')
    axes[0].set_title("Heart Rate")
    axes[0].set_ylabel("Heart Rate (BPM)")
    axes[0].grid(True, alpha=0.3)
    
    # Skin conductance plot
    axes[1].plot(time_points, sc_values, 'g-')
    axes[1].set_title("Skin Conductance")
    axes[1].set_ylabel("Skin Conductance (µS)")
    axes[1].grid(True, alpha=0.3)
    
    # Respiratory rate plot
    axes[2].plot(time_points, resp_rate, 'b-')
    axes[2].set_title("Respiratory Rate")
    axes[2].set_ylabel("Breaths per minute")
    axes[2].grid(True, alpha=0.3)
    
    # Respiratory volume plot
    axes[3].plot(time_points, resp_volume, 'c-')
    axes[3].set_title("Tidal Volume")
    axes[3].set_ylabel("Volume (L)")
    axes[3].set_xlabel("Time (seconds)")
    axes[3].grid(True, alpha=0.3)
    
    fig.suptitle(f"Coordinated Biometric Response - {scenario_name.capitalize()} Scenario\nProfile: {profile.name}")
    plt.tight_layout()
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{scenario_name}_coordinated_response_{profile.name.replace(' ', '_')}_{timestamp}.png"
        output_path = os.path.join(output_dir, filename)
        plt.savefig(output_path)
        print(f"Saved coordinated response plot to {output_path}")
    
    plt.close()


def plot_stress_index_comparison(
    scenario_name: str,
    profiles: List[BiometricProfile],
    output_dir: str = None
) -> None:
    """Plot a comparison of stress indices for different profiles under the same scenario.
    
    Args:
        scenario_name: Name of the scenario to simulate
        profiles: List of BiometricProfile instances to compare
        output_dir: Optional directory to save plots
    """
    fig, ax = plt.subplots(figsize=(12, 8))
    
    for profile in profiles:
        time_points, _ = simulate_scenario(
            profile, scenario_name
        )
        
        # Calculate stress index at each time point
        stress_indices = [profile.calculate_stress_index() for _ in time_points]
        
        ax.plot(time_points, stress_indices, label=profile.name)
    
    ax.set_title(f"Stress Index Comparison - {scenario_name.capitalize()} Scenario")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Stress Index (0-1)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{scenario_name}_stress_index_comparison_{timestamp}.png"
        output_path = os.path.join(output_dir, filename)
        plt.savefig(output_path)
        print(f"Saved stress index plot to {output_path}")
    
    plt.close()


def analyze_pattern_detection(
    scenario_name: str,
    profile: BiometricProfile
) -> None:
    """Analyze pattern detection for a specific scenario and profile.
    
    Args:
        scenario_name: Name of the scenario to simulate
        profile: BiometricProfile to analyze
    """
    time_points, _ = simulate_scenario(
        profile, scenario_name
    )
    
    # Get pattern detection results
    results = profile.detect_biometric_pattern()
    
    print(f"\nPattern Detection Results for {profile.name} - {scenario_name} scenario:")
    print("-" * 50)
    
    if results.get("insufficient_data", False):
        print("Insufficient data for pattern detection")
        return
    
    print(f"Primary Factor: {results['primary_factor']} (confidence: {results['confidence']:.2f})")
    print("Detected Patterns:")
    for pattern, detected in results.items():
        if pattern not in ["confidence", "primary_factor", "insufficient_data"] and detected:
            print(f"- {pattern.replace('_', ' ').title()}")


def main():
    """Main function to run the biometric profile demonstration."""
    # Create output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'output', 'biometrics')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create demographic profiles
    profiles = create_demographic_profiles()
    
    # Define scenarios to simulate
    scenarios = [
        "resting",
        "exercise",
        "chemical_exposure",
        "stress_response",
        "environmental",
        "combined_stressors"
    ]
    
    # Plot heart rate comparison for all scenarios
    for scenario in scenarios:
        plot_profile_comparison(scenario, profiles, "heart_rate", output_dir)
    
    # Plot skin conductance comparison for stress and chemical exposure
    for scenario in ["stress_response", "chemical_exposure"]:
        plot_profile_comparison(scenario, profiles, "skin_conductance", output_dir)
    
    # Plot respiratory rate comparison for exercise and environmental
    for scenario in ["exercise", "environmental"]:
        plot_profile_comparison(scenario, profiles, "respiratory_rate", output_dir)
    
    # Plot coordinated responses for selected profiles and scenarios
    interesting_pairs = [
        (profiles[0], "resting"),           # Base profile at rest
        (profiles[1], "exercise"),          # Athletic profile during exercise
        (profiles[2], "chemical_exposure"), # Older adult with chemical exposure
        (profiles[4], "chemical_exposure"), # Chemically sensitive with chemical exposure
        (profiles[3], "exercise"),          # Sedentary during exercise
        (profiles[0], "combined_stressors") # Base profile with combined stressors
    ]
    
    for profile, scenario in interesting_pairs:
        plot_coordinated_response(profile, scenario, output_dir)
    
    # Plot stress index comparison for all scenarios
    for scenario in scenarios:
        plot_stress_index_comparison(scenario, profiles, output_dir)
    
    # Analyze pattern detection
    for scenario in scenarios:
        for profile in profiles:
            analyze_pattern_detection(scenario, profile)
    
    print("\nBiometric profile demonstration complete!")
    print(f"Output saved to {output_dir}")


if __name__ == "__main__":
    main()
