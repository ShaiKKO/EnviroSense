"""
Delayed Response Modeling Example.

This example demonstrates how to use the DelayedResponseModel to analyze
and predict time-lagged relationships between environmental exposures and responses.
"""

import numpy as np
import matplotlib.pyplot as plt
import datetime
from typing import Dict, List, Tuple

from envirosense.core_platform.temporal_correlation import (
    DelayedResponseModel,
    TemporalPattern,
    DelayParameters
)


def generate_example_data() -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray], np.ndarray]:
    """
    Generate synthetic exposure and response data for demonstration.
    
    Returns:
        Tuple containing:
        - exposure_data: Dictionary of exposure time series
        - response_data: Dictionary of response time series
        - timestamps: Array of timestamps
    """
    # Generate timestamps: 2 hours of data at 1-minute intervals
    n_timestamps = 120
    base_time = datetime.datetime.now()
    timestamps = np.array([
        base_time + datetime.timedelta(minutes=i) 
        for i in range(n_timestamps)
    ])
    
    # Generate exposure data: a chemical release with a peak
    time_array = np.arange(n_timestamps)
    
    # Formaldehyde exposure: spike at t=30 min with gradual decay
    formaldehyde = np.zeros(n_timestamps)
    spike_idx = 30
    formaldehyde[spike_idx:] = 10.0 * np.exp(-0.05 * (time_array[spike_idx:] - spike_idx))
    
    # VOC exposure: gradual increase over the period
    voc = 2.0 + 0.08 * time_array + 0.5 * np.random.randn(n_timestamps)
    voc = np.maximum(voc, 0)  # Ensure non-negative
    
    # Package the exposure data
    exposure_data = {
        "formaldehyde": formaldehyde,
        "voc": voc
    }
    
    # Generate response data with different temporal patterns
    
    # Respiratory response: delayed response to formaldehyde with added noise
    respiratory = np.zeros(n_timestamps)
    onset_idx = spike_idx + 10  # 10 minute delay
    peak_idx = spike_idx + 25   # 25 minute delay to peak
    
    # Create delayed response profile
    if onset_idx < n_timestamps:
        # Initial response
        respiratory[onset_idx:] = 5.0 * np.exp(-0.03 * (time_array[onset_idx:] - onset_idx))
        
        # Add some response to VOC (less sensitive)
        respiratory += 0.2 * voc
        
        # Add noise
        respiratory += 0.3 * np.random.randn(n_timestamps)
    
    # Skin response: biphasic response to VOC
    skin = 0.5 * voc + 0.2 * np.random.randn(n_timestamps)
    
    # Add a secondary delayed response to formaldehyde
    secondary_idx = spike_idx + 40  # 40 minute delay to secondary response
    if secondary_idx < n_timestamps:
        skin[secondary_idx:] += 3.0 * np.exp(-0.04 * (time_array[secondary_idx:] - secondary_idx))
    
    # Package the response data
    response_data = {
        "respiratory": respiratory,
        "skin": skin
    }
    
    return exposure_data, response_data, timestamps


