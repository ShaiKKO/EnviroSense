"""
Vibration propagation implementation.

This module provides classes and functions for modeling the propagation of
vibrations through different materials and spatial environments.
"""

import numpy as np
from typing import Tuple, List, Dict, Optional, Any, Union
import math
from dataclasses import dataclass

from envirosense.core.physics.coordinates import Vector3D


@dataclass
class Material:
    """Material properties for vibration propagation."""
    
    name: str
    # Damping coefficient (1/m) - how quickly vibration attenuates with distance
    damping_coefficient: float
    # Velocity of propagation (m/s) - speed of vibration in material
    propagation_velocity: float
    # Density (kg/m³)
    density: float
    # Reflection coefficient (0-1) - how much vibration is reflected at interfaces
    reflection_coefficient: float
    # Frequency-dependent damping scaling factor
    # Higher frequencies attenuate faster in most materials
    freq_damping_factor: float = 0.001


# Common construction materials
COMMON_MATERIALS = {
    'air': Material(
        name='air',
        damping_coefficient=0.1,  # Air has low damping for vibration
        propagation_velocity=343.0,  # Speed of sound in air (m/s)
        density=1.225,  # kg/m³
        reflection_coefficient=0.9  # High reflection at air interfaces
    ),
    'concrete': Material(
        name='concrete',
        damping_coefficient=0.05,  # Concrete has moderate damping
        propagation_velocity=3200.0,  # Speed of vibration in concrete (m/s)
        density=2400.0,  # kg/m³
        reflection_coefficient=0.3,  # Moderate reflection
        freq_damping_factor=0.002  # Higher frequency damping
    ),
    'steel': Material(
        name='steel',
        damping_coefficient=0.001,  # Steel has very low internal damping
        propagation_velocity=5100.0,  # Speed of vibration in steel (m/s)
        density=7800.0,  # kg/m³
        reflection_coefficient=0.1,  # Low reflection (good transmission)
        freq_damping_factor=0.0005  # Low frequency damping
    ),
    'wood': Material(
        name='wood',
        damping_coefficient=0.08,  # Wood has higher damping
        propagation_velocity=3500.0,  # Speed of vibration in wood (m/s)
        density=700.0,  # kg/m³ (varies by wood type)
        reflection_coefficient=0.4,  # Moderate reflection
        freq_damping_factor=0.003  # Higher frequency damping
    ),
    'rubber': Material(
        name='rubber',
        damping_coefficient=0.2,  # Rubber has high damping
        propagation_velocity=1600.0,  # Speed of vibration in rubber (m/s)
        density=1100.0,  # kg/m³
        reflection_coefficient=0.7,  # High reflection/isolation
        freq_damping_factor=0.005  # Very high frequency damping
    ),
    'soil': Material(
        name='soil',
        damping_coefficient=0.15,  # Soil has high damping
        propagation_velocity=200.0,  # Speed of vibration in soil (m/s)
        density=1600.0,  # kg/m³ (varies by soil type)
        reflection_coefficient=0.5,  # Moderate reflection
        freq_damping_factor=0.004  # Higher frequency damping
    ),
    'water': Material(
        name='water',
        damping_coefficient=0.03,  # Water has low damping
        propagation_velocity=1480.0,  # Speed of sound in water (m/s)
        density=1000.0,  # kg/m³
        reflection_coefficient=0.2,  # Low reflection
        freq_damping_factor=0.001  # Low frequency damping
    )
}


