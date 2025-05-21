"""
Skin Conductance Biometric Signal Model

This module provides skin conductance (electrodermal activity) signal generation capabilities,
simulating how skin conductance responds to environmental factors, stress, and chemical exposures.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
import math
import random

from envirosense.core.time_series.parameters import Parameter
from envirosense.core.biometrics.base import BiometricSignalModel


class SkinConductanceModel(BiometricSignalModel):
    """Skin conductance (electrodermal activity) biometric signal model.
    
    This class simulates skin conductance responses to environmental conditions, stress,
    and chemical exposures, providing realistic electrodermal activity patterns with
    appropriate variability.
    
    Attributes:
        baseline_conductance (float): Baseline skin conductance in microSiemens (µS)
        variability (float): Natural skin conductance variability (standard deviation)
        recovery_rate (float): Rate at which conductance returns to baseline
        max_conductance (float): Maximum possible skin conductance
        stress_sensitivity (float): Multiplicative factor for stress responses
        name (str): Name of the biometric signal model
        description (str): Description of what the model represents
        parameters (Dict[str, Parameter]): Dictionary of parameters that influence the signal
        response_factors (Dict[str, float]): Dictionary of response factors for different chemicals/exposures
        uuid (str): Unique identifier for the model instance
        is_active (bool): Whether the model is currently active
        history (List[Tuple[float, float]]): History of signal values (time, value)
    """
    
    def __init__(self, 
                baseline_conductance: float = 2.0,
                variability: float = 0.3,
                recovery_rate: float = 0.05,
                max_conductance: float = 25.0,
                stress_sensitivity: float = 1.5,
                name: str = "Skin Conductance",
                description: str = "Simulated skin conductance response to environmental factors and stress",
                parameters: Optional[Dict[str, Parameter]] = None,
                response_factors: Optional[Dict[str, float]] = None):
        """Initialize the skin conductance model.
        
        Args:
            baseline_conductance: Baseline skin conductance in microSiemens (µS)
            variability: Natural skin conductance variability (standard deviation)
            recovery_rate: Rate at which conductance returns to baseline
            max_conductance: Maximum possible skin conductance
            stress_sensitivity: Multiplicative factor for stress responses
            name: Name of the model
            description: Description of what the model represents
            parameters: Optional dictionary of parameters that influence the signal
            response_factors: Optional dictionary of response factors for different chemicals/exposures
        """
        super().__init__(name, description, baseline_conductance, parameters, response_factors)
        
        self.baseline_conductance = baseline_conductance
        self.variability = variability
        self.recovery_rate = recovery_rate
        self.max_conductance = max_conductance
        self.stress_sensitivity = stress_sensitivity
        
        # Default response factors if none provided
        if not response_factors:
            self.response_factors = {
                "carbon_monoxide": 1.2,  # Moderate effect on skin conductance 
                "benzene": 0.8,
                "formaldehyde": 1.1,
                "nitrogen_dioxide": 1.3,
                "ozone": 1.4,
                "particulate_matter": 0.7,
                "temperature": 0.15,   # Per degree above comfort zone
                "humidity": 0.03,      # Per percent above comfort zone
                "noise": 0.02,         # Per decibel above comfort zone
                "stress": 2.0,         # Strong effect from stress
                "anxiety": 2.5,        # Very strong effect from anxiety
            }
        
        # State variables for SCR generation
        self.last_value = baseline_conductance
        self.last_time = 0.0
        self.scr_in_progress = False
        self.scr_start_time = 0.0
        self.scr_amplitude = 0.0
        self.tonic_level = baseline_conductance
    
    def generate_signal(self, 
                       time_point: float, 
                       exposures: Optional[Dict[str, float]] = None, 
                       environmental_conditions: Optional[Dict[str, float]] = None,
                       stress_level: float = 0.0,
                       trigger_scr: bool = False) -> float:
        """Generate a skin conductance value for a given time point.
        
        Args:
            time_point: The time point to generate the signal for
            exposures: Optional dictionary of chemical exposures and their concentrations
            environmental_conditions: Optional dictionary of environmental conditions
            stress_level: Optional stress level (0.0 to 1.0)
            trigger_scr: Whether to trigger a skin conductance response at this time point
            
        Returns:
            The generated skin conductance value in microSiemens (µS)
        """
        exposures = exposures or {}
        environmental_conditions = environmental_conditions or {}
        
        # Time delta since last generation
        time_delta = time_point - self.last_time if self.last_time is not None else 0.1
        
        # Calculate exposure effect
        exposure_effect = 0.0
        for agent, concentration in exposures.items():
            if agent in self.response_factors:
                effect = concentration * self.response_factors[agent] * 0.1
                exposure_effect += effect
        
        # Calculate environmental effect
        env_effect = 0.0
        
        # Temperature effect (above 28°C increases conductance due to sweating)
        if "temperature" in environmental_conditions:
            temp = environmental_conditions["temperature"]
            if temp > 28.0:
                env_effect += (temp - 28.0) * self.response_factors.get("temperature", 0.15)
        
        # Humidity effect (above 70% increases conductance)
        if "humidity" in environmental_conditions:
            humidity = environmental_conditions["humidity"]
            if humidity > 70.0:
                env_effect += (humidity - 70.0) * self.response_factors.get("humidity", 0.03)
        
        # Noise effect (above 75 dB)
        if "noise" in environmental_conditions:
            noise = environmental_conditions["noise"]
            if noise > 75.0:
                env_effect += (noise - 75.0) * self.response_factors.get("noise", 0.02)
        
        # Calculate stress component
        stress_component = 0.0
        if stress_level > 0:
            # Apply stress response factor
            stress_component = stress_level * self.response_factors.get("stress", 2.0)
        
        # Combined arousal effect (from exposures, environment, and stress)
        arousal_effect = (exposure_effect + env_effect + stress_component) * self.stress_sensitivity
        
        # Update tonic level (slow-changing baseline)
        tonic_change = (self.baseline_conductance - self.tonic_level) * self.recovery_rate * time_delta
        tonic_change += arousal_effect * 0.2  # Arousal has some effect on tonic level
        self.tonic_level += tonic_change
        
        # Generate Skin Conductance Response (SCR) if triggered or by random chance
        scr_component = 0.0
        
        # Start a new SCR if triggered or randomly based on arousal
        scr_probability = 0.01 + (arousal_effect * 0.05)  # Base probability plus arousal influence
        if trigger_scr or (not self.scr_in_progress and random.random() < scr_probability * time_delta):
            self.scr_in_progress = True
            self.scr_start_time = time_point
            
            # SCR amplitude depends on arousal
            base_amplitude = 0.5 + (random.random() * 0.5)  # Base amplitude 0.5-1.0 µS
            self.scr_amplitude = base_amplitude * (1.0 + arousal_effect)
            
        # Calculate SCR component if in progress
        if self.scr_in_progress:
            scr_elapsed = time_point - self.scr_start_time
            
            # SCR shape follows a characteristic pattern (rapid rise, slow decay)
            if scr_elapsed < 1.0:  # Rising phase (~1 second)
                scr_component = self.scr_amplitude * (scr_elapsed / 1.0)
            else:  # Decay phase
                decay_constant = 3.0  # Time constant for decay
                scr_component = self.scr_amplitude * math.exp(-(scr_elapsed - 1.0) / decay_constant)
                
                # End SCR if amplitude is very small
                if scr_component < 0.05:
                    self.scr_in_progress = False
        
        # Apply natural variability with some autocorrelation
        variability_component = random.gauss(0, self.variability * (0.1 + 0.9 * (self.tonic_level / self.baseline_conductance)))
        
        # Calculate new skin conductance
        new_conductance = self.tonic_level + scr_component + variability_component
        
        # Ensure skin conductance stays within physiological limits
        new_conductance = max(0.5, min(new_conductance, self.max_conductance))
        
        # Update last values for next generation
        self.last_value = new_conductance
        self.last_time = time_point
        
        # Add to history
        self.add_to_history(time_point, new_conductance)
        
        return new_conductance
    
    def generate_scr_response(self, time_point: float, intensity: float = 1.0) -> float:
        """Generate a specific skin conductance response (SCR) at a given time point.
        
        Args:
            time_point: The time point to generate the SCR
            intensity: Intensity factor for the SCR (1.0 is normal)
            
        Returns:
            The generated skin conductance value after adding the SCR
        """
        return self.generate_signal(time_point, trigger_scr=True, stress_level=intensity * 0.5)
    
    def calculate_scr_frequency(self, window_size: int = 60) -> Optional[float]:
        """Calculate SCR frequency (number of significant responses per minute) from recent history.
        
        Args:
            window_size: Number of recent seconds to analyze
            
        Returns:
            SCR frequency as responses per minute, or None if not enough history
        """
        if len(self.history) < 10:
            return None
        
        # Get the data for the window
        recent_times = []
        recent_values = []
        
        current_time = self.history[-1][0]
        window_start = current_time - window_size
        
        for t, v in self.history:
            if t >= window_start:
                recent_times.append(t)
                recent_values.append(v)
        
        if len(recent_values) < 10:
            return None
        
        # Convert to numpy arrays
        times = np.array(recent_times)
        values = np.array(recent_values)
        
        # Calculate first derivative to find rapid increases
        dvalues = np.diff(values)
        dtimes = np.diff(times)
        derivatives = dvalues / dtimes
        
        # Count significant SCRs (where derivative exceeds threshold)
        threshold = 0.1  # µS/second
        scr_count = np.sum(derivatives > threshold)
        
        # Calculate frequency (responses per minute)
        window_duration_minutes = window_size / 60.0
        scr_frequency = scr_count / window_duration_minutes
        
        return scr_frequency
    
    def reset(self) -> None:
        """Reset the skin conductance model to initial state."""
        self.last_value = self.baseline_conductance
        self.last_time = 0.0
        self.tonic_level = self.baseline_conductance
        self.scr_in_progress = False
        self.reset_history()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        data = super().to_dict()
        data.update({
            "baseline_conductance": self.baseline_conductance,
            "variability": self.variability,
            "recovery_rate": self.recovery_rate,
            "max_conductance": self.max_conductance,
            "stress_sensitivity": self.stress_sensitivity,
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkinConductanceModel':
        """Create a skin conductance model from a dictionary.
        
        Args:
            data: Dictionary containing model data
            
        Returns:
            An instance of SkinConductanceModel
        """
        # Extract parameters dict and convert to Parameter objects
        parameters = {}
        if "parameters" in data:
            for name, param_data in data["parameters"].items():
                parameters[name] = Parameter.from_dict(param_data)
        
        # Create the model instance
        model = cls(
            baseline_conductance=data.get("baseline_conductance", 2.0),
            variability=data.get("variability", 0.3),
            recovery_rate=data.get("recovery_rate", 0.05),
            max_conductance=data.get("max_conductance", 25.0),
            stress_sensitivity=data.get("stress_sensitivity", 1.5),
            name=data.get("name", "Skin Conductance"),
            description=data.get("description", "Simulated skin conductance response"),
            parameters=parameters,
            response_factors=data.get("response_factors", {})
        )
        
        # Restore other attributes
        model.uuid = data.get("uuid", model.uuid)
        model.is_active = data.get("is_active", True)
        
        return model