def plot_results(
    exposure_data: Dict[str, np.ndarray],
    response_data: Dict[str, np.ndarray],
    predicted_responses: Dict[str, Dict[str, np.ndarray]],
    timestamps: np.ndarray,
    delay_params: Dict[str, DelayParameters]
):
    """
    Plot the exposure data, actual responses, and predicted responses.
    
    Args:
        exposure_data: Dictionary of exposure time series
        response_data: Dictionary of actual response time series
        predicted_responses: Dictionary of predicted response data
        timestamps: Array of timestamps
        delay_params: Dictionary of delay parameters for each response
    """
    # Convert timestamps to minutes for plotting
    minutes = np.array([
        (ts - timestamps[0]).total_seconds() / 60.0 
        for ts in timestamps
    ])
    
    # Create a figure with subplots
    fig, axs = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
    
    # Plot exposures
    ax_exposure = axs[0]
    for exposure_type, values in exposure_data.items():
        ax_exposure.plot(minutes, values, label=f"{exposure_type}")
    
    ax_exposure.set_title("Exposures")
    ax_exposure.set_ylabel("Concentration")
    ax_exposure.legend()
    ax_exposure.grid(True)
    
    # Plot actual vs predicted responses
    response_types = list(response_data.keys())
    
    for i, response_type in enumerate(response_types):
        if i < 2:  # We only have 2 subplots for responses
            ax_response = axs[i+1]
            
            # Plot actual response
            ax_response.plot(minutes, response_data[response_type], 
                         label=f"Actual {response_type}", color='blue')
            
            # Plot predicted response
            if response_type in predicted_responses:
                pred_values = predicted_responses[response_type]["predicted_values"]
                uncertainty = predicted_responses[response_type].get("uncertainty")
                
                ax_response.plot(minutes, pred_values, 
                             label=f"Predicted {response_type}", color='red', linestyle='--')
                
                # Plot uncertainty if available
                if uncertainty is not None:
                    ax_response.fill_between(
                        minutes, 
                        pred_values - uncertainty,
                        pred_values + uncertainty,
                        color='red', alpha=0.2
                    )
            
            # Mark delay parameters if available
            if response_type in delay_params:
                dp = delay_params[response_type]
                
                # Find formaldehyde spike time as reference
                spike_idx = np.argmax(exposure_data.get("formaldehyde", np.zeros_like(minutes)))
                spike_time = minutes[spike_idx]
                
                # Calculate key timestamps
                onset_time = spike_time + dp.onset_delay.total_seconds() / 60.0
                peak_time = spike_time + (dp.onset_delay + dp.time_to_peak).total_seconds() / 60.0
                
                # Mark onset and peak
                ax_response.axvline(x=onset_time, color='green', linestyle=':', label=f"Onset ({onset_time:.1f} min)")
                ax_response.axvline(x=peak_time, color='purple', linestyle=':', label=f"Peak ({peak_time:.1f} min)")
            
            ax_response.set_title(f"{response_type.capitalize()} Response")
            ax_response.set_ylabel("Response Intensity")
            ax_response.legend()
            ax_response.grid(True)
    
    # Set common x-axis label
    axs[-1].set_xlabel("Time (minutes)")
    
    plt.tight_layout()
    plt.savefig("delayed_response_example.png")
    plt.show()


def demonstrate_delayed_response_modeling():
    """
    Demonstrate the core functionality of DelayedResponseModel.
    """
    print("Demonstrating Delayed Response Modeling")
    
    # Generate synthetic data
    exposure_data, response_data, timestamps = generate_example_data()
    
    # Create and train the delayed response model
    model = DelayedResponseModel(
        use_gaussian_process=True,
        enable_uncertainty_quantification=True
    )
    
    # Train the model on the data
    model.fit(
        exposure_data=exposure_data,
        response_data=response_data,
        timestamps=timestamps,
        metadata={
            "compound_ids": {
                "formaldehyde": "formaldehyde",
                "voc": "voc_general"
            }
        }
    )
    
    # Predict responses for the same time period (for demonstration)
    predicted_responses = model.predict_response(
        exposure_data=exposure_data,
        exposure_timestamps=timestamps,
        prediction_timestamps=timestamps,
        response_types=list(response_data.keys()),
        metadata={
            "compound_ids": {
                "formaldehyde": "formaldehyde",
                "voc": "voc_general"
            }
        }
    )
    
    # Estimate delay parameters for each response type
    delay_params = {}
    for response_type, response_values in response_data.items():
        # For simplicity, just use formaldehyde as the reference exposure
        formaldehyde = exposure_data["formaldehyde"]
        
        estimated_params = model.estimate_delay_parameters(
            exposure_data=formaldehyde,
            response_data=response_values,
            timestamps=timestamps
        )
        
        delay_params[response_type] = estimated_params
        
        # Print the estimated parameters
        print(f"\nEstimated delay parameters for {response_type} response:")
        print(f"  Pattern type: {estimated_params.pattern_type}")
        print(f"  Onset delay: {estimated_params.onset_delay}")
        print(f"  Time to peak: {estimated_params.time_to_peak}")
        print(f"  Recovery duration: {estimated_params.recovery_duration}")
        
        if estimated_params.pattern_type == TemporalPattern.BIPHASIC:
            print(f"  Secondary onset: {estimated_params.secondary_onset}")
            print(f"  Secondary recovery: {estimated_params.secondary_recovery}")
    
    # Align respiratory response with formaldehyde exposure
    formaldehyde = exposure_data["formaldehyde"]
    respiratory = response_data["respiratory"]
    
    aligned_exposure, aligned_response, estimated_delay = model.align_response_with_exposure(
        exposure_data=formaldehyde,
        response_data=respiratory,
        exposure_timestamps=timestamps,
        response_timestamps=timestamps
    )
    
    print(f"\nEstimated delay between formaldehyde exposure and respiratory response: "
          f"{estimated_delay:.2f} seconds")
    
    # Plot the results
    plot_results(
        exposure_data=exposure_data,
        response_data=response_data,
        predicted_responses=predicted_responses,
        timestamps=timestamps,
        delay_params=delay_params
    )


if __name__ == "__main__":
    demonstrate_delayed_response_modeling() 