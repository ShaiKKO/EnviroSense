"""
Example demonstration of Cumulative Effect Modeling.

This script demonstrates the use of the CumulativeEffectModel to track
accumulation of substances over time, considering exposure events,
clearance rates, and threshold effects.
"""

import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import sys
import numpy as np

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from envirosense.core_platform.temporal_correlation.cumulative_effect import (
    CumulativeEffectModel, AccumulationModelType
)


def basic_accumulation_example():
    """
    Demonstrate basic substance accumulation with first-order kinetics.
    """
    print("\n--- Basic Accumulation Example ---")
    
    # Create a model
    model = CumulativeEffectModel()
    
    # Register a substance (benzene with 6-hour half-life)
    model.register_substance(
        substance_id="benzene",
        half_life=datetime.timedelta(hours=6),
        accumulation_rate=1.0,
        model_type=AccumulationModelType.FIRST_ORDER,
        threshold_value=50.0,
        threshold_description="Elevated benzene level - risk of adverse effects"
    )
    
    # Record some exposure events
    now = datetime.datetime.now()
    
    # Initial exposure
    model.record_exposure(
        substance_id="benzene",
        concentration=20.0,  # units/volume
        duration=0.5,        # hours
        timestamp=now
    )
    print(f"Recorded exposure: 20.0 units for 0.5 hours at {now}")
    
    # Check current level
    level = model.get_current_level("benzene")
    print(f"Current benzene level: {level:.2f}")
    
    # Simulate time passing (2 hours)
    later = now + datetime.timedelta(hours=2)
    model.update_current_levels(later)
    level = model.get_current_level("benzene")
    print(f"Level after 2 hours: {level:.2f}")
    
    # Another exposure
    model.record_exposure(
        substance_id="benzene",
        concentration=30.0,  # units/volume
        duration=1.0,        # hours
        timestamp=later
    )
    print(f"Recorded exposure: 30.0 units for 1.0 hours at {later}")
    
    # Check level again
    level = model.get_current_level("benzene")
    print(f"Level after second exposure: {level:.2f}")
    
    # Simulate more time passing (8 hours)
    even_later = later + datetime.timedelta(hours=8)
    model.update_current_levels(even_later)
    level = model.get_current_level("benzene")
    print(f"Level after 8 more hours: {level:.2f}")


def threshold_crossing_example():
    """
    Demonstrate threshold detection with multiple exposures.
    """
    print("\n--- Threshold Crossing Example ---")
    
    # Create a model
    model = CumulativeEffectModel()
    
    # Register a substance (formaldehyde with 30-minute half-life)
    model.register_substance(
        substance_id="formaldehyde",
        half_life=datetime.timedelta(minutes=30),
        accumulation_rate=2.0,
        model_type=AccumulationModelType.FIRST_ORDER,
        threshold_value=25.0,
        threshold_description="Formaldehyde irritation threshold"
    )
    
    # Record exposure events until we cross threshold
    now = datetime.datetime.now()
    levels = []
    times = []
    
    for i in range(5):
        # Record exposure
        timestamp = now + datetime.timedelta(minutes=i*15)
        model.record_exposure(
            substance_id="formaldehyde",
            concentration=10.0,
            duration=0.25,  # 15 minutes
            timestamp=timestamp
        )
        
        # Get level and check threshold
        level = model.get_current_level("formaldehyde")
        levels.append(level)
        times.append(timestamp)
        
        # Check for threshold crossing
        active_thresholds = model.get_active_thresholds()
        
        print(f"Time: {timestamp}, Level: {level:.2f}")
        if "formaldehyde" in active_thresholds:
            print(f"THRESHOLD CROSSED: {active_thresholds['formaldehyde']['description']}")
    
    # Plot the results
    plt.figure(figsize=(10, 6))
    plt.plot(times, levels, 'b-o', label='Formaldehyde Level')
    plt.axhline(y=25.0, color='r', linestyle='--', label='Irritation Threshold')
    plt.title('Formaldehyde Accumulation and Threshold Crossing')
    plt.xlabel('Time')
    plt.ylabel('Accumulated Level')
    plt.legend()
    plt.gcf().autofmt_xdate()
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(__file__), '../../../../output/cumulative_effect_examples')
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the plot
    output_file = os.path.join(output_dir, 'threshold_crossing_example.png')
    plt.savefig(output_file)
    plt.close()
    
    print(f"Plot saved to: {output_file}")


