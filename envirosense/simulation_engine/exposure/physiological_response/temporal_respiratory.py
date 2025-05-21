"""
Enhanced respiratory response modeling with temporal effects.

This module extends the basic respiratory system with the TemporalResponseMixin,
allowing for delayed, chronic, and cascading effects to be modeled over time.

References:
- Smith et al. (2022): "Dose-Response Relationships for Pulmonary Irritants"
- EPA Guidelines (2023): "Air Pollutant Exposure and Respiratory Effects"
- Cohen et al. (2023): "Delayed Onset of Chemical Effects in Biological Systems"
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
from envirosense.core.exposure.physiological_response.respiratory import (
    RespiratoryResponseSystem
)
from envirosense.core.exposure.physiological_response.temporal_response import (
    TemporalResponseMixin,
    TemporalParameters,
    TemporalPattern
)


class TemporalRespiratorySystem(RespiratoryResponseSystem, TemporalResponseMixin):
    """
    Respiratory system with enhanced temporal response capabilities.
    
    This class extends the basic respiratory system with the ability to model
    delayed onset, chronic accumulation, and temporal patterns of responses.
    """
    
    def __init__(
        self,
        name: str = "Temporal Respiratory System",
        description: str = "Models respiratory responses with temporal dynamics",
        thresholds: Optional[Dict[ResponseSeverityLevel, float]] = None,
        uncertainty: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize an enhanced respiratory system with temporal capabilities.
        
        Args:
            name: Name of the system
            description: Description of the system
            thresholds: Dictionary mapping severity levels to threshold values
            uncertainty: Uncertainty factor for confidence interval calculation
            metadata: Additional metadata for the system
        """
        # Initialize the base respiratory system
        super().__init__(
            name=name,
            description=description,
            thresholds=thresholds,
            uncertainty=uncertainty,
            metadata=metadata or {}
        )
        
        # Add temporal-specific metadata
        self.metadata.update({
            "supports_temporal_modeling": True,
            "temporal_version": "1.0.0"
        })
        
        # Chemical-specific temporal parameters
        # Maps chemical IDs to their typical temporal patterns
        self.chemical_temporal_patterns = {
            # Fast-acting irritants (immediate pattern)
            "chlorine": TemporalPattern.IMMEDIATE,
            "ammonia": TemporalPattern.IMMEDIATE,
            "sulfur_dioxide": TemporalPattern.IMMEDIATE,
            
            # Delayed-onset irritants
            "ozone": TemporalPattern.DELAYED,
            "nitrogen_dioxide": TemporalPattern.DELAYED,
            
            # Biphasic response chemicals
            "formaldehyde": TemporalPattern.BIPHASIC,
            
            # Chemicals with chronic accumulation
            "benzene": TemporalPattern.CHRONIC,
            "pm2_5": TemporalPattern.CHRONIC,
            
            # Recurrent pattern chemicals
            "isocyanates": TemporalPattern.RECURRENT,
            
            # Default pattern for unknown chemicals
            "default": TemporalPattern.IMMEDIATE
        }
        
        # Chemical-specific chronic accumulation factors
        self.chronic_accumulation_factors = {
            "benzene": 0.05,  # Slow accumulation
            "pm2_5": 0.03,    # Very slow accumulation
            "lead": 0.08,     # Moderate accumulation
            "default": 0.01   # Default minimal accumulation
        }
        
        # Chemical-specific clearance rates (per day)
        self.clearance_rates = {
            "benzene": 0.2,   # Clears moderately
            "pm2_5": 0.1,     # Clears very slowly
            "lead": 0.05,     # Clears extremely slowly
            "default": 0.3    # Default clearance rate
        }
    
    def _get_temporal_parameters(
        self,
        chemical_id: str,
        response_value: float,
        sensitivity_profile: Optional[Dict[str, Any]] = None
    ) -> TemporalParameters:
        """
        Get temporal parameters for a specific chemical and sensitivity profile.
        
        This method provides respiratory-specific temporal parameters for different
        chemicals and response patterns.
        
        Args:
            chemical_id: ID of the chemical
            response_value: Base response value
            sensitivity_profile: Optional sensitivity profile
            
        Returns:
            TemporalParameters object
        """
        # Get base timing from _calculate_response_timing
        exposure = {"chemical_id": chemical_id, "concentration": 10.0, "duration": 1.0}
        onset, peak, recovery = self._calculate_response_timing(
            response_value, chemical_id, exposure, sensitivity_profile
        )
        
        # Ensure we have valid timedeltas
        if onset is None:
            onset = datetime.timedelta(minutes=15)
        if peak is None:
            peak = datetime.timedelta(minutes=60)
        if recovery is None:
            recovery = datetime.timedelta(minutes=240)
            
        # Get the pattern type for this chemical
        pattern_type = self.chemical_temporal_patterns.get(
            chemical_id.lower(), self.chemical_temporal_patterns["default"]
        )
        
        # Create parameters based on the pattern type
        if pattern_type == TemporalPattern.IMMEDIATE:
            # Standard immediate pattern - already handled by base timing
            return TemporalParameters(
                onset_delay=onset,
                time_to_peak=peak - onset,
                recovery_duration=recovery - peak,
                pattern_type=pattern_type,
                chemical_id=chemical_id,
                system_id=self.name
            )
            
        elif pattern_type == TemporalPattern.DELAYED:
            # Delayed response - longer onset, potentially longer recovery
            return TemporalParameters(
                onset_delay=onset * 1.5,  # Extend onset time for delayed effects
                time_to_peak=peak * 1.2,  # Slightly longer peak time
                recovery_duration=recovery * 1.5,  # Longer recovery
                pattern_type=pattern_type,
                chemical_id=chemical_id,
                system_id=self.name
            )
            
        elif pattern_type == TemporalPattern.BIPHASIC:
            # Biphasic - initial response followed by delayed secondary response
            return TemporalParameters(
                onset_delay=onset,
                time_to_peak=peak - onset,
                recovery_duration=recovery - peak,
                # Secondary phase parameters
                secondary_onset=datetime.timedelta(hours=4),
                secondary_peak=datetime.timedelta(hours=2),
                secondary_recovery=datetime.timedelta(hours=12),
                pattern_type=pattern_type,
                chemical_id=chemical_id,
                system_id=self.name
            )
            
        elif pattern_type == TemporalPattern.CHRONIC:
            # Chronic - accumulates over repeated exposures
            return TemporalParameters(
                onset_delay=onset,
                time_to_peak=peak - onset,
                recovery_duration=recovery - peak,
                pattern_type=pattern_type,
                # Chronic parameters
                accumulation_factor=self.chronic_accumulation_factors.get(
                    chemical_id.lower(), self.chronic_accumulation_factors["default"]
                ),
                clearance_rate=self.clearance_rates.get(
                    chemical_id.lower(), self.clearance_rates["default"]
                ),
                chemical_id=chemical_id,
                system_id=self.name
            )
            
        elif pattern_type == TemporalPattern.RECURRENT:
            # Recurrent - cycles of symptoms
            return TemporalParameters(
                onset_delay=onset,
                time_to_peak=peak - onset,
                recovery_duration=recovery - peak,
                pattern_type=pattern_type,
                chemical_id=chemical_id,
                system_id=self.name
            )
            
        else:
            # Default to immediate pattern if unknown
            return TemporalParameters(
                onset_delay=onset,
                time_to_peak=peak - onset,
                recovery_duration=recovery - peak,
                pattern_type=TemporalPattern.IMMEDIATE,
                chemical_id=chemical_id,
                system_id=self.name
            )
    
    def get_temporal_characteristics(self) -> Dict[str, Any]:
        """
        Get temporal characteristics for this system.
        
        Returns:
            Dictionary with temporal characteristics
        """
        # Sample exposure for an average chemical
        sample_exposure = {"chemical_id": "default", "concentration": 10.0, "duration": 1.0}
        
        # Get default timing
        onset, peak, recovery = self._calculate_response_timing(
            50.0, "default", sample_exposure, None
        )
        
        # Convert to seconds for the effect graph
        return {
            'onset_seconds': onset.total_seconds() if onset else 900,
            'peak_seconds': peak.total_seconds() if peak else 3600,
            'recovery_seconds': recovery.total_seconds() if recovery else 14400,
            'system_type': 'respiratory'
        }
