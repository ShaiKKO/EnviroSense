"""
Integrated demonstration of the physiological response system.

This example demonstrates how to use the physiological response framework,
including:
1. Using individual response systems (respiratory, neurological)
2. Combining systems with interactions
3. Working with the threshold framework
4. Visualizing response data

Usage:
    python -m envirosense.core.exposure.physiological_response.examples.integrated_example
"""

import datetime
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Any

from envirosense.core.exposure.physiological_response import (
    ResponseSeverityLevel,
    SystemOutput,
    PhysiologicalSystemSet,
    PhysiologicalResponseSystem,
    RespiratoryResponseSystem,
    NeurologicalResponseSystem,
    ResponseThreshold,
    ThresholdSet,
    create_standard_threshold_set
)


def create_exposure_scenario() -> List[Dict[str, Any]]:
    """
    Create a simulated exposure scenario with multiple chemicals over time.
    
    This function simulates an industrial workplace with a chemical leak event.
    
    Returns:
        List of exposure records for different time points
    """
    # Time points (hours from start)
    time_points = np.linspace(0, 8, 25)  # 8-hour workday with 25 time points
    
    # Base concentrations (background levels)
    base_formaldehyde = 0.01  # ppm
    base_toluene = 1.0  # ppm
    base_co = 2.0  # ppm
    
    # Create exposure records
    records = []
    
    # Simulate a leak event at hour 3
    leak_time = 3.0
    leak_duration = 2.0  # hours
    
    for t in time_points:
        # Calculate concentrations based on time
        if t < leak_time:
            # Before leak: baseline conditions
            formaldehyde_conc = base_formaldehyde
            toluene_conc = base_toluene
            co_conc = base_co
        elif t < leak_time + leak_duration:
            # During leak: elevated levels with peak at center of event
            progress = (t - leak_time) / leak_duration
            intensity = 4.0 * progress * (1.0 - progress)  # Parabolic curve peaking at 0.5
            
            formaldehyde_conc = base_formaldehyde + 0.5 * intensity  # Peak at 0.51 ppm
            toluene_conc = base_toluene + 150.0 * intensity  # Peak at 151 ppm
            co_conc = base_co + 30.0 * intensity  # Peak at 32 ppm
        else:
            # After leak: exponential decay back to baseline
            elapsed = t - (leak_time + leak_duration)
            decay_factor = np.exp(-elapsed)
            
            formaldehyde_conc = base_formaldehyde + 0.5 * 0.2 * decay_factor
            toluene_conc = base_toluene + 150.0 * 0.2 * decay_factor
            co_conc = base_co + 30.0 * 0.2 * decay_factor
        
        # Calculate record for formaldehyde
        formaldehyde_record = {
            "time": t,
            "chemical_id": "formaldehyde",
            "concentration": formaldehyde_conc,
            "duration": 0.25 if t < 0.5 else 0.5,  # Incremental duration
            "cumulative_dose": formaldehyde_conc * t,  # Simplified cumulative dose
            "inhaled_volume": 0.5,  # L per timepoint (simplified)
            "peak_concentration": formaldehyde_conc if t < 0.5 else max(formaldehyde_conc, records[-1].get("peak_concentration", 0.0))
        }
        
        # Calculate record for toluene
        toluene_record = {
            "time": t,
            "chemical_id": "toluene",
            "concentration": toluene_conc,
            "duration": 0.25 if t < 0.5 else 0.5,  # Incremental duration
            "cumulative_dose": toluene_conc * t,  # Simplified cumulative dose
            "inhaled_volume": 0.5,  # L per timepoint (simplified)
            "peak_concentration": toluene_conc if t < 0.5 else max(toluene_conc, records[-1].get("peak_concentration", 0.0))
        }
        
        # Calculate record for carbon monoxide
        co_record = {
            "time": t,
            "chemical_id": "carbon_monoxide",
            "concentration": co_conc,
            "duration": 0.25 if t < 0.5 else 0.5,  # Incremental duration
            "cumulative_dose": co_conc * t,  # Simplified cumulative dose
            "inhaled_volume": 0.5,  # L per timepoint (simplified)
            "peak_concentration": co_conc if t < 0.5 else max(co_conc, records[-1].get("peak_concentration", 0.0))
        }
        
        records.append(formaldehyde_record)
        records.append(toluene_record)
        records.append(co_record)
    
    return records


