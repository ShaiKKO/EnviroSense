"""
EnviroSense Physics Engine - Thermal Signature Modeling

This module provides classes and functions for modeling thermal signatures
produced by utility infrastructure components such as power lines, transformers,
and other equipment. It implements thermal generation, dissipation, and visualization
methods for analyzing temperature profiles and heat signatures.

Classes:
    ThermalSource: Base class for thermal sources
    ThermalProfile: Represents temperature distribution in space
    PowerLineHeat: Models thermal signature of power lines
    TransformerHeat: Models thermal signature of transformers
    ElectronicEquipment: Models thermal signature of electronic equipment
    ThermalVisualizer: Provides visualization tools for thermal signatures
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import time
from typing import Tuple, List, Dict, Optional, Union
from abc import ABC, abstractmethod

from envirosense.core.physics.coordinates import Vector3D

# Constants
STEFAN_BOLTZMANN = 5.670374419e-8  # Stefan-Boltzmann constant (W/(m²·K⁴))
AMBIENT_TEMPERATURE = 293.15  # Default ambient temperature in Kelvin (20°C)


class ThermalSource(ABC):
    """
    Abstract base class for all thermal sources.
    
    Attributes:
        name (str): Unique identifier for the source
        position (Vector3D): 3D position of the source
        enabled (bool): Whether the source is currently active
        temperature (float): Current temperature in Kelvin
        power (float): Thermal power in watts
    """
    
    def __init__(self, name: str, 
                position: Tuple[float, float, float],
                temperature: float,
                power: float):
        """
        Initialize a thermal source.
        
        Args:
            name: Unique identifier for the source
            position: 3D coordinates (x, y, z) of the source in meters
            temperature: Initial temperature in Kelvin
            power: Thermal power in watts
        """
        self.name = name
        self.position = Vector3D(*position)
        self.enabled = True
        self.temperature = temperature
        self.power = power
    
    @abstractmethod
    def calculate_temperature_at(self, position: Tuple[float, float, float], 
                               ambient_temperature: float = AMBIENT_TEMPERATURE) -> float:
        """
        Calculate temperature at a specific point in space.
        
        Args:
            position: 3D coordinates (x, y, z) to calculate temperature at
            ambient_temperature: Ambient temperature in Kelvin
            
        Returns:
            Temperature at the specified position in Kelvin
        """
        pass
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the type of thermal source."""
        pass
    
    def enable(self):
        """Enable this thermal source."""
        self.enabled = True
    
    def disable(self):
        """Disable this thermal source."""
        self.enabled = False


