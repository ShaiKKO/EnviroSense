"""
Exposure Tracking System Integrated Demo

This module demonstrates the integration of the exposure tracking system with 
sensitivity profiles to provide personalized exposure assessments.

It showcases:
1. Creating exposure records for different chemicals
2. Building exposure histories
3. Loading sensitivity profiles
4. Generating standard and personalized exposure assessments
5. Visualizing exposure data and assessment results
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Any

from envirosense.core.exposure.records import (
    ExposureRecord,
    ExposureHistory
)
from envirosense.core.exposure.assessment import (
    RiskLevel,
    ExposureAssessment,
    PersonalizedExposureAssessment
)
from envirosense.core.exposure.storage import (
    ExposureStorage
)
from envirosense.core.chemical.chemical_properties import (
    ChemicalCategory,
    CHEMICAL_PROPERTIES
)


def load_sensitivity_profile(profile_path: str) -> Dict[str, Any]:
    """
    Load a sensitivity profile from a JSON file.
    
    Args:
        profile_path: Path to the sensitivity profile JSON file
        
    Returns:
        Loaded sensitivity profile as a dictionary
    """
    with open(profile_path, 'r') as f:
        return json.load(f)


def generate_sample_exposure_data(
    chemical_id: str,
    duration_hours: float = 8.0,
    interval_minutes: float = 15.0,
    base_concentration: float = 0.1,
    variability: float = 0.3,
    trend: str = "steady",  # Options: "steady", "increasing", "decreasing", "peak", "valley"
    location_id: str = "living_room",
    coordinates: tuple = (3.0, 4.0, 1.2)  # (x, y, z) in meters
) -> List[ExposureRecord]:
    """
    Generate a series of sample exposure records for demonstration.
    
    Args:
        chemical_id: The chemical to generate exposure data for
        duration_hours: The total duration in hours
        interval_minutes: The interval between readings in minutes
        base_concentration: The baseline concentration level
        variability: The amount of random variability to add
        trend: The trend pattern for the concentration over time
        location_id: The location identifier
        coordinates: The spatial coordinates as (x, y, z)
        
    Returns:
        List of generated ExposureRecord objects
    """
    # Calculate number of readings
    num_readings = int((duration_hours * 60) / interval_minutes) + 1
    
    # Create time points
    start_time = datetime.now() - timedelta(hours=duration_hours)
    times = [start_time + timedelta(minutes=i * interval_minutes) for i in range(num_readings)]
    
    # Create concentration values based on trend
    concentrations = []
    
    if trend == "steady":
        # Relatively steady concentration with noise
        for i in range(num_readings):
            noise = np.random.normal(0, base_concentration * variability)
            concentrations.append(max(0, base_concentration + noise))
    
    elif trend == "increasing":
        # Gradually increasing concentration
        for i in range(num_readings):
            progress = i / (num_readings - 1)  # 0 to 1
            value = base_concentration * (1 + progress)
            noise = np.random.normal(0, base_concentration * variability)
            concentrations.append(max(0, value + noise))
            
    elif trend == "decreasing":
        # Gradually decreasing concentration
        for i in range(num_readings):
            progress = i / (num_readings - 1)  # 0 to 1
            value = base_concentration * (2 - progress)
            noise = np.random.normal(0, base_concentration * variability)
            concentrations.append(max(0, value + noise))
            
    elif trend == "peak":
        # Concentration rises then falls
        for i in range(num_readings):
            progress = i / (num_readings - 1)  # 0 to 1
            # Create a peak in the middle
            if progress < 0.5:
                value = base_concentration * (1 + 2 * progress)
            else:
                value = base_concentration * (3 - 2 * progress)
            noise = np.random.normal(0, base_concentration * variability)
            concentrations.append(max(0, value + noise))
            
    elif trend == "valley":
        # Concentration falls then rises
        for i in range(num_readings):
            progress = i / (num_readings - 1)  # 0 to 1
            # Create a valley in the middle
            if progress < 0.5:
                value = base_concentration * (2 - 2 * progress)
            else:
                value = base_concentration * (2 * progress)
            noise = np.random.normal(0, base_concentration * variability)
            concentrations.append(max(0, value + noise))
    
    else:
        # Default to steady with noise
        for i in range(num_readings):
            noise = np.random.normal(0, base_concentration * variability)
            concentrations.append(max(0, base_concentration + noise))
    
    # Create exposure records
    records = []
    for i in range(num_readings):
        record = ExposureRecord(
            timestamp=times[i].isoformat(),
            chemical_id=chemical_id,
            concentration=concentrations[i],
            duration=interval_minutes * 60,  # Convert minutes to seconds
            location_id=location_id,
            coordinates=coordinates,
            source_id="simulation",
            sensor_id="virtual_sensor_01",
            context={
                "simulation": True,
                "scenario": "demo"
            }
        )
        records.append(record)
    
    return records


def create_sample_exposure_history() -> ExposureHistory:
    """
    Create a sample exposure history with multiple chemicals.
    
    Returns:
        ExposureHistory containing sample exposure records
    """
    history = ExposureHistory()
    
    # Add formaldehyde exposure - increasing trend
    formaldehyde_records = generate_sample_exposure_data(
        chemical_id="formaldehyde",
        base_concentration=0.05,  # ppm
        trend="increasing",
        location_id="kitchen"
    )
    history.add_records(formaldehyde_records)
    
    # Add carbon monoxide exposure - peak pattern
    carbon_monoxide_records = generate_sample_exposure_data(
        chemical_id="co",
        base_concentration=5.0,  # ppm
        trend="peak",
        location_id="garage",
        coordinates=(8.0, 2.0, 1.0)
    )
    history.add_records(carbon_monoxide_records)
    
    # Add nitrogen dioxide exposure - steady
    nitrogen_dioxide_records = generate_sample_exposure_data(
        chemical_id="no2",
        base_concentration=0.03,  # ppm
        trend="steady",
        location_id="living_room",
        variability=0.2
    )
    history.add_records(nitrogen_dioxide_records)
    
    # Add benzene exposure - decreasing
    benzene_records = generate_sample_exposure_data(
        chemical_id="benzene",
        base_concentration=0.5,  # ppm - higher than typical to demonstrate threshold effects
        trend="decreasing",
        location_id="garage",
        coordinates=(7.5, 2.5, 1.2)
    )
    history.add_records(benzene_records)
    
    return history


def compare_standard_vs_personalized_assessment(
    history: ExposureHistory,
    profile_path: str,
    chemical_id: str
) -> Dict[str, Any]:
    """
    Compare standard and personalized assessments for a specific chemical.
    
    Args:
        history: The exposure history to assess
        profile_path: Path to the sensitivity profile
        chemical_id: The chemical to assess
        
    Returns:
        Dictionary with both assessment results for comparison
    """
    # Load the profile
    sensitivity_profile = load_sensitivity_profile(profile_path)
    
    # Create standard assessment
    standard_assessment = ExposureAssessment(history)
    standard_result = standard_assessment.assess_chemical(chemical_id)
    
    # Create personalized assessment
    personalized_assessment = PersonalizedExposureAssessment(history, sensitivity_profile)
    personalized_result = personalized_assessment.assess_chemical(chemical_id)
    
    # Return comparison results
    return {
        "chemical_id": chemical_id,
        "chemical_name": CHEMICAL_PROPERTIES.get(chemical_id, {}).get("name", chemical_id),
        "standard_assessment": standard_result,
        "personalized_assessment": personalized_result
    }


def visualize_assessment_comparison(comparison: Dict[str, Any]) -> plt.Figure:
    """
    Visualize the comparison between standard and personalized assessments.
    
    Args:
        comparison: The comparison result from compare_standard_vs_personalized_assessment
        
    Returns:
        Matplotlib figure with the visualization
    """
    chemical_name = comparison["chemical_name"]
    
    standard = comparison["standard_assessment"]
    personalized = comparison["personalized_assessment"]
    
    # Create figure with subplots
    fig, axs = plt.subplots(2, 1, figsize=(10, 12))
    
    # Plot 1: Risk level comparison
    risk_levels = list(RiskLevel.__members__.keys())
    risk_level_values = {name: i for i, name in enumerate(risk_levels)}
    
    standard_risk = risk_level_values.get(standard["risk_level"], 0)
    personalized_risk = risk_level_values.get(personalized["risk_level"], 0)
    
    x = [0, 1]
    y = [standard_risk, personalized_risk]
    
    axs[0].bar(x, y, color=['blue', 'red'], width=0.4)
    axs[0].set_xticks(x)
    axs[0].set_xticklabels(['Standard Assessment', 'Personalized Assessment'])
    axs[0].set_yticks(range(len(risk_levels)))
    axs[0].set_yticklabels(risk_levels)
    axs[0].set_title(f'Risk Level Comparison for {chemical_name}')
    axs[0].grid(axis='y', alpha=0.3)
    
    # Add text annotations
    for i, v in enumerate(y):
        axs[0].text(i, v + 0.1, risk_levels[v], ha='center')
    
    # Plot 2: Compare standard vs. personalized metrics
    std_metrics = standard.get("metrics", {})
    pers_metrics = personalized.get("metrics", {})
    
    # Get the keys for the original metrics (not the adjusted ones)
    metric_keys = [k for k in std_metrics.keys() if not k.startswith("adjusted_")]
    
    x = np.arange(len(metric_keys))
    width = 0.35
    
    std_values = [std_metrics.get(k, 0) for k in metric_keys]
    pers_values = [pers_metrics.get(f"adjusted_{k}", 0) for k in metric_keys]
    
    # Create the grouped bar chart
    axs[1].bar(x - width/2, std_values, width, label='Standard')
    axs[1].bar(x + width/2, pers_values, width, label='Personalized (Adjusted)')
    
    # Add labels and legend
    axs[1].set_xticks(x)
    axs[1].set_xticklabels([k.replace('_', ' ').title() for k in metric_keys])
    axs[1].set_title(f'Exposure Metrics Comparison for {chemical_name}')
    axs[1].set_ylabel('Concentration (ppm)')
    axs[1].legend()
    axs[1].grid(axis='y', alpha=0.3)
    
    # Add sensitivity factor information
    sensitivity_factor = personalized.get("sensitivity_factor", 1.0)
    plt.figtext(0.5, 0.01, f'Sensitivity Factor: {sensitivity_factor:.2f}', 
               ha='center', fontsize=12, 
               bbox=dict(facecolor='yellow', alpha=0.2))
    
    plt.tight_layout(pad=3.0)
    return fig


def run_integrated_demo(profile_paths: List[str], output_dir: str = None):
    """
    Run a full integrated demo with multiple profiles.
    
    Args:
        profile_paths: List of paths to sensitivity profile JSON files
        output_dir: Optional directory for output files
    """
    if output_dir is None:
        output_dir = os.path.join("envirosense", "output", "exposure_demo")
        
    os.makedirs(output_dir, exist_ok=True)
    
    # Create storage instance
    storage = ExposureStorage(base_dir=output_dir)
    
    # Create sample exposure history
    print("Generating sample exposure data...")
    history = create_sample_exposure_history()
    
    # Save the history
    history_path = storage.save_history(history)
    print(f"Saved exposure history to: {history_path}")
    
    # Create visualization of raw exposure data
    viz_path = storage.save_history_visualization(history)
    print(f"Saved exposure visualization to: {viz_path}")
    
    # Process each profile
    for profile_path in profile_paths:
        try:
            profile = load_sensitivity_profile(profile_path)
            profile_id = profile.get("profile_id", "unknown")
            
            print(f"\nProcessing profile: {os.path.basename(profile_path)}")
            print(f"  Profile ID: {profile_id}")
            
            # Create personalized assessment for all chemicals
            personalized_assessment = PersonalizedExposureAssessment(history, profile)
            all_results = personalized_assessment.assess_all_chemicals()
            
            # Save assessment results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = os.path.join(output_dir, f"assessment_{profile_id}_{timestamp}.json")
            with open(results_file, 'w') as f:
                json.dump(all_results, f, indent=2)
            print(f"  Saved assessment results to: {results_file}")
            
            # Generate comparison for each chemical
            for chemical_id in all_results.keys():
                comparison = compare_standard_vs_personalized_assessment(
                    history, profile_path, chemical_id
                )
                
                # Visualize comparison
                fig = visualize_assessment_comparison(comparison)
                
                # Save visualization
                chemical_name = CHEMICAL_PROPERTIES.get(chemical_id, {}).get("name", chemical_id)
                viz_file = os.path.join(output_dir, 
                                      f"comparison_{profile_id}_{chemical_id}_{timestamp}.png")
                fig.savefig(viz_file, dpi=300, bbox_inches='tight')
                plt.close(fig)
                
                print(f"  Saved comparison for {chemical_name} to: {viz_file}")
            
        except Exception as e:
            print(f"Error processing profile {profile_path}: {e}")


if __name__ == "__main__":
    # Set the directory for sensitivity profiles
    profiles_dir = os.path.join("envirosense", "output", "sensitivity_profiles", "example_profiles")
    
    # Find all JSON profiles in the directory
    profile_paths = []
    for filename in os.listdir(profiles_dir):
        if filename.endswith(".json"):
            profile_paths.append(os.path.join(profiles_dir, filename))
    
    if not profile_paths:
        print("No sensitivity profiles found!")
        exit(1)
    
    # Run the demo
    print(f"Found {len(profile_paths)} sensitivity profiles")
    run_integrated_demo(profile_paths)
