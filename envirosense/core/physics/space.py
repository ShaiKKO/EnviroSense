"""
EnviroSense Physics Engine - Spatial Grid System

This module provides classes for implementing a 3D spatial grid system
that models physical environments for environmental simulations.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
import logging

logger = logging.getLogger(__name__)


class GridCell:
    """
    Represents a discrete cell in the spatial grid.
    
    Each cell stores environmental parameters and maintains relationships
    with neighboring cells for diffusion and other physics calculations.
    """
    
    def __init__(self, position: Tuple[int, int, int], volume: float = 1.0):
        """
        Initialize a grid cell at the specified position.
        
        Args:
            position: Tuple of (x, y, z) indices in the grid
            volume: Cell volume in cubic meters
        """
        self.position = position
        self.volume = volume
        self.parameters = {}  # Environmental parameters at this location
        self.neighbors = {}   # References to neighboring cells
        
    def set_parameter(self, name: str, value: float) -> None:
        """
        Set the value of an environmental parameter in this cell.
        
        Args:
            name: Parameter name
            value: Parameter value
        """
        self.parameters[name] = value
        
    def get_parameter(self, name: str, default: float = 0.0) -> float:
        """
        Get the value of an environmental parameter in this cell.
        
        Args:
            name: Parameter name
            default: Default value if parameter is not present
            
        Returns:
            The parameter value
        """
        return self.parameters.get(name, default)
    
    def add_neighbor(self, direction: str, cell: 'GridCell') -> None:
        """
        Add a reference to a neighboring cell.
        
        Args:
            direction: Label for the neighbor direction 
                      (e.g., 'north', 'south', 'up', 'down')
            cell: The neighboring GridCell
        """
        self.neighbors[direction] = cell
        
    def get_neighbor(self, direction: str) -> Optional['GridCell']:
        """
        Get a reference to a neighboring cell.
        
        Args:
            direction: Label for the neighbor direction
            
        Returns:
            The neighboring GridCell, or None if no neighbor exists
        """
        return self.neighbors.get(direction)
    
    def get_all_neighbors(self) -> Dict[str, 'GridCell']:
        """
        Get all neighboring cells.
        
        Returns:
            Dictionary mapping directions to neighboring cells
        """
        return self.neighbors


class SpatialGrid:
    """
    Implements a 3D discretized space with configurable resolution.
    
    The grid stores environmental parameters at each point and provides
    methods for propagating values between grid points to simulate
    environmental physics.
    """
    
    # Direction vectors for six cardinal directions (3D)
    CARDINAL_DIRECTIONS = {
        'east': (1, 0, 0),
        'west': (-1, 0, 0),
        'north': (0, 1, 0),
        'south': (0, -1, 0),
        'up': (0, 0, 1),
        'down': (0, 0, -1)
    }
    
    def __init__(self, dimensions: Tuple[int, int, int], cell_size: float = 0.1):
        """
        Initialize the spatial grid with the specified dimensions.
        
        Args:
            dimensions: Tuple of (width, length, height) in grid cells
            cell_size: Size of each grid cell in meters
        """
        self.dimensions = dimensions
        self.cell_size = cell_size
        self.grid = {}  # Dictionary mapping position tuples to GridCell objects
        self.boundaries = {}  # Dictionary of boundary conditions
        
        # Initialize grid cells
        self._initialize_grid()
        
    def _initialize_grid(self) -> None:
        """
        Initialize the grid with empty cells at each position.
        """
        width, length, height = self.dimensions
        for x in range(width):
            for y in range(length):
                for z in range(height):
                    position = (x, y, z)
                    self.grid[position] = GridCell(position, self.cell_size**3)
        
        # Connect neighboring cells
        self._connect_neighbors()
        
    def _connect_neighbors(self) -> None:
        """
        Connect each cell to its neighbors for efficient access.
        """
        width, length, height = self.dimensions
        
        for x in range(width):
            for y in range(length):
                for z in range(height):
                    cell = self.get_cell((x, y, z))
                    if not cell:
                        continue
                        
                    # Add neighbors in all cardinal directions
                    for direction, (dx, dy, dz) in self.CARDINAL_DIRECTIONS.items():
                        nx, ny, nz = x + dx, y + dy, z + dz
                        
                        # Skip if outside grid boundaries
                        if not (0 <= nx < width and 0 <= ny < length and 0 <= nz < height):
                            continue
                            
                        neighbor = self.get_cell((nx, ny, nz))
                        if neighbor:
                            cell.add_neighbor(direction, neighbor)
    
    def get_cell(self, position: Tuple[int, int, int]) -> Optional[GridCell]:
        """
        Get the cell at the specified grid position.
        
        Args:
            position: Tuple of (x, y, z) indices in the grid
            
        Returns:
            The GridCell at that position, or None if position is invalid
        """
        return self.grid.get(position)
    
    def set_parameter_at(self, position: Tuple[int, int, int], 
                         name: str, value: float) -> bool:
        """
        Set the value of a parameter at the specified position.
        
        Args:
            position: Tuple of (x, y, z) indices in the grid
            name: Parameter name
            value: Parameter value
            
        Returns:
            True if successful, False if position is invalid
        """
        cell = self.get_cell(position)
        if cell:
            cell.set_parameter(name, value)
            return True
        return False
    
    def get_parameter_at(self, position: Tuple[int, int, int], 
                         name: str, default: float = 0.0) -> float:
        """
        Get the value of a parameter at the specified position.
        
        Args:
            position: Tuple of (x, y, z) indices in the grid
            name: Parameter name
            default: Default value if parameter is not present
            
        Returns:
            The parameter value
        """
        cell = self.get_cell(position)
        if cell:
            return cell.get_parameter(name, default)
        return default
        
    def get_average_parameter(self, zone_positions: Optional[List[Tuple[int, int, int]]], 
                              name: str, default: float = 0.0) -> float:
        """
        Get the average value of a parameter across multiple positions.
        
        Args:
            zone_positions: List of grid positions to average, or None for all cells
            name: Parameter name
            default: Default value if parameter is not present
            
        Returns:
            The average parameter value
        """
        if zone_positions is None:
            # Average across all cells
            positions = [pos for pos, _ in self.iterate_cells()]
        else:
            positions = zone_positions
            
        if not positions:
            return default
            
        total = 0.0
        count = 0
        
        for pos in positions:
            value = self.get_parameter_at(pos, name, None)
            if value is not None:
                total += value
                count += 1
                
        if count == 0:
            return default
            
        return total / count
    
    def set_boundary_condition(self, face: str, 
                               parameter: str, 
                               condition_type: str,
                               value: Any = None) -> None:
        """
        Set a boundary condition for a particular grid face.
        
        Args:
            face: The grid face ('top', 'bottom', 'north', 'south', 'east', 'west')
            parameter: The parameter affected by this boundary condition
            condition_type: Type of boundary ('fixed', 'periodic', 'reflective')
            value: Value for the boundary condition (if applicable)
        """
        valid_faces = ['top', 'bottom', 'north', 'south', 'east', 'west']
        valid_types = ['fixed', 'periodic', 'reflective']
        
        if face not in valid_faces:
            logger.warning(f"Invalid boundary face: {face}")
            return
            
        if condition_type not in valid_types:
            logger.warning(f"Invalid boundary condition type: {condition_type}")
            return
            
        self.boundaries.setdefault(face, {})[parameter] = {
            'type': condition_type,
            'value': value
        }
        
    def apply_boundary_conditions(self) -> None:
        """
        Apply all boundary conditions to the grid.
        """
        width, length, height = self.dimensions
        
        # Handle each boundary face
        for face, conditions in self.boundaries.items():
            for parameter, config in conditions.items():
                condition_type = config['type']
                value = config['value']
                
                # Apply the appropriate boundary condition
                if face == 'top':
                    self._apply_face_boundary(parameter, condition_type, value,
                                             [(x, y, height-1) for x in range(width) for y in range(length)])
                elif face == 'bottom':
                    self._apply_face_boundary(parameter, condition_type, value,
                                             [(x, y, 0) for x in range(width) for y in range(length)])
                elif face == 'north':
                    self._apply_face_boundary(parameter, condition_type, value,
                                             [(x, length-1, z) for x in range(width) for z in range(height)])
                elif face == 'south':
                    self._apply_face_boundary(parameter, condition_type, value,
                                             [(x, 0, z) for x in range(width) for z in range(height)])
                elif face == 'east':
                    self._apply_face_boundary(parameter, condition_type, value,
                                             [(width-1, y, z) for y in range(length) for z in range(height)])
                elif face == 'west':
                    self._apply_face_boundary(parameter, condition_type, value,
                                             [(0, y, z) for y in range(length) for z in range(height)])
    
    def _apply_face_boundary(self, parameter: str, condition_type: str, 
                            value: Any, positions: List[Tuple[int, int, int]]) -> None:
        """
        Apply a boundary condition to a set of positions.
        
        Args:
            parameter: The parameter to apply the condition to
            condition_type: Type of boundary ('fixed', 'periodic', 'reflective')
            value: Value for the boundary condition (if applicable)
            positions: List of positions to apply the condition to
        """
        if condition_type == 'fixed':
            for pos in positions:
                self.set_parameter_at(pos, parameter, value)
        # The other boundary conditions would be implemented similarly
        # with more complex logic for periodic and reflective conditions
    
    def iterate_cells(self) -> List[Tuple[Tuple[int, int, int], GridCell]]:
        """
        Iterate through all cells in the grid.
        
        Returns:
            List of tuples containing position and cell
        """
        return list(self.grid.items())
    
    def diffuse_parameter(self, parameter: str, diffusion_rate: float) -> None:
        """
        Diffuse a parameter across the grid using a simple diffusion model.
        
        Args:
            parameter: Name of the parameter to diffuse
            diffusion_rate: Rate of diffusion (0 to 1)
        """
        # Create a copy of the current parameter values
        new_values = {}
        
        # Calculate diffusion for each cell
        for position, cell in self.iterate_cells():
            current_value = cell.get_parameter(parameter, 0.0)
            total_diffusion = 0.0
            neighbor_count = 0
            
            # Get diffusion from all neighbors
            for direction, neighbor in cell.get_all_neighbors().items():
                neighbor_value = neighbor.get_parameter(parameter, 0.0)
                total_diffusion += neighbor_value - current_value
                neighbor_count += 1
                
            if neighbor_count > 0:
                # Apply diffusion equation
                new_value = current_value + (diffusion_rate * total_diffusion / neighbor_count)
                new_values[position] = new_value
        
        # Update all cells with new values
        for position, value in new_values.items():
            cell = self.get_cell(position)
            if cell:
                cell.set_parameter(parameter, value)
                
    def physical_coordinates(self, grid_pos: Tuple[int, int, int]) -> Tuple[float, float, float]:
        """
        Convert grid coordinates to physical coordinates in meters.
        
        Args:
            grid_pos: Grid coordinates (x, y, z)
            
        Returns:
            Physical coordinates in meters (x, y, z)
        """
        x, y, z = grid_pos
        return (x * self.cell_size, y * self.cell_size, z * self.cell_size)
        
    def grid_coordinates(self, physical_pos: Tuple[float, float, float]) -> Tuple[int, int, int]:
        """
        Convert physical coordinates to grid coordinates.
        
        Args:
            physical_pos: Physical coordinates in meters (x, y, z)
            
        Returns:
            Grid coordinates (x, y, z)
        """
        x, y, z = physical_pos
        return (
            int(x / self.cell_size), 
            int(y / self.cell_size), 
            int(z / self.cell_size)
        )
    
    def is_position_valid(self, position: Tuple[int, int, int]) -> bool:
        """
        Check if a grid position is valid (within bounds).
        
        Args:
            position: Grid coordinates (x, y, z)
            
        Returns:
            True if the position is valid, False otherwise
        """
        x, y, z = position
        width, length, height = self.dimensions
        return 0 <= x < width and 0 <= y < length and 0 <= z < height
