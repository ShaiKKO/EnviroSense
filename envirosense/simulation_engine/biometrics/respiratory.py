"""
Respiratory Biometric Signal Model

This module provides respiratory signal generation capabilities,
simulating how breathing rate and volume respond to environmental factors, stress, and chemical exposures.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
import math
import random

from envirosense.core.time_series.parameters import Parameter
from envirosense.core.biometrics.base import BiometricSignalModel


class RespiratoryModel(BiometricSignalModel):
    """Respiratory biometric signal model.
    
    This class simulates respiratory responses to environmental conditions, stress,
    and chemical exposures, providing realistic breathing patterns with appropriate variability.
    
    Attributes:
        baseline_rate (float): Baseline breathing rate in breaths per minute (BPM)
        baseline_volume (float): Baseline tidal volume in liters (L)
        rate_variability (float): Natural variability in breathing rate (standard deviation)
        volume_variability (float): Natural variability in tidal volume (standard deviation)
        recovery_rate (float): Rate at which breathing returns to baseline
        max_rate (float): Maximum possible breathing rate
        min_rate (float): Minimum possible breathing rate
        max_volume (float): Maximum possible tidal volume
        min_volume (float): Minimum possible tidal volume
        chemical_sensitivity (float): Multiplicative factor for sensitivity to chemicals
        name (str): Name of the biometric signal model
        description (str): Description of what the model represents
        parameters (Dict[str, Parameter]): Dictionary of parameters that influence the signal
        response_factors (Dict[str, float]): Dictionary of response factors for different chemicals/exposures
        uuid (str): Unique identifier for the model instance
        is_active (bool): Whether the model is currently active
        history (List[Tuple[float, Dict]]): History of signal values (time, values)
    """
    
    def __init__(self, 
                baseline_rate: float = 16.0,
                baseline_volume: float = 0.5,
                rate_variability: float = 1.0,
                volume_variability: float = 0.05,
                recovery_rate: float = 0.1,
                max_rate: float = 40.0,
                min_rate: float = 6.0,
                max_volume: float = 1.5,
                min_volume: float = 0.2,
                chemical_sensitivity: float = 1.2,
                name: str = "Respiratory",
                description: str = "Simulated respiratory response to environmental factors and chemical exposures",
                parameters: Optional[Dict[str, Parameter]] = None,
                response_factors: Optional[Dict[str, float]] = None):
        """Initialize the respiratory model.
        
        Args:
            baseline_rate: Baseline breathing rate in breaths per minute
            baseline_volume: Baseline tidal volume in liters
            rate_variability: Natural variability in breathing rate (standard deviation)
            volume_variability: Natural variability in tidal volume (standard deviation)
            recovery_rate: Rate at which breathing returns to baseline
            max_rate: Maximum possible breathing rate
            min_rate: Minimum possible breathing rate
            max_volume: Maximum possible tidal volume
            min_volume: Minimum possible tidal volume
            chemical_sensitivity: Multiplicative factor for sensitivity to chemicals
            name: Name of the model
            description: Description of what the model represents
            parameters: Optional dictionary of parameters that influence the signal
            response_factors: Optional dictionary of response factors for different chemicals/exposures
        """
        super().__init__(name, description, baseline_rate, parameters, response_factors)
        
        self.baseline_rate = baseline_rate
        self.baseline_volume = baseline_volume
        self.rate_variability = rate_variability
        self.volume_variability = volume_variability
        self.recovery_rate = recovery_rate
        self.max_rate = max_rate
        self.min_rate = min_rate
        self.max_volume = max_volume
        self.min_volume = min_volume
        self.chemical_sensitivity = chemical_sensitivity
        
        # Default response factors if none provided
        if not response_factors:
            self.response_factors = {
                "carbon_monoxide": 1.8,    # Strong effect - increases breathing rate
                "benzene": 0.9,            # Mild effect
                "formaldehyde": 1.5,       # Moderate-strong effect - irritant
                "nitrogen_dioxide": 1.7,   # Strong effect - respiratory irritant
                "ozone": 1.6,              # Strong effect - respiratory irritant
                "particulate_matter": 1.4, # Moderate effect
                "temperature": 0.05,       # Per degree above comfort zone
                "humidity": 0.02,          # Per percent above comfort zone
                "altitude": 0.1,           # Per 100m above sea level
                "smoke": 2.0,              # Very strong effect
                "exercise": 0.15           # Per unit of exercise intensity
            }
        
        # State variables
        self.current_rate = baseline_rate
        self.current_volume = baseline_volume
        self.last_time = 0.0
        self.breathing_phase = 0.0  # 0 to 2π for breathing cycle
        self.breathing_pattern = "normal"  # normal, labored, rapid-shallow, etc.
        self.distress_level = 0.0  # 0 to 1.0 for respiratory distress
        self.breath_hold = False
        self.breath_hold_start_time = 0.0
        self.breath_hold_duration = 0.0
    
    def generate_signal(self, 
                      time_point: float, 
                      exposures: Optional[Dict[str, float]] = None, 
                      environmental_conditions: Optional[Dict[str, float]] = None,
                      exercise_level: float = 0.0,
                      distress_level: Optional[float] = None) -> Dict[str, float]:
        """Generate respiratory values for a given time point.
        
        Args:
            time_point: The time point to generate the signal for
            exposures: Optional dictionary of chemical exposures and their concentrations
            environmental_conditions: Optional dictionary of environmental conditions
            exercise_level: Optional exercise intensity (0.0 to 1.0)
            distress_level: Optional respiratory distress level (0.0 to 1.0)
            
        Returns:
            Dictionary containing respiratory values:
                - rate: Breathing rate in breaths per minute
                - volume: Tidal volume in liters
                - minute_volume: Minute ventilation (rate * volume) in liters per minute
                - phase: Current phase in breathing cycle (0 to 2π)
                - pattern: Current breathing pattern
                - distress: Current respiratory distress level
        """
        exposures = exposures or {}
        environmental_conditions = environmental_conditions or {}
        
        # Time delta since last generation
        time_delta = time_point - self.last_time if self.last_time is not None else 0.1
        
        # If distress level is provided, update the model's distress level
        if distress_level is not None:
            self.distress_level = max(0.0, min(1.0, distress_level))
        
        # Calculate exposure effect
        exposure_effect_rate = 0.0
        exposure_effect_volume = 0.0
        
        for agent, concentration in exposures.items():
            if agent in self.response_factors:
                # Different chemicals affect rate and volume differently
                factor = self.response_factors.get(agent, 1.0)
                if agent in ["carbon_monoxide", "nitrogen_dioxide", "ozone"]:
                    # These primarily increase rate (hypoxic drive)
                    effect_rate = concentration * factor * 0.3 * self.chemical_sensitivity
                    effect_volume = concentration * factor * 0.1 * self.chemical_sensitivity
                elif agent in ["formaldehyde", "particulate_matter", "smoke"]:
                    # These cause rapid, shallow breathing
                    effect_rate = concentration * factor * 0.3 * self.chemical_sensitivity
                    effect_volume = -concentration * factor * 0.1 * self.chemical_sensitivity
                else:
                    # Default effect
                    effect_rate = concentration * factor * 0.2 * self.chemical_sensitivity
                    effect_volume = concentration * factor * 0.05 * self.chemical_sensitivity
                
                exposure_effect_rate += effect_rate
                exposure_effect_volume += effect_volume
        
        # Calculate environmental effect
        env_effect_rate = 0.0
        env_effect_volume = 0.0
        
        # Temperature effect (above 30°C increases rate, decreases volume)
        if "temperature" in environmental_conditions:
            temp = environmental_conditions["temperature"]
            if temp > 30.0:
                env_effect_rate += (temp - 30.0) * self.response_factors.get("temperature", 0.05)
                env_effect_volume -= (temp - 30.0) * 0.01  # Slight decrease in volume
        
        # Humidity effect (above 80% affects breathing)
        if "humidity" in environmental_conditions:
            humidity = environmental_conditions["humidity"]
            if humidity > 80.0:
                env_effect_rate += (humidity - 80.0) * self.response_factors.get("humidity", 0.02)
        
        # Altitude effect (increases rate, decreases volume)
        if "altitude" in environmental_conditions:
            altitude = environmental_conditions["altitude"]
            altitude_effect = (altitude / 100.0) * self.response_factors.get("altitude", 0.1)
            env_effect_rate += altitude_effect
            env_effect_volume -= altitude_effect * 0.05
        
        # Exercise effect (major impact on breathing)
        exercise_effect_rate = 0.0
        exercise_effect_volume = 0.0
        
        if exercise_level > 0.0:
            exercise_effect_rate = exercise_level * 20.0 * self.response_factors.get("exercise", 0.15)
            exercise_effect_volume = exercise_level * 0.8  # Significant increase in volume
        
        # Distress effect (based on current distress level)
        distress_effect_rate = 0.0
        distress_effect_volume = 0.0
        
        if self.distress_level > 0.0:
            if self.distress_level < 0.3:
                # Mild distress: slight increase in rate
                distress_effect_rate = self.distress_level * 10.0
                distress_effect_volume = self.distress_level * 0.2
            elif self.distress_level < 0.7:
                # Moderate distress: increased rate, slight decrease in volume
                distress_effect_rate = self.distress_level * 15.0
                distress_effect_volume = -self.distress_level * 0.1
            else:
                # Severe distress: rapid, shallow breathing
                distress_effect_rate = self.distress_level * 20.0
                distress_effect_volume = -self.distress_level * 0.3
        
        # Combined effects
        rate_change = (exposure_effect_rate + env_effect_rate + exercise_effect_rate + distress_effect_rate)
        volume_change = (exposure_effect_volume + env_effect_volume + exercise_effect_volume + distress_effect_volume)
        
        # Apply recovery toward baseline
        recovery_factor = self.recovery_rate * time_delta
        rate_recovery = (self.baseline_rate - self.current_rate) * recovery_factor
        volume_recovery = (self.baseline_volume - self.current_volume) * recovery_factor
        
        # Calculate new rate and volume
        new_rate = self.current_rate + rate_change + rate_recovery
        new_volume = self.current_volume + volume_change + volume_recovery
        
        # Apply natural variability
        rate_variability = random.gauss(0, self.rate_variability)
        volume_variability = random.gauss(0, self.volume_variability)
        
        new_rate += rate_variability
        new_volume += volume_variability
        
        # Ensure values stay within physiological limits
        new_rate = max(self.min_rate, min(new_rate, self.max_rate))
        new_volume = max(self.min_volume, min(new_volume, self.max_volume))
        
        # Update breathing phase
        if not self.breath_hold:
            # Calculate phase progression based on rate
            # One complete breathing cycle per breath
            cycle_duration = 60.0 / new_rate  # seconds per breath
            phase_change = (2 * math.pi) * (time_delta / cycle_duration)
            self.breathing_phase = (self.breathing_phase + phase_change) % (2 * math.pi)
        else:
            # Handle breath holding
            if time_point - self.breath_hold_start_time >= self.breath_hold_duration:
                self.breath_hold = False
        
        # Determine breathing pattern
        if distress_level is not None and distress_level > 0.7:
            self.breathing_pattern = "labored"
        elif new_rate > 25.0 and new_volume < 0.4:
            self.breathing_pattern = "rapid-shallow"
        elif new_rate > 25.0:
            self.breathing_pattern = "rapid"
        elif new_rate < 10.0:
            self.breathing_pattern = "slow"
        else:
            self.breathing_pattern = "normal"
        
        # Calculate minute ventilation (L/min)
        minute_volume = new_rate * new_volume
        
        # Update current values
        self.current_rate = new_rate
        self.current_volume = new_volume
        self.last_time = time_point
        
        # Create result dictionary
        result = {
            "rate": new_rate,
            "volume": new_volume,
            "minute_volume": minute_volume,
            "phase": self.breathing_phase,
            "pattern": self.breathing_pattern,
            "distress": self.distress_level
        }
        
        # Add to history
        self.add_to_history(time_point, result)
        
        return result
    
    def start_breath_hold(self, time_point: float, duration: float = 15.0) -> None:
        """Simulate holding breath for a specified duration.
        
        Args:
            time_point: The time point to start holding breath
            duration: How long to hold breath in seconds
        """
        self.breath_hold = True
        self.breath_hold_start_time = time_point
        self.breath_hold_duration = duration
    
    def set_distress(self, level: float) -> None:
        """Set the respiratory distress level.
        
        Args:
            level: Distress level from 0.0 (none) to 1.0 (severe)
        """
        self.distress_level = max(0.0, min(1.0, level))
    
    def calculate_lung_capacity_used(self) -> float:
        """Calculate the percentage of total lung capacity currently being used.
        
        Returns:
            Percentage of lung capacity (0.0 to 1.0)
        """
        # Base calculation on tidal volume relative to total lung capacity
        # Average total lung capacity is around 6 liters
        total_capacity = 6.0
        capacity_used = self.current_volume / total_capacity
        return capacity_used
    
    def calculate_respiratory_efficiency(self) -> float:
        """Calculate the current respiratory efficiency based on rate and volume.
        
        Returns:
            Efficiency score (0.0 to 1.0)
        """
        # Optimal breathing is around 12-16 breaths per minute with good volume
        rate_efficiency = 1.0 - min(1.0, abs(self.current_rate - 14.0) / 10.0)
        volume_efficiency = self.current_volume / self.max_volume
        
        # Combined efficiency with rate having more weight
        efficiency = (0.7 * rate_efficiency) + (0.3 * volume_efficiency)
        
        # Distress reduces efficiency
        efficiency *= (1.0 - self.distress_level * 0.8)
        
        return max(0.0, min(1.0, efficiency))
    
    def reset(self) -> None:
        """Reset the respiratory model to initial state."""
        self.current_rate = self.baseline_rate
        self.current_volume = self.baseline_volume
        self.last_time = 0.0
        self.breathing_phase = 0.0
        self.breathing_pattern = "normal"
        self.distress_level = 0.0
        self.breath_hold = False
        self.reset_history()
    
    def add_to_history(self, time_point: float, values: Dict[str, Any]) -> None:
        """Add a data point to the signal history.
        
        Override the base method to handle dictionary values.
        
        Args:
            time_point: Time point for the data
            values: Dictionary of respiratory values
        """
        self.history.append((time_point, values))
        
        # Keep history size manageable
        if len(self.history) > self.max_history_size:
            self.history = self.history[-self.max_history_size:]
    
    def get_rate_history(self) -> List[Tuple[float, float]]:
        """Get the history of breathing rates.
        
        Returns:
            List of (time, rate) tuples
        """
        return [(t, v["rate"]) for t, v in self.history]
    
    def get_volume_history(self) -> List[Tuple[float, float]]:
        """Get the history of tidal volumes.
        
        Returns:
            List of (time, volume) tuples
        """
        return [(t, v["volume"]) for t, v in self.history]
    
    def get_minute_volume_history(self) -> List[Tuple[float, float]]:
        """Get the history of minute ventilation values.
        
        Returns:
            List of (time, minute_volume) tuples
        """
        return [(t, v["minute_volume"]) for t, v in self.history]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        data = super().to_dict()
        data.update({
            "baseline_rate": self.baseline_rate,
            "baseline_volume": self.baseline_volume,
            "rate_variability": self.rate_variability,
            "volume_variability": self.volume_variability,
            "recovery_rate": self.recovery_rate,
            "max_rate": self.max_rate,
            "min_rate": self.min_rate,
            "max_volume": self.max_volume,
            "min_volume": self.min_volume,
            "chemical_sensitivity": self.chemical_sensitivity,
            "breathing_pattern": self.breathing_pattern,
            "distress_level": self.distress_level,
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RespiratoryModel':
        """Create a respiratory model from a dictionary.
        
        Args:
            data: Dictionary containing model data
            
        Returns:
            An instance of RespiratoryModel
        """
        # Extract parameters dict and convert to Parameter objects
        parameters = {}
        if "parameters" in data:
            for name, param_data in data["parameters"].items():
                parameters[name] = Parameter.from_dict(param_data)
        
        # Create the model instance
        model = cls(
            baseline_rate=data.get("baseline_rate", 16.0),
            baseline_volume=data.get("baseline_volume", 0.5),
            rate_variability=data.get("rate_variability", 1.0),
            volume_variability=data.get("volume_variability", 0.05),
            recovery_rate=data.get("recovery_rate", 0.1),
            max_rate=data.get("max_rate", 40.0),
            min_rate=data.get("min_rate", 6.0),
            max_volume=data.get("max_volume", 1.5),
            min_volume=data.get("min_volume", 0.2),
            chemical_sensitivity=data.get("chemical_sensitivity", 1.2),
            name=data.get("name", "Respiratory"),
            description=data.get("description", "Simulated respiratory response"),
            parameters=parameters,
            response_factors=data.get("response_factors", {})
        )
        
        # Restore other attributes
        model.uuid = data.get("uuid", model.uuid)
        model.is_active = data.get("is_active", True)
        model.distress_level = data.get("distress_level", 0.0)
        model.breathing_pattern = data.get("breathing_pattern", "normal")
        
        return model