def create_sensitivity_profiles() -> Dict[str, Dict[str, Any]]:
    """
    Create example sensitivity profiles for different individuals.
    
    Returns:
        Dictionary of sensitivity profiles
    """
    profiles = {
        "healthy_adult": {
            "age": 35,
            "respiratory_sensitivity": 1.0,
            "neurological_sensitivity": 1.0,
            "respiratory_conditions": [],
            "neurological_conditions": [],
            "blood_brain_barrier_factor": 1.0,
            "medications": []
        },
        
        "elderly_with_respiratory_condition": {
            "age": 72,
            "respiratory_sensitivity": 1.4,
            "neurological_sensitivity": 1.2,
            "respiratory_conditions": ["COPD", "asthma"],
            "neurological_conditions": [],
            "blood_brain_barrier_factor": 1.3,
            "medications": ["bronchodilator"]
        },
        
        "child_with_asthma": {
            "age": 9,
            "respiratory_sensitivity": 1.6,
            "neurological_sensitivity": 1.3,
            "respiratory_conditions": ["asthma"],
            "neurological_conditions": [],
            "blood_brain_barrier_factor": 1.2,
            "medications": ["inhaled_steroid"]
        },
        
        "adult_with_neurological_condition": {
            "age": 45,
            "respiratory_sensitivity": 1.1,
            "neurological_sensitivity": 1.5,
            "respiratory_conditions": [],
            "neurological_conditions": ["migraine", "peripheral neuropathy"],
            "blood_brain_barrier_factor": 1.4,
            "medications": ["antidepressant"]
        }
    }
    
    return profiles


def create_combined_response_system() -> PhysiologicalSystemSet:
    """
    Create a combined system with respiratory and neurological components.
    
    Returns:
        PhysiologicalSystemSet with interaction factors
    """
    # Create individual systems
    respiratory_system = RespiratoryResponseSystem(
        name="Respiratory System",
        description="Models respiratory effects of chemical exposures",
        uncertainty=0.2
    )
    
    neurological_system = NeurologicalResponseSystem(
        name="Neurological System",
        description="Models central and peripheral nervous system effects",
        uncertainty=0.25
    )
    
    # Create the combined system
    combined_system = PhysiologicalSystemSet(
        systems=[respiratory_system, neurological_system],
        metadata={"description": "Combined physiological response system"}
    )
    
    # Set up interaction factors
    # Respiratory stress affects neurological response
    combined_system.set_interaction(
        source_system="Respiratory System",
        target_system="Neurological System",
        factor=0.3  # 30% effect
    )
    
    # Neurological dysfunction can affect respiratory response
    combined_system.set_interaction(
        source_system="Neurological System",
        target_system="Respiratory System",
        factor=0.2  # 20% effect
    )
    
    return combined_system


def run_simulation_scenario() -> Dict[str, Any]:
    """
    Run a simulation using the physiological response systems.
    
    Returns:
        Dictionary with simulation results
    """
    # Create exposure data
    exposure_records = create_exposure_scenario()
    
    # Create sensitivity profiles
    sensitivity_profiles = create_sensitivity_profiles()
    
    # Create response system
    combined_system = create_combined_response_system()
    
    # Store results by profile and time
    results = {
        "time_points": [],
        "profiles": {}
    }
    
    # Initialize profile results
    for profile_name in sensitivity_profiles:
        results["profiles"][profile_name] = {
            "respiratory": [],
            "neurological": [],
            "overall_severity": [],
        }
    
    # Group exposure records by time
    time_grouped_records = {}
    for record in exposure_records:
        time = record["time"]
        if time not in time_grouped_records:
            time_grouped_records[time] = []
            results["time_points"].append(time)
        
        time_grouped_records[time].append(record)
    
    # Process each time point
    for time, records in sorted(time_grouped_records.items()):
        # For each profile, calculate responses at this time
        for profile_name, profile in sensitivity_profiles.items():
            # Process each chemical at this time point
            profile_respiratory_max = 0
            profile_neurological_max = 0
            
            # Store all responses for this time point
            time_responses = {}
            
            for record in records:
                # Calculate responses for this chemical
                responses = combined_system.calculate_responses(record, profile)
                
                # Store responses by system
                for system_name, response in responses.items():
                    if system_name not in time_responses:
                        time_responses[system_name] = []
                    
                    time_responses[system_name].append(response)
                    
                    # Track max response values
                    if system_name == "Respiratory System":
                        profile_respiratory_max = max(
                            profile_respiratory_max, response.response_value
                        )
                    elif system_name == "Neurological System":
                        profile_neurological_max = max(
                            profile_neurological_max, response.response_value
                        )
            
            # Store maximum responses for this time point
            results["profiles"][profile_name]["respiratory"].append(profile_respiratory_max)
            results["profiles"][profile_name]["neurological"].append(profile_neurological_max)
            
            # Calculate overall severity if we have responses
            if time_responses:
                overall_severity = combined_system.get_overall_severity(
                    {name: responses[0] for name, responses in time_responses.items()}
                )
                results["profiles"][profile_name]["overall_severity"].append(
                    overall_severity.value
                )
            else:
                results["profiles"][profile_name]["overall_severity"].append(0)
    
    return results


