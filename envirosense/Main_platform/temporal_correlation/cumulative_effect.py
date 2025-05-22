"""
Cumulative Effect Modeling for Temporal Correlation.

This module implements cumulative effect modeling capabilities for the EnviroSense
Temporal Correlation System, allowing for analysis of how substances accumulate
over time with repeated exposures, considering biological half-lives, clearance
rates, and threshold effects.

The implementation is based on research from:
- Pharmacokinetic/Pharmacodynamic (PK/PD) models for substance accumulation and elimination
- Multi-compartment models for distribution across biological systems
- Threshold-based models for non-linear effects at specific concentrations
- Time-varying exposure patterns and their long-term physiological impacts
"""

from enum import Enum, auto
import numpy as np
import datetime
import math
import uuid
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from dataclasses import dataclass, field
from collections import deque

# Import from existing temporal correlation modules
from envirosense.core_platform.temporal_correlation.delayed_response import (
    TemporalPattern, DelayedResponseModel, DelayParameters
)


class AccumulationModelType(Enum):
    """
    Types of mathematical models for substance accumulation and clearance.
    
    These models represent different approaches to modeling how substances
    accumulate and clear from biological or environmental systems.
    """
    FIRST_ORDER = auto()        # Standard exponential model (first-order kinetics)
    SATURABLE = auto()          # Model with saturation effects (Michaelis-Menten)
    MULTI_COMPARTMENT = auto()  # Multi-compartment distribution model
    THRESHOLD_BASED = auto()    # Model with non-linear threshold effects


@dataclass
class AccumulationProfile:
    """
    Defines parameters for substance accumulation and clearance.
    
    Contains parameters that define how a substance accumulates in a system
    over time, including biological half-life, accumulation rate, saturation
    levels, and compartment distribution.
    """
    # Core accumulation parameters
    half_life: datetime.timedelta
    accumulation_rate: float
    saturation_level: Optional[float] = None
    
    # Compartment model parameters (for multi-compartment distribution)
    compartments: Dict[str, float] = field(default_factory=dict)
    inter_compartment_rates: Dict[Tuple[str, str], float] = field(default_factory=dict)
    
    # Substance specific properties
    substance_id: Optional[str] = None
    molecular_weight: Optional[float] = None
    
    # Model type
    accumulation_model: AccumulationModelType = AccumulationModelType.FIRST_ORDER
    
    # Threshold parameters
    threshold_value: Optional[float] = None
    threshold_onset_rate: Optional[float] = None
    
    def __post_init__(self):
        """Initialize derived values based on provided parameters."""
        # Calculate elimination rate constant from half-life
        self.elimination_rate = math.log(2) / self.half_life.total_seconds()
        
        # Set default compartments if using multi-compartment model and none provided
        if (self.accumulation_model == AccumulationModelType.MULTI_COMPARTMENT and 
                not self.compartments):
            # Default two-compartment model (central and peripheral)
            self.compartments = {
                "central": 0.7,  # 70% initial distribution to central compartment
                "peripheral": 0.3  # 30% to peripheral compartment
            }
            
            # Default inter-compartment transfer rates
            self.inter_compartment_rates = {
                ("central", "peripheral"): 0.05,  # 5% transfer per hour
                ("peripheral", "central"): 0.02   # 2% transfer per hour
            }
    
    def calculate_clearance_rate(self, time_delta: datetime.timedelta) -> float:
        """
        Calculate the fraction of substance cleared over a time period.
        
        Args:
            time_delta: Time period over which to calculate clearance
            
        Returns:
            Fraction of substance cleared (0.0-1.0)
        """
        # For first-order kinetics: C(t) = C₀ * e^(-k*t)
        if self.accumulation_model == AccumulationModelType.FIRST_ORDER:
            # Calculate fraction cleared using exponential decay
            return 1.0 - math.exp(-self.elimination_rate * time_delta.total_seconds())
        
        # For saturable kinetics: use Michaelis-Menten equation
        elif self.accumulation_model == AccumulationModelType.SATURABLE:
            # This is a simplification - full M-M kinetics would require concentration
            # For now, use a simple approximation
            base_clearance = 1.0 - math.exp(-self.elimination_rate * time_delta.total_seconds())
            
            # Reduce clearance as we approach saturation
            # (This is a placeholder - would need concentration to do properly)
            return base_clearance * 0.8  # Reduced clearance rate due to saturation
        
        # For multi-compartment: use the central compartment clearance as default
        elif self.accumulation_model == AccumulationModelType.MULTI_COMPARTMENT:
            # This is simplified - real multi-compartment would use differential equations
            return 1.0 - math.exp(-self.elimination_rate * time_delta.total_seconds())
        
        # Fallback to first-order clearance
        return 1.0 - math.exp(-self.elimination_rate * time_delta.total_seconds())