class PowerLineHeat(ThermalSource):
    """
    Models thermal signature of power lines based on current and resistance.
    
    Attributes:
        name (str): Unique identifier for the source
        start_point (Vector3D): Starting point of the power line
        end_point (Vector3D): Ending point of the power line
        current (float): Current in amperes
        resistance_per_meter (float): Resistance per meter in ohms/m
        diameter (float): Diameter of the conductor in meters
        emissivity (float): Surface emissivity (0-1)
    """
    
    def __init__(self, name: str,
                start_point: Tuple[float, float, float],
                end_point: Tuple[float, float, float],
                current: float,
                resistance_per_meter: float,
                diameter: float = 0.02,
                emissivity: float = 0.8,
                temperature: float = AMBIENT_TEMPERATURE + 20):  # Default 20°C above ambient
        """
        Initialize a power line thermal source.
        
        Args:
            name: Unique identifier for the source
            start_point: 3D coordinates of line start point (x, y, z) in meters
            end_point: 3D coordinates of line end point (x, y, z) in meters
            current: Current flowing through the line in amperes
            resistance_per_meter: Resistance per meter in ohms/m
            diameter: Diameter of the conductor in meters (default: 0.02)
            emissivity: Surface emissivity 0-1 (default: 0.8)
            temperature: Initial temperature in Kelvin (default: ambient + 20K)
        """
        # Calculate power based on I²R losses
        length = np.sqrt(sum((e - s) ** 2 for s, e in zip(start_point, end_point)))
        total_resistance = resistance_per_meter * length
        power = current**2 * total_resistance
        
        # Use midpoint as the position
        midpoint = tuple((s + e) / 2 for s, e in zip(start_point, end_point))
        
        super().__init__(name, midpoint, temperature, power)
        self.start_point = Vector3D(*start_point)
        self.end_point = Vector3D(*end_point)
        self.current = current
        self.resistance_per_meter = resistance_per_meter
        self.diameter = diameter
        self.emissivity = emissivity
        
        # Calculate direction vector and length
        self._direction = (self.end_point - self.start_point).normalize()
        self._length = (self.end_point - self.start_point).magnitude()
        
        # Calculate surface area for radiation calculations
        self.surface_area = np.pi * self.diameter * self._length
    
    @property
    def source_type(self) -> str:
        return "power_line_heat"
    
    def update_current(self, current: float):
        """
        Update the current flowing through the line and recalculate thermal properties.
        
        Args:
            current: New current in amperes
        """
        self.current = current
        # Update power based on new current
        self.power = current**2 * self.resistance_per_meter * self._length
        
        # Update temperature based on power balance (simplified model)
        # For steady-state, power in = power out (radiation + convection)
        # This is a simplified model - actual temperature would require solving
        # differential equations with environmental factors
        
        # Approximate convection coefficient for a cylinder in air
        h_conv = 10.0  # W/(m²·K), typical value for natural convection in air
        
        # Power balance equation (simplified):
        # P = h_conv·A·(T-T_ambient) + σ·ε·A·(T⁴-T_ambient⁴)
        # Solve for T using Newton-Raphson method
        
        T = self.temperature  # Initial guess
        T_amb = AMBIENT_TEMPERATURE
        area = self.surface_area
        
        # Newton-Raphson iterations to find steady-state temperature
        for _ in range(10):  # Usually converges in a few iterations
            # Power balance function
            f = h_conv * area * (T - T_amb) + \
                STEFAN_BOLTZMANN * self.emissivity * area * (T**4 - T_amb**4) - self.power
            
            # Derivative of the power balance function
            df = h_conv * area + 4 * STEFAN_BOLTZMANN * self.emissivity * area * T**3
            
            # Update temperature estimate
            T = T - f / df
        
        self.temperature = T
    
    def calculate_temperature_at(self, position: Tuple[float, float, float], 
                               ambient_temperature: float = AMBIENT_TEMPERATURE) -> float:
        """
        Calculate temperature at a point due to the power line.
        
        Args:
            position: 3D coordinates (x, y, z) to calculate temperature at
            ambient_temperature: Ambient temperature in Kelvin
            
        Returns:
            Temperature at the specified position in Kelvin
        """
        if not self.enabled:
            return ambient_temperature
        
        pos = Vector3D(*position)
        
        # Find closest point on the line
        closest = self._closest_point_on_line(pos)
        
        # Calculate distance from the line
        distance = (pos - closest).magnitude()
        
        if distance < self.diameter / 2:
            # Inside the conductor - return source temperature
            return self.temperature
        
        # Temperature decreases with distance from the line
        # Use an exponential decay model based on distance
        # T(r) = T_ambient + (T_source - T_ambient) * exp(-r/r_0)
        # where r_0 is a characteristic length scale
        
        # Characteristic length depends on power
        r_0 = 0.2 * (self.power / 1000.0)**0.5  # Scale with square root of power
        
        temperature = ambient_temperature + (self.temperature - ambient_temperature) * \
                      np.exp(-distance / r_0)
        
        return temperature
    
    def _closest_point_on_line(self, point: Vector3D) -> Vector3D:
        """
        Find the closest point on the line to the given point.
        
        Args:
            point: 3D position to find closest point to
            
        Returns:
            Vector3D representing the closest point on the line
        """
        # Vector from line start to the point
        line_to_point = point - self.start_point
        
        # Project this vector onto the line direction
        t = line_to_point.dot(self._direction)
        
        # Clamp t to line segment
        t = max(0, min(t, self._length))
        
        # Calculate the closest point
        closest = self.start_point + (self._direction * t)
        
        return closest


