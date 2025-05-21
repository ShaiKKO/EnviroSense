"""
Neurological response modeling for chemical exposures.

This module provides the neurological-specific implementation of the 
physiological response system, focusing on central and peripheral
nervous system responses to chemical exposures.

References:
- Grandjean et al. (2022): "Neurotoxicity of Chemical Pollutants"
- EPA Neurotoxicity Guidelines (2024): "Evaluating Neurotoxic Effects"
- WHO (2023): "Neurological Health Effects of Environmental Exposures"
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


class NeurologicalResponseSystem(PhysiologicalResponseSystem):
    """
    Neurological-specific response calculation system.
    
    Models neurological effects of chemical exposures including headaches,
    cognitive impairment, dizziness, and neuropathy.
    """
    
    def __init__(
        self,
        name: str = "Neurological System",
        description: str = "Models neurological responses to chemical exposures",
        thresholds: Optional[Dict[ResponseSeverityLevel, float]] = None,
        uncertainty: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize a neurological response system.
        
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
                ResponseSeverityLevel.SUBCLINICAL: 12.0,  # Minimal neurological effects
                ResponseSeverityLevel.MILD: 30.0,         # Mild headache, minor cognitive effects
                ResponseSeverityLevel.MODERATE: 55.0,     # Significant headache, cognitive impairment
                ResponseSeverityLevel.SEVERE: 80.0,       # Severe neurological symptoms
                ResponseSeverityLevel.CRITICAL: 95.0      # Life-threatening neurological effects
            }
        
        super().__init__(
            name=name,
            description=description,
            thresholds=thresholds,
            uncertainty=uncertainty or 0.25,  # Higher uncertainty for neurological effects
            metadata=metadata
        )
        
        # Chemical-specific neurological response factors
        # Based on literature values for common neurotoxic chemicals
        self.chemical_factors = {
            # Solvents and VOCs
            "benzene": 1.3,
            "toluene": 1.7,
            "xylene": 1.5,
            "styrene": 1.6,
            "n-hexane": 1.8,
            
            # Heavy metals
            "lead": 2.2,
            "mercury": 2.5,
            "arsenic": 1.9,
            "manganese": 2.0,
            
            # Organophosphates and pesticides
            "chlorpyrifos": 2.3,
            "parathion": 2.2,
            "glyphosate": 0.9,
            
            # Other industrial chemicals
            "carbon_monoxide": 1.5,
            "hydrogen_sulfide": 1.8,
            "carbon_disulfide": 1.9,
            "ethanol": 1.1,
            "formaldehyde": 1.0,
            
            # Default for unknown chemicals
            "default": 1.0
        }
        
        # Neurological parameter weights
        self.parameter_weights = {
            "peak_concentration": 0.5,   # Peak concentration is most important
            "duration": 0.3,             # Duration of exposure
            "cumulative_dose": 0.2       # Total absorbed dose
        }
        
        # Brain region specific sensitivities
        self.region_sensitivities = {
            "hippocampus": 1.5,          # Memory function
            "frontal_cortex": 1.3,        # Executive function
            "cerebellum": 1.2,           # Motor coordination
            "brain_stem": 1.8,           # Vital functions
            "peripheral_nerves": 1.4      # Sensory function
        }
    
    def calculate_response(
        self, 
        exposure_history: Dict[str, Any],
        sensitivity_profile: Optional[Dict[str, Any]] = None
    ) -> SystemOutput:
        """
        Calculate neurological response based on exposure history.
        
        Args:
            exposure_history: Dictionary containing exposure data
                Must include:
                - chemical_id: ID of the chemical
                - concentration: Chemical concentration
                - duration: Exposure duration
                - peak_concentration: Optional peak concentration
                - cumulative_dose: Optional cumulative dose
            sensitivity_profile: Optional dictionary with individual sensitivity factors
                May include:
                - neurological_sensitivity: General neurological sensitivity
                - neurological_conditions: List of pre-existing conditions
                - age: Age of individual
                - blood_brain_barrier_factor: Blood-brain barrier permeability factor
                
        Returns:
            SystemOutput object with neurological response metrics
        """
        # Extract exposure parameters
        chemical_id = exposure_history.get("chemical_id", "unknown")
        concentration = exposure_history.get("concentration", 0.0)
        duration = exposure_history.get("duration", 0.0)
        peak_concentration = exposure_history.get("peak_concentration", concentration)
        cumulative_dose = exposure_history.get("cumulative_dose", concentration * duration)
        
        # Get chemical-specific factor
        chemical_factor = self.chemical_factors.get(
            chemical_id.lower(), self.chemical_factors["default"]
        )
        
        # Calculate blood-brain barrier penetration factor
        bbb_factor = self._calculate_blood_brain_barrier_factor(
            chemical_id, sensitivity_profile
        )
        
        # Calculate base response components
        peak_factor = self._calculate_peak_factor(peak_concentration)
        duration_factor = self._calculate_duration_factor(duration)
        cumulative_factor = self._calculate_cumulative_factor(cumulative_dose)
        
        # Apply parameter weights
        weighted_response = (
            peak_factor * self.parameter_weights["peak_concentration"] +
            duration_factor * self.parameter_weights["duration"] +
            cumulative_factor * self.parameter_weights["cumulative_dose"]
        )
        
        # Apply chemical-specific and BBB factors
        response_value = weighted_response * chemical_factor * bbb_factor
        
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
            "blood_brain_barrier_factor": bbb_factor,
            "peak_factor": peak_factor,
            "duration_factor": duration_factor,
            "cumulative_factor": cumulative_factor,
            "weighted_response": weighted_response,
            "calculation_method": "neurological_weighted_model"
        }
        
        # Create and return the system output
        return SystemOutput(
            response_value=response_value,
            confidence_interval=confidence_interval,
            severity_level=severity_level,
            onset_time=onset_time,
            peak_time=peak_time,
            recovery_time=recovery_time,
            system_type="neurological",
            metadata=output_metadata
        )
    
    def _calculate_blood_brain_barrier_factor(
        self,
        chemical_id: str,
        sensitivity_profile: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate the blood-brain barrier penetration factor.
        
        Args:
            chemical_id: ID of the chemical
            sensitivity_profile: Optional sensitivity profile with BBB information
            
        Returns:
            Blood-brain barrier factor (0-2)
        """
        # Default BBB factors for known chemicals
        bbb_defaults = {
            # High BBB penetration
            "toluene": 1.7,
            "benzene": 1.5,
            "xylene": 1.6,
            "ethanol": 1.8,
            "methanol": 1.7,
            "mercury": 1.5,
            "carbon_monoxide": 1.9,
            
            # Medium BBB penetration
            "formaldehyde": 1.2,
            "lead": 0.9,
            "manganese": 1.0,
            "styrene": 1.3,
            
            # Low BBB penetration
            "glyphosate": 0.4,
            "pm2_5": 0.3,
            "pm10": 0.2,
            
            # Default
            "default": 1.0
        }
        
        # Get chemical-specific default
        base_factor = bbb_defaults.get(chemical_id.lower(), bbb_defaults["default"])
        
        # Apply sensitivity profile modifications if available
        if sensitivity_profile and "blood_brain_barrier_factor" in sensitivity_profile:
            # This represents individual variation in BBB permeability
            individual_factor = sensitivity_profile["blood_brain_barrier_factor"]
            return base_factor * individual_factor
        
        # Apply age-based adjustments if available
        if sensitivity_profile and "age" in sensitivity_profile:
            age = sensitivity_profile["age"]
            
            # Children and elderly have more permeable BBB
            if age < 12:
                # Children have more permeable BBB, especially very young
                age_adjustment = 1.3 - (0.02 * age)  # 1.3 at age 0, down to 1.06 at age 12
                base_factor *= age_adjustment
            elif age > 65:
                # Elderly have increasingly permeable BBB with age
                age_adjustment = 1.0 + (0.005 * (age - 65))  # Increases by 0.5% per year over 65
                base_factor *= age_adjustment
        
        return base_factor
    
    def _calculate_peak_factor(self, peak_concentration: float) -> float:
        """
        Calculate the factor for peak chemical concentration.
        
        Args:
            peak_concentration: Peak concentration in appropriate units
            
        Returns:
            Peak concentration factor (0-100)
        """
        if peak_concentration <= 0:
            return 0.0
            
        # Apply sigmoidal response curve
        # Neurological effects often show threshold effects
        normalized_conc = peak_concentration / 100.0  # Normalize to reference concentration
        return 100.0 / (1 + math.exp(-6 * (normalized_conc - 0.4)))  # Steeper curve, lower threshold
    
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
            
        # Neurological effects can have different time courses than respiratory
        # Some are more acute (fast onset), others develop more gradually
        # Use a different curve shape than respiratory
        return min(100.0, 80.0 * (1 - math.exp(-0.8 * duration)) + 20.0 * (duration / (duration + 10)))
    
    def _calculate_cumulative_factor(self, cumulative_dose: float) -> float:
        """
        Calculate the factor for cumulative dose.
        
        Args:
            cumulative_dose: Cumulative chemical dose
            
        Returns:
            Cumulative dose factor (0-100)
        """
        if cumulative_dose <= 0:
            return 0.0
            
        # Apply power function with diminishing returns
        # Some neurological effects accumulate non-linearly
        normalized_dose = cumulative_dose / 100.0  # Normalize to reference dose
        return min(100.0, 100.0 * math.pow(normalized_dose, 0.7))
    
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
        
        # Apply general neurological sensitivity factor if available
        neuro_sensitivity = sensitivity_profile.get("neurological_sensitivity", 1.0)
        adjusted_response *= neuro_sensitivity
        
        # Apply condition-based adjustments
        neuro_conditions = sensitivity_profile.get("neurological_conditions", [])
        for condition in neuro_conditions:
            condition_factor = 1.0
            
            # Apply specific condition adjustments
            if condition.lower() in ["dementia", "alzheimer's", "alzheimers"]:
                condition_factor = 1.7
            elif condition.lower() in ["parkinson's", "parkinsons"]:
                condition_factor = 1.6
            elif condition.lower() == "multiple sclerosis":
                condition_factor = 1.6
            elif condition.lower() in ["epilepsy", "seizure disorder"]:
                condition_factor = 1.5
            elif condition.lower() == "migraine":
                condition_factor = 1.4
            elif condition.lower() in ["neuropathy", "peripheral neuropathy"]:
                condition_factor = 1.3
            elif condition.lower() == "stroke":
                condition_factor = 1.5
            elif condition.lower() == "traumatic brain injury":
                condition_factor = 1.6
            else:
                # Default factor for other neurological conditions
                condition_factor = 1.3
                
            adjusted_response *= condition_factor
        
        # Apply medication effects if present
        medications = sensitivity_profile.get("medications", [])
        for medication in medications:
            # Some medications may increase or decrease neurological sensitivity
            if medication.lower() in ["antidepressant", "ssri", "snri"]:
                adjusted_response *= 1.2  # Increased sensitivity
            elif medication.lower() in ["benzodiazepine", "anti-anxiety"]:
                adjusted_response *= 1.3  # Increased sensitivity
            elif medication.lower() in ["anticonvulsant", "anti-seizure"]:
                adjusted_response *= 0.8  # Protective effect
            elif medication.lower() in ["neuroprotective", "antioxidant"]:
                adjusted_response *= 0.9  # Protective effect
        
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
        Calculate timing information for the neurological response.
        
        Args:
            response_value: Calculated response value
            chemical_id: ID of the chemical
            exposure_history: Dictionary containing exposure data
            sensitivity_profile: Optional sensitivity profile
            
        Returns:
            Tuple of (onset_time, peak_time, recovery_time)
        """
        # Default timing values (in minutes)
        default_onset = 30.0
        default_peak = 120.0
        default_recovery = 480.0
        
        # Chemical-specific timing adjustments
        chemical_timing = {
            # Fast-acting CNS depressants
            "ethanol": (20.0, 60.0, 360.0),
            "carbon_monoxide": (15.0, 45.0, 720.0),
            "hydrogen_sulfide": (10.0, 30.0, 240.0),
            
            # Moderate-onset neurotoxicants
            "toluene": (30.0, 120.0, 480.0),
            "xylene": (30.0, 120.0, 480.0),
            "styrene": (45.0, 150.0, 540.0),
            
            # Slower-onset neurotoxicants
            "lead": (720.0, 4320.0, 20160.0),  # 12h, 3d, 14d
            "mercury": (360.0, 2880.0, 10080.0),  # 6h, 2d, 7d
            "n-hexane": (180.0, 720.0, 4320.0),  # 3h, 12h, 3d
        }
        
        # Get chemical-specific timing if available
        onset, peak, recovery = chemical_timing.get(
            chemical_id.lower(), (default_onset, default_peak, default_recovery)
        )
        
        # Adjust timing based on response severity
        # More severe responses often have different timing profiles
        severity_adjustment = response_value / 50.0  # Normalized to typical moderate response
        
        # Severe responses may have faster onset but much longer recovery
        onset /= max(0.7, min(1.5, severity_adjustment))  
        recovery *= max(0.8, min(3.5, severity_adjustment))
        
        # Apply sensitivity adjustments if available
        if sensitivity_profile:
            # Pre-existing conditions can significantly affect timing
            if "neurological_conditions" in sensitivity_profile and sensitivity_profile["neurological_conditions"]:
                onset *= 0.8  # 20% faster onset
                recovery *= 2.0  # Twice as long recovery
            
            # Age affects neurological recovery substantially
            if "age" in sensitivity_profile:
                age = sensitivity_profile["age"]
                if age < 12:
                    # Children may recover faster
                    recovery *= 0.7
                elif age > 65:
                    # Elderly recover much more slowly
                    age_factor = 1.0 + (0.03 * (age - 65))  # 3% longer per year over 65
                    recovery *= age_factor
        
        # Convert to timedelta objects
        onset_time = datetime.timedelta(minutes=onset)
        peak_time = datetime.timedelta(minutes=peak)
        recovery_time = datetime.timedelta(minutes=recovery)
        
        return onset_time, peak_time, recovery_time
