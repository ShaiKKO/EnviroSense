"""
Base classes for physiological response systems.

This module provides the foundation for modeling physiological responses
to chemical exposures, including the base system class, response severity
classification, and confidence interval calculations.

References:
- Smith et al. (2022): "Dose-Response Relationships for Pulmonary Irritants"
- EPA Guidelines (2023): "Air Pollutant Exposure and Respiratory Effects"
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Dict, List, Optional, Union, Any, Tuple
import numpy as np
import uuid
import datetime
from dataclasses import dataclass


class ResponseSeverityLevel(Enum):
    """
    Severity levels for physiological responses.
    
    These levels follow standard medical severity classifications from
    subclinical to life-threatening effects.
    """
    NONE = auto()         # No detectable response
    SUBCLINICAL = auto()  # Detectable only through specialized measurements, no symptoms
    MILD = auto()         # Noticeable symptoms, but no functional impairment
    MODERATE = auto()     # Symptoms with some functional impairment
    SEVERE = auto()       # Significant functional impairment
    CRITICAL = auto()     # Life-threatening effects


@dataclass
class SystemOutput:
    """
    Output from a physiological response system.
    
    Contains the calculated response metrics, confidence intervals,
    severity classification, and metadata about the calculation.
    """
    # Core outputs
    response_value: float
    confidence_interval: Tuple[float, float]
    severity_level: ResponseSeverityLevel
    
    # Time-based properties
    onset_time: Optional[datetime.timedelta] = None
    peak_time: Optional[datetime.timedelta] = None
    recovery_time: Optional[datetime.timedelta] = None
    
    # Metadata
    calculation_id: str = None
    system_type: str = None
    timestamp: datetime.datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize default values for optional fields."""
        if self.calculation_id is None:
            self.calculation_id = str(uuid.uuid4())
        
        if self.timestamp is None:
            self.timestamp = datetime.datetime.now()
            
        if self.metadata is None:
            self.metadata = {}


