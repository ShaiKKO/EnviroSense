"""
Demonstration of temporal response and cascade modeling in physiological systems.

This example demonstrates the use of temporal effects in physiological response
systems, including delayed response patterns, chronic accumulation, and cascading
effects between systems. It provides practical examples of how to use the
temporal physiological systems and the PhysiologicalEffectGraph.

References:
- Cohen et al. (2023): "Delayed Onset of Chemical Effects in Biological Systems"
"""

import datetime
import matplotlib.pyplot as plt
import numpy as np
import os
import json
from typing import Dict, List, Optional, Union, Any

from envirosense.core.exposure.physiological_response.base import (
    PhysiologicalSystemSet,
    ResponseSeverityLevel
)
from envirosense.core.exposure.physiological_response.temporal_respiratory import (
    TemporalRespiratorySystem
)
from envirosense.core.exposure.physiological_response.temporal_neurological import (
    TemporalNeurologicalSystem
)
from envirosense.core.exposure.physiological_response.temporal_response import (
    TemporalSystemSet,
    TemporalPattern,
    PhysiologicalEffectGraph
)


def create_demo_system_set() -> PhysiologicalSystemSet:
    """
    Create a demonstration system set with respiratory and neurological systems.
    
    Returns:
        PhysiologicalSystemSet with configured systems
    """
    # Create the system set
    system_set = PhysiologicalSystemSet()
    
    # Add temporal respiratory system
    respiratory = TemporalRespiratorySystem(
        name="Respiratory System",
        description="Models respiratory effects with temporal dynamics"
    )
    system_set.add_system(respiratory)
    
    # Add temporal neurological system
    neurological = TemporalNeurologicalSystem(
        name="Neurological System",
        description="Models neurological effects with temporal dynamics"
    )
    system_set.add_system(neurological)
    
    # Set interaction factors
    # Respiratory issues can impact neurological function
    system_set.set_interaction(
        "Respiratory System",
        "Neurological System",
        0.4  # Strong effect - respiratory issues affect brain oxygenation
    )
    
    # Neurological issues can affect breathing control
    system_set.set_interaction(
        "Neurological System",
        "Respiratory System",
        0.3  # Moderate effect - brain controls respiratory function
    )
    
    return system_set


