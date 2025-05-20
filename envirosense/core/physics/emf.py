"""
EnviroSense Physics Engine - Electromagnetic Field Modeling

This module provides classes and functions for modeling electromagnetic fields
produced by utility infrastructure components such as power lines, transformers,
and switches. It implements the Biot-Savart law for magnetic field calculation and
provides tools for field visualization and analysis.

Classes:
    EMFSource: Base class for electromagnetic field sources
    PowerLine: Represents a power line as an EMF source
    Transformer: Represents a transformer as an EMF source
    Switch: Represents a power switch as an EMF source
    EMFField: Manages multiple EMF sources and calculates combined fields
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Optional, Union

from envirosense.core.physics.coordinates import Vector3D

# Constants
MU_0 = 4 * np.pi * 1e-7  # Permeability of free space (H/m)


class EMFSource(ABC):
    """
    Abstract base class for all electromagnetic field sources.
    
    Attributes:
        name (str): Unique identifier for the source
        position (Vector3D): 3D position of the source
        enabled (bool): Whether the source is currently active
    """
    
    def __init__(self, name: str, position: Tuple[float, float, float]):
        """
        Initialize an EMF source.
        
        Args:
            name: Unique identifier for the source
            position: 3D coordinates (x, y, z) of the source in meters
        """
        self.name = name
        self.position = Vector3D(*position)
        self.enabled = True
    
    @abstractmethod
    def calculate_field_at(self, position: Tuple[float, float, float]) -> Tuple[Vector3D, Vector3D]:
        """
        Calculate the electric and magnetic fields at a specific position.
        
        Args:
            position: 3D coordinates (x, y, z) to calculate the field at
            
        Returns:
            Tuple of Vector3D representing (electric_field, magnetic_field) in V/m and T
        """
        pass
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the type of EMF source."""
        pass
    
    def enable(self):
        """Enable this EMF source."""
        self.enabled = True
        
    def disable(self):
        """Disable this EMF source."""
        self.enabled = False


class PowerLine(EMFSource):
    """
    Represents a power transmission or distribution line as an EMF source.
    
    Attributes:
        name (str): Unique identifier for the source
        start_point (Vector3D): Starting point of the power line
        end_point (Vector3D): Ending point of the power line
        current (float): Current flowing through the line in amperes
        voltage (float): Voltage of the line in volts
        frequency (float): AC frequency in Hz (typically 50 or 60)
        phase (float): Phase angle in radians
    """
    
    def __init__(self, name: str, 
                start_point: Tuple[float, float, float], 
                end_point: Tuple[float, float, float],
                current: float, 
                voltage: float,
                frequency: float = 60.0,
                phase: float = 0.0):
        """
        Initialize a power line EMF source.
        
        Args:
            name: Unique identifier for the source
            start_point: 3D coordinates of line start point (x, y, z) in meters
            end_point: 3D coordinates of line end point (x, y, z) in meters
            current: Current flowing through the line in amperes
            voltage: Voltage of the line in volts
            frequency: AC frequency in Hz (default: 60.0)
            phase: Phase angle in radians (default: 0.0)
        """
        # Use the midpoint as the source position
        midpoint = ((start_point[0] + end_point[0]) / 2,
                    (start_point[1] + end_point[1]) / 2,
                    (start_point[2] + end_point[2]) / 2)
        
        super().__init__(name, midpoint)
        self.start_point = Vector3D(*start_point)
        self.end_point = Vector3D(*end_point)
        self.current = current
        self.voltage = voltage
        self.frequency = frequency
        self.phase = phase
        
        # Calculate direction vector of the line
        self._direction = (self.end_point - self.start_point).normalize()
        self._length = (self.end_point - self.start_point).magnitude()
    
    @property
    def source_type(self) -> str:
        return "power_line"
    
    def calculate_field_at(self, position: Tuple[float, float, float]) -> Tuple[Vector3D, Vector3D]:
        """
        Calculate the electric and magnetic fields at a specific position using
        the Biot-Savart law for the magnetic field and a simplified model for the electric field.
        
        Args:
            position: 3D coordinates (x, y, z) to calculate the field at
            
        Returns:
            Tuple of Vector3D representing (electric_field, magnetic_field) in V/m and T
        """
        if not self.enabled:
            return Vector3D(0, 0, 0), Vector3D(0, 0, 0)
        
        pos = Vector3D(*position)
        
        # Calculate magnetic field using the Biot-Savart law
        # For a finite straight wire, we integrate along the wire
        # B = (μ₀*I/4π) * (sinθ₂ - sinθ₁)/r
        
        # Vector from position to start and end points
        r1 = pos - self.start_point
        r2 = pos - self.end_point
        
        # Distance from the line to the position
        p = self._closest_point_on_line(pos)
        r = (pos - p).magnitude()
        
        if r < 0.01:  # Avoid division by zero or numerical issues
            r = 0.01
        
        # Calculate angles
        cos_theta1 = r1.dot(self._direction) / r1.magnitude()
        cos_theta2 = r2.dot(self._direction) / r2.magnitude()
        
        # Clamp to valid range [-1, 1] to avoid numerical issues
        cos_theta1 = max(-1.0, min(1.0, cos_theta1))
        cos_theta2 = max(-1.0, min(1.0, cos_theta2))
        
        sin_theta1 = np.sqrt(1 - cos_theta1**2)
        sin_theta2 = np.sqrt(1 - cos_theta2**2)
        
        if r1.dot(self._direction) < 0:
            sin_theta1 *= -1
        if r2.dot(self._direction) < 0:
            sin_theta2 *= -1
        
        # Calculate magnetic field magnitude
        # Using simplified Biot-Savart for finite wire segment
        B_mag = (MU_0 * self.current) / (4 * np.pi * r) * (sin_theta2 - sin_theta1)
        
        # Direction of B is perpendicular to both the wire and the displacement vector
        # from wire to the position
        displacement = pos - p
        if displacement.magnitude() < 0.01:
            B_dir = Vector3D(0, 0, 0)
        else:
            B_dir = self._direction.cross(displacement.normalize())
        
        # Magnetic field vector
        B_vec = B_dir.normalize() * B_mag if B_dir.magnitude() > 0 else Vector3D(0, 0, 0)
        
        # Calculate electric field - simplified model based on distance and voltage
        # Using approximate formula for power line electric field
        if r < 0.01:  # Avoid division by zero
            r = 0.01
            
        # Electric field strength decreases with distance from the line
        # This is a simplified model - actual field calculation would use Coulomb's law
        # with charge distribution
        E_mag = self.voltage / (2 * np.pi * 8.85e-12 * r * np.log(10))
        
        # Direction of E points radially from the line
        E_dir = displacement
        E_vec = E_dir.normalize() * E_mag if E_dir.magnitude() > 0 else Vector3D(0, 0, 0)
        
        return E_vec, B_vec
    
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


