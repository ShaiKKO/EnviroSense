"""
Temporal response modeling for physiological systems.

This module provides the foundation for modeling delayed, chronic, and
cascading temporal effects of chemical exposures across physiological systems.
It extends the base physiological response framework with time-based models.

References:
- Cohen et al. (2023): "Delayed Onset of Chemical Effects in Biological Systems"
- WHO (2024): "Time-Course Dynamics of Toxicant Exposures"
- EPA (2023): "Chronic Exposure Assessment Guidelines"
"""

from typing import Dict, List, Optional, Union, Any, Tuple, Callable
import datetime
import numpy as np
import math
import uuid
from dataclasses import dataclass
from enum import Enum, auto
from collections import deque

from envirosense.core.exposure.physiological_response.base import (
    PhysiologicalResponseSystem,
    SystemOutput,
    ResponseSeverityLevel
)


class TemporalPattern(Enum):
    """
    Temporal response patterns for physiological systems.
    
    These patterns describe the time-course of responses to chemical exposures.
    """
    IMMEDIATE = auto()    # Rapid onset, rapid recovery
    DELAYED = auto()      # Delayed onset, variable recovery
    BIPHASIC = auto()     # Initial response followed by delayed secondary response
    CHRONIC = auto()      # Ongoing effects from cumulative exposure
    RECURRENT = auto()    # Effects that cycle through periods of intensity