def create_sample_exposure(
    chemical_id: str,
    concentration: float,
    duration: float,
    previous_exposures: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Create a sample exposure history.
    
    Args:
        chemical_id: ID of the chemical
        concentration: Chemical concentration
        duration: Exposure duration in hours
        previous_exposures: Optional list of previous exposure events
        
    Returns:
        Exposure history dictionary
    """
    exposure = {
        "chemical_id": chemical_id,
        "concentration": concentration,
        "duration": duration,
        "timestamp": datetime.datetime.now(),
        "exposure_id": f"exp_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
    }
    
    # Add optional fields
    if chemical_id.lower() in ["benzene", "toluene", "xylene", "ethanol"]:
        # Add peak concentration for volatile organics
        exposure["peak_concentration"] = concentration * 1.5
    
    if chemical_id.lower() in ["carbon_monoxide", "nitrogen_dioxide"]:
        # Add inhaled volume for gases
        exposure["inhaled_volume"] = 10.0  # Default 10L
    
    # Add previous exposures if provided
    if previous_exposures:
        exposure["previous_exposures"] = previous_exposures
        
    return exposure


def create_sample_sensitivity_profile() -> Dict[str, Any]:
    """
    Create a sample sensitivity profile.
    
    Returns:
        Sensitivity profile dictionary
    """
    return {
        "age": 45,
        "weight": 70,  # kg
        "height": 170,  # cm
        "sex": "female",
        "respiratory_sensitivity": 1.2,  # Higher than average sensitivity
        "neurological_sensitivity": 1.1,  # Slightly higher than average sensitivity
        "respiratory_conditions": ["asthma"],
        "neurological_conditions": [],
        "medications": ["bronchodilator"],
        "blood_brain_barrier_factor": 1.1,  # Slightly increased permeability
    }


def demonstrate_temporal_patterns():
    """
    Demonstrate different temporal response patterns for chemicals.
    
    This shows how immediate, delayed, biphasic, chronic, and recurrent
    patterns behave over time.
    """
    print("\n=== Demonstrating Temporal Patterns ===\n")
    
    # Create a respiratory system for demonstration
    respiratory = TemporalRespiratorySystem()
    
    # Create sample exposures for different chemicals with different patterns
    chemical_patterns = {
        "chlorine": TemporalPattern.IMMEDIATE,
        "nitrogen_dioxide": TemporalPattern.DELAYED,
        "formaldehyde": TemporalPattern.BIPHASIC,
        "benzene": TemporalPattern.CHRONIC,
        "isocyanates": TemporalPattern.RECURRENT
    }
    
    # Time points for projection (0 to 72 hours)
    start_time = datetime.datetime.now()
    time_points = [
        start_time + datetime.timedelta(hours=h)
        for h in range(0, 73, 3)  # Every 3 hours for 72 hours
    ]
    
    # Create plot
    plt.figure(figsize=(12, 8))
    
    # Generate response projections for each chemical
    for chemical_id, pattern in chemical_patterns.items():
        print(f"Projecting {chemical_id} ({pattern.name}) responses...")
        
        # Create exposure
        exposure = create_sample_exposure(
            chemical_id=chemical_id,
            concentration=20.0,
            duration=1.0
        )
        
        # Add previous exposures for chronic chemicals
        if pattern == TemporalPattern.CHRONIC:
            # Add series of previous exposures over the past month
            previous_exposures = []
            for days_ago in [1, 3, 7, 14, 21, 28]:
                prev_timestamp = start_time - datetime.timedelta(days=days_ago)
                prev_exposure = {
                    "chemical_id": chemical_id,
                    "concentration": 15.0,
                    "duration": 1.0,
                    "timestamp": prev_timestamp
                }
                previous_exposures.append(prev_exposure)
            exposure["previous_exposures"] = previous_exposures
        
        # Project responses over time
        projections = respiratory.project_response_over_time(
            exposure_history=exposure,
            time_points=time_points
        )
        
        # Extract response values
        times = [t.timestamp() for t in projections.keys()]
        times = [(t - times[0]) / 3600.0 for t in times]  # Convert to hours
        values = [r.response_value for r in projections.values()]
        
        # Plot
        plt.plot(times, values, label=f"{chemical_id} ({pattern.name})")
    
    # Format plot
    plt.xlabel("Time (hours)")
    plt.ylabel("Response Value")
    plt.title("Temporal Response Patterns for Different Chemicals")
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Save plot
    os.makedirs("envirosense/plots", exist_ok=True)
    plt.savefig("envirosense/plots/temporal_patterns.png")
    print("Plot saved to envirosense/plots/temporal_patterns.png")
    
    plt.close()


def demonstrate_system_cascade():
    """
    Demonstrate cascading effects between physiological systems.
    
    This shows how a response in one system can propagate to other systems
    over time with appropriate delays.
    """
    print("\n=== Demonstrating System Cascades ===\n")
    
    # Create the system set
    system_set = create_demo_system_set()
    
    # Create the temporal system set
    temporal_set = TemporalSystemSet(system_set)
    
    # Create a severe exposure to carbon monoxide
    # (affects respiratory system first, then cascades to neurological)
    severe_co_exposure = create_sample_exposure(
        chemical_id="carbon_monoxide",
        concentration=50.0,  # High concentration
        duration=2.0         # 2 hour exposure
    )
    
    # Define time points for cascade calculation
    reference_time = datetime.datetime.now()
    time_points = [
        reference_time + datetime.timedelta(hours=h)
        for h in [0, 1, 2, 4, 8, 12, 24, 48]
    ]
    
    # Calculate cascade effects starting from respiratory system
    cascade_results = temporal_set.calculate_temporal_cascade(
        initial_system="Respiratory System",
        exposure_history=severe_co_exposure,
        time_points=time_points
    )
    
    # Extract data for plotting
    times = [(t - reference_time).total_seconds() / 3600.0 for t in cascade_results.keys()]
    respiratory_values = [
        responses.get("Respiratory System").response_value 
        if "Respiratory System" in responses else 0.0
        for responses in cascade_results.values()
    ]
    neurological_values = [
        responses.get("Neurological System").response_value 
        if "Neurological System" in responses else 0.0
        for responses in cascade_results.values()
    ]
    
    # Create plot
    plt.figure(figsize=(12, 8))
    plt.plot(times, respiratory_values, 'b-o', label="Respiratory System")
    plt.plot(times, neurological_values, 'r-s', label="Neurological System")
    
    # Add severity thresholds for reference
    for level in [ResponseSeverityLevel.MILD, ResponseSeverityLevel.MODERATE, ResponseSeverityLevel.SEVERE]:
        respiratory_threshold = None
        neurological_threshold = None
        
        resp_system = system_set.get_system("Respiratory System")
        neuro_system = system_set.get_system("Neurological System")
        
        if resp_system and level in resp_system.thresholds:
            respiratory_threshold = resp_system.thresholds[level]
        
        if neuro_system and level in neuro_system.thresholds:
            neurological_threshold = neuro_system.thresholds[level]
        
        if respiratory_threshold:
            plt.axhline(y=respiratory_threshold, color='b', linestyle='--', alpha=0.5,
                        label=f"Respiratory {level.name}")
        
        if neurological_threshold:
            plt.axhline(y=neurological_threshold, color='r', linestyle='--', alpha=0.5,
                        label=f"Neurological {level.name}")
    
    # Format plot
    plt.xlabel("Time (hours)")
    plt.ylabel("Response Value")
    plt.title("Cascade of Effects Between Physiological Systems")
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Save plot
    plt.savefig("envirosense/plots/system_cascade.png")
    print("Plot saved to envirosense/plots/system_cascade.png")
    
    plt.close()
    
    # Print detailed cascade information for the 8-hour point
    hour_8_point = time_points[4]  # Index 4 corresponds to 8 hours
    hour_8_data = cascade_results[hour_8_point]
    
    print("\nDetailed cascade information at 8 hours:")
    for system_name, response in hour_8_data.items():
        severity = response.severity_level.name
        print(f"- {system_name}: Response = {response.response_value:.2f}, " 
              f"Severity = {severity}")
        
        if "cascade_source" in response.metadata:
            cascade_source = response.metadata["cascade_source"]
            cascade_magnitude = response.metadata.get("cascade_magnitude", "N/A")
            cascade_path = response.metadata.get("cascade_path", [])
            
            print(f"  Cascade from: {cascade_source}")
            print(f"  Cascade magnitude: {cascade_magnitude}")
            print(f"  Cascade path: {' -> '.join(cascade_path)}")
        
        print(f"  Onset time: {response.onset_time}")
        print(f"  Peak time: {response.peak_time}")
        print(f"  Recovery time: {response.recovery_time}")
        print("")


def demonstrate_response_prediction():
    """
    Demonstrate prediction of when responses will reach certain thresholds.
    
    This shows how to predict when symptoms of different severities might occur.
    """
    print("\n=== Demonstrating Response Prediction ===\n")
    
    # Create the system set
    system_set = create_demo_system_set()
    
    # Create the temporal system set
    temporal_set = TemporalSystemSet(system_set)
    
    # Create a moderate exposure to formaldehyde
    formaldehyde_exposure = create_sample_exposure(
        chemical_id="formaldehyde",
        concentration=30.0,  # Moderate concentration
        duration=4.0         # 4 hour exposure
    )
    
    # Define sensitivity profile
    sensitivity = create_sample_sensitivity_profile()
    
    # Set custom thresholds for prediction
    threshold_levels = {
        "Respiratory System": 25.0,  # MILD symptoms threshold
        "Neurological System": 30.0  # MILD symptoms threshold
    }
    
    # Predict when each system will reach its threshold
    predictions = temporal_set.predict_system_responses(
        exposure_history=formaldehyde_exposure,
        sensitivity_profile=sensitivity,
        threshold_levels=threshold_levels,
        max_prediction_time=datetime.timedelta(days=2)
    )
    
    print("Response threshold predictions:")
    reference_time = datetime.datetime.now()
    
    for system_name, (predicted_time, confidence) in predictions.items():
        if predicted_time:
            hours_until = (predicted_time - reference_time).total_seconds() / 3600.0
            print(f"- {system_name} will reach threshold in {hours_until:.1f} hours "
                  f"(confidence: {confidence:.2f})")
        else:
            print(f"- {system_name} will not reach threshold within prediction window")
    
    # Demonstrate more detailed prediction with confidence intervals
    respiratory = system_set.get_system("Respiratory System")
    if hasattr(respiratory, "predict_time_to_response"):
        print("\nDetailed respiratory prediction with confidence intervals:")
        threshold = 50.0  # MODERATE symptoms
        predicted_time, confidence_interval = respiratory.predict_time_to_response(
            formaldehyde_exposure,
            threshold,
            sensitivity_profile=sensitivity
        )
        
        if predicted_time:
            hours_until = (predicted_time - reference_time).total_seconds() / 3600.0
            earliest = (confidence_interval[0] - reference_time).total_seconds() / 3600.0
            latest = (confidence_interval[1] - reference_time).total_seconds() / 3600.0
            
            print(f"Respiratory MODERATE symptoms (threshold {threshold}):")
            print(f"- Best estimate: {hours_until:.1f} hours")
            print(f"- Confidence interval: {earliest:.1f} to {latest:.1f} hours")
        else:
            print(f"Respiratory system will not reach MODERATE symptoms within prediction window")


def main():
    """Run all demonstrations."""
    print("Temporal Physiological Response System Demonstration")
    print("===================================================\n")
    
    # Demonstrate different temporal patterns
    demonstrate_temporal_patterns()
    
    # Demonstrate system cascades
    demonstrate_system_cascade()
    
    # Demonstrate response prediction
    demonstrate_response_prediction()
    
    print("\nDemonstration completed successfully.")


if __name__ == "__main__":
    main()
