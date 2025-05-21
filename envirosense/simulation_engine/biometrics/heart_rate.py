"""
Heart Rate Biometric Signal Model

This module provides heart rate signal generation capabilities, simulating how 
heart rate responds to environmental factors and chemical exposures.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
import math
import random

from envirosense.core.time_series.parameters import Parameter
from envirosense.core.biometrics.base import BiometricSignalModel


class HeartRateModel(BiometricSignalModel):
    """Heart rate biometric signal model.
    
    This class simulates heart rate responses to environmental conditions and chemical
    exposures, providing realistic heart rate patterns with appropriate variability.
    
    Attributes:
        baseline_heart_rate (float): Baseline heart rate in beats per minute (BPM)
        variability (float): Natural heart rate variability (standard deviation)
        recovery_rate (float): Rate at which heart rate returns to baseline
        max_heart_rate (float): Maximum possible heart rate
        stress_factor (float): Multiplicative factor for stress responses
        name (str): Name of the biometric signal model
        description (str): Description of what the model represents
        parameters (Dict[str, Parameter]): Dictionary of parameters that influence the signal
        response_factors (Dict[str, float]): Dictionary of response factors for different chemicals/exposures
        uuid (str): Unique identifier for the model instance
        is_active (bool): Whether the model is currently active
        history (List[Tuple[float, float]]): History of signal values (time, value)
    """
    
    def __init__(self, 
                baseline_heart_rate: float = 70.0,
                variability: float = 3.0,
                recovery_rate: float = 0.1,
                max_heart_rate: float = 180.0,
                stress_factor: float = 1.2,
                name: str = "Heart Rate",
                description: str = "Simulated heart rate response to environmental factors and exposures",
                parameters: Optional[Dict[str, Parameter]] = None,
                response_factors: Optional[Dict[str, float]] = None):
        """Initialize the heart rate model.
        
        Args:
            baseline_heart_rate: Baseline heart rate in beats per minute (BPM)
            variability: Natural heart rate variability (standard deviation)
            recovery_rate: Rate at which heart rate returns to baseline
            max_heart_rate: Maximum possible heart rate
            stress_factor: Multiplicative factor for stress responses
            name: Name of the model
            description: Description of what the model represents
            parameters: Optional dictionary of parameters that influence the signal
            response_factors: Optional dictionary of response factors for different chemicals/exposures
        """
        super().__init__(name, description, baseline_heart_rate, parameters, response_factors)
        
        self.baseline_heart_rate = baseline_heart_rate
        self.variability = variability
        self.recovery_rate = recovery_rate
        self.max_heart_rate = max_heart_rate
        self.stress_factor = stress_factor
        
        # Default response factors if none provided
        if not response_factors:
            self.response_factors = {
                "carbon_monoxide": 2.5,  # Strong effect on heart rate
                "benzene": 1.2,
                "formaldehyde": 1.5,
                "nitrogen_dioxide": 1.8,
                "ozone": 1.7,
                "particulate_matter": 1.3,
                "temperature": 0.05,  # Per degree above comfort zone
                "humidity": 0.02,  # Per percent above comfort zone
                "noise": 0.01,  # Per decibel above comfort zone
            }
        
        # Initialize last value for continuity in signal generation
        self.last_value = baseline_heart_rate
        self.last_time = 0.0
    
    def generate_signal(self, 
                       time_point: float, 
                       exposures: Optional[Dict[str, float]] = None, 
                       environmental_conditions: Optional[Dict[str, float]] = None) -> float:
        """Generate a heart rate value for a given time point.
        
        Args:
            time_point: The time point to generate the signal for
            exposures: Optional dictionary of chemical exposures and their concentrations
            environmental_conditions: Optional dictionary of environmental conditions
            
        Returns:
            The generated heart rate value in BPM
        """
        exposures = exposures or {}
        environmental_conditions = environmental_conditions or {}
        
        # Time delta since last generation
        time_delta = time_point - self.last_time if self.last_time is not None else 0.1
        
        # Calculate exposure effect
        exposure_effect = 0.0
        for agent, concentration in exposures.items():
            if agent in self.response_factors:
                effect = concentration * self.response_factors[agent]
                exposure_effect += effect
        
        # Calculate environmental effect
        env_effect = 0.0
        
        # Temperature effect (above 25°C increases heart rate)
        if "temperature" in environmental_conditions:
            temp = environmental_conditions["temperature"]
            if temp > 25.0:
                env_effect += (temp - 25.0) * self.response_factors.get("temperature", 0.05)
        
        # Humidity effect (above 60% increases heart rate)
        if "humidity" in environmental_conditions:
            humidity = environmental_conditions["humidity"]
            if humidity > 60.0:
                env_effect += (humidity - 60.0) * self.response_factors.get("humidity", 0.02)
        
        # Noise effect
        if "noise" in environmental_conditions:
            noise = environmental_conditions["noise"]
            if noise > 70.0:  # Above 70 dB
                env_effect += (noise - 70.0) * self.response_factors.get("noise", 0.01)
        
        # Calculate stress component (can be affected by multiple factors)
        stress_component = (exposure_effect + env_effect) * self.stress_factor
        
        # Apply natural variability with some autocorrelation
        variability_component = random.gauss(0, self.variability)
        
        # Recovery component - heart rate tends to return to baseline
        recovery_component = (self.baseline_heart_rate - self.last_value) * self.recovery_rate * time_delta
        
        # Calculate new heart rate with continuity from previous value
        new_heart_rate = self.last_value + recovery_component + stress_component + variability_component
        
        # Ensure heart rate stays within physiological limits
        new_heart_rate = max(40.0, min(new_heart_rate, self.max_heart_rate))
        
        # Update last values for next generation
        self.last_value = new_heart_rate
        self.last_time = time_point
        
        # Add to history
        self.add_to_history(time_point, new_heart_rate)
        
        return new_heart_rate
    
    def calculate_hrv(self, window_size: int = 20) -> Optional[float]:
        """Calculate heart rate variability (HRV) from recent history.
        
        Args:
            window_size: Number of recent samples to use
            
        Returns:
            Heart rate variability as standard deviation of heart rate, or None if not enough history
        """
        if len(self.history) < window_size:
            return None
        
        recent_values = [value for _, value in self.history[-window_size:]]
        return np.std(recent_values)
    
    def reset(self) -> None:
        """Reset the heart rate model to initial state."""
        self.last_value = self.baseline_heart_rate
        self.last_time = 0.0
        self.reset_history()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        data = super().to_dict()
        data.update({
            "baseline_heart_rate": self.baseline_heart_rate,
            "variability": self.variability,
            "recovery_rate": self.recovery_rate,
            "max_heart_rate": self.max_heart_rate,
            "stress_factor": self.stress_factor,
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HeartRateModel':
        """Create a heart rate model from a dictionary.
        
        Args:
            data: Dictionary containing model data
            
        Returns:
            An instance of HeartRateModel
        """
        # Extract parameters dict and convert to Parameter objects
        parameters = {}
        if "parameters" in data:
            for name, param_data in data["parameters"].items():
                parameters[name] = Parameter.from_dict(param_data)
        
        # Create the model instance
        model = cls(
            baseline_heart_rate=data.get("baseline_heart_rate", 70.0),
            variability=data.get("variability", 3.0),
            recovery_rate=data.get("recovery_rate", 0.1),
            max_heart_rate=data.get("max_heart_rate", 180.0),
            stress_factor=data.get("stress_factor", 1.2),
            name=data.get("name", "Heart Rate"),
            description=data.get("description", "Simulated heart rate response"),
            parameters=parameters,
            response_factors=data.get("response_factors", {})
        )
        
        # Restore other attributes
        model.uuid = data.get("uuid", model.uuid)
        model.is_active = data.get("is_active", True)
        
        return model