class TransformerHeat(ThermalSource):
    """
    Models thermal signature of transformers based on load and efficiency.
    
    Attributes:
        name (str): Unique identifier for the source
        position (Vector3D): Position of the transformer
        dimensions (Tuple[float, float, float]): Width, depth, height in meters
        power_rating (float): Power rating in VA
        efficiency (float): Efficiency as a fraction (0-1)
        load_factor (float): Current load factor (0-1)
        cooling_method (str): Cooling method (OIL_NATURAL, OIL_FORCED, etc.)
    """
    
    # Cooling method constants
    COOLING_OIL_NATURAL = "ONAN"  # Oil Natural, Air Natural
    COOLING_OIL_FORCED = "ONAF"   # Oil Natural, Air Forced
    COOLING_DIRECTED = "ODAF"     # Oil Directed, Air Forced
    COOLING_WATER = "OFWF"        # Oil Forced, Water Forced
    
    def __init__(self, name: str,
                position: Tuple[float, float, float],
                dimensions: Tuple[float, float, float],
                power_rating: float,
                efficiency: float = 0.98,
                load_factor: float = 0.8,
                cooling_method: str = COOLING_OIL_NATURAL):
        """
        Initialize a transformer thermal source.
        
        Args:
            name: Unique identifier for the source
            position: 3D coordinates (x, y, z) of the transformer in meters
            dimensions: Width, depth, height in meters
            power_rating: Power rating in VA
            efficiency: Efficiency as a fraction (default: 0.98)
            load_factor: Current load factor 0-1 (default: 0.8)
            cooling_method: Cooling method (default: ONAN)
        """
        self.dimensions = dimensions
        self.power_rating = power_rating
        self.efficiency = min(1.0, max(0.0, efficiency))  # Clamp to valid range
        self.load_factor = min(1.0, max(0.0, load_factor))  # Clamp to valid range
        self.cooling_method = cooling_method
        
        # Calculate power losses based on efficiency and load
        # Losses = S * (1-η) * (load factor)²
        losses = power_rating * (1 - efficiency) * (load_factor**2)
        
        # Calculate initial temperature based on losses and cooling method
        # This is a simplified model - actual transformer temperature would
        # require detailed thermal modeling with cooling system consideration
        
        # Temperature rise depends on cooling method
        if cooling_method == self.COOLING_OIL_NATURAL:
            temp_rise_factor = 1.0
        elif cooling_method == self.COOLING_OIL_FORCED:
            temp_rise_factor = 0.8
        elif cooling_method == self.COOLING_DIRECTED:
            temp_rise_factor = 0.7
        elif cooling_method == self.COOLING_WATER:
            temp_rise_factor = 0.5
        else:
            temp_rise_factor = 1.0  # Default to most conservative
        
        # Simplified temperature rise calculation
        # Typical full-load temperature rise is around 65K for ONAN
        temperature_rise = 65 * (losses / (power_rating * (1 - efficiency))) * temp_rise_factor
        temperature = AMBIENT_TEMPERATURE + temperature_rise
        
        super().__init__(name, position, temperature, losses)
    
    @property
    def source_type(self) -> str:
        return "transformer_heat"
    
    def set_load_factor(self, load_factor: float):
        """
        Update the transformer's load factor and recalculate thermal properties.
        
        Args:
            load_factor: New load factor (0-1)
        """
        self.load_factor = min(1.0, max(0.0, load_factor))  # Clamp to valid range
        
        # Recalculate power losses
        self.power = self.power_rating * (1 - self.efficiency) * (self.load_factor**2)
        
        # Recalculate temperature
        # Temperature rise depends on cooling method
        if self.cooling_method == self.COOLING_OIL_NATURAL:
            temp_rise_factor = 1.0
        elif self.cooling_method == self.COOLING_OIL_FORCED:
            temp_rise_factor = 0.8
        elif self.cooling_method == self.COOLING_DIRECTED:
            temp_rise_factor = 0.7
        elif self.cooling_method == self.COOLING_WATER:
            temp_rise_factor = 0.5
        else:
            temp_rise_factor = 1.0  # Default to most conservative
        
        # Simplified temperature rise calculation
        temperature_rise = 65 * (self.power / (self.power_rating * (1 - self.efficiency))) * temp_rise_factor
        self.temperature = AMBIENT_TEMPERATURE + temperature_rise
    
    def calculate_temperature_at(self, position: Tuple[float, float, float], 
                               ambient_temperature: float = AMBIENT_TEMPERATURE) -> float:
        """
        Calculate temperature at a point due to the transformer.
        
        Args:
            position: 3D coordinates (x, y, z) to calculate temperature at
            ambient_temperature: Ambient temperature in Kelvin
            
        Returns:
            Temperature at the specified position in Kelvin
        """
        if not self.enabled:
            return ambient_temperature
        
        pos = Vector3D(*position)
        
        # Calculate distance from the center of the transformer
        distance = (pos - self.position).magnitude()
        
        # Check if point is inside the transformer bounding box
        half_width = self.dimensions[0] / 2
        half_depth = self.dimensions[1] / 2
        half_height = self.dimensions[2] / 2
        
        if (abs(pos.x - self.position.x) <= half_width and
            abs(pos.y - self.position.y) <= half_depth and
            abs(pos.z - self.position.z) <= half_height):
            # Inside the transformer - use a slightly lower temperature than core
            # Temperature is not uniform inside a transformer
            return self.temperature - (self.temperature - ambient_temperature) * 0.1
        
        # Outside the transformer - use exponential decay model
        # Adjusted for shape by using the distance to the surface
        
        # Calculate distance to surface (simplified as distance from bounding box)
        dx = max(0, abs(pos.x - self.position.x) - half_width)
        dy = max(0, abs(pos.y - self.position.y) - half_depth)
        dz = max(0, abs(pos.z - self.position.z) - half_height)
        distance_to_surface = np.sqrt(dx**2 + dy**2 + dz**2)
        
        # Characteristic length depends on power and cooling method
        if self.cooling_method == self.COOLING_OIL_NATURAL:
            r_0 = 0.6 * (self.power / 1000.0)**0.3
        elif self.cooling_method == self.COOLING_OIL_FORCED:
            r_0 = 0.4 * (self.power / 1000.0)**0.3
        elif self.cooling_method == self.COOLING_DIRECTED:
            r_0 = 0.3 * (self.power / 1000.0)**0.3
        elif self.cooling_method == self.COOLING_WATER:
            r_0 = 0.2 * (self.power / 1000.0)**0.3
        else:
            r_0 = 0.5 * (self.power / 1000.0)**0.3
        
        # Calculate temperature
        temperature = ambient_temperature + (self.temperature - ambient_temperature) * \
                      np.exp(-distance_to_surface / r_0)
        
        return temperature


