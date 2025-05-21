"""
Respiratory response modeling for chemical exposures.

This module provides the respiratory-specific implementation of the 
physiological response system, focusing on pulmonary responses to 
inhaled chemical exposures.

References:
- Smith et al. (2022): "Dose-Response Relationships for Pulmonary Irritants"
- EPA Guidelines (2023): "Air Pollutant Exposure and Respiratory Effects"
- WHO (2021): "Health Effects of Particulate Matter"
"""

from typing import Dict, List, Optional, Union, Any, Tuple
import datetime
import numpy as np
import math

from envirosense.core.exposure.physiological_response.base import (
    PhysiologicalResponseSystem,
    SystemOutput,
    ResponseSeverityLevel
)


class RespiratoryResponseSystem(PhysiologicalResponseSystem):
    """
    Respiratory-specific response calculation system.
    
    Models respiratory effects of chemical exposures including irritation,
    inflammation, bronchoconstriction, and reduced lung function.
    """
    
    def __init__(
        self,
        name: str = "Respiratory System",
        description: str = "Models respiratory responses to chemical exposures",
        thresholds: Optional[Dict[ResponseSeverityLevel, float]] = None,
        uncertainty: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize a respiratory response system.
        
        Args:
            name: Name of the system
            description: Description of the system
            thresholds: Dictionary mapping severity levels to threshold values
            uncertainty: Uncertainty factor for confidence interval calculation
            metadata: Additional metadata for the system
        """
        # Set default thresholds if not provided
        if thresholds is None:
            thresholds = {
                ResponseSeverityLevel.SUBCLINICAL: 10.0,  # Minimal detectable effect
                ResponseSeverityLevel.MILD: 25.0,         # Mild irritation
                ResponseSeverityLevel.MODERATE: 50.0,     # Noticeable respiratory effects
                ResponseSeverityLevel.SEVERE: 75.0,       # Significant respiratory impairment
                ResponseSeverityLevel.CRITICAL: 90.0      # Severe respiratory distress
            }
        
        super().__init__(
            name=name,
            description=description,
            thresholds=thresholds,
            uncertainty=uncertainty,
            metadata=metadata
        )
        
        # Chemical-specific respiratory response factors
        # Based on literature values for common respiratory irritants
        self.chemical_factors = {
            # Respiratory irritants
            "formaldehyde": 1.5,
            "acrolein": 2.0,
            "ozone": 1.8,
            "chlorine": 2.2,
            "ammonia": 1.4,
            "sulfur_dioxide": 1.6,
            "nitrogen_dioxide": 1.4,
            
            # Particulate matter
            "pm2_5": 1.3,
            "pm10": 1.1,
            
            # VOCs
            "benzene": 0.8,
            "toluene": 0.9,
            "xylene": 1.0,
            
            # Default for unknown chemicals
            "default": 1.0
        }
        
        # Respiratory parameter weights
        self.parameter_weights = {
            "volume": 0.3,      # Inhaled volume
            "duration": 0.3,    # Exposure duration
            "concentration": 0.4 # Chemical concentration
        }
    
    def calculate_response(
        self, 
        exposure_history: Dict[str, Any],
        sensitivity_profile: Optional[Dict[str, Any]] = None
    ) -> SystemOutput:
        """
        Calculate respiratory response based on exposure history.
        
        Args:
            exposure_history: Dictionary containing exposure data
                Must include:
                - chemical_id: ID of the chemical
                - concentration: Chemical concentration
                - duration: Exposure duration
                - inhaled_volume: Optional volume of inhaled air
            sensitivity_profile: Optional dictionary with individual sensitivity factors
                May include:
                - respiratory_sensitivity: General respiratory sensitivity factor
                - respiratory_conditions: List of respiratory conditions
                - age: Age of individual
                
        Returns:
            SystemOutput object with respiratory response metrics
        """
        # Extract exposure parameters
        chemical_id = exposure_history.get("chemical_id", "unknown")
        concentration = exposure_history.get("concentration", 0.0)
        duration = exposure_history.get("duration", 0.0)
        inhaled_volume = exposure_history.get("inhaled_volume", 1.0)
        
        # Get chemical-specific factor
        chemical_factor = self.chemical_factors.get(
            chemical_id.lower(), self.chemical_factors["default"]
        )
        
        # Calculate base response
        volume_factor = self._calculate_volume_factor(inhaled_volume)
        duration_factor = self._calculate_duration_factor(duration)
        concentration_factor = self._calculate_concentration_factor(concentration)
        
        # Apply parameter weights
        weighted_response = (
            volume_factor * self.parameter_weights["volume"] +
            duration_factor * self.parameter_weights["duration"] +
            concentration_factor * self.parameter_weights["concentration"]
        )
        
        # Apply chemical-specific factor
        response_value = weighted_response * chemical_factor
        
        # Apply sensitivity adjustments if available
        if sensitivity_profile:
            response_value = self._apply_sensitivity_adjustments(
                response_value, sensitivity_profile
            )
        
        # Calculate confidence interval
        confidence_interval = self.calculate_confidence_interval(response_value)
        
        # Classify severity
        severity_level = self.classify_severity(response_value)
        
        # Calculate timing information
        onset_time, peak_time, recovery_time = self._calculate_response_timing(
            response_value, chemical_id, exposure_history, sensitivity_profile
        )
        
        # Create metadata
        output_metadata = {
            "chemical_id": chemical_id,
            "chemical_factor": chemical_factor,
            "volume_factor": volume_factor,
            "duration_factor": duration_factor,
            "concentration_factor": concentration_factor,
            "weighted_response": weighted_response,
            "calculation_method": "weighted_parameter_model"
        }
        
        # Create and return the system output
        return SystemOutput(
            response_value=response_value,
            confidence_interval=confidence_interval,
            severity_level=severity_level,
            onset_time=onset_time,
            peak_time=peak_time,
            recovery_time=recovery_time,
            system_type="respiratory",
            metadata=output_metadata
        )
    
    def _calculate_volume_factor(self, inhaled_volume: float) -> float:
        """
        Calculate the factor for inhaled volume.
        
        Args:
            inhaled_volume: Volume of inhaled air in liters
            
        Returns:
            Volume factor (0-100)
        """
        # Apply logarithmic scaling to handle wide range of volumes
        if inhaled_volume <= 0:
            return 0.0
            
        # Normalize to reference volume of 10L
        normalized_volume = inhaled_volume / 10.0
        
        # Apply logarithmic scaling with cap at 100
        return min(100.0, 50.0 * math.log10(1 + normalized_volume))
    
    def _calculate_duration_factor(self, duration: float) -> float:
        """
        Calculate the factor for exposure duration.
        
        Args:
            duration: Exposure duration in hours
            
        Returns:
            Duration factor (0-100)
        """
        if duration <= 0:
            return 0.0
            
        # Apply non-linear scaling that increases more rapidly at first
        # then levels off for very long exposures
        # Based on time to steady-state for most respiratory irritants
        return min(100.0, 100.0 * (1 - math.exp(-0.5 * duration)))
    
    def _calculate_concentration_factor(self, concentration: float) -> float:
        """
        Calculate the factor for chemical concentration.
        
        Args:
            concentration: Chemical concentration in appropriate units
            
        Returns:
            Concentration factor (0-100)
        """
        if concentration <= 0:
            return 0.0
            
        # Apply sigmoidal response curve typical of dose-response relationships
        # This creates an S-shaped curve with steeper response in the middle range
        # and flattening at very low and very high concentrations
        normalized_conc = concentration / 100.0  # Normalize to reference concentration
        return 100.0 / (1 + math.exp(-5 * (normalized_conc - 0.5)))
    
    def _apply_sensitivity_adjustments(
        self,
        response_value: float,
        sensitivity_profile: Dict[str, Any]
    ) -> float:
        """
        Apply individual sensitivity adjustments to the response.
        
        Args:
            response_value: Base response value
            sensitivity_profile: Dictionary with sensitivity information
            
        Returns:
            Adjusted response value
        """
        # Start with the base response
        adjusted_response = response_value
        
        # Apply general respiratory sensitivity factor if available
        respiratory_sensitivity = sensitivity_profile.get("respiratory_sensitivity", 1.0)
        adjusted_response *= respiratory_sensitivity
        
        # Apply age-based adjustment if available
        if "age" in sensitivity_profile:
            age = sensitivity_profile["age"]
            
            # Children and elderly have higher respiratory sensitivity
            if age < 12:
                # Children have 20-50% higher sensitivity depending on age
                age_factor = 1.5 - (0.025 * age)  # 1.5 at age 0, decreasing to 1.2 at age 12
                adjusted_response *= age_factor
            elif age > 65:
                # Elderly have increasing sensitivity with age
                age_factor = 1.0 + (0.01 * (age - 65))  # Increases by 1% per year over 65
                adjusted_response *= age_factor
        
        # Apply condition-based adjustments
        respiratory_conditions = sensitivity_profile.get("respiratory_conditions", [])
        for condition in respiratory_conditions:
            condition_factor = 1.0
            
            # Apply specific condition adjustments
            if condition.lower() == "asthma":
                condition_factor = 1.8
            elif condition.lower() in ["copd", "chronic obstructive pulmonary disease"]:
                condition_factor = 1.6
            elif condition.lower() == "emphysema":
                condition_factor = 1.7
            elif condition.lower() in ["bronchitis", "chronic bronchitis"]:
                condition_factor = 1.5
            elif condition.lower() == "allergic rhinitis":
                condition_factor = 1.3
            else:
                # Default factor for other respiratory conditions
                condition_factor = 1.2
                
            adjusted_response *= condition_factor
        
        return adjusted_response
    
    def _calculate_response_timing(
        self,
        response_value: float,
        chemical_id: str,
        exposure_history: Dict[str, Any],
        sensitivity_profile: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[datetime.timedelta], 
                Optional[datetime.timedelta], 
                Optional[datetime.timedelta]]:
        """
        Calculate timing information for the respiratory response.
        
        Args:
            response_value: Calculated response value
            chemical_id: ID of the chemical
            exposure_history: Dictionary containing exposure data
            sensitivity_profile: Optional sensitivity profile
            
        Returns:
            Tuple of (onset_time, peak_time, recovery_time)
        """
        # Default timing values (in minutes)
        default_onset = 15.0
        default_peak = 60.0
        default_recovery = 240.0
        
        # Chemical-specific timing adjustments
        chemical_timing = {
            # Fast-acting irritants
            "chlorine": (5.0, 30.0, 360.0),
            "ammonia": (5.0, 30.0, 240.0),
            "sulfur_dioxide": (10.0, 45.0, 300.0),
            
            # Moderate-onset irritants
            "ozone": (15.0, 60.0, 360.0),
            "nitrogen_dioxide": (20.0, 90.0, 480.0),
            "formaldehyde": (10.0, 60.0, 360.0),
            
            # Slower-onset chemicals
            "benzene": (60.0, 180.0, 720.0),
            "toluene": (45.0, 150.0, 600.0),
            "xylene": (45.0, 150.0, 600.0),
        }
        
        # Get chemical-specific timing if available
        onset, peak, recovery = chemical_timing.get(
            chemical_id.lower(), (default_onset, default_peak, default_recovery)
        )
        
        # Adjust timing based on response severity
        # More severe responses typically have faster onset and longer recovery
        severity_adjustment = response_value / 50.0  # Normalized to typical moderate response
        onset /= max(0.5, min(2.0, severity_adjustment))  # Faster onset for severe responses
        recovery *= max(0.5, min(3.0, severity_adjustment))  # Longer recovery for severe responses
        
        # Apply sensitivity adjustments if available
        if sensitivity_profile:
            # Pre-existing conditions can speed onset and extend recovery
            if "respiratory_conditions" in sensitivity_profile and sensitivity_profile["respiratory_conditions"]:
                onset *= 0.7  # 30% faster onset
                recovery *= 1.5  # 50% longer recovery
        
        # Convert to timedelta objects
        onset_time = datetime.timedelta(minutes=onset)
        peak_time = datetime.timedelta(minutes=peak)
        recovery_time = datetime.timedelta(minutes=recovery)
        
        return onset_time, peak_time, recovery_time