class CumulativeThresholdSystem:
    """
    System for modeling thresholds in cumulative exposures.
    
    This class implements methods for defining thresholds, detecting when
    cumulative exposures cross thresholds, and modeling the physiological
    or environmental responses that occur at threshold crossings.
    """
    
    def __init__(self):
        """Initialize the cumulative threshold system."""
        # Dictionary mapping substance IDs to their threshold parameters
        self.threshold_registry: Dict[str, Dict[str, Any]] = {}
        
        # History of threshold crossings
        self.crossing_history: List[Dict[str, Any]] = []
    
    def register_threshold(
        self,
        substance_id: str,
        threshold_value: float,
        effect_description: str,
        onset_delay: Optional[datetime.timedelta] = None,
        severity_level: Optional[str] = None,
        confidence_level: float = 0.95,
        is_reversible: bool = True,
        uncertainty: float = 0.1
    ) -> None:
        """
        Register a threshold for a substance.
        
        Args:
            substance_id: Identifier for the substance
            threshold_value: Concentration threshold value
            effect_description: Description of the effect at this threshold
            onset_delay: Optional delay before effect manifests
            severity_level: Optional severity categorization
            confidence_level: Confidence in this threshold (0.0-1.0)
            is_reversible: Whether effects reverse when concentration drops
            uncertainty: Uncertainty in the threshold value (0.0-1.0)
        """
        self.threshold_registry[substance_id] = {
            "value": threshold_value,
            "description": effect_description,
            "onset_delay": onset_delay or datetime.timedelta(minutes=15),
            "severity": severity_level or "MODERATE",
            "confidence": confidence_level,
            "reversible": is_reversible,
            "uncertainty": uncertainty,
            "last_crossing": None,
            "is_active": False
        }
    
    def check_threshold_crossing(
        self,
        substance_id: str,
        current_level: float,
        timestamp: Optional[datetime.datetime] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if current level crosses a registered threshold.
        
        Args:
            substance_id: Identifier for the substance
            current_level: Current accumulated level
            timestamp: Optional timestamp for the check
            
        Returns:
            Tuple of (crossed, crossing_details)
        """
        if substance_id not in self.threshold_registry:
            return False, {}
            
        if timestamp is None:
            timestamp = datetime.datetime.now()
            
        threshold = self.threshold_registry[substance_id]
        threshold_value = threshold["value"]
        uncertainty_range = threshold_value * threshold["uncertainty"]
        
        # Get previous state
        previously_active = threshold.get("is_active", False)
        
        # Check for crossing
        is_crossed = current_level >= threshold_value
        
        # Uncertainty zone
        in_uncertainty_zone = abs(current_level - threshold_value) <= uncertainty_range
        
        # Update threshold registry with current state
        self.threshold_registry[substance_id]["is_active"] = is_crossed
        
        # If this is a new crossing
        if is_crossed and not previously_active:
            crossing_details = {
                "substance_id": substance_id,
                "threshold_value": threshold_value,
                "current_level": current_level,
                "timestamp": timestamp,
                "crossing_type": "exceedance",
                "uncertainty": in_uncertainty_zone,
                "description": threshold["description"],
                "severity": threshold["severity"],
                "expected_onset_time": timestamp + threshold["onset_delay"]
            }
            
            # Update last crossing time
            self.threshold_registry[substance_id]["last_crossing"] = timestamp
            
            # Add to history
            self.crossing_history.append(crossing_details)
            
            return True, crossing_details
            
        # If this is a recovery (dropping below threshold)
        elif not is_crossed and previously_active:
            crossing_details = {
                "substance_id": substance_id,
                "threshold_value": threshold_value,
                "current_level": current_level,
                "timestamp": timestamp,
                "crossing_type": "recovery",
                "uncertainty": in_uncertainty_zone,
                "description": f"Recovery from {threshold['description']}",
                "severity": "RECOVERING",
                "reversible": threshold["reversible"]
            }
            
            # Add to history
            self.crossing_history.append(crossing_details)
            
            return True, crossing_details
            
        return False, {}
    
    def get_active_thresholds(
        self,
        substance_id: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get currently active thresholds.
        
        Args:
            substance_id: Optional substance ID to filter by
            
        Returns:
            Dictionary of active thresholds
        """
        active_thresholds = {}
        
        if substance_id:
            # Check just this substance
            if substance_id in self.threshold_registry:
                threshold = self.threshold_registry[substance_id]
                if threshold.get("is_active", False):
                    active_thresholds[substance_id] = threshold
        else:
            # Check all substances
            for subst_id, threshold in self.threshold_registry.items():
                if threshold.get("is_active", False):
                    active_thresholds[subst_id] = threshold
                    
        return active_thresholds
    
    def predict_threshold_crossing(
        self,
        substance_id: str,
        current_level: float,
        accumulation_rate: float,
        clearance_rate: float,
        start_time: Optional[datetime.datetime] = None,
        max_prediction_time: Optional[datetime.timedelta] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Predict when a threshold will be crossed.
        
        Args:
            substance_id: Identifier for the substance
            current_level: Current accumulated level
            accumulation_rate: Rate of accumulation (units/time)
            clearance_rate: Rate of clearance (fraction/time)
            start_time: Optional start time for prediction
            max_prediction_time: Maximum time to predict into future
            
        Returns:
            Dictionary with prediction details or None if no crossing expected
        """
        if substance_id not in self.threshold_registry:
            return None
            
        if start_time is None:
            start_time = datetime.datetime.now()
            
        if max_prediction_time is None:
            max_prediction_time = datetime.timedelta(days=7)
            
        threshold = self.threshold_registry[substance_id]
        threshold_value = threshold["value"]
        
        # If already above threshold
        if current_level >= threshold_value:
            return {
                "substance_id": substance_id,
                "threshold_value": threshold_value,
                "current_level": current_level,
                "prediction_time": start_time,
                "is_already_exceeded": True,
                "confidence": 1.0
            }
            
        # Simple model: assume constant rates
        # First-order kinetics: dC/dt = rate_in - k*C
        # At equilibrium: C = rate_in/k
        # If equilibrium < threshold, will never cross
        
        equilibrium_level = accumulation_rate / clearance_rate
        
        if equilibrium_level <= threshold_value:
            # Will never cross threshold
            return None
            
        # Calculate time to threshold
        # C(t) = C₀*e^(-k*t) + (rate_in/k)*(1-e^(-k*t))
        # Solve for t when C(t) = threshold
        
        # Rearrange to get:
        # e^(-k*t) = (threshold - rate_in/k)/(C₀ - rate_in/k)
        
        numerator = threshold_value - equilibrium_level
        denominator = current_level - equilibrium_level
        
        # If denominator is zero or very close, use a different approach
        if abs(denominator) < 1e-10:
            # Linear approximation
            if accumulation_rate > 0:
                time_to_threshold = (threshold_value - current_level) / accumulation_rate
                crossing_time = start_time + datetime.timedelta(seconds=time_to_threshold)
                
                if crossing_time > start_time + max_prediction_time:
                    return None
                    
                return {
                    "substance_id": substance_id,
                    "threshold_value": threshold_value,
                    "current_level": current_level,
                    "prediction_time": crossing_time,
                    "is_already_exceeded": False,
                    "confidence": 0.7  # Lower confidence due to approximation
                }
            return None
            
        # If we can solve the equation
        ratio = numerator / denominator
        
        # Check if ratio is negative (means we're heading away from threshold)
        if ratio <= 0:
            return None
            
        # Calculate time to threshold
        time_to_threshold = -math.log(ratio) / clearance_rate
        
        # Check if prediction is within our maximum prediction time
        if time_to_threshold <= max_prediction_time.total_seconds():
            crossing_time = start_time + datetime.timedelta(seconds=time_to_threshold)
            
            # Calculate confidence based on uncertainty
            # More uncertainty for longer predictions
            time_factor = time_to_threshold / max_prediction_time.total_seconds()
            confidence = max(0.5, 1.0 - (time_factor * threshold["uncertainty"]))
            
            return {
                "substance_id": substance_id,
                "threshold_value": threshold_value,
                "current_level": current_level,
                "prediction_time": crossing_time,
                "is_already_exceeded": False,
                "confidence": confidence,
                "expected_onset_time": crossing_time + threshold["onset_delay"]
            }
            
        return None


class CumulativeEffectModel:
    """
    Models cumulative effects from repeated or continuous exposures over time.
    
    This class implements models for accumulation and clearance of substances,
    thresholding effects, and visualization of buildup over time. It extends
    the delayed response modeling capabilities with specific focus on
    long-term accumulated exposures.
    """
    
    def __init__(self):
        """Initialize the cumulative effect model."""
        # Dictionary mapping substance IDs to their accumulation profiles
        self.substance_profiles: Dict[str, AccumulationProfile] = {}
        
        # Dictionary tracking current accumulated levels
        self.current_levels: Dict[str, Dict[str, Any]] = {}
        
        # System for threshold management
        self.threshold_system = CumulativeThresholdSystem()
        
        # Optional delayed response model for time-based effects
        self.delayed_response_model = DelayedResponseModel()
        
        # Exposure history
        self.exposure_history: Dict[str, List[Dict[str, Any]]] = {}
    
    def register_substance(
        self,
        substance_id: str,
        half_life: datetime.timedelta,
        accumulation_rate: float,
        saturation_level: Optional[float] = None,
        model_type: AccumulationModelType = AccumulationModelType.FIRST_ORDER,
        threshold_value: Optional[float] = None,
        threshold_description: Optional[str] = None
    ) -> None:
        """
        Register a substance with its accumulation parameters.
        
        Args:
            substance_id: Identifier for the substance
            half_life: Biological or environmental half-life
            accumulation_rate: Rate of accumulation (relative to exposure)
            saturation_level: Optional level at which saturation occurs
            model_type: Type of accumulation model to use
            threshold_value: Optional threshold value for effects
            threshold_description: Description of threshold effects
        """
        # Create accumulation profile
        profile = AccumulationProfile(
            half_life=half_life,
            accumulation_rate=accumulation_rate,
            saturation_level=saturation_level,
            accumulation_model=model_type,
            substance_id=substance_id,
            threshold_value=threshold_value
        )
        
        # Register the profile
        self.substance_profiles[substance_id] = profile
        
        # Initialize current level tracking
        self.current_levels[substance_id] = {
            "level": 0.0,
            "last_update": datetime.datetime.now(),
            "compartments": {} if model_type == AccumulationModelType.MULTI_COMPARTMENT else None
        }
        
        # Initialize exposure history
        self.exposure_history[substance_id] = []
        
        # Register threshold if provided
        if threshold_value is not None and threshold_description is not None:
            self.threshold_system.register_threshold(
                substance_id=substance_id,
                threshold_value=threshold_value,
                effect_description=threshold_description
            )
    
    def record_exposure(
        self,
        substance_id: str,
        concentration: float,
        duration: float,
        timestamp: Optional[datetime.datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record an exposure event for a substance.
        
        Args:
            substance_id: Identifier for the substance
            concentration: Concentration of the exposure
            duration: Duration of the exposure in seconds
            timestamp: Optional timestamp for the exposure
            metadata: Optional additional metadata
            
        Returns:
            Unique ID for this exposure record
        """
        if substance_id not in self.substance_profiles:
            raise ValueError(f"Substance '{substance_id}' not registered")
            
        if timestamp is None:
            timestamp = datetime.datetime.now()
            
        # Create exposure record
        exposure_id = str(uuid.uuid4())
        exposure_record = {
            "id": exposure_id,
            "substance_id": substance_id,
            "concentration": concentration,
            "duration": duration,
            "timestamp": timestamp,
            "metadata": metadata or {}
        }
        
        # Add to history
        if substance_id not in self.exposure_history:
            self.exposure_history[substance_id] = []
            
        self.exposure_history[substance_id].append(exposure_record)
        
        # Update accumulated level
        self._update_accumulated_level(substance_id, exposure_record)
        
        # Check threshold crossing
        self._check_threshold_crossing(substance_id)
        
        return exposure_id
    
    def _update_accumulated_level(
        self,
        substance_id: str,
        exposure_record: Dict[str, Any]
    ) -> None:
        """
        Update the accumulated level for a substance.
        
        Args:
            substance_id: Identifier for the substance
            exposure_record: Dictionary with exposure details
        """
        if substance_id not in self.substance_profiles:
            return
            
        profile = self.substance_profiles[substance_id]
        current_data = self.current_levels[substance_id]
        
        # Get current timestamp
        current_time = exposure_record["timestamp"]
        last_update = current_data["last_update"]
        
        # Calculate time since last update
        time_since_update = current_time - last_update
        
        # Calculate clearance over this period
        clearance_fraction = profile.calculate_clearance_rate(time_since_update)
        
        # Handle different model types
        if profile.accumulation_model == AccumulationModelType.FIRST_ORDER:
            # First-order kinetics: C(t) = C₀*e^(-k*t) + (rate_in/k)*(1-e^(-k*t))
            # First, apply clearance to existing level
            remaining_fraction = 1.0 - clearance_fraction
            updated_level = current_data["level"] * remaining_fraction
            
            # Then, add new exposure contribution
            concentration = exposure_record["concentration"]
            duration = exposure_record["duration"]
            
            # Scale by accumulation rate
            exposure_contribution = concentration * duration * profile.accumulation_rate
            
            # Update the level
            self.current_levels[substance_id]["level"] = updated_level + exposure_contribution
            
        elif profile.accumulation_model == AccumulationModelType.SATURABLE:
            # First, apply clearance to existing level
            remaining_fraction = 1.0 - clearance_fraction
            updated_level = current_data["level"] * remaining_fraction
            
            # Then, add new exposure with saturation effect
            concentration = exposure_record["concentration"]
            duration = exposure_record["duration"]
            
            # Scale by accumulation rate with saturation
            raw_contribution = concentration * duration * profile.accumulation_rate
            
            # Apply saturation effect using Michaelis-Menten equation
            if profile.saturation_level:
                saturation_factor = 1.0 / (1.0 + (updated_level / profile.saturation_level))
                exposure_contribution = raw_contribution * saturation_factor
            else:
                exposure_contribution = raw_contribution
                
            # Update the level
            self.current_levels[substance_id]["level"] = updated_level + exposure_contribution
            
        elif profile.accumulation_model == AccumulationModelType.MULTI_COMPARTMENT:
            # Handle multi-compartment model
            compartments = current_data.get("compartments", {})
            
            # Initialize if empty
            if not compartments:
                for name, fraction in profile.compartments.items():
                    compartments[name] = 0.0
                    
            # First, update each compartment with clearance
            for name in compartments:
                # Apply clearance to this compartment
                compartments[name] *= (1.0 - clearance_fraction)
                
            # Process inter-compartment transfers
            for (source, target), rate in profile.inter_compartment_rates.items():
                # Calculate amount to transfer
                transfer_amount = compartments.get(source, 0.0) * rate * time_since_update.total_seconds()
                # Remove from source
                compartments[source] = max(0.0, compartments.get(source, 0.0) - transfer_amount)
                # Add to target
                compartments[target] = compartments.get(target, 0.0) + transfer_amount
                
            # Add new exposure
            concentration = exposure_record["concentration"]
            duration = exposure_record["duration"]
            
            # Distribute to compartments
            raw_contribution = concentration * duration * profile.accumulation_rate
            for name, fraction in profile.compartments.items():
                compartments[name] += raw_contribution * fraction
                
            # Update compartments in storage
            self.current_levels[substance_id]["compartments"] = compartments
            
            # Update total level (sum of all compartments)
            self.current_levels[substance_id]["level"] = sum(compartments.values())
            
        else:  # Default case
            # Similar to first-order
            remaining_fraction = 1.0 - clearance_fraction
            updated_level = current_data["level"] * remaining_fraction
            
            concentration = exposure_record["concentration"]
            duration = exposure_record["duration"]
            
            exposure_contribution = concentration * duration * profile.accumulation_rate
            self.current_levels[substance_id]["level"] = updated_level + exposure_contribution
        
        # Update last update time
        self.current_levels[substance_id]["last_update"] = current_time
    
    def _check_threshold_crossing(
        self,
        substance_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if current level crosses any threshold.
        
        Args:
            substance_id: Identifier for the substance
            
        Returns:
            Dictionary with threshold crossing details or None
        """
        if substance_id not in self.current_levels:
            return None
            
        current_level = self.current_levels[substance_id]["level"]
        current_time = self.current_levels[substance_id]["last_update"]
        
        crossed, details = self.threshold_system.check_threshold_crossing(
            substance_id, current_level, current_time
        )
        
        if crossed:
            return details
            
        return None
    
    def get_current_level(
        self,
        substance_id: str,
        compartment: Optional[str] = None
    ) -> float:
        """
        Get the current accumulated level for a substance.
        
        Args:
            substance_id: Identifier for the substance
            compartment: Optional compartment name for multi-compartment models
            
        Returns:
            Current accumulated level
        """
        if substance_id not in self.current_levels:
            return 0.0
            
        if compartment is not None:
            # Get level from specific compartment
            compartments = self.current_levels[substance_id].get("compartments", {})
            return compartments.get(compartment, 0.0)
            
        # Get total level
        return self.current_levels[substance_id]["level"]
    
    def update_current_levels(
        self,
        reference_time: Optional[datetime.datetime] = None
    ) -> Dict[str, float]:
        """
        Update current levels for all substances based on time passage.
        
        Args:
            reference_time: Optional reference time
            
        Returns:
            Dictionary mapping substance IDs to their updated levels
        """
        if reference_time is None:
            reference_time = datetime.datetime.now()
            
        updated_levels = {}
        
        # Update each substance
        for substance_id, profile in self.substance_profiles.items():
            if substance_id not in self.current_levels:
                continue
                
            current_data = self.current_levels[substance_id]
            last_update = current_data["last_update"]
            
            # Calculate time since last update
            time_delta = reference_time - last_update
            
            # Skip if no time has passed
            if time_delta.total_seconds() <= 0:
                updated_levels[substance_id] = current_data["level"]
                continue
                
            # Calculate clearance
            clearance_fraction = profile.calculate_clearance_rate(time_delta)
            remaining_fraction = 1.0 - clearance_fraction
            
            if profile.accumulation_model == AccumulationModelType.MULTI_COMPARTMENT:
                # Handle multi-compartment update
                compartments = current_data.get("compartments", {})
                
                # Apply clearance to each compartment
                for name in compartments:
                    compartments[name] *= remaining_fraction
                    
                # Handle inter-compartment transfers
                for (source, target), rate in profile.inter_compartment_rates.items():
                    transfer_amount = compartments.get(source, 0.0) * rate * time_delta.total_seconds()
                    compartments[source] = max(0.0, compartments.get(source, 0.0) - transfer_amount)
                    compartments[target] = compartments.get(target, 0.0) + transfer_amount
                
                # Update compartments
                self.current_levels[substance_id]["compartments"] = compartments
                
                # Update total level
                new_level = sum(compartments.values())
                self.current_levels[substance_id]["level"] = new_level
                
            else:
                # Handle single-compartment update
                new_level = current_data["level"] * remaining_fraction
                self.current_levels[substance_id]["level"] = new_level
            
            # Update last update time
            self.current_levels[substance_id]["last_update"] = reference_time
            
            # Check threshold crossing
            self._check_threshold_crossing(substance_id)
            
            # Store updated level
            updated_levels[substance_id] = self.current_levels[substance_id]["level"]
            
        return updated_levels
    
    def predict_future_levels(
        self,
        substance_id: str,
        time_points: List[datetime.datetime],
        future_exposures: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[datetime.datetime, float]:
        """
        Predict future levels for a substance.
        
        Args:
            substance_id: Identifier for the substance
            time_points: List of time points to predict for
            future_exposures: Optional list of future exposure events
            
        Returns:
            Dictionary mapping time points to predicted levels
        """
        if substance_id not in self.substance_profiles:
            return {t: 0.0 for t in time_points}
            
        # Get profile and current data
        profile = self.substance_profiles[substance_id]
        current_data = self.current_levels.get(substance_id, {"level": 0.0, "last_update": datetime.datetime.now()})
        
        # Start with current level
        current_level = current_data["level"]
        last_update = current_data["last_update"]
        
        # Sort time points
        sorted_times = sorted(time_points)
        
        # Sort future exposures if provided
        future_events = []
        if future_exposures:
            for exp in future_exposures:
                if "timestamp" not in exp:
                    continue
                future_events.append(exp)
            future_events.sort(key=lambda x: x["timestamp"])
        
        # Results dictionary
        predictions = {}
        
        # For each time point
        for target_time in sorted_times:
            # Skip if in the past
            if target_time <= last_update:
                predictions[target_time] = current_level
                continue
                
            # Calculate basic clearance from current level to this time
            time_delta = target_time - last_update
            clearance_fraction = profile.calculate_clearance_rate(time_delta)
            remaining_fraction = 1.0 - clearance_fraction
            
            # Apply basic clearance
            predicted_level = current_level * remaining_fraction
            
            # Apply future exposures that occur before this time point
            for event in future_events:
                event_time = event["timestamp"]
                
                # Only consider events between last update and target time
                if event_time > last_update and event_time <= target_time:
                    # Calculate contribution from this event
                    concentration = event.get("concentration", 0.0)
                    duration = event.get("duration", 0.0)
                    
                    # Time from event to target for clearance calculation
                    event_to_target = target_time - event_time
                    event_clearance = profile.calculate_clearance_rate(event_to_target)
                    event_remaining = 1.0 - event_clearance
                    
                    # Add contribution with clearance applied
                    contribution = concentration * duration * profile.accumulation_rate * event_remaining
                    predicted_level += contribution
            
            # Store prediction
            predictions[target_time] = predicted_level
            
        return predictions
    
    def predict_threshold_crossings(
        self,
        substance_id: str,
        max_prediction_time: Optional[datetime.timedelta] = None,
        future_exposures: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Predict when thresholds will be crossed.
        
        Args:
            substance_id: Identifier for the substance
            max_prediction_time: Maximum time to predict into future
            future_exposures: Optional list of future exposure events
            
        Returns:
            List of dictionaries with threshold crossing predictions
        """
        if substance_id not in self.substance_profiles:
            return []
            
        if max_prediction_time is None:
            max_prediction_time = datetime.timedelta(days=7)
            
        # Get current level and parameters
        current_level = self.get_current_level(substance_id)
        profile = self.substance_profiles[substance_id]
        
        # Start time for prediction
        start_time = self.current_levels[substance_id]["last_update"]
        end_time = start_time + max_prediction_time
        
        # If we have future exposures, need to handle differently
        if future_exposures and len(future_exposures) > 0:
            # Create time series for predictions
            time_points = []
            current_time = start_time
            while current_time <= end_time:
                time_points.append(current_time)
                current_time += datetime.timedelta(hours=1)  # 1-hour steps
                
            # Get predicted levels at each time point
            predictions = self.predict_future_levels(
                substance_id, time_points, future_exposures
            )
            
            # Check each time point for threshold crossings
            crossings = []
            last_crossed = False
            
            for time_point in sorted(predictions.keys()):
                level = predictions[time_point]
                
                # Check for crossing
                crossed, details = self.threshold_system.check_threshold_crossing(
                    substance_id, level, time_point
                )
                
                if crossed and details.get("crossing_type") == "exceedance":
                    crossings.append(details)
                    last_crossed = True
                elif crossed and details.get("crossing_type") == "recovery":
                    crossings.append(details)
                    last_crossed = False
                    
            return crossings
            
        else:
            # If no future exposures, use simpler method
            # Calculate effective accumulation and clearance rates
            
            # Use recent history to estimate accumulation rate if available
            recent_exposures = self.exposure_history.get(substance_id, [])
            recent_exposures = sorted(recent_exposures, key=lambda x: x["timestamp"], reverse=True)
            
            if len(recent_exposures) > 0:
                # Use most recent exposure as a guide
                recent = recent_exposures[0]
                
                # Calculate effective accumulation rate based on recent exposure
                effective_rate = recent["concentration"] * recent["duration"] * profile.accumulation_rate
                
                # Use half-life for clearance rate
                clearance_rate = profile.elimination_rate
                
                # Get prediction from threshold system
                prediction = self.threshold_system.predict_threshold_crossing(
                    substance_id,
                    current_level,
                    effective_rate,
                    clearance_rate,
                    start_time,
                    max_prediction_time
                )
                
                if prediction:
                    return [prediction]
            
            return []
    
    def get_active_thresholds(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all currently active thresholds.
        
        Returns:
            Dictionary mapping substance IDs to threshold details
        """
        # First update all levels to current time
        self.update_current_levels()
        
        # Get active thresholds from threshold system
        return self.threshold_system.get_active_thresholds()
    
    def export_substance_history(
        self,
        substance_id: str,
        include_exposures: bool = True,
        include_thresholds: bool = True
    ) -> Dict[str, Any]:
        """
        Export history for a substance.
        
        Args:
            substance_id: Identifier for the substance
            include_exposures: Whether to include exposure history
            include_thresholds: Whether to include threshold crossings
            
        Returns:
            Dictionary with substance history
        """
        if substance_id not in self.substance_profiles:
            return {"substance_id": substance_id, "exists": False}
            
        # Update level to current time
        self.update_current_levels()
        
        # Get profile and current data
        profile = self.substance_profiles[substance_id]
        current_data = self.current_levels.get(substance_id, {"level": 0.0})
        
        # Build result
        result = {
            "substance_id": substance_id,
            "exists": True,
            "current_level": current_data["level"],
            "last_update": current_data["last_update"].isoformat(),
            "half_life": profile.half_life.total_seconds(),
            "accumulation_rate": profile.accumulation_rate,
            "model_type": profile.accumulation_model.name
        }
        
        # Add compartment data if available
        if profile.accumulation_model == AccumulationModelType.MULTI_COMPARTMENT:
            result["compartments"] = current_data.get("compartments", {})
            
        # Add exposure history if requested
        if include_exposures:
            result["exposure_history"] = self.exposure_history.get(substance_id, [])
            
        # Add threshold data if requested
        if include_thresholds:
            # Get threshold definitions
            if substance_id in self.threshold_system.threshold_registry:
                result["threshold"] = self.threshold_system.threshold_registry[substance_id]
                
            # Get threshold crossings
            crossings = []
            for crossing in self.threshold_system.crossing_history:
                if crossing.get("substance_id") == substance_id:
                    crossings.append(crossing)
            
            result["threshold_crossings"] = crossings
            
        return result


class CumulativeEffectVisualizer:
    """
    Visualization tools for cumulative effect data.
    
    Provides methods for plotting accumulation over time, threshold crossings,
    and predicted effects based on cumulative exposure patterns.
    """
    
    def __init__(self, model: CumulativeEffectModel):
        """
        Initialize with a cumulative effect model.
        
        Args:
            model: CumulativeEffectModel to visualize
        """
        self.model = model
    
    def plot_accumulation_curve(
        self,
        substance_id: str,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
        include_thresholds: bool = True,
        future_exposures: Optional[List[Dict[str, Any]]] = None,
        output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate data for plotting accumulation over time.
        
        Args:
            substance_id: Identifier for the substance
            start_time: Start time for the plot
            end_time: End time for the plot
            include_thresholds: Whether to include threshold lines
            future_exposures: Optional list of future exposure events
            output_file: Optional output file path
            
        Returns:
            Dictionary with plot data
        """
        if substance_id not in self.model.substance_profiles:
            return {"error": f"Substance '{substance_id}' not found"}
            
        # Set default time range if not provided
        if start_time is None:
            # Default to earliest exposure or 7 days ago
            exposures = self.model.exposure_history.get(substance_id, [])
            if exposures:
                # Get earliest exposure timestamp
                earliest = min(e["timestamp"] for e in exposures)
                start_time = earliest
            else:
                # Default to 7 days ago
                start_time = datetime.datetime.now() - datetime.timedelta(days=7)
                
        if end_time is None:
            # Default to 7 days in the future
            end_time = datetime.datetime.now() + datetime.timedelta(days=7)
            
        # Generate time points
        time_points = []
        current = start_time
        while current <= end_time:
            time_points.append(current)
            # Use 1-hour intervals for smoother plotting
            current += datetime.timedelta(hours=1)
            
        # Get historical levels (actual recorded exposures)
        historical_levels = {}
        
        # For each exposure, calculate level at that point
        exposures = sorted(self.model.exposure_history.get(substance_id, []), 
                          key=lambda x: x["timestamp"])
        
        current_level = 0.0
        last_time = start_time
        
        for exposure in exposures:
            time = exposure["timestamp"]
            if time < start_time:
                continue
            if time > end_time:
                break
                
            # If there's a gap, add clearance
            if time > last_time:
                profile = self.model.substance_profiles[substance_id]
                time_delta = time - last_time
                clearance = profile.calculate_clearance_rate(time_delta)
                current_level *= (1.0 - clearance)
                
            # Add this exposure
            concentration = exposure["concentration"]
            duration = exposure["duration"]
            profile = self.model.substance_profiles[substance_id]
            current_level += concentration * duration * profile.accumulation_rate
            
            # Record level
            historical_levels[time] = current_level
            last_time = time
            
        # Get predicted future levels
        future_levels = self.model.predict_future_levels(
            substance_id, time_points, future_exposures
        )
        
        # Get threshold information if requested
        thresholds = {}
        if include_thresholds and substance_id in self.model.threshold_system.threshold_registry:
            threshold_data = self.model.threshold_system.threshold_registry[substance_id]
            thresholds = {
                "value": threshold_data["value"],
                "description": threshold_data["description"],
                "severity": threshold_data["severity"]
            }
            
        # Combine data
        plot_data = {
            "substance_id": substance_id,
            "time_points": [t.isoformat() for t in time_points],
            "historical_levels": {t.isoformat(): level for t, level in historical_levels.items()},
            "predicted_levels": {t.isoformat(): level for t, level in future_levels.items()},
            "thresholds": thresholds
        }
        
        # Save to file if requested
        if output_file:
            try:
                import matplotlib.pyplot as plt
                import matplotlib.dates as mdates
                
                # Convert data for plotting
                times = [datetime.datetime.fromisoformat(t) for t in plot_data["time_points"]]
                levels = [plot_data["predicted_levels"].get(t, None) for t in plot_data["time_points"]]
                
                # Create plot
                plt.figure(figsize=(10, 6))
                plt.plot(times, levels, 'b-', label='Predicted Level')
                
                # Add historical points
                hist_times = [datetime.datetime.fromisoformat(t) for t in plot_data["historical_levels"].keys()]
                hist_levels = list(plot_data["historical_levels"].values())
                plt.scatter(hist_times, hist_levels, color='red', s=30, label='Recorded Exposures')
                
                # Add threshold line if available
                if thresholds:
                    threshold_value = thresholds["value"]
                    plt.axhline(y=threshold_value, color='r', linestyle='--', 
                               label=f'Threshold: {thresholds["description"]}')
                
                # Format plot
                plt.title(f'Cumulative Level for {substance_id}')
                plt.xlabel('Time')
                plt.ylabel('Accumulated Level')
                plt.legend()
                
                # Format x-axis
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
                plt.gcf().autofmt_xdate()
                
                # Save plot
                plt.tight_layout()
                plt.savefig(output_file)
                plt.close()
                
                plot_data["output_file"] = output_file
                
            except ImportError:
                plot_data["error"] = "Matplotlib required for plotting"
        
        return plot_data