def visualize_results(results: Dict[str, Any]) -> None:
    """
    Visualize the simulation results.
    
    Args:
        results: Simulation results from run_simulation_scenario
    """
    # Set up the figure
    fig = plt.figure(figsize=(15, 10))
    
    # Define colors and line styles for profiles
    styles = {
        "healthy_adult": {"color": "green", "linestyle": "-", "label": "Healthy Adult"},
        "elderly_with_respiratory_condition": {"color": "red", "linestyle": "-", "label": "Elderly with COPD"},
        "child_with_asthma": {"color": "orange", "linestyle": "-", "label": "Child with Asthma"},
        "adult_with_neurological_condition": {"color": "blue", "linestyle": "-", "label": "Adult with Neurological Condition"}
    }
    
    # 1. Respiratory responses
    ax1 = fig.add_subplot(3, 1, 1)
    for profile_name, profile_data in results["profiles"].items():
        ax1.plot(
            results["time_points"], 
            profile_data["respiratory"],
            color=styles[profile_name]["color"],
            linestyle=styles[profile_name]["linestyle"],
            label=styles[profile_name]["label"]
        )
    
    ax1.set_title("Respiratory Response Over Time")
    ax1.set_xlabel("Time (hours)")
    ax1.set_ylabel("Response Value")
    ax1.grid(True)
    ax1.legend()
    
    # Add severity level indicators
    severity_levels = [
        (10, "Subclinical"),
        (25, "Mild"),
        (50, "Moderate"),
        (75, "Severe"),
        (90, "Critical")
    ]
    
    for level, name in severity_levels:
        ax1.axhline(y=level, color="gray", linestyle="--", alpha=0.5)
        ax1.text(8.1, level, name, va="center", ha="left", fontsize=8)
    
    # 2. Neurological responses
    ax2 = fig.add_subplot(3, 1, 2)
    for profile_name, profile_data in results["profiles"].items():
        ax2.plot(
            results["time_points"], 
            profile_data["neurological"],
            color=styles[profile_name]["color"],
            linestyle=styles[profile_name]["linestyle"],
            label=styles[profile_name]["label"]
        )
    
    ax2.set_title("Neurological Response Over Time")
    ax2.set_xlabel("Time (hours)")
    ax2.set_ylabel("Response Value")
    ax2.grid(True)
    ax2.legend()
    
    # Add severity level indicators - neurological has slightly different thresholds
    severity_levels = [
        (12, "Subclinical"),
        (30, "Mild"),
        (55, "Moderate"),
        (80, "Severe"),
        (95, "Critical")
    ]
    
    for level, name in severity_levels:
        ax2.axhline(y=level, color="gray", linestyle="--", alpha=0.5)
        ax2.text(8.1, level, name, va="center", ha="left", fontsize=8)
    
    # 3. Overall severity
    ax3 = fig.add_subplot(3, 1, 3)
    for profile_name, profile_data in results["profiles"].items():
        ax3.plot(
            results["time_points"], 
            profile_data["overall_severity"],
            color=styles[profile_name]["color"],
            linestyle=styles[profile_name]["linestyle"],
            label=styles[profile_name]["label"]
        )
    
    ax3.set_title("Overall Severity Over Time")
    ax3.set_xlabel("Time (hours)")
    ax3.set_ylabel("Severity Level")
    ax3.set_yticks([1, 2, 3, 4, 5, 6])
    ax3.set_yticklabels(["None", "Subclinical", "Mild", "Moderate", "Severe", "Critical"])
    ax3.grid(True)
    ax3.legend()
    
    # Adjust layout and save
    plt.tight_layout()
    plt.savefig("physiological_response_simulation.png")
    plt.close()


def demonstrate_threshold_framework() -> None:
    """
    Demonstrate the threshold framework functionality.
    """
    # Create a standard threshold set for VOC respiratory response
    voc_thresholds = create_standard_threshold_set(
        response_type="VOC_respiratory",
        subclinical_value=15.0,
        mild_value=35.0,
        moderate_value=60.0,
        severe_value=85.0,
        critical_value=95.0,
        uncertainty=0.25,
        name="VOC Respiratory Thresholds",
        description="Thresholds for respiratory responses to volatile organic compounds",
        source="EPA VOC Guidelines (2023)"
    )
    
    # Create some test response values
    test_values = [10.0, 25.0, 45.0, 72.0, 90.0, 98.0]
    
    print("\n===== Threshold Framework Demonstration =====")
    print(f"Created threshold set: {voc_thresholds.name}")
    
    # Demonstrate classification
    print("\nBasic classification:")
    for value in test_values:
        severity = voc_thresholds.classify_severity(value)
        print(f"Response value {value:.1f} classified as: {severity.name}")
    
    # Demonstrate confidence
    print("\nClassification with confidence:")
    for value in test_values:
        severity, confidence = voc_thresholds.classify_severity(
            value, with_confidence=True
        )
        print(f"Response value {value:.1f} classified as {severity.name} with {confidence:.2f} confidence")
    
    # Demonstrate detailed classification
    print("\nDetailed classification for response value 72.0:")
    details = voc_thresholds.get_classification_details(72.0)
    print(f"Classification: {details['classification']}")
    print(f"Confidence: {details['confidence']:.2f}")
    
    print("\nThreshold details:")
    for threshold in details['threshold_details']:
        print(f"  {threshold['severity_level']}: value={threshold['threshold_value']:.1f}, "
              f"exceedance_probability={threshold['exceedance_probability']:.2f}, "
              f"confidence_interval=({threshold['confidence_interval'][0]:.1f}, "
              f"{threshold['confidence_interval'][1]:.1f})")


