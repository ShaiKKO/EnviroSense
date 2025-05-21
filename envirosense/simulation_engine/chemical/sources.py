"""
EnviroSense Chemical Sources

This module provides classes for simulating various chemical sources in an environmental
simulation. Sources can emit chemicals according to different patterns (constant, pulsed,
decaying, etc.) and can be affected by environmental conditions.

Each source type provides an emit() method that calculates the emission rate at a given
time step, considering environmental factors like temperature and humidity.
"""

import math
import numpy as np
from datetime import datetime, timedelta
from enum import Enum, auto
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Union, Any

from envirosense.core.physics.coordinates import Vector3D
from envirosense.core.chemical.chemical_properties import (
    ChemicalCategory, 
    CHEMICAL_PROPERTIES,
    get_chemical_property
)


class SourceStatus(Enum):
    """Possible statuses for a chemical source."""
    ACTIVE = auto()      # Source is actively emitting
    INACTIVE = auto()    # Source is temporarily dormant but can be activated
    DEPLETED = auto()    # Source has been fully depleted
    DISABLED = auto()    # Source has been manually disabled
    ERROR = auto()       # Source has encountered an error


class ChemicalSource(ABC):
    """
    Base class for all chemical sources in the simulation.
    
    A chemical source emits a specific chemical at a specific location
    according to a defined pattern. The emission rate may be affected by
    environmental conditions like temperature and humidity.
    """
    
    def __init__(
        self,
        source_id: str,
        position: Union[Tuple[float, float, float], Vector3D],
        chemical_id: str,
        initial_strength: float,
        properties: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a chemical source.
        
        Args:
            source_id: Unique identifier for this source
            position: 3D position (x, y, z) in the environment
            chemical_id: Identifier for the chemical being emitted
            initial_strength: Initial emission strength in appropriate units
                (typically g/s for gases, mg/s for particulates)
            properties: Additional source-specific properties
        """
        self.source_id = source_id
        
        # Convert position to Vector3D if it's a tuple
        if isinstance(position, tuple):
            self.position = Vector3D(*position)
        else:
            self.position = position
            
        # Validate chemical ID exists in database
        if chemical_id not in CHEMICAL_PROPERTIES:
            raise ValueError(f"Unknown chemical ID: {chemical_id}")
        
        self.chemical_id = chemical_id
        self.initial_strength = initial_strength
        self.current_strength = initial_strength
        self.properties = properties or {}
        
        # Set default properties if not provided
        self.properties.setdefault("radius", 0.1)  # Default radius of influence in meters
        self.properties.setdefault("temperature_sensitive", True)
        self.properties.setdefault("humidity_sensitive", True)
        
        self.creation_time = datetime.now()
        self.activation_time = self.creation_time
        self.last_emission_time = None
        self.total_emitted = 0.0  # Total amount emitted over lifetime
        self.status = SourceStatus.ACTIVE
        
        # Get chemical properties
        self.chemical_properties = CHEMICAL_PROPERTIES.get(chemical_id, {})
        
    @abstractmethod
    def emit(self, time_step: float, environment: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate emission rate for this time step.
        
        Args:
            time_step: Time step in seconds
            environment: Environment conditions at the source location,
                typically including temperature, humidity, etc.
        
        Returns:
            Emission rate in appropriate units (g/s for gases, mg/s for particulates)
        """
        pass
    
    def get_temperature_factor(self, temperature: float) -> float:
        """
        Calculate how temperature affects the emission rate.
        
        Args:
            temperature: Current temperature in Celsius
        
        Returns:
            Scaling factor for emission rate due to temperature
        """
        if not self.properties.get("temperature_sensitive", True):
            return 1.0
            
        temp_scaling = self.chemical_properties.get("temperature_scaling", {})
        scaling_type = temp_scaling.get("type", "linear")
        
        if scaling_type == "linear":
            # Linear scaling based on temperature difference from reference
            slope = temp_scaling.get("slope", 0.02)  # Default: 2% per °C
            ref_temp = temp_scaling.get("reference_temp", 25.0)
            return 1.0 + slope * (temperature - ref_temp)
            
        elif scaling_type == "arrhenius":
            # Arrhenius equation: rate ∝ exp(-Ea/RT)
            activation_energy = temp_scaling.get("activation_energy", 50.0)  # kJ/mol
            ref_temp = temp_scaling.get("reference_temp", 298.15)  # K
            scaling_factor = temp_scaling.get("scaling_factor", 2.0)
            
            # Convert to Kelvin
            temp_k = temperature + 273.15
            
            # Universal gas constant (R) = 8.314 J/(mol·K)
            R = 8.314 / 1000  # Convert to kJ/(mol·K)
            
            # Calculate relative rates at two temperatures using Arrhenius
            return math.exp((activation_energy / R) * (1/ref_temp - 1/temp_k))
            
        elif scaling_type == "complex":
            # Use reference curve with interpolation
            ref_curve = temp_scaling.get("reference_curve", [(0, 0.5), (25, 1.0), (50, 2.0)])
            
            # Sort by temperature
            ref_curve.sort(key=lambda x: x[0])
            
            # Find appropriate interval and interpolate
            for i in range(len(ref_curve) - 1):
                t1, f1 = ref_curve[i]
                t2, f2 = ref_curve[i + 1]
                
                if t1 <= temperature <= t2:
                    # Linear interpolation
                    return f1 + (f2 - f1) * (temperature - t1) / (t2 - t1)
            
            # Outside range, use endpoint
            if temperature < ref_curve[0][0]:
                return ref_curve[0][1]
            else:
                return ref_curve[-1][1]
        
        # For minimal or other types, use simple factor
        return 1.0 + temp_scaling.get("factor", 0.01) * (temperature - 25.0)
    
    def get_humidity_factor(self, relative_humidity: float) -> float:
        """
        Calculate how humidity affects the emission rate.
        
        Args:
            relative_humidity: Current relative humidity (0-100%)
        
        Returns:
            Scaling factor for emission rate due to humidity
        """
        if not self.properties.get("humidity_sensitive", True):
            return 1.0
            
        # Get humidity effect coefficient (0-1 scale, higher means more affected)
        humidity_effect = self.chemical_properties.get("humidity_effect", 0.2)
        
        # For most chemicals, higher humidity increases emissions
        # Scale is from 0.8 (at 0% RH) to 1.5 (at 100% RH) for humidity_effect=1.0
        humidity_factor = 0.8 + (0.7 * humidity_effect * relative_humidity / 100.0)
        
        return humidity_factor
    
    def deactivate(self) -> None:
        """Deactivate the source temporarily."""
        self.status = SourceStatus.INACTIVE
    
    def activate(self) -> None:
        """Activate the source."""
        self.status = SourceStatus.ACTIVE
        self.activation_time = datetime.now()
    
    def set_depleted(self) -> None:
        """Mark the source as depleted (cannot emit anymore)."""
        self.status = SourceStatus.DEPLETED
        self.current_strength = 0.0
    
    def is_active(self) -> bool:
        """Check if the source is currently active."""
        return self.status == SourceStatus.ACTIVE
    
    def get_remaining_capacity(self) -> Optional[float]:
        """
        Get remaining capacity if the source has a finite capacity.
        
        Returns:
            Remaining capacity or None if infinite
        """
        total_capacity = self.properties.get("total_capacity")
        
        if total_capacity is not None:
            return max(0.0, total_capacity - self.total_emitted)
        
        return None


class ConstantSource(ChemicalSource):
    """
    A chemical source that emits at a constant rate.
    
    The emission rate may still be affected by environmental factors
    like temperature and humidity, but the base rate remains constant.
    """
    
    def emit(self, time_step: float, environment: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate emission for this time step.
        
        Args:
            time_step: Time step in seconds
            environment: Environment conditions (temperature, humidity, etc.)
        
        Returns:
            Emission rate in appropriate units
        """
        if not self.is_active():
            return 0.0
            
        # Default environmental conditions if not provided
        if environment is None:
            environment = {"temperature": 25.0, "relative_humidity": 50.0}
            
        # Apply environmental factors
        temperature_factor = self.get_temperature_factor(environment.get("temperature", 25.0))
        humidity_factor = self.get_humidity_factor(environment.get("relative_humidity", 50.0))
        
        # Calculate emission rate
        emission_rate = self.current_strength * temperature_factor * humidity_factor
        
        # Update total emitted
        emitted_amount = emission_rate * time_step
        self.total_emitted += emitted_amount
        self.last_emission_time = datetime.now()
        
        # Check if source is depleted (if it has a finite capacity)
        total_capacity = self.properties.get("total_capacity")
        if total_capacity is not None and self.total_emitted >= total_capacity:
            self.set_depleted()
            
        return emission_rate


class PulsedSource(ChemicalSource):
    """
    A chemical source that emits in pulses with a defined frequency.
    
    The source alternates between active and inactive states based on
    the defined pulse period and duty cycle.
    """
    
    def __init__(
        self,
        source_id: str,
        position: Union[Tuple[float, float, float], Vector3D],
        chemical_id: str,
        initial_strength: float,
        pulse_period: float,
        duty_cycle: float = 0.5,
        properties: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a pulsed chemical source.
        
        Args:
            source_id: Unique identifier for this source
            position: 3D position (x, y, z) in the environment
            chemical_id: Identifier for the chemical being emitted
            initial_strength: Initial emission strength
            pulse_period: Period of the pulse in seconds
            duty_cycle: Fraction of the period the source is active (0-1)
            properties: Additional source-specific properties
        """
        super().__init__(source_id, position, chemical_id, initial_strength, properties)
        
        self.pulse_period = pulse_period
        self.duty_cycle = max(0.0, min(1.0, duty_cycle))  # Clamp to 0-1
        self.active_time = self.pulse_period * self.duty_cycle
        self.elapsed_time = 0.0
        
    def emit(self, time_step: float, environment: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate emission for this time step based on the pulse pattern.
        
        Args:
            time_step: Time step in seconds
            environment: Environment conditions (temperature, humidity, etc.)
        
        Returns:
            Emission rate in appropriate units
        """
        if not self.is_active():
            return 0.0
            
        # Update elapsed time in the current cycle
        self.elapsed_time = (self.elapsed_time + time_step) % self.pulse_period
        
        # Determine if we're in the active part of the cycle
        if self.elapsed_time <= self.active_time:
            # During active part of the pulse
            
            # Default environmental conditions if not provided
            if environment is None:
                environment = {"temperature": 25.0, "relative_humidity": 50.0}
                
            # Apply environmental factors
            temperature_factor = self.get_temperature_factor(environment.get("temperature", 25.0))
            humidity_factor = self.get_humidity_factor(environment.get("relative_humidity", 50.0))
            
            # Calculate emission rate
            emission_rate = self.current_strength * temperature_factor * humidity_factor
            
            # Update total emitted
            emitted_amount = emission_rate * time_step
            self.total_emitted += emitted_amount
            self.last_emission_time = datetime.now()
            
            # Check if source is depleted (if it has a finite capacity)
            total_capacity = self.properties.get("total_capacity")
            if total_capacity is not None and self.total_emitted >= total_capacity:
                self.set_depleted()
                
            return emission_rate
        else:
            # During inactive part of the pulse
            return 0.0


class DecayingSource(ChemicalSource):
    """
    A chemical source that starts strong and decays over time.
    
    The emission rate decreases according to an exponential decay model.
    """
    
    def __init__(
        self,
        source_id: str,
        position: Union[Tuple[float, float, float], Vector3D],
        chemical_id: str,
        initial_strength: float,
        half_life: float,
        properties: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a decaying chemical source.
        
        Args:
            source_id: Unique identifier for this source
            position: 3D position (x, y, z) in the environment
            chemical_id: Identifier for the chemical being emitted
            initial_strength: Initial emission strength
            half_life: Time in seconds for strength to reduce by half
            properties: Additional source-specific properties
        """
        super().__init__(source_id, position, chemical_id, initial_strength, properties)
        
        self.half_life = half_life
        # Calculate decay constant (lambda) from half-life
        # Using formula: half_life = ln(2) / lambda
        self.decay_constant = math.log(2) / half_life
        self.time_elapsed = 0.0
        
    def emit(self, time_step: float, environment: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate emission for this time step based on exponential decay.
        
        Args:
            time_step: Time step in seconds
            environment: Environment conditions (temperature, humidity, etc.)
        
        Returns:
            Emission rate in appropriate units
        """
        if not self.is_active():
            return 0.0
            
        # Update elapsed time
        self.time_elapsed += time_step
        
        # Calculate decayed strength using exponential decay model
        # S(t) = S₀ * e^(-λt)
        decayed_strength = self.initial_strength * math.exp(-self.decay_constant * self.time_elapsed)
        self.current_strength = decayed_strength
        
        # If strength has decayed below a threshold, consider depleted
        depletion_threshold = self.properties.get("depletion_threshold", 0.01)
        if decayed_strength < self.initial_strength * depletion_threshold:
            self.set_depleted()
            return 0.0
            
        # Default environmental conditions if not provided
        if environment is None:
            environment = {"temperature": 25.0, "relative_humidity": 50.0}
            
        # Apply environmental factors
        temperature_factor = self.get_temperature_factor(environment.get("temperature", 25.0))
        humidity_factor = self.get_humidity_factor(environment.get("relative_humidity", 50.0))
        
        # Calculate emission rate
        emission_rate = decayed_strength * temperature_factor * humidity_factor
        
        # Update total emitted
        emitted_amount = emission_rate * time_step
        self.total_emitted += emitted_amount
        self.last_emission_time = datetime.now()
        
        # Check if source is depleted (if it has a finite capacity)
        total_capacity = self.properties.get("total_capacity")
        if total_capacity is not None and self.total_emitted >= total_capacity:
            self.set_depleted()
            
        return emission_rate


class DiurnalSource(ChemicalSource):
    """
    A chemical source that varies emission by time of day.
    
    The emission rate follows a sinusoidal pattern with peak and trough
    at configurable times, simulating day/night cycles.
    """
    
    def __init__(
        self,
        source_id: str,
        position: Union[Tuple[float, float, float], Vector3D],
        chemical_id: str,
        initial_strength: float,
        peak_hour: int = 15,  # 3 PM default peak
        trough_hour: int = 3,  # 3 AM default trough
        min_factor: float = 0.2,  # At trough, emit 20% of initial_strength
        properties: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a diurnal chemical source.
        
        Args:
            source_id: Unique identifier for this source
            position: 3D position (x, y, z) in the environment
            chemical_id: Identifier for the chemical being emitted
            initial_strength: Initial emission strength (this is the peak value)
            peak_hour: Hour of day (0-23) when emissions peak
            trough_hour: Hour of day (0-23) when emissions are lowest
            min_factor: Minimum emission factor (0-1) relative to initial_strength
            properties: Additional source-specific properties
        """
        super().__init__(source_id, position, chemical_id, initial_strength, properties)
        
        self.peak_hour = peak_hour % 24
        self.trough_hour = trough_hour % 24
        self.min_factor = max(0.0, min(1.0, min_factor))
        
        # Calculate phase shift for the sinusoidal pattern
        # We want the peak at peak_hour and trough at trough_hour
        hours_diff = (self.peak_hour - self.trough_hour) % 24
        if hours_diff == 0:
            hours_diff = 24  # Full day if same hour
        self.period = hours_diff * 2  # Time between peak and trough and back
        
        # Calculate phase shift in radians
        # For a sin wave, we want sin(ωt + φ) = 1 at t = peak_hour
        # This means ωt + φ = π/2 (sine peaks at π/2)
        # So φ = π/2 - ωt
        omega = 2 * math.pi / self.period  # Angular frequency
        self.phase_shift = math.pi / 2 - omega * self.peak_hour
        
    def emit(self, time_step: float, environment: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate emission for this time step based on time of day.
        
        Args:
            time_step: Time step in seconds
            environment: Environment conditions (temperature, humidity, etc.)
        
        Returns:
            Emission rate in appropriate units
        """
        if not self.is_active():
            return 0.0
            
        # Get current hour
        now = datetime.now()
        current_hour = now.hour + now.minute / 60.0
        
        # Calculate diurnal factor using sinusoidal model
        # We want a value between min_factor and 1.0, varying sinusoidally
        omega = 2 * math.pi / self.period
        time_factor = current_hour
        
        # Calculate the raw sine value (-1 to 1)
        sine_value = math.sin(omega * time_factor + self.phase_shift)
        
        # Convert to range [min_factor, 1.0]
        diurnal_factor = (1.0 - self.min_factor) * (sine_value + 1) / 2 + self.min_factor
        
        # Default environmental conditions if not provided
        if environment is None:
            environment = {"temperature": 25.0, "relative_humidity": 50.0}
            
        # Apply environmental factors
        temperature_factor = self.get_temperature_factor(environment.get("temperature", 25.0))
        humidity_factor = self.get_humidity_factor(environment.get("relative_humidity", 50.0))
        
        # Calculate emission rate
        emission_rate = self.initial_strength * diurnal_factor * temperature_factor * humidity_factor
        self.current_strength = emission_rate  # Update current strength
        
        # Update total emitted
        emitted_amount = emission_rate * time_step
        self.total_emitted += emitted_amount
        self.last_emission_time = now
        
        # Check if source is depleted (if it has a finite capacity)
        total_capacity = self.properties.get("total_capacity")
        if total_capacity is not None and self.total_emitted >= total_capacity:
            self.set_depleted()
            
        return emission_rate


class EventTriggeredSource(ChemicalSource):
    """
    A chemical source that emits based on specific event triggers.
    
    The source remains inactive until triggered by an event. Once triggered,
    it emits according to a specified pattern for a defined duration.
    """
    
    def __init__(
        self,
        source_id: str,
        position: Union[Tuple[float, float, float], Vector3D],
        chemical_id: str,
        initial_strength: float,
        emission_duration: float,
        pattern: str = "constant",
        properties: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an event-triggered chemical source.
        
        Args:
            source_id: Unique identifier for this source
            position: 3D position (x, y, z) in the environment
            chemical_id: Identifier for the chemical being emitted
            initial_strength: Initial emission strength
            emission_duration: Duration of emission after triggering (seconds)
            pattern: Emission pattern after triggering ("constant", "decay", "pulse")
            properties: Additional source-specific properties
        """
        super().__init__(source_id, position, chemical_id, initial_strength, properties)
        
        self.emission_duration = emission_duration
        self.pattern = pattern
        self.elapsed_since_trigger = 0.0
        self.last_trigger_time = None
        self.triggered = False
        
        # Additional pattern parameters
        if pattern == "decay":
            # Default half-life is 1/4 of the emission duration
            self.decay_half_life = properties.get("decay_half_life", emission_duration / 4)
            self.decay_constant = math.log(2) / self.decay_half_life
        elif pattern == "pulse":
            # Default pulse period is 1/10 of the emission duration
            self.pulse_period = properties.get("pulse_period", emission_duration / 10)
            self.duty_cycle = properties.get("duty_cycle", 0.5)
            self.pulse_elapsed = 0.0
            
        # Initially inactive
        self.status = SourceStatus.INACTIVE
        
    def trigger(self, strength_multiplier: float = 1.0) -> None:
        """
        Trigger the source to begin emitting.
        
        Args:
            strength_multiplier: Optional multiplier for emission strength
        """
        self.triggered = True
        self.status = SourceStatus.ACTIVE
        self.elapsed_since_trigger = 0.0
        self.last_trigger_time = datetime.now()
        
        # Apply the strength multiplier
        self.current_strength = self.initial_strength * strength_multiplier
        
    def emit(self, time_step: float, environment: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate emission for this time step if triggered.
        
        Args:
            time_step: Time step in seconds
            environment: Environment conditions (temperature, humidity, etc.)
        
        Returns:
            Emission rate in appropriate units
        """
        if not self.triggered or not self.is_active():
            return 0.0
            
        # Update elapsed time since triggering
        self.elapsed_since_trigger += time_step
        
        # Check if emission duration has elapsed
        if self.elapsed_since_trigger > self.emission_duration:
            self.triggered = False
            self.status = SourceStatus.INACTIVE
            return 0.0
            
        # Default environmental conditions if not provided
        if environment is None:
            environment = {"temperature": 25.0, "relative_humidity": 50.0}
            
        # Apply environmental factors
        temperature_factor = self.get_temperature_factor(environment.get("temperature", 25.0))
        humidity_factor = self.get_humidity_factor(environment.get("relative_humidity", 50.0))
        
        # Calculate emission rate based on pattern
        if self.pattern == "constant":
            emission_rate = self.current_strength * temperature_factor * humidity_factor
        
        elif self.pattern == "decay":
            # Exponential decay from initial strength
            decayed_strength = self.current_strength * math.exp(
                -self.decay_constant * self.elapsed_since_trigger
            )
            emission_rate = decayed_strength * temperature_factor * humidity_factor
            
        elif self.pattern == "pulse":
            # Update pulse elapsed time
            self.pulse_elapsed = (self.pulse_elapsed + time_step) % self.pulse_period
            
            # Check if in active part of pulse
            if self.pulse_elapsed <= self.duty_cycle * self.pulse_period:
                emission_rate = self.current_strength * temperature_factor * humidity_factor
            else:
                return 0.0
        else:
            # Default to constant
            emission_rate = self.current_strength * temperature_factor * humidity_factor
        
        # Update total emitted
        emitted_amount = emission_rate * time_step
        self.total_emitted += emitted_amount
        self.last_emission_time = datetime.now()
        
        # Check if source is depleted (if it has a finite capacity)
        total_capacity = self.properties.get("total_capacity")
        if total_capacity is not None and self.total_emitted >= total_capacity:
            self.set_depleted()
            
        return emission_rate


class ChemicalSourceManager:
    """
    Manages a collection of chemical sources in the simulation.
    
    This class provides methods to add, remove, and update sources,
    as well as to apply emissions to the environment.
    """
    
    def __init__(self):
        """Initialize the chemical source manager."""
        self.sources = {}  # Dictionary mapping source_id to source object
        
    def add_source(self, source: ChemicalSource) -> None:
        """
        Add a chemical source to the environment.
        
        Args:
            source: The chemical source to add
        
        Raises:
            ValueError: If a source with the same ID already exists
        """
        if source.source_id in self.sources:
            raise ValueError(f"Source with ID {source.source_id} already exists")
            
        self.sources[source.source_id] = source
        
    def remove_source(self, source_id: str) -> bool:
        """
        Remove a chemical source from the environment.
        
        Args:
            source_id: The ID of the source to remove
            
        Returns:
            True if the source was removed, False if not found
        """
        if source_id in self.sources:
            del self.sources[source_id]
            return True
        return False
        
    def get_source(self, source_id: str) -> Optional[ChemicalSource]:
        """
        Get a chemical source by ID.
        
        Args:
            source_id: The ID of the source to retrieve
            
        Returns:
            The chemical source or None if not found
        """
        return self.sources.get(source_id)
        
    def get_sources_by_chemical(self, chemical_id: str) -> List[ChemicalSource]:
        """
        Get all sources emitting a specific chemical.
        
        Args:
            chemical_id: The ID of the chemical
            
        Returns:
            List of chemical sources emitting the specified chemical
        """
        return [
            source for source in self.sources.values()
            if source.chemical_id == chemical_id
        ]
        
    def get_active_sources(self) -> List[ChemicalSource]:
        """
        Get all currently active sources.
        
        Returns:
            List of active chemical sources
        """
        return [
            source for source in self.sources.values()
            if source.is_active()
        ]
        
    def get_sources_in_radius(
        self, 
        position: Union[Tuple[float, float, float], Vector3D],
        radius: float
    ) -> List[ChemicalSource]:
        """
        Get all sources within a specified radius of a position.
        
        Args:
            position: The position to search around
            radius: The search radius in meters
            
        Returns:
            List of chemical sources within the radius
        """
        # Convert position to Vector3D if needed
        if isinstance(position, tuple):
            position = Vector3D(*position)
            
        return [
            source for source in self.sources.values()
            if position.distance_to(source.position) <= radius
        ]
        
    def apply_emissions(
        self,
        time_step: float,
        environment_function,
        apply_function
    ) -> Dict[str, float]:
        """
        Calculate and apply emissions from all sources to the environment.
        
        Args:
            time_step: Time step in seconds
            environment_function: Function that takes a position and returns
                environmental conditions at that position
            apply_function: Function that takes (source, emission_rate) and
                applies the emission to the environment
                
        Returns:
            Dictionary mapping source_id to emission rate
        """
        emission_rates = {}
        
        for source_id, source in self.sources.items():
            if not source.is_active():
                emission_rates[source_id] = 0.0
                continue
                
            # Get environment conditions at source position
            env_conditions = environment_function(source.position)
            
            # Calculate emission rate
            emission_rate = source.emit(time_step, env_conditions)
            emission_rates[source_id] = emission_rate
            
            # Apply emission to environment
            apply_function(source, emission_rate)
            
        return emission_rates
        
    def trigger_source(self, source_id: str, strength_multiplier: float = 1.0) -> bool:
        """
        Trigger an event-triggered source.
        
        Args:
            source_id: The ID of the source to trigger
            strength_multiplier: Optional multiplier for emission strength
            
        Returns:
            True if the source was triggered, False if not found or not triggerable
        """
        source = self.get_source(source_id)
        if source is None:
            return False
            
        if isinstance(source, EventTriggeredSource):
            source.trigger(strength_multiplier)
            return True
        
        return False
        
    def deactivate_all_sources(self) -> None:
        """Deactivate all chemical sources."""
        for source in self.sources.values():
            source.deactivate()
            
    def activate_all_sources(self) -> None:
        """Activate all chemical sources."""
        for source in self.sources.values():
            source.activate()
            
    def get_emission_statistics(self) -> Dict[str, Dict[str, float]]:
        """
        Get statistics about emissions from all sources.
        
        Returns:
            Dictionary mapping chemical_id to statistics about emissions
        """
        stats = {}
        
        # Group sources by chemical
        for chemical_id in set(source.chemical_id for source in self.sources.values()):
            chem_sources = self.get_sources_by_chemical(chemical_id)
            
            stats[chemical_id] = {
                "total_sources": len(chem_sources),
                "active_sources": sum(1 for s in chem_sources if s.is_active()),
                "total_emitted": sum(s.total_emitted for s in chem_sources),
                "current_strength_sum": sum(s.current_strength for s in chem_sources if s.is_active()),
                "average_strength": (
                    sum(s.current_strength for s in chem_sources if s.is_active()) / 
                    max(1, sum(1 for s in chem_sources if s.is_active()))
                ),
            }
            
        return stats
