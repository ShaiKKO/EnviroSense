"""
EnviroSense Physics Engine - Airflow Modeling System

This module provides classes for modeling airflow patterns in indoor environments,
which is essential for simulating how parameters like VOCs and particulates
propagate through a space.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
import logging
from .space import SpatialGrid, GridCell
from .geometry import Room, GeometryObject
from .coordinates import Vector3D

logger = logging.getLogger(__name__)


class VentilationSource:
    """
    Represents a source of airflow such as an HVAC vent, fan, or natural opening.
    
    Ventilation sources create airflow patterns that affect the movement of
    parameters throughout the space.
    """
    
    # Ventilation source types
    TYPE_INLET = "inlet"       # Air flows into the room (positive pressure)
    TYPE_OUTLET = "outlet"     # Air flows out of the room (negative pressure)
    TYPE_BIDIRECTIONAL = "bidirectional"  # Air can flow in both directions (window)
    
    def __init__(self, name: str, position: Tuple[float, float, float],
                direction: Tuple[float, float, float],
                flow_rate: float, 
                source_type: str = TYPE_INLET,
                radius: float = 0.15):
        """
        Initialize a ventilation source.
        
        Args:
            name: Source identifier
            position: Position of the source in space (x, y, z) in meters
            direction: Direction vector of airflow (normalized internally)
            flow_rate: Air flow rate in cubic meters per second
            source_type: Type of source (inlet, outlet, bidirectional)
            radius: Radius of influence in meters
        """
        self.name = name
        self.position = Vector3D.from_tuple(position)
        
        # Normalize direction vector
        dir_vec = Vector3D.from_tuple(direction)
        if dir_vec.magnitude() > 0:
            self.direction = dir_vec.normalize()
        else:
            self.direction = Vector3D(0, 0, 1)  # Default to vertical if zero
            
        self.flow_rate = flow_rate
        self.source_type = source_type
        self.radius = radius
        
        # For bidirectional sources, track the current direction
        self.current_direction = 1.0  # 1.0 for inflow, -1.0 for outflow
        
        # Precompute some values for efficiency
        self._update_derived_values()
    
    def _update_derived_values(self) -> None:
        """
        Update derived values when source properties change.
        """
        # Calculate maximum velocity at source based on flow rate and area
        area = np.pi * self.radius**2
        self.max_velocity = self.flow_rate / area
        
        # Adjust direction based on source type
        if self.source_type == self.TYPE_OUTLET:
            self.current_direction = -1.0
        elif self.source_type == self.TYPE_INLET:
            self.current_direction = 1.0
        # For bidirectional, current_direction should be set externally
    
    def set_flow_rate(self, flow_rate: float) -> None:
        """
        Set the flow rate of the source.
        
        Args:
            flow_rate: New flow rate in cubic meters per second
        """
        self.flow_rate = flow_rate
        self._update_derived_values()
    
    def set_direction(self, direction: Tuple[float, float, float]) -> None:
        """
        Set the direction of airflow.
        
        Args:
            direction: New direction vector (normalized internally)
        """
        dir_vec = Vector3D.from_tuple(direction)
        if dir_vec.magnitude() > 0:
            self.direction = dir_vec.normalize()
            self._update_derived_values()
    
    def toggle_direction(self) -> None:
        """
        Toggle the flow direction for bidirectional sources.
        """
        if self.source_type == self.TYPE_BIDIRECTIONAL:
            self.current_direction *= -1.0
    
    def get_velocity_at(self, point: Tuple[float, float, float]) -> Vector3D:
        """
        Calculate the air velocity vector at a given point due to this source.
        
        Uses an inverse square model to approximate velocity falloff with distance.
        
        Args:
            point: Position to calculate velocity at (x, y, z) in meters
            
        Returns:
            Vector3D representing velocity in meters per second
        """
        # Convert point to Vector3D for easier calculations
        pos = Vector3D.from_tuple(point)
        
        # Calculate distance from source to point
        distance = self.position.distance_to(pos)
        
        # If point is at the source position, return maximum velocity
        if distance < 0.001:
            return self.direction * self.max_velocity * self.current_direction
        
        # If point is beyond effective radius, velocity is negligible
        effective_radius = self.radius * 10.0  # Extend influence beyond physical radius
        if distance > effective_radius:
            return Vector3D(0, 0, 0)
        
        # Calculate direction from source to point
        to_point = (pos - self.position).normalize()
        
        # Calculate cosine of angle between flow direction and direction to point
        cos_angle = self.direction.dot(to_point)
        
        # For outlets or reverse flow, we care about flow toward the source
        if self.current_direction < 0:
            cos_angle = -cos_angle
        
        # Adjust influence based on angle (stronger in flow direction)
        angle_factor = max(0.0, cos_angle)  # Only affect downstream
        
        # Calculate velocity magnitude using inverse square law
        # We use a smoother falloff within the physical radius
        if distance < self.radius:
            # Linear falloff within radius
            velocity_magnitude = self.max_velocity * (1.0 - distance / self.radius)
        else:
            # Inverse square falloff beyond radius
            velocity_magnitude = self.max_velocity * (self.radius / distance)**2
        
        # Apply angle factor and direction
        velocity = self.direction * velocity_magnitude * angle_factor * self.current_direction
        
        return velocity


class AirflowModel:
    """
    Models airflow patterns in an enclosed space.
    
    This class provides simplified fluid dynamics for real-time simulation
    of air movement, which affects the propagation of parameters throughout the space.
    """
    
    def __init__(self, grid: SpatialGrid, room: Optional[Room] = None):
        """
        Initialize the airflow model.
        
        Args:
            grid: The spatial grid to model airflow on
            room: Optional room geometry for boundary conditions
        """
        self.grid = grid
        self.room = room
        self.sources = {}  # Dictionary mapping names to VentilationSource instances
        
        # Velocity field - will be initialized on demand
        self.velocity_field = None
        
        # Air exchange rate (in air changes per hour)
        self.air_exchange_rate = 1.0
        
        # Properties for simulation
        self.diffusion_coefficient = 0.05
        self.time_step = 0.1  # seconds
    
    def add_source(self, source: VentilationSource) -> None:
        """
        Add a ventilation source to the model.
        
        Args:
            source: The ventilation source to add
        """
        self.sources[source.name] = source
        # Invalidate velocity field so it will be recalculated
        self.velocity_field = None
    
    def remove_source(self, name: str) -> None:
        """
        Remove a ventilation source from the model.
        
        Args:
            name: The name of the source to remove
        """
        if name in self.sources:
            del self.sources[name]
            # Invalidate velocity field
            self.velocity_field = None
    
    def get_sources(self) -> List[VentilationSource]:
        """
        Get all ventilation sources.
        
        Returns:
            List of ventilation sources
        """
        return list(self.sources.values())
    
    def set_air_exchange_rate(self, rate: float) -> None:
        """
        Set the air exchange rate for the room.
        
        Args:
            rate: Air exchange rate in air changes per hour
        """
        self.air_exchange_rate = max(0.0, rate)
    
    def calculate_velocity_field(self) -> Dict[Tuple[int, int, int], Vector3D]:
        """
        Calculate the velocity vector at each grid cell based on all sources.
        
        Returns:
            Dictionary mapping grid positions to velocity vectors
        """
        # Initialize empty velocity field
        velocity_field = {}
        
        # For each grid cell
        for position, cell in self.grid.iterate_cells():
            # Get physical coordinates of cell center
            physical_pos = self.grid.physical_coordinates(position)
            
            # Initialize zero velocity
            velocity = Vector3D(0, 0, 0)
            
            # Add contribution from each source
            for source in self.sources.values():
                src_velocity = source.get_velocity_at(physical_pos)
                velocity = velocity + src_velocity
            
            # Store in velocity field
            velocity_field[position] = velocity
        
        # Cache the calculated field
        self.velocity_field = velocity_field
        return velocity_field
    
    def get_velocity_at(self, position: Tuple[int, int, int]) -> Vector3D:
        """
        Get the velocity vector at a specific grid position.
        
        Args:
            position: Grid position (x, y, z)
            
        Returns:
            Vector3D representing velocity in meters per second
        """
        # Calculate velocity field if needed
        if self.velocity_field is None:
            self.calculate_velocity_field()
        
        # Return velocity at the specified position, or zero if not found
        return self.velocity_field.get(position, Vector3D(0, 0, 0))
    
    def advect_parameter(self, parameter: str, time_step: Optional[float] = None) -> None:
        """
        Advect a parameter through the grid based on the velocity field.
        
        This moves parameter values through the grid based on airflow.
        
        Args:
            parameter: The name of the parameter to advect
            time_step: Time step for advection in seconds, or None to use default
        """
        if time_step is None:
            time_step = self.time_step
        
        # Calculate velocity field if needed
        if self.velocity_field is None:
            self.calculate_velocity_field()
        
        # Create a copy of current parameter values
        new_values = {}
        
        # For each cell
        for position, cell in self.grid.iterate_cells():
            x, y, z = position
            
            # Get current parameter value
            current_value = cell.get_parameter(parameter, 0.0)
            
            # Get velocity at this cell
            velocity = self.get_velocity_at(position)
            
            if velocity.magnitude() < 0.001:
                # No significant airflow, value stays the same
                new_values[position] = current_value
                continue
            
            # Calculate where the air at this cell came from
            # using semi-Lagrangian advection (backward tracing)
            src_x = x - velocity.x * time_step / self.grid.cell_size
            src_y = y - velocity.y * time_step / self.grid.cell_size
            src_z = z - velocity.z * time_step / self.grid.cell_size
            
            # Convert to integer indices with clamping to grid bounds
            width, length, height = self.grid.dimensions
            src_x_idx = max(0, min(width - 1, int(src_x)))
            src_y_idx = max(0, min(length - 1, int(src_y)))
            src_z_idx = max(0, min(height - 1, int(src_z)))
            
            # Get parameter value at source position
            src_position = (src_x_idx, src_y_idx, src_z_idx)
            src_cell = self.grid.get_cell(src_position)
            if src_cell:
                src_value = src_cell.get_parameter(parameter, 0.0)
                new_values[position] = src_value
            else:
                new_values[position] = current_value
        
        # Update grid with new values
        for position, value in new_values.items():
            cell = self.grid.get_cell(position)
            if cell:
                cell.set_parameter(parameter, value)
    
    def apply_airflow_step(self, parameters: List[str], time_step: Optional[float] = None) -> None:
        """
        Apply a single time step of airflow to the specified parameters.
        
        This performs both advection due to airflow and diffusion.
        
        Args:
            parameters: List of parameter names to update
            time_step: Time step in seconds, or None to use default
        """
        if time_step is None:
            time_step = self.time_step
        
        # First advect parameters due to airflow
        for param in parameters:
            self.advect_parameter(param, time_step)
        
        # Then apply diffusion
        for param in parameters:
            self.grid.diffuse_parameter(param, self.diffusion_coefficient * time_step)
        
        # Apply air exchange with outside
        self._apply_air_exchange(parameters, time_step)
    
    def _apply_air_exchange(self, parameters: List[str], time_step: float) -> None:
        """
        Apply air exchange with the outside environment.
        
        This models the effect of fresh air entering the space.
        
        Args:
            parameters: List of parameter names to update
            time_step: Time step in seconds
        """
        # Convert air changes per hour to a rate per second
        exchange_rate = self.air_exchange_rate / 3600.0
        
        # Calculate the fraction of air exchanged in this time step
        exchange_fraction = 1.0 - np.exp(-exchange_rate * time_step)
        
        # For each parameter
        for param in parameters:
            # Get assumed outside concentration (usually zero)
            outside_concentration = 0.0
            
            # For each cell
            for position, cell in self.grid.iterate_cells():
                current_value = cell.get_parameter(param, 0.0)
                
                # Mix with outside air
                new_value = current_value * (1.0 - exchange_fraction) + outside_concentration * exchange_fraction
                
                # Update cell parameter
                cell.set_parameter(param, new_value)
    
    def simulate(self, parameters: List[str], 
                duration: float, 
                time_step: Optional[float] = None) -> None:
        """
        Simulate airflow for a specified duration.
        
        Args:
            parameters: List of parameter names to update
            duration: Total simulation time in seconds
            time_step: Time step in seconds, or None to use default
        """
        if time_step is None:
            time_step = self.time_step
        
        # Calculate number of steps
        num_steps = int(duration / time_step)
        
        # Run simulation steps
        for _ in range(num_steps):
            self.apply_airflow_step(parameters, time_step)


class AirflowVisualizer:
    """
    Helper class for visualizing airflow patterns.
    """
    
    @staticmethod
    def create_vector_field(airflow_model: AirflowModel, 
                          plane: str = 'xy', 
                          offset: int = 0,
                          spacing: int = 1) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Create a vector field representation for visualization.
        
        Args:
            airflow_model: The airflow model to visualize
            plane: Plane to visualize ('xy', 'xz', or 'yz')
            offset: Offset from origin in the normal direction
            spacing: Spacing between vectors in grid cells
            
        Returns:
            Tuple of (X, Y, U, V) for 2D plotting
        """
        # Ensure velocity field is calculated
        if airflow_model.velocity_field is None:
            airflow_model.calculate_velocity_field()
        
        grid = airflow_model.grid
        width, length, height = grid.dimensions
        
        if plane == 'xy':
            # Create meshgrid for xy plane
            x_points = np.arange(0, width, spacing)
            y_points = np.arange(0, length, spacing)
            X, Y = np.meshgrid(x_points, y_points)
            
            # Initialize velocity components
            U = np.zeros_like(X, dtype=float)
            V = np.zeros_like(Y, dtype=float)
            
            # Fill velocity components
            for i, x in enumerate(x_points):
                for j, y in enumerate(y_points):
                    z = min(offset, height - 1)
                    pos = (x, y, z)
                    velocity = airflow_model.get_velocity_at(pos)
                    U[j, i] = velocity.x
                    V[j, i] = velocity.y
            
            return X, Y, U, V
        
        elif plane == 'xz':
            # Create meshgrid for xz plane
            x_points = np.arange(0, width, spacing)
            z_points = np.arange(0, height, spacing)
            X, Z = np.meshgrid(x_points, z_points)
            
            # Initialize velocity components
            U = np.zeros_like(X, dtype=float)
            V = np.zeros_like(Z, dtype=float)
            
            # Fill velocity components
            for i, x in enumerate(x_points):
                for j, z in enumerate(z_points):
                    y = min(offset, length - 1)
                    pos = (x, y, z)
                    velocity = airflow_model.get_velocity_at(pos)
                    U[j, i] = velocity.x
                    V[j, i] = velocity.z
            
            return X, Z, U, V
        
        elif plane == 'yz':
            # Create meshgrid for yz plane
            y_points = np.arange(0, length, spacing)
            z_points = np.arange(0, height, spacing)
            Y, Z = np.meshgrid(y_points, z_points)
            
            # Initialize velocity components
            U = np.zeros_like(Y, dtype=float)
            V = np.zeros_like(Z, dtype=float)
            
            # Fill velocity components
            for i, y in enumerate(y_points):
                for j, z in enumerate(z_points):
                    x = min(offset, width - 1)
                    pos = (x, y, z)
                    velocity = airflow_model.get_velocity_at(pos)
                    U[j, i] = velocity.y
                    V[j, i] = velocity.z
            
            return Y, Z, U, V
        
        else:
            raise ValueError(f"Invalid plane: {plane}. Must be 'xy', 'xz', or 'yz'.")
    
    @staticmethod
    def create_streamlines(airflow_model: AirflowModel, 
                         plane: str = 'xy', 
                         offset: int = 0) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Create streamline data for visualization.
        
        Args:
            airflow_model: The airflow model to visualize
            plane: Plane to visualize ('xy', 'xz', or 'yz')
            offset: Offset from origin in the normal direction
            
        Returns:
            Tuple of (X, Y, U, V) for streamplot
        """
        # Get vector field with fine spacing for streamlines
        spacing = 1  # Use every grid cell for smooth streamlines
        return AirflowVisualizer.create_vector_field(airflow_model, plane, offset, spacing)
    
    @staticmethod
    def plot_vector_field(ax, X, Y, U, V, 
                        scale: float = 1.0, 
                        density: float = 1.0,
                        color: str = 'blue') -> None:
        """
        Plot a vector field on the given matplotlib axis.
        
        Args:
            ax: Matplotlib axis to plot on
            X, Y: Meshgrid coordinates
            U, V: Vector components
            scale: Scale factor for vector lengths
            density: Density of vectors to plot
            color: Color of vectors
        """
        try:
            import matplotlib.pyplot as plt
            
            # Calculate vector magnitudes for coloring
            magnitude = np.sqrt(U**2 + V**2)
            
            # Plot vector field
            ax.quiver(X, Y, U, V, magnitude, 
                     scale=scale, 
                     cmap='viridis',
                     width=0.002,
                     headwidth=4,
                     headlength=4)
            
            # Add colorbar
            cbar = plt.colorbar(ax.collections[0], ax=ax)
            cbar.set_label('Velocity magnitude (m/s)')
            
        except ImportError:
            logger.warning("Matplotlib is required for visualization but not installed.")
    
    @staticmethod
    def plot_streamlines(ax, X, Y, U, V, 
                       density: float = 1.0,
                       color: str = 'blue') -> None:
        """
        Plot streamlines on the given matplotlib axis.
        
        Args:
            ax: Matplotlib axis to plot on
            X, Y: Meshgrid coordinates
            U, V: Vector components
            density: Density of streamlines
            color: Color of streamlines
        """
        try:
            import matplotlib.pyplot as plt
            
            # Calculate vector magnitudes for coloring
            magnitude = np.sqrt(U**2 + V**2)
            
            # Plot streamlines
            strm = ax.streamplot(X, Y, U, V, 
                               density=density,
                               color=magnitude,
                               cmap='viridis',
                               linewidth=1.5 * magnitude / magnitude.max())
            
            # Add colorbar
            cbar = plt.colorbar(strm.lines, ax=ax)
            cbar.set_label('Velocity magnitude (m/s)')
            
        except ImportError:
            logger.warning("Matplotlib is required for visualization but not installed.")