class Transformer(EMFSource):
    """
    Represents an electrical transformer as an EMF source.
    
    Attributes:
        name (str): Unique identifier for the source
        position (Vector3D): 3D position of the transformer
        power_rating (float): Power rating in VA
        primary_voltage (float): Voltage on the primary side in volts
        secondary_voltage (float): Voltage on the secondary side in volts
        frequency (float): AC frequency in Hz
        load_factor (float): Current load factor (0.0-1.0)
    """
    
    def __init__(self, name: str, 
                position: Tuple[float, float, float],
                power_rating: float,
                primary_voltage: float,
                secondary_voltage: float,
                frequency: float = 60.0,
                load_factor: float = 0.8):
        """
        Initialize a transformer EMF source.
        
        Args:
            name: Unique identifier for the source
            position: 3D coordinates (x, y, z) of the transformer in meters
            power_rating: Power rating in VA
            primary_voltage: Voltage on the primary side in volts
            secondary_voltage: Voltage on the secondary side in volts
            frequency: AC frequency in Hz (default: 60.0)
            load_factor: Current load factor 0.0-1.0 (default: 0.8)
        """
        super().__init__(name, position)
        self.power_rating = power_rating
        self.primary_voltage = primary_voltage
        self.secondary_voltage = secondary_voltage
        self.frequency = frequency
        self.load_factor = max(0.0, min(1.0, load_factor))  # Clamp to valid range
        
        # Calculate primary and secondary currents
        self.primary_current = self.power_rating * self.load_factor / self.primary_voltage
        self.secondary_current = self.power_rating * self.load_factor / self.secondary_voltage
    
    @property
    def source_type(self) -> str:
        return "transformer"
    
    def set_load_factor(self, load_factor: float):
        """
        Update the transformer's load factor and recalculate currents.
        
        Args:
            load_factor: New load factor (0.0-1.0)
        """
        self.load_factor = max(0.0, min(1.0, load_factor))
        self.primary_current = self.power_rating * self.load_factor / self.primary_voltage
        self.secondary_current = self.power_rating * self.load_factor / self.secondary_voltage
    
    def calculate_field_at(self, position: Tuple[float, float, float]) -> Tuple[Vector3D, Vector3D]:
        """
        Calculate the electric and magnetic fields at a specific position.
        For transformers, we use a dipole approximation for the magnetic field.
        
        Args:
            position: 3D coordinates (x, y, z) to calculate the field at
            
        Returns:
            Tuple of Vector3D representing (electric_field, magnetic_field) in V/m and T
        """
        if not self.enabled:
            return Vector3D(0, 0, 0), Vector3D(0, 0, 0)
        
        pos = Vector3D(*position)
        
        # Vector from transformer to position
        r_vec = pos - self.position
        r = r_vec.magnitude()
        
        if r < 0.1:  # Minimum distance to avoid singularity
            r = 0.1
        
        # Magnetic field - using approximate model for transformer
        # Transformers can be approximated as magnetic dipoles
        # Field falls off as 1/r³ for dipole
        
        # Effective magnetic moment is proportional to transformer size/rating
        # This is a simplified model - actual field would require detailed transformer model
        moment_factor = 1e-7 * self.power_rating / 1000  # Scale based on power rating
        
        # Assume dipole is aligned with z-axis
        dipole_orientation = Vector3D(0, 0, 1)
        
        # Magnetic field from dipole
        r_norm = r_vec.normalize()
        B_mag = moment_factor * (3 * r_norm.dot(dipole_orientation) * r_norm - dipole_orientation) / (r**3)
        
        # Electric field - very simplified model
        # In reality, transformer electric field is complex and shielded
        E_mag = Vector3D(0, 0, 0)
        if r > 0.1:
            # Simple inverse square approximation for electric field
            # Field strength related to voltage
            field_strength = 0.5 * self.primary_voltage / (r**2)
            E_mag = r_vec.normalize() * field_strength
        
        return E_mag, B_mag


