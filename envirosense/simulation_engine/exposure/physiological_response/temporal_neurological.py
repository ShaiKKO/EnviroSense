"""
Enhanced neurological response modeling with temporal effects.

This module extends the basic neurological system with the TemporalResponseMixin,
allowing for delayed, chronic, and cascading effects to be modeled over time.

References:
- Grandjean et al. (2022): "Neurotoxicity of Chemical Pollutants"
- EPA Neurotoxicity Guidelines (2024): "Evaluating Neurotoxic Effects"
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
from envirosense.core.exposure.physiological_response.neurological import (
    NeurologicalResponseSystem
)
from envirosense.core.exposure.physiological_response.temporal_response import (
    TemporalResponseMixin,
    TemporalParameters,
    TemporalPattern
)


class TemporalNeurologicalSystem(NeurologicalResponseSystem, TemporalResponseMixin):
    """
    Neurological system with enhanced temporal response capabilities.
    
    This class extends the basic neurological system with the ability to model
    delayed onset, chronic accumulation, and temporal patterns of responses.
    """
    
    def __init__(
        self,
        name: str = "Temporal Neurological System",
        description: str = "Models neurological responses with temporal dynamics",
        thresholds: Optional[Dict[ResponseSeverityLevel, float]] = None,
        uncertainty: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize an enhanced neurological system with temporal capabilities.
        
        Args:
            name: Name of the system
            description: Description of the system
            thresholds: Dictionary mapping severity levels to threshold values
            uncertainty: Uncertainty factor for confidence interval calculation
            metadata: Additional metadata for the system
        """
        # Initialize the base neurological system
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
            # Fast-acting neurotoxicants (immediate pattern)
            "ethanol": TemporalPattern.IMMEDIATE,
            "carbon_monoxide": TemporalPattern.IMMEDIATE,
            "hydrogen_sulfide": TemporalPattern.IMMEDIATE,
            
            # Delayed-onset neurotoxicants
            "mercury": TemporalPattern.DELAYED,
            "toluene": TemporalPattern.DELAYED,
            "styrene": TemporalPattern.DELAYED,
            
            # Biphasic response chemicals
            "carbon_disulfide": TemporalPattern.BIPHASIC,
            "manganese": TemporalPattern.BIPHASIC,
            
            # Chemicals with chronic accumulation
            "lead": TemporalPattern.CHRONIC,
            "arsenic": TemporalPattern.CHRONIC,
            "n-hexane": TemporalPattern.CHRONIC,
            
            # Recurrent pattern chemicals (neurological symptoms often fluctuate)
            "organophosphates": TemporalPattern.RECURRENT,
            "chlorpyrifos": TemporalPattern.RECURRENT,
            
            # Default pattern for unknown chemicals
            "default": TemporalPattern.DELAYED  # Most neurotoxicants have delayed effects
        }
        
        # Chemical-specific chronic accumulation factors
        self.chronic_accumulation_factors = {
            "lead": 0.10,     # Significant accumulation in neural tissue
            "mercury": 0.08,  # Strong accumulation in neural tissue
            "arsenic": 0.07,  # Moderate accumulation
            "n-hexane": 0.05, # Slower accumulation
            "default": 0.03   # Default accumulation
        }
        
        # Chemical-specific clearance rates (per day)
        self.clearance_rates = {
            "lead": 0.002,    # Extremely slow clearance from neural tissue
            "mercury": 0.003, # Very slow clearance
            "arsenic": 0.01,  # Slow clearance
            "toluene": 0.2,   # Moderate clearance
            "ethanol": 0.5,   # Relatively rapid clearance
            "default": 0.05   # Default clearance rate
        }
    
    def _get_temporal_parameters(
        self,
        chemical_id: str,
        response_value: float,
        sensitivity_profile: Optional[Dict[str, Any]] = None
    ) -> TemporalParameters:
        """
        Get temporal parameters for a specific chemical and sensitivity profile.
        
        This method provides neurological-specific temporal parameters for different
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
            onset = datetime.timedelta(minutes=30)  # Neurological effects often delayed
        if peak is None:
            peak = datetime.timedelta(minutes=120)  # Longer time to peak than respiratory
        if recovery is None:
            recovery = datetime.timedelta(minutes=480)  # Longer recovery time
            
        # Get the pattern type for this chemical
        pattern_type = self.chemical_temporal_patterns.get(
            chemical_id.lower(), self.chemical_temporal_patterns["default"]
        )
        
        # Create parameters based on the pattern type
        if pattern_type == TemporalPattern.IMMEDIATE:
            # Even for "immediate" neurological effects, there's still some delay
            return TemporalParameters(
                onset_delay=onset,
                time_to_peak=peak - onset,
                recovery_duration=recovery - peak,
                pattern_type=pattern_type,
                chemical_id=chemical_id,
                system_id=self.name
            )
            
        elif pattern_type == TemporalPattern.DELAYED:
            # Neurological effects often have much longer delays
            return TemporalParameters(
                onset_delay=onset * 2.0,      # Significantly longer onset
                time_to_peak=peak * 1.5,      # Longer peak time
                recovery_duration=recovery * 2.0,  # Much longer recovery
                pattern_type=pattern_type,
                chemical_id=chemical_id,
                system_id=self.name
            )
            
        elif pattern_type == TemporalPattern.BIPHASIC:
            # Biphasic neurological responses can have very delayed secondary phases
            return TemporalParameters(
                onset_delay=onset,
                time_to_peak=peak - onset,
                recovery_duration=recovery - peak,
                # Secondary phase often occurs days to weeks later
                secondary_onset=datetime.timedelta(hours=48),  # 2 days later
                secondary_peak=datetime.timedelta(hours=12),   # Takes half a day to peak
                secondary_recovery=datetime.timedelta(hours=72),  # 3 days to recover
                pattern_type=pattern_type,
                chemical_id=chemical_id,
                system_id=self.name
            )
            
        elif pattern_type == TemporalPattern.CHRONIC:
            # Neurotoxic chemicals often accumulate severely
            return TemporalParameters(
                onset_delay=onset,
                time_to_peak=peak - onset,
                recovery_duration=recovery - peak,
                pattern_type=pattern_type,
                # Chronic parameters - typically higher for neurological than respiratory
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
            # Recurrent neurological symptoms (common with some neurotoxicants)
            return TemporalParameters(
                onset_delay=onset,
                time_to_peak=peak - onset,
                recovery_duration=recovery - peak,
                pattern_type=pattern_type,
                chemical_id=chemical_id,
                system_id=self.name
            )
            
        else:
            # Default to delayed pattern for neurological effects
            return TemporalParameters(
                onset_delay=onset * 1.5,
                time_to_peak=(peak - onset) * 1.2,
                recovery_duration=(recovery - peak) * 1.5,
                pattern_type=TemporalPattern.DELAYED,
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
            'onset_seconds': onset.total_seconds() if onset else 1800,  # 30 minutes
            'peak_seconds': peak.total_seconds() if peak else 7200,     # 2 hours
            'recovery_seconds': recovery.total_seconds() if recovery else 28800,  # 8 hours
            'system_type': 'neurological'
        }
