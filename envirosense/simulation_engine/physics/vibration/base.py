"""
Base classes for the vibration modeling system.

This module provides the foundational classes and interfaces for modeling
vibration sources, propagation, and analysis in the EnviroSense physics engine.
"""

import numpy as np
from typing import Tuple, List, Dict, Optional, Any, Union
import matplotlib.pyplot as plt
from abc import ABC, abstractmethod
import uuid
import json

from envirosense.core.physics.coordinates import Vector3D


class VibrationSource(ABC):
    """
    Abstract base class for all vibration sources.
    
    This class defines the common interface for all vibration sources
    in the system, allowing them to be used interchangeably in the
    vibration propagation and analysis systems.
    """
    
    def __init__(self, 
                 name: str, 
                 position: Union[Vector3D, Tuple[float, float, float]],
                 source_id: Optional[str] = None):
        """
        Initialize a vibration source.
        
        Args:
            name: Name of the vibration source
            position: Position of the source in 3D space
            source_id: Unique identifier for the source, auto-generated if not provided
        """
        self.name = name
        
        # Convert position tuple to Vector3D if necessary
        if isinstance(position, tuple):
            self.position = Vector3D.from_tuple(position)
        else:
            self.position = position
            
        # Generate a unique ID if not provided
        self.source_id = source_id or str(uuid.uuid4())
        
        # Default properties
        self.is_active = True
        self.metadata = {}
    
    @abstractmethod
    def generate_spectrum(self, freq_range: Tuple[float, float, int]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate frequency spectrum for this vibration source.
        
        Args:
            freq_range: Tuple of (min_freq, max_freq, num_points)
            
        Returns:
            Tuple of (frequencies, amplitudes) arrays
        """
        pass
    
    @abstractmethod
    def generate_time_signal(self, duration: float, sample_rate: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate time-domain signal for this vibration source.
        
        Args:
            duration: Signal duration in seconds
            sample_rate: Sample rate in Hz, defaults to 10x max expected frequency
            
        Returns:
            Tuple of (time_points, amplitude) arrays
        """
        pass
    
    def set_position(self, position: Union[Vector3D, Tuple[float, float, float]]) -> None:
        """
        Set the position of the vibration source.
        
        Args:
            position: New position in 3D space
        """
        if isinstance(position, tuple):
            self.position = Vector3D.from_tuple(position)
        else:
            self.position = position
    
    def get_amplitude_at_frequency(self, frequency: float) -> float:
        """
        Get amplitude at a specific frequency.
        
        Args:
            frequency: Frequency in Hz
            
        Returns:
            Amplitude at the specified frequency
        """
        freqs, amps = self.generate_spectrum((frequency*0.9, frequency*1.1, 100))
        idx = np.abs(freqs - frequency).argmin()
        return amps[idx]
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get all metadata for this source.
        
        Returns:
            Dictionary of metadata
        """
        return self.metadata
    
    def set_metadata(self, key: str, value: Any) -> None:
        """
        Set metadata for this source.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary.
        
        Returns:
            Dictionary representation of the source
        """
        return {
            'name': self.name,
            'source_id': self.source_id,
            'position': self.position.to_tuple(),
            'is_active': self.is_active,
            'type': self.__class__.__name__,
            'metadata': self.metadata
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Deserialize from dictionary.
        
        Args:
            data: Dictionary representation of the source
        """
        self.name = data['name']
        self.source_id = data['source_id']
        self.position = Vector3D.from_tuple(data['position'])
        self.is_active = data['is_active']
        self.metadata = data.get('metadata', {})
    
    def __str__(self) -> str:
        """String representation of the vibration source."""
        return f"{self.__class__.__name__}({self.name}, pos={self.position})"


class Material:
    """
    Represents material properties for vibration propagation.
    
    This class defines the acoustic and mechanical properties of materials
    that influence how vibrations propagate through them.
    """
    
    # Default properties for common materials
    MATERIALS = {
        'air': {
            'density': 1.225,  # kg/m³
            'damping_factor': 0.01,
            'sound_speed': 343,  # m/s
            'impedance': 420,  # kg/m²s
        },
        'concrete': {
            'density': 2400,  # kg/m³
            'damping_factor': 0.02,
            'sound_speed': 3200,  # m/s
            'impedance': 7.7e6,  # kg/m²s
        },
        'steel': {
            'density': 7800,  # kg/m³
            'damping_factor': 0.001,
            'sound_speed': 5100,  # m/s
            'impedance': 39.8e6,  # kg/m²s
        },
        'wood': {
            'density': 700,  # kg/m³
            'damping_factor': 0.05,
            'sound_speed': 3300,  # m/s
            'impedance': 2.3e6,  # kg/m²s
        },
        'rubber': {
            'density': 1100,  # kg/m³
            'damping_factor': 0.1,
            'sound_speed': 60,  # m/s
            'impedance': 6.6e4,  # kg/m²s
        },
        'soil': {
            'density': 1600,  # kg/m³
            'damping_factor': 0.07,
            'sound_speed': 200,  # m/s
            'impedance': 3.2e5,  # kg/m²s
        }
    }
    
    def __init__(self, 
                 name: str,
                 **properties):
        """
        Initialize material properties.
        
        Args:
            name: Material name
            **properties: Material properties as keyword arguments
        """
        self.name = name
        
        # Set default properties based on predefined materials
        if name.lower() in self.MATERIALS:
            self.properties = self.MATERIALS[name.lower()].copy()
        else:
            self.properties = {
                'density': 1000,  # kg/m³
                'damping_factor': 0.05,
                'sound_speed': 1000,  # m/s
                'impedance': 1e6,  # kg/m²s
            }
        
        # Override with any provided properties
        self.properties.update(properties)
    
    def get_property(self, prop_name: str) -> float:
        """
        Get a specific material property.
        
        Args:
            prop_name: Name of the property
            
        Returns:
            Value of the property
        """
        return self.properties.get(prop_name, 0.0)
    
    def set_property(self, prop_name: str, value: float) -> None:
        """
        Set a specific material property.
        
        Args:
            prop_name: Name of the property
            value: New value for the property
        """
        self.properties[prop_name] = value
    
    def calculate_transmission_coefficient(self, other_material: 'Material') -> float:
        """
        Calculate transmission coefficient between this material and another.
        
        This coefficient represents the fraction of vibration energy that
        passes from one material to another at their interface.
        
        Args:
            other_material: Material on the other side of the interface
            
        Returns:
            Transmission coefficient [0-1]
        """
        Z1 = self.properties['impedance']
        Z2 = other_material.properties['impedance']
        
        # Transmission coefficient formula for normal incidence
        T = 4 * Z1 * Z2 / ((Z1 + Z2) ** 2)
        return T
    
    def calculate_reflection_coefficient(self, other_material: 'Material') -> float:
        """
        Calculate reflection coefficient between this material and another.
        
        This coefficient represents the fraction of vibration energy that
        is reflected at the interface between materials.
        
        Args:
            other_material: Material on the other side of the interface
            
        Returns:
            Reflection coefficient [-1 to 1]
        """
        Z1 = self.properties['impedance']
        Z2 = other_material.properties['impedance']
        
        # Reflection coefficient formula for normal incidence
        R = (Z2 - Z1) / (Z2 + Z1)
        return R
    
    def calculate_attenuation(self, distance: float, frequency: float) -> float:
        """
        Calculate attenuation factor for vibrations in this material.
        
        Args:
            distance: Propagation distance in meters
            frequency: Vibration frequency in Hz
            
        Returns:
            Attenuation factor [0-1] where 1 means no attenuation
        """
        # Simple frequency-dependent attenuation model
        damping = self.properties['damping_factor']
        
        # Higher frequencies attenuate more quickly
        freq_factor = frequency / 100.0  # Normalized to 100 Hz
        
        # Exponential decay with distance
        attenuation = np.exp(-damping * freq_factor * distance)
        return attenuation