class Switch(EMFSource):
    """
    Represents an electrical switch (circuit breaker, disconnect, etc.) as an EMF source.
    
    Attributes:
        name (str): Unique identifier for the source
        position (Vector3D): 3D position of the switch
        current_rating (float): Current rating in amps
        voltage_rating (float): Voltage rating in volts
        is_switching (bool): Whether the switch is actively changing state
        state (str): Current state ('open', 'closed', 'arcing')
    """
    
    # Constants for switch state
    STATE_OPEN = "open"
    STATE_CLOSED = "closed"
    STATE_ARCING = "arcing"
    
    def __init__(self, name: str, 
                position: Tuple[float, float, float],
                current_rating: float,
                voltage_rating: float,
                state: str = STATE_CLOSED):
        """
        Initialize a switch EMF source.
        
        Args:
            name: Unique identifier for the source
            position: 3D coordinates (x, y, z) of the switch in meters
            current_rating: Current rating in amps
            voltage_rating: Voltage rating in volts
            state: Initial state (default: closed)
        """
        super().__init__(name, position)
        self.current_rating = current_rating
        self.voltage_rating = voltage_rating
        self.is_switching = False
        
        # Validate and set the initial state
        if state not in [self.STATE_OPEN, self.STATE_CLOSED, self.STATE_ARCING]:
            state = self.STATE_CLOSED
        self.state = state
        
        # Current flow depends on state
        self.current = 0.8 * current_rating if state == self.STATE_CLOSED else 0.0
        if state == self.STATE_ARCING:
            self.current = 0.3 * current_rating  # Partial current during arcing
    
    @property
    def source_type(self) -> str:
        return "switch"
    
    def set_state(self, state: str, is_switching: bool = False):
        """
        Update the switch state and recalculate EMF properties.
        
        Args:
            state: New state ('open', 'closed', 'arcing')
            is_switching: Whether the switch is actively changing state
        """
        if state not in [self.STATE_OPEN, self.STATE_CLOSED, self.STATE_ARCING]:
            return
        
        self.state = state
        self.is_switching = is_switching
        
        # Update current based on state
        if state == self.STATE_CLOSED:
            self.current = 0.8 * self.current_rating
        elif state == self.STATE_OPEN:
            self.current = 0.0
        else:  # arcing
            self.current = 0.3 * self.current_rating  # Partial current during arcing
    
    def calculate_field_at(self, position: Tuple[float, float, float]) -> Tuple[Vector3D, Vector3D]:
        """
        Calculate the electric and magnetic fields at a specific position.
        Switch EMF characteristics vary significantly based on state.
        
        Args:
            position: 3D coordinates (x, y, z) to calculate the field at
            
        Returns:
            Tuple of Vector3D representing (electric_field, magnetic_field) in V/m and T
        """
        if not self.enabled:
            return Vector3D(0, 0, 0), Vector3D(0, 0, 0)
        
        pos = Vector3D(*position)
        
        # Vector from switch to position
        r_vec = pos - self.position
        r = r_vec.magnitude()
        
        if r < 0.05:  # Minimum distance to avoid singularity
            r = 0.05
        
        # Calculate magnetic field
        # For a closed switch, approximate as a current-carrying conductor
        # For open switch, field is minimal
        # For arcing switch, field includes high-frequency components
        
        # Base magnetic field calculation (simplified)
        B_mag = MU_0 * self.current / (2 * np.pi * r)
        
        # Direction perpendicular to radial vector and assumed current direction (z-axis)
        B_dir = r_vec.cross(Vector3D(0, 0, 1))
        
        if B_dir.magnitude() < 0.001:
            # If parallel to z-axis, pick arbitrary perpendicular
            B_dir = Vector3D(1, 0, 0)
            
        B_vec = B_dir.normalize() * B_mag if B_dir.magnitude() > 0 else Vector3D(0, 0, 0)
        
        # For arcing state, add high-frequency components (simplified)
        if self.state == self.STATE_ARCING:
            # Add random fluctuations to simulate arc instability
            arc_factor = 1.0 + 0.5 * np.sin(r * 10) + 0.3 * np.cos(r * 15)
            B_vec = B_vec * arc_factor
        
        # Electric field calculation
        # Open switch has stronger electric field due to voltage difference
        # Closed switch has minimal electric field
        E_base = self.voltage_rating / (4 * np.pi * 8.85e-12 * r**2)
        
        if self.state == self.STATE_OPEN:
            # Stronger electric field when open
            E_factor = 1.0
        elif self.state == self.STATE_ARCING:
            # Erratic electric field during arcing
            E_factor = 0.7 + 0.5 * np.sin(r * 20)
        else:  # closed
            # Minimal electric field when closed
            E_factor = 0.1
            
        E_vec = r_vec.normalize() * E_base * E_factor
        
        return E_vec, B_vec