def individual_system_demo() -> None:
    """
    Demonstrate using individual response systems directly.
    """
    # Create respiratory system
    respiratory_system = RespiratoryResponseSystem()
    
    # Create neurological system
    neurological_system = NeurologicalResponseSystem()
    
    # Create test exposure data
    test_exposures = [
        {
            "chemical_id": "formaldehyde",
            "concentration": 0.5,  # ppm
            "duration": 1.0,  # hours
            "inhaled_volume": 0.5,  # liters
        },
        {
            "chemical_id": "toluene",
            "concentration": 100.0,  # ppm
            "duration": 2.0,  # hours
            "peak_concentration": 150.0,  # ppm
            "cumulative_dose": 200.0,  # ppm-hours
        }
    ]
    
    # Create test sensitivity profiles
    test_profiles = [
        {
            "name": "Healthy Adult",
            "profile": {
                "age": 35,
                "respiratory_sensitivity": 1.0,
                "neurological_sensitivity": 1.0,
                "respiratory_conditions": [],
                "neurological_conditions": [],
            }
        },
        {
            "name": "Sensitive Individual",
            "profile": {
                "age": 70,
                "respiratory_sensitivity": 1.5,
                "neurological_sensitivity": 1.3,
                "respiratory_conditions": ["asthma", "COPD"],
                "neurological_conditions": ["migraine"],
                "blood_brain_barrier_factor": 1.2
            }
        }
    ]
    
    print("\n===== Individual System Demonstration =====")
    
    # Demonstrate respiratory system
    print("\nRespiratory System Responses:")
    for exposure in test_exposures:
        print(f"\nExposure to {exposure['chemical_id']} at {exposure['concentration']} ppm for {exposure['duration']} hours:")
        
        for profile_info in test_profiles:
            response = respiratory_system.calculate_response(
                exposure, profile_info["profile"]
            )
            
            print(f"  {profile_info['name']}:")
            print(f"    Response value: {response.response_value:.2f}")
            print(f"    Severity: {response.severity_level.name}")
            print(f"    Confidence interval: ({response.confidence_interval[0]:.2f}, {response.confidence_interval[1]:.2f})")
            print(f"    Onset time: {response.onset_time}")
            print(f"    Peak time: {response.peak_time}")
            print(f"    Recovery time: {response.recovery_time}")
    
    # Demonstrate neurological system
    print("\nNeurological System Responses:")
    for exposure in test_exposures:
        print(f"\nExposure to {exposure['chemical_id']} at {exposure['concentration']} ppm for {exposure['duration']} hours:")
        
        for profile_info in test_profiles:
            response = neurological_system.calculate_response(
                exposure, profile_info["profile"]
            )
            
            print(f"  {profile_info['name']}:")
            print(f"    Response value: {response.response_value:.2f}")
            print(f"    Severity: {response.severity_level.name}")
            print(f"    Confidence interval: ({response.confidence_interval[0]:.2f}, {response.confidence_interval[1]:.2f})")
            print(f"    Onset time: {response.onset_time}")
            print(f"    Peak time: {response.peak_time}")
            print(f"    Recovery time: {response.recovery_time}")


def main():
    """Main demonstration function."""
    print("===== EnviroSense Physiological Response System Demonstration =====\n")
    
    print("This demonstration shows the capabilities of the physiological response")
    print("modeling framework, including respiratory and neurological responses")
    print("to chemical exposures with various sensitivity profiles.\n")
    
    # Demonstrate individual systems
    individual_system_demo()
    
    # Demonstrate the threshold framework
    demonstrate_threshold_framework()
    
    # Run the simulation
    print("\n===== Running Simulation Scenario =====")
    results = run_simulation_scenario()
    print("Simulation complete. Generating visualization...")
    
    # Visualize the results
    visualize_results(results)
    print("\nVisualization saved as 'physiological_response_simulation.png'")
    
    print("\nDemonstration complete!")


if __name__ == "__main__":
    main()