class PhysiologicalResponseSystem(ABC):
    """
    Base class for physiological response systems.
    
    Provides the common interface and functionality for all specific
    physiological response systems (respiratory, neurological, etc.)
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        thresholds: Optional[Dict[ResponseSeverityLevel, float]] = None,
        uncertainty: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize a physiological response system.
        
        Args:
            name: Name of the system
            description: Description of the system
            thresholds: Dictionary mapping severity levels to threshold values
            uncertainty: Uncertainty factor for confidence interval calculation
            metadata: Additional metadata for the system
        """
        self.name = name
        self.description = description
        self.thresholds = thresholds or {}
        self.uncertainty = uncertainty or 0.2  # Default 20% uncertainty
        self.metadata = metadata or {}
    
    @abstractmethod
    def calculate_response(
        self,
        exposure_history: Dict[str, Any],
        sensitivity_profile: Optional[Dict[str, Any]] = None
    ) -> SystemOutput:
        """
        Calculate physiological response based on exposure history.
        
        This method must be implemented by specific system subclasses to
        provide system-specific response calculations.
        
        Args:
            exposure_history: Dictionary containing exposure data
            sensitivity_profile: Optional dictionary with individual sensitivity factors
            
        Returns:
            SystemOutput object with response metrics
        """
        pass
    
    def calculate_confidence_interval(
        self,
        value: float,
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """
        Calculate confidence interval for a response value.
        
        Uses the system's uncertainty factor to determine the width
        of the confidence interval.
        
        Args:
            value: Response value to calculate interval for
            confidence: Confidence level (default 95%)
            
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        # Calculate z-score for the given confidence level
        # For 95% confidence, z = 1.96
        if confidence == 0.95:
            z_score = 1.96
        elif confidence == 0.99:
            z_score = 2.58
        elif confidence == 0.90:
            z_score = 1.64
        else:
            # For other values, use the normal distribution
            z_score = np.abs(np.percentile(np.random.normal(0, 1, 10000), 
                                         (1 - confidence) * 100 / 2))
        
        # Calculate the margin of error
        margin = value * self.uncertainty * z_score
        
        # Return the confidence interval
        return (max(0, value - margin), value + margin)
    
    def classify_severity(self, response_value: float) -> ResponseSeverityLevel:
        """
        Classify the severity of a response based on thresholds.
        
        Args:
            response_value: Calculated response value
            
        Returns:
            ResponseSeverityLevel indicating severity
        """
        # Default to no response
        result = ResponseSeverityLevel.NONE
        
        # Find the highest threshold that the response exceeds
        for level, threshold in sorted(
            self.thresholds.items(),
            key=lambda x: x[1]  # Sort by threshold value
        ):
            if response_value >= threshold:
                result = level
            else:
                break
                
        return result
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get information about this response system.
        
        Returns:
            Dictionary containing system details
        """
        return {
            "name": self.name,
            "description": self.description,
            "thresholds": {level.name: value for level, value in self.thresholds.items()},
            "uncertainty": self.uncertainty,
            "type": type(self).__name__,
            "metadata": self.metadata
        }


class PhysiologicalSystemSet:
    """
    A collection of physiological response systems that work together.
    
    This class manages multiple response systems and handles their interactions,
    providing coordinated response calculations across systems.
    """
    
    def __init__(
        self,
        systems: Optional[List[PhysiologicalResponseSystem]] = None,
        interaction_matrix: Optional[Dict[str, Dict[str, float]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize a collection of physiological systems.
        
        Args:
            systems: List of physiological response systems
            interaction_matrix: Dictionary mapping system pairs to interaction factors
            metadata: Additional metadata for the system set
        """
        self.systems = systems or []
        self.interaction_matrix = interaction_matrix or {}
        self.metadata = metadata or {}
        
        # Create a mapping of system names to systems for easy lookup
        self._system_map = {system.name: system for system in self.systems}
    
    def add_system(self, system: PhysiologicalResponseSystem) -> None:
        """
        Add a physiological system to the set.
        
        Args:
            system: PhysiologicalResponseSystem to add
        """
        self.systems.append(system)
        self._system_map[system.name] = system
    
    def get_system(self, name: str) -> Optional[PhysiologicalResponseSystem]:
        """
        Get a system by name.
        
        Args:
            name: Name of the system to retrieve
            
        Returns:
            The requested system, or None if not found
        """
        return self._system_map.get(name)
    
    def set_interaction(
        self,
        source_system: str,
        target_system: str,
        factor: float
    ) -> None:
        """
        Set an interaction factor between two systems.
        
        The factor indicates how much the source system's response
        affects the target system's response.
        
        Args:
            source_system: Name of the source system
            target_system: Name of the target system
            factor: Interaction factor (0 = no effect, 1 = full effect)
        """
        if source_system not in self._system_map:
            raise ValueError(f"Source system '{source_system}' not found")
            
        if target_system not in self._system_map:
            raise ValueError(f"Target system '{target_system}' not found")
        
        # Create the nested dictionaries if they don't exist
        if source_system not in self.interaction_matrix:
            self.interaction_matrix[source_system] = {}
            
        self.interaction_matrix[source_system][target_system] = factor
    
    def calculate_responses(
        self,
        exposure_history: Dict[str, Any],
        sensitivity_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, SystemOutput]:
        """
        Calculate responses for all systems with interactions.
        
        This method calculates the baseline responses for each system,
        then applies the interaction effects to get the final responses.
        
        Args:
            exposure_history: Dictionary containing exposure data
            sensitivity_profile: Optional dictionary with individual sensitivity factors
            
        Returns:
            Dictionary mapping system names to their outputs
        """
        # First, calculate baseline responses without interactions
        baseline_responses = {}
        for system in self.systems:
            baseline_responses[system.name] = system.calculate_response(
                exposure_history, sensitivity_profile
            )
        
        # Now apply interaction effects
        final_responses = {}
        for system in self.systems:
            # Start with the baseline response
            response = baseline_responses[system.name]
            
            # Apply incoming interactions from other systems
            for source_name, targets in self.interaction_matrix.items():
                if system.name in targets:
                    # Get the interaction factor
                    factor = targets[system.name]
                    
                    # Get the source system's response
                    source_response = baseline_responses[source_name]
                    
                    # Apply the interaction effect
                    # Scale the response value by the interaction factor
                    response.response_value *= (1 + factor * 
                                             (source_response.response_value / 100))
                    
                    # Update the confidence interval
                    lower, upper = response.confidence_interval
                    lower *= (1 + factor * (source_response.response_value / 100))
                    upper *= (1 + factor * (source_response.response_value / 100))
                    response.confidence_interval = (lower, upper)
                    
                    # Recalculate severity based on new response value
                    response.severity_level = system.classify_severity(response.response_value)
                    
                    # Add interaction info to metadata
                    if "interactions" not in response.metadata:
                        response.metadata["interactions"] = []
                        
                    response.metadata["interactions"].append({
                        "source_system": source_name,
                        "factor": factor,
                        "effect": factor * source_response.response_value
                    })
            
            final_responses[system.name] = response
        
        return final_responses
    
    def get_overall_severity(
        self,
        responses: Dict[str, SystemOutput]
    ) -> ResponseSeverityLevel:
        """
        Determine the overall severity level across all systems.
        
        Returns the highest severity level from any system.
        
        Args:
            responses: Dictionary mapping system names to their outputs
            
        Returns:
            The highest ResponseSeverityLevel across all systems
        """
        if not responses:
            return ResponseSeverityLevel.NONE
            
        # Find the highest severity level
        max_severity = ResponseSeverityLevel.NONE
        for response in responses.values():
            if response.severity_level.value > max_severity.value:
                max_severity = response.severity_level
                
        return max_severity