def multi_compartment_example():
    """
    Demonstrate multi-compartment model for substance distribution.
    """
    print("\n--- Multi-Compartment Example ---")
    
    # Create a model
    model = CumulativeEffectModel()
    
    # Register a substance with multi-compartment model (e.g., mercury)
    model.register_substance(
        substance_id="mercury",
        half_life=datetime.timedelta(days=30),  # Long half-life in body
        accumulation_rate=0.8,
        model_type=AccumulationModelType.MULTI_COMPARTMENT,
        threshold_value=10.0,
        threshold_description="Mercury toxicity threshold"
    )
    
    # Get the profile to set custom compartment distribution
    profile = model.substance_profiles["mercury"]
    
    # Define three-compartment model (blood, organs, brain)
    profile.compartments = {
        "blood": 0.6,    # 60% initially distributes to blood
        "organs": 0.3,   # 30% to organs
        "brain": 0.1     # 10% to brain
    }
    
    # Define inter-compartment transfer rates
    profile.inter_compartment_rates = {
        ("blood", "organs"): 0.02,   # 2% transfer from blood to organs per hour
        ("blood", "brain"): 0.005,   # 0.5% transfer from blood to brain per hour
        ("organs", "blood"): 0.01,   # 1% transfer from organs to blood per hour
        ("brain", "blood"): 0.001    # 0.1% transfer from brain to blood per hour
    }
    
    # Record exposure
    now = datetime.datetime.now()
    model.record_exposure(
        substance_id="mercury",
        concentration=10.0,
        duration=1.0,
        timestamp=now
    )
    
    # Track levels over time
    times = []
    blood_levels = []
    organ_levels = []
    brain_levels = []
    total_levels = []
    
    # Track for 10 days
    for day in range(11):
        timestamp = now + datetime.timedelta(days=day)
        model.update_current_levels(timestamp)
        
        # Get compartment levels
        blood = model.get_current_level("mercury", "blood")
        organs = model.get_current_level("mercury", "organs")
        brain = model.get_current_level("mercury", "brain")
        total = model.get_current_level("mercury")
        
        times.append(timestamp)
        blood_levels.append(blood)
        organ_levels.append(organs)
        brain_levels.append(brain)
        total_levels.append(total)
        
        print(f"Day {day}: Blood={blood:.2f}, Organs={organs:.2f}, Brain={brain:.2f}, Total={total:.2f}")
    
    # Plot the results
    plt.figure(figsize=(12, 8))
    plt.plot(times, blood_levels, 'r-o', label='Blood')
    plt.plot(times, organ_levels, 'g-s', label='Organs')
    plt.plot(times, brain_levels, 'b-^', label='Brain')
    plt.plot(times, total_levels, 'k--', label='Total')
    plt.title('Mercury Distribution in Multi-Compartment Model')
    plt.xlabel('Time')
    plt.ylabel('Mercury Level')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.gcf().autofmt_xdate()
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(__file__), '../../../../output/cumulative_effect_examples')
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the plot
    output_file = os.path.join(output_dir, 'multi_compartment_example.png')
    plt.savefig(output_file)
    plt.close()
    
    print(f"Plot saved to: {output_file}")