class EMFField:
    """
    Manages multiple EMF sources and calculates combined electromagnetic fields.
    
    Attributes:
        sources (Dict[str, EMFSource]): Collection of EMF sources by name
    """
    
    def __init__(self):
        """Initialize an empty EMF field."""
        self.sources: Dict[str, EMFSource] = {}
    
    def add_source(self, source: EMFSource) -> bool:
        """
        Add an EMF source to the field.
        
        Args:
            source: The EMF source to add
            
        Returns:
            True if the source was added, False if a source with the same name exists
        """
        if source.name in self.sources:
            return False
        
        self.sources[source.name] = source
        return True
    
    def remove_source(self, name: str) -> bool:
        """
        Remove an EMF source from the field.
        
        Args:
            name: Name of the source to remove
            
        Returns:
            True if the source was removed, False if not found
        """
        if name in self.sources:
            del self.sources[name]
            return True
        return False
    
    def get_source(self, name: str) -> Optional[EMFSource]:
        """
        Get a source by name.
        
        Args:
            name: Name of the source to retrieve
            
        Returns:
            The EMF source if found, None otherwise
        """
        return self.sources.get(name)
    
    def calculate_field_at(self, position: Tuple[float, float, float]) -> Tuple[Vector3D, Vector3D]:
        """
        Calculate the combined electric and magnetic fields at a specific position.
        
        Args:
            position: 3D coordinates (x, y, z) to calculate the field at
            
        Returns:
            Tuple of Vector3D representing (electric_field, magnetic_field) in V/m and T
        """
        # Initialize zero fields
        total_e = Vector3D(0, 0, 0)
        total_b = Vector3D(0, 0, 0)
        
        # Sum contributions from all sources
        for source in self.sources.values():
            if source.enabled:
                e_field, b_field = source.calculate_field_at(position)
                total_e += e_field
                total_b += b_field
                
        return total_e, total_b
    
    def calculate_field_grid(self, 
                          x_range: Tuple[float, float, int],
                          y_range: Tuple[float, float, int],
                          z: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate the EMF field over a 2D grid at a fixed height.
        
        Args:
            x_range: Tuple of (min_x, max_x, num_points) for x-axis sampling
            y_range: Tuple of (min_y, max_y, num_points) for y-axis sampling
            z: Fixed z-coordinate for the 2D slice
            
        Returns:
            Tuple of (X, Y, E_mag, B_mag) where:
                X, Y are coordinate meshgrids
                E_mag is the electric field magnitude at each point
                B_mag is the magnetic field magnitude at each point
        """
        # Create coordinate grid
        x = np.linspace(x_range[0], x_range[1], x_range[2])
        y = np.linspace(y_range[0], y_range[1], y_range[2])
        X, Y = np.meshgrid(x, y)
        
        # Initialize field magnitude arrays
        E_mag = np.zeros_like(X)
        B_mag = np.zeros_like(X)
        
        # Calculate field at each point
        for i in range(X.shape[0]):
            for j in range(X.shape[1]):
                e_field, b_field = self.calculate_field_at((X[i, j], Y[i, j], z))
                E_mag[i, j] = e_field.magnitude()
                B_mag[i, j] = b_field.magnitude()
                
        return X, Y, E_mag, B_mag
    
    def plot_fields_2d(self, 
                      x_range: Tuple[float, float, int],
                      y_range: Tuple[float, float, int],
                      z: float,
                      show_e_field: bool = True,
                      show_b_field: bool = True,
                      show_sources: bool = True,
                      title: Optional[str] = None,
                      filename: Optional[str] = None):
        """
        Plot the EMF field strengths over a 2D grid.
        
        Args:
            x_range: Tuple of (min_x, max_x, num_points) for x-axis sampling
            y_range: Tuple of (min_y, max_y, num_points) for y-axis sampling
            z: Fixed z-coordinate for the 2D slice
            show_e_field: Whether to show electric field plot
            show_b_field: Whether to show magnetic field plot
            show_sources: Whether to show source positions
            title: Optional title for the plot
            filename: Optional filename to save the plot
        """
        # Calculate field grid
        X, Y, E_mag, B_mag = self.calculate_field_grid(x_range, y_range, z)
        
        # Create subplot layout based on what's shown
        if show_e_field and show_b_field:
            fig, axs = plt.subplots(1, 2, figsize=(16, 7))
        else:
            fig, axs = plt.subplots(1, 1, figsize=(8, 7))
            axs = [axs]
        
        # Plot titles
        main_title = title if title else f"EMF Field at z={z}m"
        fig.suptitle(main_title, fontsize=16)
        
        plot_idx = 0
        
        # Plot electric field
        if show_e_field:
            im_e = axs[plot_idx].contourf(X, Y, E_mag, cmap='hot', levels=50)
            axs[plot_idx].set_title('Electric Field Magnitude (V/m)')
            axs[plot_idx].set_xlabel('X (m)')
            axs[plot_idx].set_ylabel('Y (m)')
            plt.colorbar(im_e, ax=axs[plot_idx])
            
            # Show source positions
            if show_sources:
                for source in self.sources.values():
                    if abs(source.position.z - z) < 1.0:  # Only show if near the slice
                        axs[plot_idx].plot(source.position.x, source.position.y, 'ko', markersize=8)
                        axs[plot_idx].text(source.position.x + 0.1, source.position.y + 0.1, 
                                         source.name, fontsize=8)
            plot_idx += 1
            
        # Plot magnetic field
        if show_b_field:
            # Convert to microtesla for better readability
            B_mag_uT = B_mag * 1e6
            im_b = axs[plot_idx].contourf(X, Y, B_mag_uT, cmap='viridis', levels=50)
            axs[plot_idx].set_title('Magnetic Field Magnitude (μT)')
            axs[plot_idx].set_xlabel('X (m)')
            axs[plot_idx].set_ylabel('Y (m)')
            plt.colorbar(im_b, ax=axs[plot_idx])
            
            # Show source positions
            if show_sources:
                for source in self.sources.values():
                    if abs(source.position.z - z) < 1.0:  # Only show if near the slice
                        axs[plot_idx].plot(source.position.x, source.position.y, 'ko', markersize=8)
                        axs[plot_idx].text(source.position.x + 0.1, source.position.y + 0.1, 
                                         source.name, fontsize=8)
        
        plt.tight_layout()
        
        # Save figure if filename provided
        if filename:
            plt.savefig(filename, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def get_sources_by_type(self, source_type: str) -> List[EMFSource]:
        """
        Get all sources of a specific type.
        
        Args:
            source_type: Type of sources to retrieve
            
        Returns:
            List of EMF sources of the specified type
        """
        return [src for src in self.sources.values() if src.source_type == source_type]
    
    def __len__(self) -> int:
        """Return the number of sources in the field."""
        return len(self.sources)