class ElectronicEquipment(ThermalSource):
    """
    Models thermal signature of electronic equipment (switch gear, servers, etc.).
    
    Attributes:
        name (str): Unique identifier for the source
        position (Vector3D): Position of the equipment
        dimensions (Tuple[float, float, float]): Width, depth, height in meters
        power_consumption (float): Power consumption in watts
        cooling_efficiency (float): Cooling system efficiency (0-1)
        active (bool): Whether equipment is currently active
    """
    
    def __init__(self, name: str,
                position: Tuple[float, float, float],
                dimensions: Tuple[float, float, float],
                power_consumption: float,
                cooling_efficiency: float = 0.7,
                active: bool = True):
        """
        Initialize an electronic equipment thermal source.
        
        Args:
            name: Unique identifier for the source
            position: 3D coordinates (x, y, z) of the equipment in meters
            dimensions: Width, depth, height in meters
            power_consumption: Power consumption in watts
            cooling_efficiency: Cooling efficiency as a fraction (default: 0.7)
            active: Whether the equipment is currently active (default: True)
        """
        self.dimensions = dimensions
        self.power_consumption = power_consumption
        self.cooling_efficiency = min(1.0, max(0.0, cooling_efficiency))
        self.active = active
        
        # Calculate heat output
        heat_output = power_consumption * (1 - cooling_efficiency) if active else 0.0
        
        # Calculate temperature based on heat output and size
        # Simplified model: temperature rise proportional to power density
        volume = dimensions[0] * dimensions[1] * dimensions[2]
        power_density = heat_output / volume
        
        # Temperature rise estimation based on power density
        # Typical electronics temperature rise is around 20-40K above ambient
        # This is a simplified model - actual temperature would depend on many factors
        temperature_rise = min(60, 20 + 100 * power_density)  # Cap at 60K rise
        temperature = AMBIENT_TEMPERATURE + (temperature_rise if active else 0)
        
        super().__init__(name, position, temperature, heat_output)
    
    @property
    def source_type(self) -> str:
        return "electronic_equipment"
    
    def set_active(self, active: bool):
        """
        Update the equipment's active status and recalculate thermal properties.
        
        Args:
            active: Whether the equipment is active
        """
        self.active = active
        
        # Recalculate heat output
        self.power = self.power_consumption * (1 - self.cooling_efficiency) if active else 0.0
        
        # Recalculate temperature
        volume = self.dimensions[0] * self.dimensions[1] * self.dimensions[2]
        power_density = self.power / volume if volume > 0 else 0
        
        temperature_rise = min(60, 20 + 100 * power_density) if active else 0
        self.temperature = AMBIENT_TEMPERATURE + temperature_rise
    
    def calculate_temperature_at(self, position: Tuple[float, float, float], 
                               ambient_temperature: float = AMBIENT_TEMPERATURE) -> float:
        """
        Calculate temperature at a point due to the electronic equipment.
        
        Args:
            position: 3D coordinates (x, y, z) to calculate temperature at
            ambient_temperature: Ambient temperature in Kelvin
            
        Returns:
            Temperature at the specified position in Kelvin
        """
        if not self.enabled or not self.active:
            return ambient_temperature
        
        pos = Vector3D(*position)
        
        # Check if point is inside the equipment bounding box
        half_width = self.dimensions[0] / 2
        half_depth = self.dimensions[1] / 2
        half_height = self.dimensions[2] / 2
        
        if (abs(pos.x - self.position.x) <= half_width and
            abs(pos.y - self.position.y) <= half_depth and
            abs(pos.z - self.position.z) <= half_height):
            # Inside the equipment - return source temperature
            return self.temperature
        
        # Calculate distance to surface
        dx = max(0, abs(pos.x - self.position.x) - half_width)
        dy = max(0, abs(pos.y - self.position.y) - half_depth)
        dz = max(0, abs(pos.z - self.position.z) - half_height)
        distance = np.sqrt(dx**2 + dy**2 + dz**2)
        
        # For electronic equipment, heat dissipation is often directional
        # due to cooling systems, vents, etc.
        # Simplified model: stronger heat in +z direction (typical cooling design)
        direction_factor = 1.0
        if pos.z > self.position.z + half_height:  # Above the equipment
            direction_factor = 1.5  # More heat rises
        
        # Characteristic length depends on power
        r_0 = 0.3 * (self.power / 100.0)**0.3
        
        # Calculate temperature
        temperature = ambient_temperature + direction_factor * \
                      (self.temperature - ambient_temperature) * np.exp(-distance / r_0)
        
        return temperature