class VibrationPath:
    """
    Represents a path that vibration takes from source to receiver.
    
    This class models how vibration propagates along a specific path,
    accounting for distance, materials, and interfaces between materials.
    """
    
    def __init__(self, 
                 path_segments: List[Tuple[float, Material]],
                 name: Optional[str] = None):
        """
        Initialize a vibration path.
        
        Args:
            path_segments: List of (distance, material) tuples representing segments
            name: Optional name for the path
        """
        self.path_segments = path_segments
        self.name = name or "unnamed_path"
        
        # Calculate total path length
        self.total_distance = sum(segment[0] for segment in path_segments)
        
        # Calculate interfaces (material transitions)
        self.interfaces = []
        for i in range(len(path_segments) - 1):
            material1 = path_segments[i][1]
            material2 = path_segments[i + 1][1]
            if material1 != material2:
                # Record the position and materials at the interface
                position = sum(segment[0] for segment in path_segments[:i+1])
                self.interfaces.append((position, material1, material2))
    
    def calculate_attenuation(self, frequency: float) -> float:
        """
        Calculate the attenuation of vibration along this path for a given frequency.
        
        Args:
            frequency: Frequency in Hz
            
        Returns:
            Attenuation factor (0-1 where 0 is complete attenuation)
        """
        # Start with no attenuation
        attenuation_factor = 1.0
        
        # Apply attenuation for each segment
        for distance, material in self.path_segments:
            # Frequency-dependent damping coefficient
            # Higher frequencies are attenuated more
            effective_damping = material.damping_coefficient * (
                1 + material.freq_damping_factor * frequency)
            
            # Exponential attenuation with distance
            segment_attenuation = math.exp(-effective_damping * distance)
            attenuation_factor *= segment_attenuation
        
        # Apply attenuation at each interface
        for _, material1, material2 in self.interfaces:
            # Simplified transmission coefficient calculation
            # Based on impedance mismatch (density * velocity)
            z1 = material1.density * material1.propagation_velocity
            z2 = material2.density * material2.propagation_velocity
            
            # Transmission coefficient
            if z1 == 0 or z2 == 0:  # Avoid division by zero
                transmission = 0
            else:
                # Simplified transmission calculation
                # More accurate models would use the full acoustic equation
                transmission = 4 * z1 * z2 / ((z1 + z2) ** 2)
            
            # Apply interface attenuation
            attenuation_factor *= transmission
        
        return attenuation_factor
    
    def calculate_time_delay(self) -> float:
        """
        Calculate the time it takes for vibration to travel along this path.
        
        Returns:
            Time delay in seconds
        """
        time_delay = 0.0
        
        # Add time for each segment
        for distance, material in self.path_segments:
            # Time = distance / velocity
            segment_time = distance / material.propagation_velocity
            time_delay += segment_time
        
        return time_delay
    
    def calculate_frequency_response(self, 
                                   freq_range: Tuple[float, float, int]
                                   ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate the frequency response of the path.
        
        Args:
            freq_range: Tuple of (min_freq, max_freq, num_points)
            
        Returns:
            Tuple of (frequencies, attenuation) arrays
        """
        min_freq, max_freq, num_points = freq_range
        
        # Generate frequency array
        frequencies = np.linspace(min_freq, max_freq, num_points)
        
        # Calculate attenuation for each frequency
        attenuation = np.zeros(num_points)
        for i, freq in enumerate(frequencies):
            attenuation[i] = self.calculate_attenuation(freq)
        
        return frequencies, attenuation
    
    def apply_to_spectrum(self, 
                        frequencies: np.ndarray, 
                        spectrum: np.ndarray
                       ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply path effects to a vibration spectrum.
        
        Args:
            frequencies: Array of frequencies (Hz)
            spectrum: Array of amplitude values
            
        Returns:
            Modified spectrum after propagation effects
        """
        # Create output arrays
        modified_spectrum = np.zeros_like(spectrum)
        
        # Apply attenuation to each frequency component
        for i, freq in enumerate(frequencies):
            modified_spectrum[i] = spectrum[i] * self.calculate_attenuation(freq)
        
        return frequencies, modified_spectrum
    
    def apply_to_time_signal(self,
                           time_points: np.ndarray,
                           time_signal: np.ndarray,
                           sample_rate: float
                          ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply path effects to a time domain signal.
        
        This applies frequency-dependent attenuation and time delay.
        
        Args:
            time_points: Array of time points (seconds)
            time_signal: Array of amplitude values
            sample_rate: Sampling rate in Hz
            
        Returns:
            Modified time signal after propagation effects
        """
        # Calculate time delay in samples
        delay_samples = int(self.calculate_time_delay() * sample_rate)
        
        # Convert to frequency domain
        spectrum = np.fft.rfft(time_signal)
        freq_resolution = sample_rate / len(time_signal)
        frequencies = np.arange(len(spectrum)) * freq_resolution
        
        # Apply frequency-dependent attenuation
        for i, freq in enumerate(frequencies):
            spectrum[i] *= self.calculate_attenuation(freq)
        
        # Convert back to time domain
        modified_signal = np.fft.irfft(spectrum, n=len(time_signal))
        
        # Apply time delay (shift the signal)
        delayed_signal = np.zeros_like(time_signal)
        if delay_samples < len(time_signal):
            delayed_signal[delay_samples:] = modified_signal[:len(time_signal)-delay_samples]
        
        return time_points, delayed_signal


class PropagationModel:
    """
    Models vibration propagation through an environment.
    
    This class models how vibration propagates from sources to receivers
    through various paths and materials.
    """
    
    def __init__(self, name: str):
        """
        Initialize a propagation model.
        
        Args:
            name: Model name
        """
        self.name = name
        self.paths = {}  # Dictionary of path_id -> VibrationPath
        self.default_material = COMMON_MATERIALS['air']
    
    def add_path(self, path_id: str, path: VibrationPath) -> None:
        """
        Add a vibration path to the model.
        
        Args:
            path_id: Path identifier
            path: VibrationPath instance
        """
        self.paths[path_id] = path
    
    def create_simple_path(self, 
                          path_id: str,
                          distance: float,
                          material: Material,
                          name: Optional[str] = None) -> VibrationPath:
        """
        Create and add a simple single-segment path.
        
        Args:
            path_id: Path identifier
            distance: Distance in meters
            material: Material for the path
            name: Optional path name
            
        Returns:
            Created VibrationPath instance
        """
        path = VibrationPath([(distance, material)], name)
        self.add_path(path_id, path)
        return path
    
    def create_direct_path(self,
                         path_id: str,
                         source_pos: Union[Vector3D, Tuple[float, float, float]],
                         receiver_pos: Union[Vector3D, Tuple[float, float, float]],
                         material: Material,
                         name: Optional[str] = None) -> VibrationPath:
        """
        Create a direct path between source and receiver positions.
        
        Args:
            path_id: Path identifier
            source_pos: Source position
            receiver_pos: Receiver position
            material: Material for the path
            name: Optional path name
            
        Returns:
            Created VibrationPath instance
        """
        # Convert to Vector3D if needed
        if not isinstance(source_pos, Vector3D):
            source_pos = Vector3D(source_pos[0], source_pos[1], source_pos[2])
        if not isinstance(receiver_pos, Vector3D):
            receiver_pos = Vector3D(receiver_pos[0], receiver_pos[1], receiver_pos[2])
        
        # Calculate distance
        distance = source_pos.distance_to(receiver_pos)
        
        # Create path
        return self.create_simple_path(path_id, distance, material, name)
    
    def create_multi_segment_path(self,
                                path_id: str,
                                segments: List[Tuple[float, Material]],
                                name: Optional[str] = None) -> VibrationPath:
        """
        Create a path with multiple segments of different materials.
        
        Args:
            path_id: Path identifier
            segments: List of (distance, material) tuples
            name: Optional path name
            
        Returns:
            Created VibrationPath instance
        """
        path = VibrationPath(segments, name)
        self.add_path(path_id, path)
        return path
    
    def create_multi_point_path(self,
                              path_id: str,
                              points: List[Union[Vector3D, Tuple[float, float, float]]],
                              materials: List[Material],
                              name: Optional[str] = None) -> VibrationPath:
        """
        Create a path with multiple points and materials.
        
        Args:
            path_id: Path identifier
            points: List of positions (must be at least 2)
            materials: List of materials (must be length of points - 1)
            name: Optional path name
            
        Returns:
            Created VibrationPath instance
        """
        if len(points) < 2:
            raise ValueError("At least 2 points are required")
        if len(materials) != len(points) - 1:
            raise ValueError("Number of materials must be number of points - 1")
        
        # Convert points to Vector3D if needed
        vector_points = []
        for p in points:
            if not isinstance(p, Vector3D):
                vector_points.append(Vector3D(p[0], p[1], p[2]))
            else:
                vector_points.append(p)
        
        # Calculate segments
        segments = []
        for i in range(len(vector_points) - 1):
            distance = vector_points[i].distance_to(vector_points[i+1])
            segments.append((distance, materials[i]))
        
        # Create path
        return self.create_multi_segment_path(path_id, segments, name)
    
    def calculate_combined_response(self, 
                                  path_ids: List[str],
                                  freq_range: Tuple[float, float, int]
                                 ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate the combined frequency response of multiple paths.
        
        Args:
            path_ids: List of path identifiers
            freq_range: Tuple of (min_freq, max_freq, num_points)
            
        Returns:
            Tuple of (frequencies, combined_response) arrays
        """
        min_freq, max_freq, num_points = freq_range
        
        # Generate frequency array
        frequencies = np.linspace(min_freq, max_freq, num_points)
        
        # Initialize combined response
        combined_response = np.zeros(num_points, dtype=complex)
        
        # Add contribution from each path
        for path_id in path_ids:
            if path_id in self.paths:
                path = self.paths[path_id]
                
                # Calculate attenuation for each frequency
                for i, freq in enumerate(frequencies):
                    attenuation = path.calculate_attenuation(freq)
                    time_delay = path.calculate_time_delay()
                    
                    # Convert to complex representation with phase shift due to delay
                    phase_shift = 2 * np.pi * freq * time_delay
                    complex_attenuation = attenuation * np.exp(1j * phase_shift)
                    
                    # Add to combined response
                    combined_response[i] += complex_attenuation
        
        # Calculate magnitude of combined response
        magnitude_response = np.abs(combined_response)
        
        return frequencies, magnitude_response
    
    def apply_propagation(self,
                        frequencies: np.ndarray,
                        source_spectrum: np.ndarray,
                        path_ids: Optional[List[str]] = None
                       ) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        """
        Apply propagation effects to a source spectrum for multiple paths.
        
        Args:
            frequencies: Array of frequencies (Hz)
            source_spectrum: Source vibration spectrum
            path_ids: List of path identifiers (if None, use all paths)
            
        Returns:
            Dictionary mapping path_id to (frequencies, attenuated_spectrum)
        """
        if path_ids is None:
            path_ids = list(self.paths.keys())
        
        results = {}
        for path_id in path_ids:
            if path_id in self.paths:
                path = self.paths[path_id]
                _, attenuated_spectrum = path.apply_to_spectrum(frequencies, source_spectrum)
                results[path_id] = (frequencies, attenuated_spectrum)
        
        return results
    
    def calculate_transfer_function(self,
                                  source_pos: Union[Vector3D, Tuple[float, float, float]],
                                  receiver_pos: Union[Vector3D, Tuple[float, float, float]],
                                  material: Material,
                                  freq_range: Tuple[float, float, int]
                                 ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate transfer function between source and receiver positions.
        
        Args:
            source_pos: Source position
            receiver_pos: Receiver position
            material: Material for direct path
            freq_range: Tuple of (min_freq, max_freq, num_points)
            
        Returns:
            Tuple of (frequencies, transfer_function) arrays
        """
        # Create temporary path for calculation
        temp_path = self.create_direct_path(
            "temp", source_pos, receiver_pos, material, "temp_transfer_function")
        
        # Calculate response
        frequencies, response = temp_path.calculate_frequency_response(freq_range)
        
        # Remove temporary path
        if "temp" in self.paths:
            del self.paths["temp"]
        
        return frequencies, response


class SpatialPropagationModel(PropagationModel):
    """
    Enhanced propagation model that handles spatial representation of environment.
    
    This class adds the ability to define spatial regions with different materials
    and calculates paths through these regions automatically.
    """
    
    def __init__(self, name: str):
        """
        Initialize a spatial propagation model.
        
        Args:
            name: Model name
        """
        super().__init__(name)
        
        # Map of region_id to (bounding_box, material)
        # Bounding box is ((min_x, min_y, min_z), (max_x, max_y, max_z))
        self.regions = {}
        
        # Default material for space not covered by regions
        self.default_material = COMMON_MATERIALS['air']
    
    def add_region(self, 
                 region_id: str,
                 bounding_box: Tuple[Tuple[float, float, float], Tuple[float, float, float]],
                 material: Material) -> None:
        """
        Add a spatial region with a specific material.
        
        Args:
            region_id: Region identifier
            bounding_box: ((min_x, min_y, min_z), (max_x, max_y, max_z))
            material: Material for this region
        """
        self.regions[region_id] = (bounding_box, material)
    
    def get_material_at_point(self, point: Union[Vector3D, Tuple[float, float, float]]) -> Material:
        """
        Get the material at a specific point in space.
        
        Args:
            point: Position to check
            
        Returns:
            Material at that position
        """
        # Convert to tuple if Vector3D
        if isinstance(point, Vector3D):
            point = (point.x, point.y, point.z)
        
        # Check each region
        for region_id, (bounding_box, material) in self.regions.items():
            min_point, max_point = bounding_box
            
            # Check if point is inside bounding box
            if (min_point[0] <= point[0] <= max_point[0] and
                min_point[1] <= point[1] <= max_point[1] and
                min_point[2] <= point[2] <= max_point[2]):
                return material
        
        # If not in any region, use default material
        return self.default_material
    
    def find_path_through_regions(self,
                                source_pos: Union[Vector3D, Tuple[float, float, float]],
                                receiver_pos: Union[Vector3D, Tuple[float, float, float]],
                                num_segments: int = 10) -> VibrationPath:
        """
        Find a path through regions between source and receiver.
        
        Args:
            source_pos: Source position
            receiver_pos: Receiver position
            num_segments: Number of segments to divide path into
            
        Returns:
            VibrationPath through the regions
        """
        # Convert to Vector3D if needed
        if not isinstance(source_pos, Vector3D):
            source_pos = Vector3D(source_pos[0], source_pos[1], source_pos[2])
        if not isinstance(receiver_pos, Vector3D):
            receiver_pos = Vector3D(receiver_pos[0], receiver_pos[1], receiver_pos[2])
        
        # Create points along straight line path
        points = []
        for i in range(num_segments + 1):
            t = i / num_segments
            # Linear interpolation between source and receiver
            x = source_pos.x + t * (receiver_pos.x - source_pos.x)
            y = source_pos.y + t * (receiver_pos.y - source_pos.y)
            z = source_pos.z + t * (receiver_pos.z - source_pos.z)
            points.append(Vector3D(x, y, z))
        
        # Determine segments based on materials at each point
        segments = []
        current_material = self.get_material_at_point(points[0])
        current_start = 0
        
        for i in range(1, len(points)):
            point_material = self.get_material_at_point(points[i])
            
            # If material changes, create segment
            if point_material != current_material:
                # Calculate distance from start to current point
                distance = points[current_start].distance_to(points[i])
                segments.append((distance, current_material))
                
                # Update for next segment
                current_start = i
                current_material = point_material
        
        # Add final segment
        distance = points[current_start].distance_to(points[-1])
        segments.append((distance, current_material))
        
        # Create path with unique ID based on positions
        path_id = f"path_{hash((str(source_pos), str(receiver_pos)))}"
        path_name = f"Path from {source_pos} to {receiver_pos}"
        
        return self.create_multi_segment_path(path_id, segments, path_name)
    
    def calculate_spatial_response(self,
                                 source_pos: Union[Vector3D, Tuple[float, float, float]],
                                 receiver_positions: List[Union[Vector3D, Tuple[float, float, float]]],
                                 freq_range: Tuple[float, float, int],
                                 num_segments: int = 10
                                ) -> Dict[int, Tuple[np.ndarray, np.ndarray]]:
        """
        Calculate frequency response at multiple receiver positions from one source.
        
        Args:
            source_pos: Source position
            receiver_positions: List of receiver positions
            freq_range: Tuple of (min_freq, max_freq, num_points)
            num_segments: Number of segments to divide paths into
            
        Returns:
            Dictionary mapping receiver index to (frequencies, response) arrays
        """
        results = {}
        
        for i, receiver_pos in enumerate(receiver_positions):
            # Find path through regions
            path = self.find_path_through_regions(source_pos, receiver_pos, num_segments)
            
            # Calculate frequency response
            frequencies, response = path.calculate_frequency_response(freq_range)
            
            # Store result
            results[i] = (frequencies, response)
        
        return results