def future_prediction_example():
    """
    Demonstrate future level prediction and threshold crossing prediction.
    """
    print("\n--- Future Prediction Example ---")
    
    # Create a model
    model = CumulativeEffectModel()
    
    # Register carbon monoxide
    model.register_substance(
        substance_id="carbon_monoxide",
        half_life=datetime.timedelta(hours=4),  # CO half-life in blood
        accumulation_rate=1.5,
        model_type=AccumulationModelType.FIRST_ORDER,
        threshold_value=60.0,
        threshold_description="CO toxicity threshold"
    )
    
    # Record some past exposures
    now = datetime.datetime.now()
    
    # Initial exposures
    model.record_exposure(
        substance_id="carbon_monoxide",
        concentration=15.0,
        duration=0.5,
        timestamp=now - datetime.timedelta(hours=3)
    )
    
    model.record_exposure(
        substance_id="carbon_monoxide",
        concentration=20.0,
        duration=0.75,
        timestamp=now - datetime.timedelta(hours=1)
    )
    
    # Define future exposures
    future_exposures = [
        {
            "substance_id": "carbon_monoxide",
            "concentration": 30.0,
            "duration": 1.0,
            "timestamp": now + datetime.timedelta(hours=2)
        },
        {
            "substance_id": "carbon_monoxide",
            "concentration": 25.0,
            "duration": 1.5,
            "timestamp": now + datetime.timedelta(hours=5)
        },
        {
            "substance_id": "carbon_monoxide",
            "concentration": 35.0,
            "duration": 0.5,
            "timestamp": now + datetime.timedelta(hours=8)
        }
    ]
    
    # Generate time points for prediction
    time_points = []
    current = now - datetime.timedelta(hours=4)
    while current <= now + datetime.timedelta(hours=12):
        time_points.append(current)
        current += datetime.timedelta(minutes=30)
    
    # Get predicted levels
    predictions = model.predict_future_levels(
        substance_id="carbon_monoxide",
        time_points=time_points,
        future_exposures=future_exposures
    )
    
    # Get threshold crossings
    crossings = model.predict_threshold_crossings(
        substance_id="carbon_monoxide",
        max_prediction_time=datetime.timedelta(hours=12),
        future_exposures=future_exposures
    )
    
    # Print current level
    current_level = model.get_current_level("carbon_monoxide")
    print(f"Current CO level: {current_level:.2f}")
    
    # Print predicted threshold crossings
    if crossings:
        for crossing in crossings:
            crossing_type = crossing.get("crossing_type", "unknown")
            time = crossing.get("prediction_time", "unknown")
            print(f"Predicted {crossing_type} at {time}")
    else:
        print("No threshold crossings predicted")
    
    # Plot the results
    plt.figure(figsize=(12, 8))
    
    # Plot predicted levels
    times = list(predictions.keys())
    levels = list(predictions.values())
    plt.plot(times, levels, 'b-', label='Predicted CO Level')
    
    # Mark future exposures
    for exposure in future_exposures:
        time = exposure["timestamp"]
        plt.axvline(x=time, color='g', linestyle=':', alpha=0.7)
        plt.text(time, max(levels) * 0.9, f"{exposure['concentration']}", 
                 rotation=90, verticalalignment='top')
    
    # Mark threshold
    plt.axhline(y=60.0, color='r', linestyle='--', label='Toxicity Threshold')
    
    # Mark threshold crossings
    for crossing in crossings:
        if crossing.get("crossing_type") == "exceedance":
            time = crossing.get("prediction_time")
            plt.plot([time], [60.0], 'ro', markersize=10)
            plt.text(time, 62.0, "Threshold Crossed", 
                    horizontalalignment='center', color='red')
    
    # Mark "now" line
    plt.axvline(x=now, color='k', linestyle='-', label='Current Time')
    
    plt.title('Carbon Monoxide Level Prediction with Future Exposures')
    plt.xlabel('Time')
    plt.ylabel('CO Level')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.gcf().autofmt_xdate()
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(__file__), '../../../../output/cumulative_effect_examples')
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the plot
    output_file = os.path.join(output_dir, 'future_prediction_example.png')
    plt.savefig(output_file)
    plt.close()
    
    print(f"Plot saved to: {output_file}")


if __name__ == "__main__":
    # Run the examples
    basic_accumulation_example()
    threshold_crossing_example()
    multi_compartment_example()
    future_prediction_example()
    
    print("\nAll examples completed successfully.")