class ThermalProfile:
    """
    Represents temperature distribution in space from multiple thermal sources.
    
    Attributes:
        sources (Dict[str, ThermalSource]): Collection of thermal sources by name
        ambient_temperature (float): Ambient temperature in Kelvin
    """
    
    def __init__(self, ambient_temperature: float = AMBIENT_TEMPERATURE):
        """
        Initialize a thermal profile.
        
        Args:
            ambient_temperature: Ambient temperature in Kelvin (default: 293.15K, 20°C)
        """
        self.sources: Dict[str, ThermalSource] = {}
        self.ambient_temperature = ambient_temperature
    
    def add_source(self, source: ThermalSource) -> bool:
        """
        Add a thermal source to the profile.
        
        Args:
            source: The thermal source to add
            
        Returns:
            True if the source was added, False if a source with the same name exists
        """
        if source.name in self.sources:
            return False
        
        self.sources[source.name] = source
        return True
    
    def remove_source(self, name: str) -> bool:
        """
        Remove a thermal source from the profile.
        
        Args:
            name: Name of the source to remove
            
        Returns:
            True if the source was removed, False if not found
        """
        if name in self.sources:
            del self.sources[name]
            return True
        return False
    
    def get_source(self, name: str) -> Optional[ThermalSource]:
        """
        Get a source by name.
        
        Args:
            name: Name of the source to retrieve
            
        Returns:
            The thermal source if found, None otherwise
        """
        return self.sources.get(name)
    
    def set_ambient_temperature(self, temperature: float):
        """
        Set the ambient temperature.
        
        Args:
            temperature: New ambient temperature in Kelvin
        """
        self.ambient_temperature = temperature
    
    def calculate_temperature_at(self, position: Tuple[float, float, float]) -> float:
        """
        Calculate the combined temperature at a specific point from all sources.
        
        Args:
            position: 3D coordinates (x, y, z) to calculate temperature at
            
        Returns:
            Combined temperature at the specified position in Kelvin
        """
        # Start with ambient temperature
        ambient_temp = self.ambient_temperature
        
        # If no sources, just return ambient temperature
        if not self.sources:
            return ambient_temp
        
        # For temperature, using a "maximum temperature wins" approach is often reasonable
        # rather than additive, as heat sources don't typically add linearly
        max_temp = ambient_temp
        
        # Check each source
        for source in self.sources.values():
            if source.enabled:
                temp = source.calculate_temperature_at(position, ambient_temp)
                max_temp = max(max_temp, temp)
        
        return max_temp
    
    def calculate_temperature_grid(self, 
                                 x_range: Tuple[float, float, int],
                                 y_range: Tuple[float, float, int],
                                 z: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate temperature over a 2D grid at a fixed height.
        
        Args:
            x_range: Tuple of (min_x, max_x, num_points) for x-axis sampling
            y_range: Tuple of (min_y, max_y, num_points) for y-axis sampling
            z: Fixed z-coordinate for the 2D slice
            
        Returns:
            Tuple of (X, Y, T) where:
                X, Y are coordinate meshgrids
                T is the temperature at each point in Kelvin
        """
        # Create coordinate grid
        x = np.linspace(x_range[0], x_range[1], x_range[2])
        y = np.linspace(y_range[0], y_range[1], y_range[2])
        X, Y = np.meshgrid(x, y)
        
        # Initialize temperature array
        T = np.ones_like(X) * self.ambient_temperature
        
        # Calculate temperature at each point
        for i in range(X.shape[0]):
            for j in range(X.shape[1]):
                T[i, j] = self.calculate_temperature_at((X[i, j], Y[i, j], z))
                
        return X, Y, T
    
    def plot_temperature_2d(self, 
                          x_range: Tuple[float, float, int],
                          y_range: Tuple[float, float, int],
                          z: float,
                          show_sources: bool = True,
                          show_celsius: bool = True,
                          title: Optional[str] = None,
                          filename: Optional[str] = None):
        """
        Plot temperature distribution over a 2D grid.
        
        Args:
            x_range: Tuple of (min_x, max_x, num_points) for x-axis sampling
            y_range: Tuple of (min_y, max_y, num_points) for y-axis sampling
            z: Fixed z-coordinate for the 2D slice
            show_sources: Whether to show source positions
            show_celsius: Whether to show temperature in Celsius (otherwise Kelvin)
            title: Optional title for the plot
            filename: Optional filename to save the plot
        """
        # Calculate temperature grid
        X, Y, T = self.calculate_temperature_grid(x_range, y_range, z)
        
        # Convert to Celsius if requested
        if show_celsius:
            T = T - 273.15  # Kelvin to Celsius conversion
            temp_label = 'Temperature (°C)'
        else:
            temp_label = 'Temperature (K)'
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Plot temperature contours
        contour = ax.contourf(X, Y, T, cmap='hot', levels=50)
        
        # Add colorbar
        cbar = plt.colorbar(contour, ax=ax)
        cbar.set_label(temp_label)
        
        # Set labels
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        
        # Set title
        plot_title = title if title else f"Temperature Distribution at z={z}m"
        ax.set_title(plot_title)
        
        # Show source positions if requested
        if show_sources:
            for source in self.sources.values():
                # Only show if near the slice
                if abs(source.position.z - z) < 1.0:
                    # For point sources, show as markers
                    ax.plot(source.position.x, source.position.y, 'ko', markersize=8)
                    ax.text(source.position.x + 0.1, source.position.y + 0.1, 
                          source.name, fontsize=8)
                    
                    # For sources with dimensions, show bounding box
                    if hasattr(source, 'dimensions'):
                        half_width = source.dimensions[0] / 2
                        half_depth = source.dimensions[1] / 2
                        
                        # Draw rectangle for bounding box
                        x_min = source.position.x - half_width
                        x_max = source.position.x + half_width
                        y_min = source.position.y - half_depth
                        y_max = source.position.y + half_depth
                        
                        ax.plot([x_min, x_max, x_max, x_min, x_min],
                              [y_min, y_min, y_max, y_max, y_min],
                              'k--', linewidth=1)
        
        plt.tight_layout()
        
        # Save figure if filename provided
        if filename:
            plt.savefig(filename, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def get_sources_by_type(self, source_type: str) -> List[ThermalSource]:
        """
        Get all sources of a specific type.
        
        Args:
            source_type: Type of sources to retrieve
            
        Returns:
            List of thermal sources of the specified type
        """
        return [src for src in self.sources.values() if src.source_type == source_type]
    
    def __len__(self) -> int:
        """Return the number of sources in the profile."""
        return len(self.sources)


class ThermalVisualizer:
    """
    Provides visualization tools for thermal signatures.
    """
    
    @staticmethod
    def plot_thermal_image(thermal_profile: ThermalProfile,
                           x_range: Tuple[float, float, int],
                           y_range: Tuple[float, float, int],
                           z: float,
                           colormap: str = 'inferno',
                           show_sources: bool = True,
                           show_celsius: bool = True,
                           title: Optional[str] = None,
                           filename: Optional[str] = None):
        """
        Generate a thermal image visualization of a temperature distribution.
        
        Args:
            thermal_profile: The thermal profile to visualize
            x_range: Tuple of (min_x, max_x, num_points) for x-axis sampling
            y_range: Tuple of (min_y, max_y, num_points) for y-axis sampling
            z: Fixed z-coordinate for the 2D slice
            colormap: Colormap to use for visualization (default: 'inferno')
            show_sources: Whether to show source positions
            show_celsius: Whether to show temperature in Celsius (otherwise Kelvin)
            title: Optional title for the plot
            filename: Optional filename to save the plot
        """
        # Calculate temperature grid
        X, Y, T = thermal_profile.calculate_temperature_grid(x_range, y_range, z)
        
        # Convert to Celsius if requested
        if show_celsius:
            T = T - 273.15  # Kelvin to Celsius conversion
            temp_label = 'Temperature (°C)'
        else:
            temp_label = 'Temperature (K)'
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Use a thermal imaging style colormap
        contour = ax.imshow(T, extent=[x_range[0], x_range[1], y_range[0], y_range[1]],
                           origin='lower', cmap=colormap, interpolation='bilinear')
        
        # Add colorbar
        cbar = plt.colorbar(contour, ax=ax)
        cbar.set_label(temp_label)
        
        # Set labels
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        
        # Set title
        plot_title = title if title else f"Thermal Image at z={z}m"
        ax.set_title(plot_title)
        
        # Show source positions if requested
        if show_sources:
            for source in thermal_profile.sources.values():
                # Only show if near the slice
                if abs(source.position.z - z) < 1.0:
                    # For point sources, show as markers
                    ax.plot(source.position.x, source.position.y, 'wo', markersize=8)
                    ax.text(source.position.x + 0.1, source.position.y + 0.1, 
                          source.name, fontsize=8, color='white')
                    
                    # For sources with dimensions, show bounding box
                    if hasattr(source, 'dimensions'):
                        half_width = source.dimensions[0] / 2
                        half_depth = source.dimensions[1] / 2
                        
                        # Draw rectangle for bounding box
                        x_min = source.position.x - half_width
                        x_max = source.position.x + half_width
                        y_min = source.position.y - half_depth
                        y_max = source.position.y + half_depth
                        
                        ax.plot([x_min, x_max, x_max, x_min, x_min],
                              [y_min, y_min, y_max, y_max, y_min],
                              'w--', linewidth=1)
        
        plt.tight_layout()
        
        # Save figure if filename provided
        if filename:
            plt.savefig(filename, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    @staticmethod
    def plot_3d_temperature_distribution(thermal_profile: ThermalProfile,
                                       x_range: Tuple[float, float, int],
                                       y_range: Tuple[float, float, int],
                                       z_range: Tuple[float, float, int],
                                       show_celsius: bool = True,
                                       opacity: float = 0.7,
                                       title: Optional[str] = None,
                                       filename: Optional[str] = None):
        """
        Generate a 3D visualization of a temperature distribution.
        
        Args:
            thermal_profile: The thermal profile to visualize
            x_range: Tuple of (min_x, max_x, num_points) for x-axis sampling
            y_range: Tuple of (min_y, max_y, num_points) for y-axis sampling
            z_range: Tuple of (min_z, max_z, num_points) for z-axis sampling
            show_celsius: Whether to show temperature in Celsius (otherwise Kelvin)
            opacity: Opacity level for the 3D visualization (0-1)
            title: Optional title for the plot
            filename: Optional filename to save the plot
        """
        # Create coordinate grid
        x = np.linspace(x_range[0], x_range[1], x_range[2])
        y = np.linspace(y_range[0], y_range[1], y_range[2])
        z = np.linspace(z_range[0], z_range[1], z_range[2])
        
        # Create figure
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # For each z-slice, calculate and visualize temperature
        for k, z_val in enumerate(z):
            # Calculate temperature grid for this slice
            X, Y = np.meshgrid(x, y)
            T = np.zeros_like(X)
            
            # Calculate temperature at each point
            for i in range(X.shape[0]):
                for j in range(X.shape[1]):
                    T[i, j] = thermal_profile.calculate_temperature_at((X[i, j], Y[i, j], z_val))
            
            # Convert to Celsius if requested
            if show_celsius:
                T = T - 273.15  # Kelvin to Celsius
            
            # Only show points above ambient temperature (with some margin)
            threshold = thermal_profile.ambient_temperature + 2
            if show_celsius:
                threshold = threshold - 273.15
                
            # Create mask for values above threshold
            mask = T > threshold
            
            if np.any(mask):
                # Plot the points with temperature color coding
                scatter = ax.scatter(X[mask], Y[mask], np.full_like(X[mask], z_val),
                                   c=T[mask], cmap='hot', alpha=opacity,
                                   s=5, edgecolor='none')
        
        # Add sources as markers
        for source in thermal_profile.sources.values():
            ax.scatter([source.position.x], [source.position.y], [source.position.z],
                     color='black', s=50, marker='o', edgecolor='white')
            ax.text(source.position.x, source.position.y, source.position.z,
                  source.name, fontsize=8)
        
        # Add colorbar
        cbar = fig.colorbar(scatter, ax=ax, pad=0.1)
        if show_celsius:
            cbar.set_label('Temperature (°C)')
        else:
            cbar.set_label('Temperature (K)')
        
        # Set labels and title
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_zlabel('Z (m)')
        
        if title:
            ax.set_title(title)
        else:
            ax.set_title('3D Temperature Distribution')
        
        # Save figure if filename provided
        if filename:
            plt.savefig(filename, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    @staticmethod
    def generate_thermal_time_sequence(thermal_profile: ThermalProfile,
                                     x_range: Tuple[float, float, int],
                                     y_range: Tuple[float, float, int],
                                     z: float,
                                     time_steps: int,
                                     update_function: callable,
                                     colormap: str = 'inferno',
                                     show_celsius: bool = True,
                                     output_dir: Optional[str] = None,
                                     base_filename: str = 'thermal_frame'):
        """
        Generate a sequence of thermal images over time.
        
        Args:
            thermal_profile: The thermal profile to visualize
            x_range: Tuple of (min_x, max_x, num_points) for x-axis sampling
            y_range: Tuple of (min_y, max_y, num_points) for y-axis sampling
            z: Fixed z-coordinate for the 2D slice
            time_steps: Number of time steps to simulate
            update_function: Function that updates the thermal sources between frames
                             Takes (thermal_profile, time_step) as arguments
            colormap: Colormap to use for visualization
            show_celsius: Whether to show temperature in Celsius (otherwise Kelvin)
            output_dir: Directory to save frames (if None, frames are not saved)
            base_filename: Base filename for saved frames
        """
        for step in range(time_steps):
            # Update thermal sources for this time step
            update_function(thermal_profile, step)
            
            # Generate frame title
            title = f"Thermal Distribution - Time Step {step+1}/{time_steps}"
            
            # Generate output filename if needed
            filename = None
            if output_dir:
                filename = f"{output_dir}/{base_filename}_{step:04d}.png"
            
            # Generate thermal image
            ThermalVisualizer.plot_thermal_image(
                thermal_profile, x_range, y_range, z,
                colormap=colormap, show_celsius=show_celsius,
                title=title, filename=filename
            )
            
            # Small pause between frames for visualization
            plt.pause(0.1)