@dataclass
class TemporalParameters:
    """
    Parameters defining the temporal characteristics of a response.
    
    Contains the timing parameters needed to model the time course of
    physiological responses to chemical exposures.
    """
    # Core timing parameters
    onset_delay: datetime.timedelta
    time_to_peak: datetime.timedelta
    recovery_duration: datetime.timedelta
    
    # Optional parameters for complex patterns
    effect_duration: Optional[datetime.timedelta] = None
    secondary_onset: Optional[datetime.timedelta] = None
    secondary_peak: Optional[datetime.timedelta] = None
    secondary_recovery: Optional[datetime.timedelta] = None
    
    # Pattern type
    pattern_type: TemporalPattern = TemporalPattern.IMMEDIATE
    
    # Chronic accumulation parameters
    accumulation_factor: float = 0.0  # How much prior exposure contributes to current response
    clearance_rate: float = 0.0       # Rate at which accumulated exposure clears
    
    # Metadata
    chemical_id: Optional[str] = None
    system_id: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values for derived fields."""
        if self.effect_duration is None:
            # Default duration is from onset to end of recovery
            self.effect_duration = self.onset_delay + self.time_to_peak + self.recovery_duration


class TemporalResponseMixin:
    """
    Mixin class adding temporal response capabilities to physiological systems.
    
    This mixin provides methods for calculating delayed and chronic responses,
    projecting response values over time, and modeling temporal effects.
    """
    
    def calculate_delayed_response(
        self,
        exposure_history: Dict[str, Any],
        sensitivity_profile: Optional[Dict[str, Any]] = None,
        temporal_params: Optional[TemporalParameters] = None,
        reference_time: Optional[datetime.datetime] = None
    ) -> SystemOutput:
        """
        Calculate delayed and chronic responses based on exposure history.
        
        This method extends the basic response calculation to incorporate
        delayed onset, chronic accumulation, and temporal patterns.
        
        Args:
            exposure_history: Dictionary containing exposure data
            sensitivity_profile: Optional dictionary with individual sensitivity factors
            temporal_params: Optional parameters for temporal response calculation
            reference_time: Optional reference time for calculations
            
        Returns:
            SystemOutput with temporal response information
        """
        # Get the base immediate response
        immediate_response = self.calculate_response(exposure_history, sensitivity_profile)
        
        # If no temporal parameters provided, try to calculate them
        if temporal_params is None:
            chemical_id = exposure_history.get("chemical_id", "unknown")
            temporal_params = self._get_temporal_parameters(
                chemical_id, immediate_response.response_value, sensitivity_profile
            )
        
        # Set reference time if not provided
        if reference_time is None:
            reference_time = datetime.datetime.now()
        
        # Calculate the delayed and chronic components
        delayed_response = self._calculate_delayed_component(
            immediate_response, temporal_params, exposure_history
        )
        
        chronic_response = self._calculate_chronic_component(
            immediate_response, temporal_params, exposure_history
        )
        
        # Combine the components based on the temporal pattern
        combined_response = self._combine_temporal_components(
            immediate_response, delayed_response, chronic_response, 
            temporal_params, reference_time
        )
        
        # Add temporal metadata
        combined_response.metadata["temporal_calculation"] = {
            "immediate_component": immediate_response.response_value,
            "delayed_component": delayed_response,
            "chronic_component": chronic_response,
            "pattern_type": temporal_params.pattern_type.name,
            "reference_time": reference_time.isoformat(),
        }
        
        return combined_response
    
    def project_response_over_time(
        self,
        exposure_history: Dict[str, Any],
        sensitivity_profile: Optional[Dict[str, Any]] = None,
        time_points: List[datetime.datetime] = None,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
        interval: Optional[datetime.timedelta] = None
    ) -> Dict[datetime.datetime, SystemOutput]:
        """
        Project response values over a specified time range.
        
        This method calculates the expected response at multiple time points,
        creating a time series of predicted responses.
        
        Args:
            exposure_history: Dictionary containing exposure data
            sensitivity_profile: Optional dictionary with individual sensitivity factors
            time_points: Optional list of specific time points to calculate
            start_time: Optional start time for the projection
            end_time: Optional end time for the projection
            interval: Optional interval between time points
            
        Returns:
            Dictionary mapping time points to SystemOutput objects
        """
        # Handle time points specification
        if time_points is None:
            if start_time is None:
                start_time = datetime.datetime.now()
                
            if end_time is None:
                # Default to projecting 24 hours
                end_time = start_time + datetime.timedelta(hours=24)
                
            if interval is None:
                # Default to 1-hour intervals
                interval = datetime.timedelta(hours=1)
                
            # Generate time points based on start, end, and interval
            current_time = start_time
            time_points = []
            while current_time <= end_time:
                time_points.append(current_time)
                current_time += interval
        
        # Get the base immediate response
        immediate_response = self.calculate_response(exposure_history, sensitivity_profile)
        
        # Get temporal parameters
        chemical_id = exposure_history.get("chemical_id", "unknown")
        temporal_params = self._get_temporal_parameters(
            chemical_id, immediate_response.response_value, sensitivity_profile
        )
        
        # Calculate response for each time point
        projected_responses = {}
        for time_point in time_points:
            projected_responses[time_point] = self.calculate_delayed_response(
                exposure_history, sensitivity_profile, temporal_params, time_point
            )
            
        return projected_responses
    
    def predict_time_to_response(
        self,
        exposure_history: Dict[str, Any],
        threshold: float,
        sensitivity_profile: Optional[Dict[str, Any]] = None,
        start_time: Optional[datetime.datetime] = None,
        max_prediction_time: Optional[datetime.timedelta] = None,
        confidence_level: float = 0.95
    ) -> Tuple[Optional[datetime.datetime], Optional[Tuple[datetime.datetime, datetime.datetime]]]:
        """
        Predict when a response will reach a specified threshold value.
        
        Args:
            exposure_history: Dictionary containing exposure data
            threshold: Response threshold to predict timing for
            sensitivity_profile: Optional dictionary with individual sensitivity factors
            start_time: Optional start time for the prediction
            max_prediction_time: Optional maximum prediction time horizon
            confidence_level: Confidence level for the prediction interval
            
        Returns:
            Tuple of (predicted_time, confidence_interval) where confidence_interval
            is a tuple of (earliest_time, latest_time)
        """
        if start_time is None:
            start_time = datetime.datetime.now()
            
        if max_prediction_time is None:
            # Default to 7 days maximum prediction horizon
            max_prediction_time = datetime.timedelta(days=7)
            
        # Get the base immediate response
        immediate_response = self.calculate_response(exposure_history, sensitivity_profile)
        
        # Get temporal parameters
        chemical_id = exposure_history.get("chemical_id", "unknown")
        temporal_params = self._get_temporal_parameters(
            chemical_id, immediate_response.response_value, sensitivity_profile
        )
        
        # If immediate response already exceeds threshold, return start time
        if immediate_response.response_value >= threshold:
            return start_time, (start_time, start_time)
        
        # Create a time series of projected responses to find threshold crossing
        end_time = start_time + max_prediction_time
        interval = max_prediction_time / 100  # Use 100 points for projection
        
        time_points = []
        current_time = start_time
        while current_time <= end_time:
            time_points.append(current_time)
            current_time += interval
            
        # Get response projections
        projections = self.project_response_over_time(
            exposure_history, sensitivity_profile, time_points
        )
        
        # Find threshold crossing
        crossing_time = None
        for time_point, response in sorted(projections.items()):
            if response.response_value >= threshold:
                crossing_time = time_point
                break
                
        # If no crossing found, return None
        if crossing_time is None:
            return None, None
            
        # Calculate confidence interval for the timing
        # Use system uncertainty to determine timing uncertainty
        uncertainty = getattr(self, 'uncertainty', 0.2)  # Default to 20% if not available
        
        # Calculate z-score for the confidence level
        if confidence_level == 0.95:
            z_score = 1.96
        elif confidence_level == 0.99:
            z_score = 2.58
        elif confidence_level == 0.90:
            z_score = 1.64
        else:
            # For other values, approximate the z-score
            z_score = 1.96  # Default to 95% confidence
            
        # Calculate time margin based on the pattern type
        if temporal_params.pattern_type == TemporalPattern.IMMEDIATE:
            time_margin = datetime.timedelta(minutes=30 * uncertainty * z_score)
        elif temporal_params.pattern_type == TemporalPattern.DELAYED:
            time_margin = datetime.timedelta(hours=2 * uncertainty * z_score)
        elif temporal_params.pattern_type == TemporalPattern.CHRONIC:
            time_margin = datetime.timedelta(hours=12 * uncertainty * z_score)
        else:
            time_margin = datetime.timedelta(hours=4 * uncertainty * z_score)
            
        # Calculate confidence interval for the crossing time
        earliest_time = crossing_time - time_margin
        latest_time = crossing_time + time_margin
        
        # Ensure the earliest time isn't before the start time
        earliest_time = max(earliest_time, start_time)
        
        return crossing_time, (earliest_time, latest_time)
    
    def _get_temporal_parameters(
        self,
        chemical_id: str,
        response_value: float,
        sensitivity_profile: Optional[Dict[str, Any]] = None
    ) -> TemporalParameters:
        """
        Get temporal parameters for a specific chemical and sensitivity profile.
        
        This is a placeholder method that should be implemented by subclasses.
        It should return appropriate temporal parameters based on the chemical
        and individual sensitivity factors.
        
        Args:
            chemical_id: ID of the chemical
            response_value: Base response value
            sensitivity_profile: Optional sensitivity profile
            
        Returns:
            TemporalParameters object
        """
        # This is a placeholder - concrete system implementations should override
        # with chemical-specific and system-specific parameters
        default_onset = datetime.timedelta(minutes=15)
        default_peak = datetime.timedelta(minutes=60)
        default_recovery = datetime.timedelta(minutes=240)
        
        return TemporalParameters(
            onset_delay=default_onset,
            time_to_peak=default_peak,
            recovery_duration=default_recovery,
            pattern_type=TemporalPattern.IMMEDIATE,
            chemical_id=chemical_id,
            system_id=getattr(self, 'name', 'unknown')
        )
    
    def _calculate_delayed_component(
        self,
        immediate_response: SystemOutput,
        temporal_params: TemporalParameters,
        exposure_history: Dict[str, Any]
    ) -> float:
        """
        Calculate the delayed component of a response.
        
        Args:
            immediate_response: Base immediate response
            temporal_params: Temporal parameters for the response
            exposure_history: Dictionary containing exposure data
            
        Returns:
            Delayed component value
        """
        if temporal_params.pattern_type == TemporalPattern.IMMEDIATE:
            return 0.0  # No delayed component for immediate responses
            
        # For delayed patterns, scaling depends on the chemical and response magnitude
        if temporal_params.pattern_type == TemporalPattern.DELAYED:
            # Delayed responses often have higher peak values 
            return immediate_response.response_value * 1.5
            
        elif temporal_params.pattern_type == TemporalPattern.BIPHASIC:
            # Biphasic responses typically have a secondary peak that's
            # either stronger or weaker than the initial peak
            
            # Get concentration for scaling
            concentration = exposure_history.get("concentration", 0.0)
            
            # Higher concentrations tend to produce stronger secondary responses
            if concentration > 10.0:
                # Strong secondary response
                return immediate_response.response_value * 1.8
            else:
                # Weaker secondary response
                return immediate_response.response_value * 0.7
                
        # Default for other patterns
        return immediate_response.response_value
    
    def _calculate_chronic_component(
        self,
        immediate_response: SystemOutput,
        temporal_params: TemporalParameters,
        exposure_history: Dict[str, Any]
    ) -> float:
        """
        Calculate the chronic component of a response.
        
        This applies accumulation factors for chemicals that produce
        effects from chronic exposure.
        
        Args:
            immediate_response: Base immediate response
            temporal_params: Temporal parameters for the response
            exposure_history: Dictionary containing exposure data
            
        Returns:
            Chronic component value
        """
        if temporal_params.pattern_type != TemporalPattern.CHRONIC:
            return 0.0  # No chronic component for non-chronic patterns
            
        # Get previous exposures if available
        previous_exposures = exposure_history.get("previous_exposures", [])
        
        # Calculate accumulated exposure
        accumulated_exposure = 0.0
        for prev_exposure in previous_exposures:
            # Get concentration and duration
            prev_concentration = prev_exposure.get("concentration", 0.0)
            prev_duration = prev_exposure.get("duration", 0.0)
            
            # Get the timestamp of the previous exposure
            prev_time = prev_exposure.get(
                "timestamp", 
                datetime.datetime.now() - datetime.timedelta(days=1)
            )
            
            # Calculate time since previous exposure
            time_since = datetime.datetime.now() - prev_time
            
            # Apply clearance rate based on time elapsed
            clearance_factor = math.exp(-temporal_params.clearance_rate * 
                                     time_since.total_seconds() / 86400.0)  # Convert to days
            
            # Add the contribution of this previous exposure
            accumulated_exposure += (prev_concentration * prev_duration * clearance_factor)
        
        # Apply accumulation factor to determine the chronic component
        return accumulated_exposure * temporal_params.accumulation_factor
    
    def _combine_temporal_components(
        self,
        immediate_response: SystemOutput,
        delayed_component: float,
        chronic_component: float,
        temporal_params: TemporalParameters,
        reference_time: datetime.datetime
    ) -> SystemOutput:
        """
        Combine temporal components into a final response.
        
        This method combines immediate, delayed, and chronic components
        based on the temporal pattern and reference time.
        
        Args:
            immediate_response: Base immediate response
            delayed_component: Calculated delayed component
            chronic_component: Calculated chronic component
            temporal_params: Temporal parameters for the response
            reference_time: Reference time for the calculation
            
        Returns:
            Combined SystemOutput with all temporal components
        """
        # Start with a copy of the immediate response
        result = SystemOutput(
            response_value=immediate_response.response_value,
            confidence_interval=immediate_response.confidence_interval,
            severity_level=immediate_response.severity_level,
            onset_time=immediate_response.onset_time,
            peak_time=immediate_response.peak_time,
            recovery_time=immediate_response.recovery_time,
            calculation_id=immediate_response.calculation_id,
            system_type=immediate_response.system_type,
            timestamp=immediate_response.timestamp,
            metadata=dict(immediate_response.metadata)
        )
        
        # Get exposure time from the immediate response metadata
        exposure_time = result.metadata.get(
            "exposure_time", 
            result.timestamp - datetime.timedelta(hours=1)
        )
        
        # Calculate time since exposure
        time_since_exposure = reference_time - exposure_time
        time_since_seconds = time_since_exposure.total_seconds()
        
        # Apply the appropriate temporal pattern
        if temporal_params.pattern_type == TemporalPattern.IMMEDIATE:
            # For immediate responses, the value decays after the peak
            if time_since_seconds < temporal_params.onset_delay.total_seconds():
                # Before onset, response is minimal
                scaling_factor = time_since_seconds / temporal_params.onset_delay.total_seconds()
                result.response_value *= max(0.1, scaling_factor)
                
            elif time_since_seconds < (temporal_params.onset_delay + temporal_params.time_to_peak).total_seconds():
                # During rise to peak, response increases
                result.response_value = result.response_value  # Already at appropriate value
                
            else:
                # After peak, response decays
                time_past_peak = time_since_seconds - (temporal_params.onset_delay + temporal_params.time_to_peak).total_seconds()
                decay_factor = math.exp(-0.7 * time_past_peak / temporal_params.recovery_duration.total_seconds())
                result.response_value *= max(0.1, decay_factor)
                
        elif temporal_params.pattern_type == TemporalPattern.DELAYED:
            # For delayed responses, there's a period of low response, then a delayed peak
            if time_since_seconds < temporal_params.onset_delay.total_seconds():
                # Before delayed onset, response is minimal
                result.response_value *= 0.1  # Just a minimal immediate effect
                
            elif time_since_seconds < (temporal_params.onset_delay + temporal_params.time_to_peak).total_seconds():
                # During rise to delayed peak
                time_into_rise = time_since_seconds - temporal_params.onset_delay.total_seconds()
                rise_factor = time_into_rise / temporal_params.time_to_peak.total_seconds()
                result.response_value = delayed_component * rise_factor
                
            else:
                # After delayed peak, response decays
                time_past_peak = time_since_seconds - (temporal_params.onset_delay + temporal_params.time_to_peak).total_seconds()
                decay_factor = math.exp(-0.5 * time_past_peak / temporal_params.recovery_duration.total_seconds())
                result.response_value = delayed_component * max(0.1, decay_factor)
                
        elif temporal_params.pattern_type == TemporalPattern.BIPHASIC:
            # Biphasic: initial peak, partial recovery, secondary peak
            
            # Calculate timing parameters
            initial_phase_duration = (temporal_params.onset_delay + 
                                    temporal_params.time_to_peak + 
                                    temporal_params.recovery_duration).total_seconds()
            
            if time_since_seconds < initial_phase_duration:
                # In the first phase, use the immediate response model
                if time_since_seconds < temporal_params.onset_delay.total_seconds():
                    # Before initial onset
                    scaling_factor = time_since_seconds / temporal_params.onset_delay.total_seconds()
                    result.response_value *= max(0.1, scaling_factor)
                    
                elif time_since_seconds < (temporal_params.onset_delay + temporal_params.time_to_peak).total_seconds():
                    # Rising to initial peak
                    result.response_value = result.response_value  # Already at appropriate value
                    
                else:
                    # Decaying from initial peak
                    time_past_peak = time_since_seconds - (temporal_params.onset_delay + temporal_params.time_to_peak).total_seconds()
                    decay_factor = math.exp(-1.0 * time_past_peak / temporal_params.recovery_duration.total_seconds())
                    result.response_value *= max(0.3, decay_factor)  # Don't decay fully, maintain some response
                
            elif time_since_seconds < (initial_phase_duration + temporal_params.secondary_onset.total_seconds()):
                # Between phases, maintain the residual response
                result.response_value *= 0.3  # Residual from first phase
                
            elif time_since_seconds < (initial_phase_duration + 
                                     temporal_params.secondary_onset.total_seconds() + 
                                     temporal_params.secondary_peak.total_seconds()):
                # Rising to secondary peak
                time_into_rise = time_since_seconds - (initial_phase_duration + temporal_params.secondary_onset.total_seconds())
                rise_factor = time_into_rise / temporal_params.secondary_peak.total_seconds()
                result.response_value = delayed_component * rise_factor
                
            else:
                # Decaying from secondary peak
                time_past_peak = (time_since_seconds - initial_phase_duration - 
                                temporal_params.secondary_onset.total_seconds() - 
                                temporal_params.secondary_peak.total_seconds())
                decay_factor = math.exp(-0.4 * time_past_peak / temporal_params.secondary_recovery.total_seconds())
                result.response_value = delayed_component * max(0.1, decay_factor)
                
        elif temporal_params.pattern_type == TemporalPattern.CHRONIC:
            # For chronic responses, add the accumulated chronic component
            # Base response from immediate effects
            immediate_contribution = immediate_response.response_value
            
            # Add chronic component
            result.response_value = immediate_contribution + chronic_component
            
        elif temporal_params.pattern_type == TemporalPattern.RECURRENT:
            # Recurrent: cycles of symptoms with peaks and valleys
            # Implement as a damped oscillation
            
            # Base period of oscillation (in seconds)
            oscillation_period = 3600.0  # Default 1 hour
            
            # Calculate the oscillation using a damped sine wave
            oscillation = math.sin(2 * math.pi * time_since_seconds / oscillation_period)
            damping = math.exp(-0.05 * time_since_seconds / 3600.0)  # Slow damping
            
            # Apply oscillation to the response value
            result.response_value *= (0.7 + 0.3 * oscillation * damping)
        
        # Update severity level based on the new response value
        system = getattr(self, 'system', self)
        result.severity_level = system.classify_severity(result.response_value)
        
        # Update confidence interval
        result.confidence_interval = system.calculate_confidence_interval(result.response_value)
        
        return result


class PhysiologicalEffectGraph:
    """
    Directed graph of physiological effects with temporal relationships.
    
    This class models cascading effects between different physiological systems,
    incorporating time delays and effect magnitudes using an efficient
    adjacency list implementation.
    """
    
    def __init__(self):
        """Initialize an empty physiological effect graph."""
        # Adjacency list representation: 
        # {node_id: [(target_node_id, temporal_delay, effect_magnitude), ...]}
        self.adj_list = {}
        
        # Node attributes containing physiological system metadata
        self.nodes = {}
        
        # Cache for cascade calculations
        self._cascade_cache = {}
    
    def add_node(
        self, 
        node_id: str, 
        system_type: str, 
        response_characteristics: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a physiological response node to the graph.
        
        Args:
            node_id: Unique identifier for the node
            system_type: Type of physiological system
            response_characteristics: Optional characteristics of the system
        """
        if node_id not in self.nodes:
            self.nodes[node_id] = {
                'system_type': system_type,
                'characteristics': response_characteristics or {}
            }
            self.adj_list[node_id] = []
            
            # Invalidate cache when graph structure changes
            self._cascade_cache = {}
    
    def add_edge(
        self, 
        source_node: str, 
        target_node: str, 
        temporal_delay: datetime.timedelta, 
        effect_magnitude: float = 1.0
    ) -> None:
        """
        Add a directed edge representing a causal relationship with temporal delay.
        
        Args:
            source_node: Source node identifier
            target_node: Target node identifier
            temporal_delay: Time delay for the effect
            effect_magnitude: Magnitude of the effect (0-2, where 1 is normal)
        """
        if source_node in self.adj_list and target_node in self.nodes:
            # Store tuple of (target, delay, magnitude)
            self.adj_list[source_node].append(
                (target_node, temporal_delay, effect_magnitude)
            )
            
            # Invalidate cache when graph structure changes
            self._cascade_cache = {}
    
    def get_cascade_effects(
        self, 
        source_node: str, 
        time_point: datetime.datetime,
        initial_time: Optional[datetime.datetime] = None,
        max_depth: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Calculate cascading effects at a specific time point.
        
        Args:
            source_node: Source node to start cascade calculation from
            time_point: Time point to calculate effects at
            initial_time: Optional starting time (defaults to time_point - 24h)
            max_depth: Optional maximum cascade depth
            
        Returns:
            Dictionary mapping node IDs to effect magnitudes
        """
        if source_node not in self.adj_list:
            return {}
            
        if initial_time is None:
            initial_time = time_point - datetime.timedelta(hours=24)
            
        # Check cache for this calculation
        cache_key = (source_node, time_point, initial_time, max_depth)
        if cache_key in self._cascade_cache:
            return self._cascade_cache[cache_key]
        
        # Initialize results
        results = {}
        
        # Use breadth-first search to traverse the graph
        # This works better than DFS for time-based propagation
        visited = set()
        queue = deque([(source_node, initial_time, 0, 1.0, [source_node])])
        
        while queue:
            node, current_time, current_depth, path_magnitude, path = queue.popleft()
            
            # Skip if we've reached max depth
            if max_depth is not None and current_depth > max_depth:
                continue
                
            # Record effect at this node if the time is valid
            if current_time <= time_point:
                time_delta = (time_point - current_time).total_seconds()
                effect = self._calculate_effect_at_time(node, time_delta, path_magnitude)
                
                if node in results:
                    # Take the largest effect if multiple paths lead to this node
                    results[node] = max(results[node], effect)
                else:
                    results[node] = effect
                    
                # For debugging, store the path that led to this effect
                if "paths" not in results:
                    results["paths"] = {}
                    
                results["paths"][node] = path
            
            # Skip further exploration if this node was visited with a stronger effect
            if node in visited:
                continue
                
            visited.add(node)
            
            # Explore outgoing edges (cascade effects)
            for target, delay, magnitude in self.adj_list[node]:
                # Calculate the time when this effect reaches the target
                next_time = current_time + delay
                
                # Calculate the cascaded magnitude
                # Use multiplicative model for magnitude propagation
                next_magnitude = path_magnitude * magnitude
                
                # Only follow if the delay doesn't exceed our time horizon
                if next_time <= time_point:
                    queue.append(
                        (target, next_time, current_depth + 1, next_magnitude, path + [target])
                    )
        
        # Cache the result
        self._cascade_cache[cache_key] = results
        return results
    
    def _calculate_effect_at_time(
        self, 
        node: str, 
        time_delta_seconds: float, 
        magnitude: float
    ) -> float:
        """
        Calculate the effect strength based on time since activation.
        
        Args:
            node: Node identifier
            time_delta_seconds: Seconds since the node was activated
            magnitude: Base magnitude of the effect
            
        Returns:
            Calculated effect strength at the specified time
        """
        # Get response characteristics for this node
        characteristics = self.nodes[node]['characteristics']
        
        # Get the onset, peak, and recovery durations (in seconds)
        onset_seconds = characteristics.get('onset_seconds', 900)  # Default 15 minutes
        peak_seconds = characteristics.get('peak_seconds', 3600)  # Default 1 hour
        recovery_seconds = characteristics.get('recovery_seconds', 14400)  # Default 4 hours
        
        # Get system type to determine appropriate response curve
        system_type = self.nodes[node]['system_type']
        
        # Apply the appropriate temporal response curve
        if time_delta_seconds < 0:
            # Future events have no effect
            return 0.0
            
        elif time_delta_seconds < onset_seconds:
            # During onset phase, effect gradually increases
            progress = time_delta_seconds / onset_seconds
            # Use sigmoid curve for smooth onset
            effect = magnitude * (1 / (1 + math.exp(-10 * (progress - 0.5))))
            return effect
            
        elif time_delta_seconds < (onset_seconds + peak_seconds):
            # At peak effect
            return magnitude
            
        else:
            # In recovery/decay phase
            time_past_peak = time_delta_seconds - (onset_seconds + peak_seconds)
            
            # Apply system-specific decay patterns
            if system_type.lower() in ['respiratory', 'pulmonary']:
                # Respiratory effects often follow exponential decay
                decay_factor = math.exp(-3.0 * time_past_peak / recovery_seconds)
            elif system_type.lower() in ['neurological', 'nervous']:
                # Neurological effects may have longer tails
                decay_factor = math.exp(-2.0 * time_past_peak / recovery_seconds)
            elif system_type.lower() in ['cardiovascular', 'cardiac']:
                # Cardiovascular effects may oscillate during recovery
                base_decay = math.exp(-2.5 * time_past_peak / recovery_seconds)
                oscillation = 0.2 * math.sin(2 * math.pi * time_past_peak / 1800)  # 30-min cycle
                decay_factor = base_decay * (1 + oscillation)
            else:
                # Default decay pattern
                decay_factor = math.exp(-2.5 * time_past_peak / recovery_seconds)
                
            return magnitude * max(0.0, decay_factor)


class TemporalSystemSet:
    """
    Extension of PhysiologicalSystemSet with temporal cascade capabilities.
    
    This class integrates the PhysiologicalEffectGraph with the existing
    system set, providing methods for time-based cascade analysis.
    """
    
    def __init__(self, system_set):
        """
        Initialize with an existing PhysiologicalSystemSet.
        
        Args:
            system_set: Existing PhysiologicalSystemSet to enhance
        """
        self.system_set = system_set
        self.effect_graph = PhysiologicalEffectGraph()
        
        # Initialize the effect graph from the system set
        self._initialize_graph()
    
    def _initialize_graph(self):
        """
        Initialize the effect graph based on the system set.
        
        Creates nodes for each physiological system and edges based on
        the interaction matrix.
        """
        # Add nodes for each system
        for system_name, system in self.system_set._system_map.items():
            # Extract temporal characteristics if available
            characteristics = {}
            
            # If system implements get_temporal_characteristics method
            if hasattr(system, 'get_temporal_characteristics'):
                characteristics = system.get_temporal_characteristics()
            else:
                # Extract from typical response timing
                sample_exposure = {"chemical_id": "default", "concentration": 10.0, "duration": 1.0}
                try:
                    # Try to get timing information from the system
                    onset, peak, recovery = system._calculate_response_timing(
                        50.0, "default", sample_exposure, None
                    )
                    
                    # Convert timedeltas to seconds
                    characteristics = {
                        'onset_seconds': onset.total_seconds() if onset else 900,
                        'peak_seconds': peak.total_seconds() if peak else 3600,
                        'recovery_seconds': recovery.total_seconds() if recovery else 14400
                    }
                except:
                    # Use default characteristics if timing calculation fails
                    characteristics = {
                        'onset_seconds': 900,  # 15 minutes
                        'peak_seconds': 3600,  # 1 hour
                        'recovery_seconds': 14400  # 4 hours
                    }
            
            # Add the node to the graph
            self.effect_graph.add_node(
                system_name,
                system_type=type(system).__name__,
                response_characteristics=characteristics
            )
            
        # Add edges based on the interaction matrix
        if hasattr(self.system_set, 'interaction_matrix'):
            for source, targets in self.system_set.interaction_matrix.items():
                for target, factor in targets.items():
                    # Calculate appropriate delay based on system types
                    delay = self._estimate_delay(source, target)
                    
                    # Add the edge with the delay and factor
                    self.effect_graph.add_edge(
                        source,
                        target,
                        temporal_delay=delay,
                        effect_magnitude=factor
                    )
    
    def _estimate_delay(self, source_system: str, target_system: str) -> datetime.timedelta:
        """
        Estimate the temporal delay between effects in two systems.
        
        Args:
            source_system: Source system name
            target_system: Target system name
            
        Returns:
            Estimated delay as a timedelta
        """
        # Get the system types
        source_type = type(self.system_set._system_map.get(source_system)).__name__
        target_type = type(self.system_set._system_map.get(target_system)).__name__
        
        # Define known delays between system types
        system_delays = {
            # Format: (source_type, target_type): minutes
            ('RespiratoryResponseSystem', 'NeurologicalResponseSystem'): 10,
            ('RespiratoryResponseSystem', 'CardiovascularResponseSystem'): 5,
            ('NeurologicalResponseSystem', 'RespiratoryResponseSystem'): 15,
            ('CardiovascularResponseSystem', 'NeurologicalResponseSystem'): 8,
            # Add more known delays as needed
        }
        
        # Get the delay if known, otherwise use default
        delay_minutes = system_delays.get(
            (source_type, target_type), 
            30  # Default 30 minute delay
        )
        
        return datetime.timedelta(minutes=delay_minutes)
    
    def calculate_temporal_cascade(
        self,
        initial_system: str,
        exposure_history: Dict[str, Any],
        sensitivity_profile: Optional[Dict[str, Any]] = None,
        time_points: Optional[List[datetime.datetime]] = None,
        reference_time: Optional[datetime.datetime] = None
    ) -> Dict[datetime.datetime, Dict[str, SystemOutput]]:
        """
        Calculate how responses cascade through systems over time.
        
        Args:
            initial_system: Name of the system where the cascade starts
            exposure_history: Dictionary containing exposure data
            sensitivity_profile: Optional individual sensitivity factors
            time_points: Optional list of time points to calculate for
            reference_time: Optional reference time (defaults to now)
            
        Returns:
            Dictionary mapping time points to system responses
        """
        if reference_time is None:
            reference_time = datetime.datetime.now()
            
        if time_points is None:
            # Default: calculate for 1, 2, 4, 8, 16, 24, 48 hours
            time_points = [
                reference_time + datetime.timedelta(hours=hours)
                for hours in [1, 2, 4, 8, 16, 24, 48]
            ]
        
        # Get initial system response
        initial_system_obj = self.system_set._system_map.get(initial_system)
        if not initial_system_obj:
            raise ValueError(f"System '{initial_system}' not found")
            
        initial_response = initial_system_obj.calculate_response(
            exposure_history, sensitivity_profile
        )
        
        # Calculate cascades for each time point
        results = {}
        for time_point in time_points:
            # Get cascade effects at this time point
            cascade_effects = self.effect_graph.get_cascade_effects(
                initial_system,
                time_point,
                initial_time=reference_time
            )
            
            # Calculate responses for each affected system
            time_responses = {}
            for system_name, effect_magnitude in cascade_effects.items():
                if system_name == "paths":  # Skip the debug data
                    continue
                    
                # Get the original system
                system = self.system_set._system_map.get(system_name)
                if not system:
                    continue
                    
                # Calculate the modified response based on the effect magnitude
                if system_name == initial_system:
                    # For the initial system, use its direct response with temporal projection
                    if hasattr(system, 'calculate_delayed_response'):
                        response = system.calculate_delayed_response(
                            exposure_history, 
                            sensitivity_profile,
                            reference_time=time_point
                        )
                    else:
                        # Fall back to immediate response
                        response = initial_response
                else:
                    # For secondary systems, scale based on the cascade effect magnitude
                    # Create a proxy exposure representing the cascaded effect
                    proxy_exposure = dict(exposure_history)
                    # Scale concentration based on the effect magnitude
                    proxy_exposure["concentration"] = proxy_exposure.get("concentration", 1.0) * effect_magnitude
                    
                    # Calculate the response based on this proxy exposure
                    response = system.calculate_response(proxy_exposure, sensitivity_profile)
                    
                    # Add metadata about the cascade
                    response.metadata["cascade_source"] = initial_system
                    response.metadata["cascade_magnitude"] = effect_magnitude
                    response.metadata["cascade_path"] = cascade_effects.get("paths", {}).get(system_name, [])
                
                time_responses[system_name] = response
            
            results[time_point] = time_responses
            
        return results
    
    def predict_system_responses(
        self,
        exposure_history: Dict[str, Any],
        sensitivity_profile: Optional[Dict[str, Any]] = None,
        target_systems: Optional[List[str]] = None,
        threshold_levels: Optional[Dict[str, float]] = None,
        max_prediction_time: Optional[datetime.timedelta] = None
    ) -> Dict[str, Tuple[datetime.datetime, float]]:
        """
        Predict when each system will reach a response threshold.
        
        Args:
            exposure_history: Dictionary containing exposure data
            sensitivity_profile: Optional individual sensitivity factors
            target_systems: Optional list of systems to predict for (defaults to all)
            threshold_levels: Optional dictionary mapping systems to threshold values
            max_prediction_time: Optional maximum prediction time horizon
            
        Returns:
            Dictionary mapping system names to (predicted_time, confidence) tuples
        """
        if max_prediction_time is None:
            max_prediction_time = datetime.timedelta(days=7)
            
        if target_systems is None:
            # Use all systems
            target_systems = list(self.system_set._system_map.keys())
            
        reference_time = datetime.datetime.now()
        
        # Create default thresholds if not provided
        if threshold_levels is None:
            threshold_levels = {}
            for system_name in target_systems:
                system = self.system_set._system_map.get(system_name)
                if system and hasattr(system, 'thresholds'):
                    # Use the MODERATE threshold as default
                    for level, value in system.thresholds.items():
                        if level.name == 'MODERATE':
                            threshold_levels[system_name] = value
                            break
                    else:
                        # If no MODERATE threshold, use first threshold found
                        if system.thresholds:
                            threshold_levels[system_name] = next(iter(system.thresholds.values()))
                        else:
                            # Default threshold of 50 if no thresholds defined
                            threshold_levels[system_name] = 50.0
                else:
                    # Default threshold of 50 if no system thresholds
                    threshold_levels[system_name] = 50.0
        
        # Calculate predictions for each system
        predictions = {}
        for system_name in target_systems:
            system = self.system_set._system_map.get(system_name)
            if not system:
                continue
                
            threshold = threshold_levels.get(system_name, 50.0)
            
            # If system has predict_time_to_response method, use it
            if hasattr(system, 'predict_time_to_response'):
                predicted_time, confidence_interval = system.predict_time_to_response(
                    exposure_history,
                    threshold,
                    sensitivity_profile,
                    start_time=reference_time,
                    max_prediction_time=max_prediction_time
                )
                
                # Calculate confidence value from interval width
                if predicted_time and confidence_interval:
                    interval_width = (confidence_interval[1] - confidence_interval[0]).total_seconds()
                    total_time = (predicted_time - reference_time).total_seconds()
                    confidence = 1.0 - min(1.0, interval_width / (total_time * 2))
                else:
                    confidence = 0.0
                    
                predictions[system_name] = (predicted_time, confidence)
            else:
                # No prediction capability for this system
                predictions[system_name] = (None, 0.0)
        
        return predictions
