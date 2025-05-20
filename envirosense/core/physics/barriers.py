"""
EnviroSense Physics Engine - Barriers and Partitions Module

This module provides classes for implementing barriers and partitions
with material properties that affect diffusion, absorption, and reflection
of environmental parameters.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
import logging
from .space import SpatialGrid, GridCell
from .geometry import GeometryObject, Material, Wall

logger = logging.getLogger(__name__)


class Barrier(GeometryObject):
    """
    Represents a barrier or partition in the environment.
    
    Unlike walls, barriers can be partially permeable to chemicals and
    can have varying degrees of transmission for different parameters.
    """
    
    def __init__(self, name: str, material: Material, 
                start_point: Tuple[float, float, float],
                end_point: Tuple[float, float, float],
                thickness: float = 0.05,
                permeability: Dict[str, float] = None):
        """
        Initialize a barrier object.
        
        Args:
            name: Barrier identifier
            material: Barrier material properties
            start_point: Starting corner (x, y, z) in meters
            end_point: Opposite corner (x, y, z) in meters
            thickness: Barrier thickness in meters
            permeability: Dictionary mapping parameter names to permeability values (0-1)
                          where 0 is completely impermeable and 1 is completely permeable
        """
        super().__init__(name, material)
        self.start_point = start_point
        self.end_point = end_point
        self.thickness = thickness
        
        # Default permeability is based on material's vapor permeability
        if permeability is None:
            permeability = {}
        self.permeability = permeability
        
        # Identify which dimension is the "thickness" dimension
        x1, y1, z1 = start_point
        x2, y2, z2 = end_point
        dims = [abs(x2 - x1), abs(y2 - y1), abs(z2 - z1)]
        self.thin_dim = dims.index(min(dims))
        
    def contains_point(self, point: Tuple[float, float, float]) -> bool:
        """
        Check if a point is contained within this barrier.
        
        Args:
            point: Physical coordinates (x, y, z) in meters
            
        Returns:
            True if the point is inside the barrier, False otherwise
        """
        x, y, z = point
        x1, y1, z1 = self.start_point
        x2, y2, z2 = self.end_point
        
        # Ensure point is within the bounding box
        if not (min(x1, x2) <= x <= max(x1, x2) and
                min(y1, y2) <= y <= max(y1, y2) and
                min(z1, z2) <= z <= max(z1, z2)):
            return False
            
        return True
    
    def surface_normal_at(self, point: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """
        Get the surface normal vector at a given point on the barrier.
        
        Args:
            point: Physical coordinates (x, y, z) in meters
            
        Returns:
            Normalized direction vector (nx, ny, nz) perpendicular to the barrier
        """
        # For a barrier, the normal is along the thin dimension
        normal = [0, 0, 0]
        x1, y1, z1 = self.start_point
        x2, y2, z2 = self.end_point
        
        if self.thin_dim == 0:  # X is the thin dimension
            normal[0] = 1 if x2 > x1 else -1
        elif self.thin_dim == 1:  # Y is the thin dimension
            normal[1] = 1 if y2 > y1 else -1
        else:  # Z is the thin dimension
            normal[2] = 1 if z2 > z1 else -1
            
        return tuple(normal)
    
    def get_bounding_box(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """
        Get the axis-aligned bounding box containing this barrier.
        
        Returns:
            Tuple of (min_point, max_point) where each point is (x, y, z)
        """
        x1, y1, z1 = self.start_point
        x2, y2, z2 = self.end_point
        
        min_point = (min(x1, x2), min(y1, y2), min(z1, z2))
        max_point = (max(x1, x2), max(y1, y2), max(z1, z2))
        
        return (min_point, max_point)
    
    def get_permeability(self, parameter: str) -> float:
        """
        Get the permeability value for a specific parameter.
        
        Args:
            parameter: The parameter name
            
        Returns:
            Permeability value between 0 and 1
        """
        # If parameter has a specific permeability, use it
        if parameter in self.permeability:
            return self.permeability[parameter]
        
        # For VOCs, use the material's VOC absorption rates
        if parameter in self.material.voc_absorption_rates:
            # Convert absorption rate to permeability
            # High absorption = low permeability
            absorption = self.material.voc_absorption_rates[parameter]
            return 1.0 - absorption
        
        # Default to material's vapor permeability for other parameters
        return self.material.vapor_permeability
    
    def set_permeability(self, parameter: str, value: float) -> None:
        """
        Set the permeability value for a specific parameter.
        
        Args:
            parameter: The parameter name
            value: Permeability value between 0 and 1
        """
        # Ensure value is between 0 and 1
        value = max(0.0, min(1.0, value))
        self.permeability[parameter] = value
    
    def affects_parameter(self, parameter: str, point: Tuple[float, float, float], 
                         value: float) -> float:
        """
        Calculate how this barrier affects a parameter value at a point.
        
        Args:
            parameter: Parameter name
            point: Physical coordinates (x, y, z) in meters
            value: Current parameter value
            
        Returns:
            Modified parameter value based on barrier properties
        """
        perm = self.get_permeability(parameter)
        
        # Apply permeability - reduces the value based on barrier properties
        return value * perm


class BarrierHandler:
    """
    Manages the effect of barriers on parameter diffusion in the spatial grid.
    """
    
    def __init__(self, grid: SpatialGrid):
        """
        Initialize the barrier handler.
        
        Args:
            grid: The spatial grid to manage barriers for
        """
        self.grid = grid
        self.barriers = []  # List of all barriers
        
        # Cache barrier information at grid cell interfaces for efficiency
        self.barrier_cache = {}  # (pos1, pos2) -> List[Barrier]
    
    def add_barrier(self, barrier: Barrier) -> None:
        """
        Add a barrier to the handler.
        
        Args:
            barrier: The barrier to add
        """
        self.barriers.append(barrier)
        # Invalidate cache since barriers have changed
        self.barrier_cache = {}
    
    def remove_barrier(self, barrier_name: str) -> None:
        """
        Remove a barrier from the handler.
        
        Args:
            barrier_name: Name of the barrier to remove
        """
        self.barriers = [b for b in self.barriers if b.name != barrier_name]
        # Invalidate cache since barriers have changed
        self.barrier_cache = {}
    
    def _get_barriers_between(self, pos1: Tuple[int, int, int], 
                             pos2: Tuple[int, int, int]) -> List[Barrier]:
        """
        Get all barriers between two adjacent grid cells.
        
        Args:
            pos1: Position of first grid cell
            pos2: Position of second grid cell
            
        Returns:
            List of barriers between the cells
        """
        # Check cache first
        cache_key = (pos1, pos2)
        if cache_key in self.barrier_cache:
            return self.barrier_cache[cache_key]
        
        # Convert grid positions to physical coordinates
        phys_pos1 = self.grid.physical_coordinates(pos1)
        phys_pos2 = self.grid.physical_coordinates(pos2)
        
        # Find midpoint between the cells
        midpoint = tuple((p1 + p2) / 2 for p1, p2 in zip(phys_pos1, phys_pos2))
        
        # Check which barriers contain this midpoint
        barriers_between = [b for b in self.barriers if b.contains_point(midpoint)]
        
        # Cache the result
        self.barrier_cache[cache_key] = barriers_between
        return barriers_between
    
    def modify_diffusion_rate(self, parameter: str, 
                             pos1: Tuple[int, int, int],
                             pos2: Tuple[int, int, int],
                             base_rate: float) -> float:
        """
        Modify the diffusion rate between two adjacent cells based on barriers.
        
        Args:
            parameter: The parameter being diffused
            pos1: Position of first grid cell
            pos2: Position of second grid cell
            base_rate: Base diffusion rate before barrier effects
            
        Returns:
            Modified diffusion rate accounting for barriers
        """
        # Get barriers between the cells
        barriers = self._get_barriers_between(pos1, pos2)
        
        if not barriers:
            # No barriers, use base rate
            return base_rate
        
        # Apply each barrier's effect
        modified_rate = base_rate
        for barrier in barriers:
            perm = barrier.get_permeability(parameter)
            modified_rate *= perm
        
        return modified_rate
    
    def diffuse_parameter_with_barriers(self, parameter: str, diffusion_rate: float) -> None:
        """
        Diffuse a parameter across the grid accounting for barriers.
        
        Args:
            parameter: Name of the parameter to diffuse
            diffusion_rate: Base rate of diffusion (0 to 1)
        """
        # Create a copy of the current parameter values
        new_values = {}
        
        # Calculate diffusion for each cell
        for position, cell in self.grid.iterate_cells():
            current_value = cell.get_parameter(parameter, 0.0)
            total_diffusion = 0.0
            neighbor_count = 0
            
            # Get diffusion from all neighbors
            for direction, neighbor in cell.get_all_neighbors().items():
                neighbor_pos = neighbor.position
                neighbor_value = neighbor.get_parameter(parameter, 0.0)
                
                # Modify diffusion rate based on barriers
                local_diffusion_rate = self.modify_diffusion_rate(
                    parameter, position, neighbor_pos, diffusion_rate)
                
                # Calculate diffusion contribution
                diffusion = (neighbor_value - current_value) * local_diffusion_rate
                total_diffusion += diffusion
                neighbor_count += 1
                
            if neighbor_count > 0:
                # Apply diffusion equation
                new_value = current_value + total_diffusion / neighbor_count
                new_values[position] = new_value
        
        # Update all cells with new values
        for position, value in new_values.items():
            cell = self.grid.get_cell(position)
            if cell:
                cell.set_parameter(parameter, value)


class PartitionedRoom:
    """
    Extension of Room class that adds management of internal partitions and barriers.
    """
    
    @staticmethod
    def add_partition(grid: SpatialGrid, barrier_handler: BarrierHandler,
                     start_point: Tuple[float, float, float],
                     end_point: Tuple[float, float, float],
                     material_name: str = "drywall",
                     partition_name: str = None,
                     permeability: Dict[str, float] = None) -> Barrier:
        """
        Add an internal partition to a room.
        
        Args:
            grid: The spatial grid to add the partition to
            barrier_handler: The barrier handler to register the partition with
            start_point: Starting corner (x, y, z) in meters
            end_point: Opposite corner (x, y, z) in meters
            material_name: Name of the material to use for the partition
            partition_name: Optional name for the partition
            permeability: Optional dictionary of parameter-specific permeability values
            
        Returns:
            The created Barrier object
        """
        from .geometry import Material
        
        material = Material.from_library(material_name)
        
        if partition_name is None:
            partition_name = f"partition_{len(barrier_handler.barriers)}"
        
        barrier = Barrier(
            name=partition_name,
            material=material,
            start_point=start_point,
            end_point=end_point,
            permeability=permeability
        )
        
        barrier_handler.add_barrier(barrier)
        return barrier
    
    @staticmethod
    def create_room_divider(grid: SpatialGrid, barrier_handler: BarrierHandler,
                           room_origin: Tuple[float, float, float],
                           room_dimensions: Tuple[float, float, float],
                           orientation: str,
                           position_ratio: float,
                           opening_start: float = None,
                           opening_width: float = None,
                           material_name: str = "drywall") -> List[Barrier]:
        """
        Create a room divider with an optional opening.
        
        Args:
            grid: The spatial grid to add the divider to
            barrier_handler: The barrier handler to register the divider with
            room_origin: Room origin (x, y, z) in meters
            room_dimensions: Room dimensions (width, length, height) in meters
            orientation: 'x' for divider along YZ plane, 'y' for XZ plane
            position_ratio: Position of divider as ratio of room dimension (0-1)
            opening_start: Optional start position of opening as ratio (0-1)
            opening_width: Optional width of opening as ratio of room dimension (0-1)
            material_name: Name of the material to use for the divider
            
        Returns:
            List of created Barrier objects (1 or 2 depending on if opening exists)
        """
        x, y, z = room_origin
        width, length, height = room_dimensions
        
        barriers = []
        
        if orientation == 'x':
            # Divider along YZ plane
            divider_x = x + width * position_ratio
            
            if opening_start is not None and opening_width is not None:
                # Create divider with opening
                opening_y = y + length * opening_start
                opening_height = length * opening_width
                
                # Lower part
                if opening_start > 0:
                    lower = PartitionedRoom.add_partition(
                        grid, barrier_handler,
                        (divider_x, y, z),
                        (divider_x, opening_y, z + height),
                        material_name,
                        f"divider_x_{position_ratio}_lower"
                    )
                    barriers.append(lower)
                
                # Upper part
                if opening_start + opening_width < 1.0:
                    upper = PartitionedRoom.add_partition(
                        grid, barrier_handler,
                        (divider_x, opening_y + opening_height, z),
                        (divider_x, y + length, z + height),
                        material_name,
                        f"divider_x_{position_ratio}_upper"
                    )
                    barriers.append(upper)
            else:
                # Create full divider
                full = PartitionedRoom.add_partition(
                    grid, barrier_handler,
                    (divider_x, y, z),
                    (divider_x, y + length, z + height),
                    material_name,
                    f"divider_x_{position_ratio}"
                )
                barriers.append(full)
                
        elif orientation == 'y':
            # Divider along XZ plane
            divider_y = y + length * position_ratio
            
            if opening_start is not None and opening_width is not None:
                # Create divider with opening
                opening_x = x + width * opening_start
                opening_width = width * opening_width
                
                # Lower part
                if opening_start > 0:
                    lower = PartitionedRoom.add_partition(
                        grid, barrier_handler,
                        (x, divider_y, z),
                        (opening_x, divider_y, z + height),
                        material_name,
                        f"divider_y_{position_ratio}_lower"
                    )
                    barriers.append(lower)
                
                # Upper part
                if opening_start + opening_width < 1.0:
                    upper = PartitionedRoom.add_partition(
                        grid, barrier_handler,
                        (opening_x + opening_width, divider_y, z),
                        (x + width, divider_y, z + height),
                        material_name,
                        f"divider_y_{position_ratio}_upper"
                    )
                    barriers.append(upper)
            else:
                # Create full divider
                full = PartitionedRoom.add_partition(
                    grid, barrier_handler,
                    (x, divider_y, z),
                    (x + width, divider_y, z + height),
                    material_name,
                    f"divider_y_{position_ratio}"
                )
                barriers.append(full)
        
        return barriers
