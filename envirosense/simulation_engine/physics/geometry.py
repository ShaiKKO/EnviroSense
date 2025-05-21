"""
EnviroSense Physics Engine - Room Geometry Framework

This module provides classes for defining and managing room geometries
and other physical structures in environmental simulations.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class Material:
    """
    Represents physical and chemical properties of materials.
    
    Materials define how environmental parameters interact with geometry objects,
    affecting processes like absorption, reflection, and transmission.
    """
    name: str
    density: float  # kg/m³
    thermal_conductivity: float  # W/(m·K)
    specific_heat: float  # J/(kg·K)
    vapor_permeability: float  # permeability to water vapor
    voc_absorption_rates: Dict[str, float]  # absorption rates for various VOCs
    
    @classmethod
    def from_library(cls, material_name: str) -> 'Material':
        """
        Create a material instance from a predefined library.
        
        Args:
            material_name: Name of the material in the library
            
        Returns:
            Material instance with standard properties
        """
        # Standard material properties for common building materials
        # These values would ideally be loaded from a database
        library = {
            "concrete": {
                "density": 2300.0,
                "thermal_conductivity": 1.7,
                "specific_heat": 880.0,
                "vapor_permeability": 0.03,
                "voc_absorption_rates": {"formaldehyde": 0.05, "benzene": 0.02}
            },
            "drywall": {
                "density": 700.0,
                "thermal_conductivity": 0.17,
                "specific_heat": 840.0,
                "vapor_permeability": 0.06,
                "voc_absorption_rates": {"formaldehyde": 0.12, "benzene": 0.07}
            },
            "wood": {
                "density": 700.0,
                "thermal_conductivity": 0.12,
                "specific_heat": 1700.0,
                "vapor_permeability": 0.5,
                "voc_absorption_rates": {"formaldehyde": 0.18, "benzene": 0.09}
            },
            "glass": {
                "density": 2500.0,
                "thermal_conductivity": 1.0,
                "specific_heat": 840.0,
                "vapor_permeability": 0.0,
                "voc_absorption_rates": {"formaldehyde": 0.0, "benzene": 0.0}
            },
            "carpet": {
                "density": 200.0,
                "thermal_conductivity": 0.06,
                "specific_heat": 1500.0,
                "vapor_permeability": 0.8,
                "voc_absorption_rates": {"formaldehyde": 0.25, "benzene": 0.2}
            },
            "air": {
                "density": 1.225,
                "thermal_conductivity": 0.024,
                "specific_heat": 1005.0,
                "vapor_permeability": 1.0,
                "voc_absorption_rates": {"formaldehyde": 0.0, "benzene": 0.0}
            }
        }
        
        if material_name not in library:
            logger.warning(f"Material '{material_name}' not found in library. Using 'air' as default.")
            material_name = "air"
            
        props = library[material_name]
        return cls(
            name=material_name,
            density=props["density"],
            thermal_conductivity=props["thermal_conductivity"],
            specific_heat=props["specific_heat"],
            vapor_permeability=props["vapor_permeability"],
            voc_absorption_rates=props["voc_absorption_rates"]
        )


class GeometryObject:
    """
    Base class for all geometric objects in the environment.
    
    This abstract class defines the interface for all physical objects
    that can be placed in the spatial grid.
    """
    
    def __init__(self, name: str, material: Material):
        """
        Initialize a geometry object.
        
        Args:
            name: Object identifier
            material: Material properties of the object
        """
        self.name = name
        self.material = material
        
    def contains_point(self, point: Tuple[float, float, float]) -> bool:
        """
        Check if a point in physical space is contained within this object.
        
        Args:
            point: Physical coordinates (x, y, z) in meters
            
        Returns:
            True if the point is inside the object, False otherwise
        """
        # Abstract method, should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement contains_point")
    
    def surface_normal_at(self, point: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """
        Get the surface normal vector at a given point on the object.
        
        Args:
            point: Physical coordinates (x, y, z) in meters
            
        Returns:
            Normalized direction vector (nx, ny, nz) perpendicular to the surface
        """
        # Abstract method, should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement surface_normal_at")
    
    def get_bounding_box(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """
        Get the axis-aligned bounding box containing this object.
        
        Returns:
            Tuple of (min_point, max_point) where each point is (x, y, z)
        """
        # Abstract method, should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement get_bounding_box")
    
    def affects_parameter(self, parameter: str, point: Tuple[float, float, float], 
                         value: float) -> float:
        """
        Calculate how this object affects a parameter value at a point.
        
        Args:
            parameter: Parameter name
            point: Physical coordinates (x, y, z) in meters
            value: Current parameter value
            
        Returns:
            Modified parameter value based on object's properties
        """
        # Default implementation - subclasses can override for specific behaviors
        if parameter in self.material.voc_absorption_rates:
            absorption_rate = self.material.voc_absorption_rates[parameter]
            # Simple absorption model - reduce by absorption rate
            return value * (1.0 - absorption_rate)
        return value


class Wall(GeometryObject):
    """
    Represents a rectangular wall in the environment.
    """
    
    def __init__(self, name: str, material: Material, 
                start_point: Tuple[float, float, float],
                end_point: Tuple[float, float, float],
                thickness: float = 0.1):
        """
        Initialize a wall object.
        
        Args:
            name: Wall identifier
            material: Wall material properties
            start_point: Starting corner (x, y, z) in meters
            end_point: Opposite corner (x, y, z) in meters
            thickness: Wall thickness in meters
        """
        super().__init__(name, material)
        self.start_point = start_point
        self.end_point = end_point
        self.thickness = thickness
        
        # Identify which dimension is the "thickness" dimension
        # by finding the dimension with the smallest difference
        x1, y1, z1 = start_point
        x2, y2, z2 = end_point
        dims = [abs(x2 - x1), abs(y2 - y1), abs(z2 - z1)]
        self.thin_dim = dims.index(min(dims))
        
    def contains_point(self, point: Tuple[float, float, float]) -> bool:
        """
        Check if a point is contained within this wall.
        
        Args:
            point: Physical coordinates (x, y, z) in meters
            
        Returns:
            True if the point is inside the wall, False otherwise
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
        Get the surface normal vector at a given point on the wall.
        
        Args:
            point: Physical coordinates (x, y, z) in meters
            
        Returns:
            Normalized direction vector (nx, ny, nz) perpendicular to the wall
        """
        # For a wall, the normal is along the thin dimension
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
        Get the axis-aligned bounding box containing this wall.
        
        Returns:
            Tuple of (min_point, max_point) where each point is (x, y, z)
        """
        x1, y1, z1 = self.start_point
        x2, y2, z2 = self.end_point
        
        min_point = (min(x1, x2), min(y1, y2), min(z1, z2))
        max_point = (max(x1, x2), max(y1, y2), max(z1, z2))
        
        return (min_point, max_point)


class Window(Wall):
    """
    Represents a window in the environment.
    Windows have special properties for light transmission and airflow.
    """
    
    def __init__(self, name: str, material: Material, 
                start_point: Tuple[float, float, float],
                end_point: Tuple[float, float, float],
                thickness: float = 0.01,
                is_open: bool = False,
                open_fraction: float = 0.0):
        """
        Initialize a window object.
        
        Args:
            name: Window identifier
            material: Window material properties (typically glass)
            start_point: Starting corner (x, y, z) in meters
            end_point: Opposite corner (x, y, z) in meters
            thickness: Window thickness in meters
            is_open: Whether the window is currently open
            open_fraction: Fraction of window that is open (0.0 to 1.0)
        """
        super().__init__(name, material, start_point, end_point, thickness)
        self.is_open = is_open
        self.open_fraction = open_fraction
        
    def affects_parameter(self, parameter: str, point: Tuple[float, float, float], 
                         value: float) -> float:
        """
        Calculate how this window affects a parameter value at a point.
        
        Windows have special behavior for airflow and light transmission.
        
        Args:
            parameter: Parameter name
            point: Physical coordinates (x, y, z) in meters
            value: Current parameter value
            
        Returns:
            Modified parameter value based on window properties
        """
        # If window is open, it affects airflow and parameter diffusion
        if self.is_open and parameter in ['airflow_x', 'airflow_y', 'airflow_z']:
            # Simplistic: just return the value (no resistance to airflow)
            return value
            
        # For closed window, use normal material behavior
        return super().affects_parameter(parameter, point, value)


class Door(GeometryObject):
    """
    Represents a door in the environment.
    Doors can be open or closed, affecting parameter propagation.
    """
    
    def __init__(self, name: str, material: Material, 
                start_point: Tuple[float, float, float],
                end_point: Tuple[float, float, float],
                thickness: float = 0.05,
                is_open: bool = False):
        """
        Initialize a door object.
        
        Args:
            name: Door identifier
            material: Door material properties
            start_point: Starting corner (x, y, z) in meters
            end_point: Opposite corner (x, y, z) in meters
            thickness: Door thickness in meters
            is_open: Whether the door is currently open
        """
        super().__init__(name, material)
        self.start_point = start_point
        self.end_point = end_point
        self.thickness = thickness
        self.is_open = is_open
        
        # Identify which dimension is the "thickness" dimension
        x1, y1, z1 = start_point
        x2, y2, z2 = end_point
        dims = [abs(x2 - x1), abs(y2 - y1), abs(z2 - z1)]
        self.thin_dim = dims.index(min(dims))
        
    def contains_point(self, point: Tuple[float, float, float]) -> bool:
        """
        Check if a point is contained within this door.
        
        If the door is open, it does not contain any points.
        
        Args:
            point: Physical coordinates (x, y, z) in meters
            
        Returns:
            True if the point is inside the door, False otherwise
        """
        if self.is_open:
            return False
            
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
        Get the surface normal vector at a given point on the door.
        
        Args:
            point: Physical coordinates (x, y, z) in meters
            
        Returns:
            Normalized direction vector (nx, ny, nz) perpendicular to the door
        """
        # For a door, the normal is along the thin dimension
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
        Get the axis-aligned bounding box containing this door.
        
        Returns:
            Tuple of (min_point, max_point) where each point is (x, y, z)
        """
        x1, y1, z1 = self.start_point
        x2, y2, z2 = self.end_point
        
        min_point = (min(x1, x2), min(y1, y2), min(z1, z2))
        max_point = (max(x1, x2), max(y1, y2), max(z1, z2))
        
        return (min_point, max_point)
    
    def affects_parameter(self, parameter: str, point: Tuple[float, float, float], 
                         value: float) -> float:
        """
        Calculate how this door affects a parameter value at a point.
        
        If the door is open, it does not affect parameter propagation.
        
        Args:
            parameter: Parameter name
            point: Physical coordinates (x, y, z) in meters
            value: Current parameter value
            
        Returns:
            Modified parameter value based on door properties
        """
        if self.is_open:
            # Open door does not affect parameters
            return value
            
        # For closed door, use normal material behavior
        return super().affects_parameter(parameter, point, value)


class Room:
    """
    Represents a room with walls, doors, windows, and other objects.
    
    The room is the primary container for geometric objects in the
    environment simulation.
    """
    
    def __init__(self, name: str, dimensions: Tuple[float, float, float], 
                position: Tuple[float, float, float] = (0, 0, 0)):
        """
        Initialize a room with the specified dimensions.
        
        Args:
            name: Room identifier
            dimensions: Room dimensions (width, length, height) in meters
            position: Position of room origin (x, y, z) in the global coordinate system
        """
        self.name = name
        self.dimensions = dimensions
        self.position = position
        self.objects = {}  # Dictionary mapping object names to GeometryObject instances
        
    def add_object(self, obj: GeometryObject) -> None:
        """
        Add a geometric object to the room.
        
        Args:
            obj: The GeometryObject to add
        """
        self.objects[obj.name] = obj
        
    def get_object(self, name: str) -> Optional[GeometryObject]:
        """
        Get a geometric object by name.
        
        Args:
            name: Object identifier
            
        Returns:
            The GeometryObject if found, None otherwise
        """
        return self.objects.get(name)
    
    def get_objects_at(self, point: Tuple[float, float, float]) -> List[GeometryObject]:
        """
        Get all objects that contain the specified point.
        
        Args:
            point: Physical coordinates (x, y, z) in meters
            
        Returns:
            List of GeometryObject instances containing the point
        """
        return [obj for obj in self.objects.values() if obj.contains_point(point)]
    
    def get_all_objects(self) -> List[GeometryObject]:
        """
        Get all objects in the room.
        
        Returns:
            List of all GeometryObject instances
        """
        return list(self.objects.values())
    
    def is_point_inside(self, point: Tuple[float, float, float]) -> bool:
        """
        Check if a point is inside the room's boundaries.
        
        Args:
            point: Physical coordinates (x, y, z) in meters
            
        Returns:
            True if the point is inside the room, False otherwise
        """
        x, y, z = point
        rx, ry, rz = self.position
        width, length, height = self.dimensions
        
        return (rx <= x <= rx + width and
                ry <= y <= ry + length and
                rz <= z <= rz + height)
    
    def get_parameter_effects(self, parameter: str, point: Tuple[float, float, float], 
                             value: float) -> float:
        """
        Calculate the combined effect of all objects on a parameter at a point.
        
        Args:
            parameter: Parameter name
            point: Physical coordinates (x, y, z) in meters
            value: Current parameter value
            
        Returns:
            Modified parameter value based on all objects' properties
        """
        modified_value = value
        
        # Find objects at this point and apply their effects
        objects_at_point = self.get_objects_at(point)
        for obj in objects_at_point:
            modified_value = obj.affects_parameter(parameter, point, modified_value)
            
        return modified_value
    
    def create_standard_walls(self, material_name: str = "drywall") -> None:
        """
        Create standard walls, floor, and ceiling for the room.
        
        Args:
            material_name: Material to use for the walls
        """
        material = Material.from_library(material_name)
        width, length, height = self.dimensions
        rx, ry, rz = self.position
        
        # Create floor
        floor = Wall(
            name=f"{self.name}_floor",
            material=Material.from_library("concrete"),
            start_point=(rx, ry, rz),
            end_point=(rx + width, ry + length, rz),
            thickness=0.2
        )
        self.add_object(floor)
        
        # Create ceiling
        ceiling = Wall(
            name=f"{self.name}_ceiling",
            material=material,
            start_point=(rx, ry, rz + height),
            end_point=(rx + width, ry + length, rz + height),
            thickness=0.1
        )
        self.add_object(ceiling)
        
        # Create walls
        # North wall
        north_wall = Wall(
            name=f"{self.name}_north_wall",
            material=material,
            start_point=(rx, ry + length, rz),
            end_point=(rx + width, ry + length, rz + height),
            thickness=0.1
        )
        self.add_object(north_wall)
        
        # South wall
        south_wall = Wall(
            name=f"{self.name}_south_wall",
            material=material,
            start_point=(rx, ry, rz),
            end_point=(rx + width, ry, rz + height),
            thickness=0.1
        )
        self.add_object(south_wall)
        
        # East wall
        east_wall = Wall(
            name=f"{self.name}_east_wall",
            material=material,
            start_point=(rx + width, ry, rz),
            end_point=(rx + width, ry + length, rz + height),
            thickness=0.1
        )
        self.add_object(east_wall)
        
        # West wall
        west_wall = Wall(
            name=f"{self.name}_west_wall",
            material=material,
            start_point=(rx, ry, rz),
            end_point=(rx, ry + length, rz + height),
            thickness=0.1
        )
        self.add_object(west_wall)
    
    def add_window(self, wall_name: str, 
                  start_offset: Tuple[float, float], 
                  dimensions: Tuple[float, float],
                  is_open: bool = False,
                  open_fraction: float = 0.0) -> Optional[Window]:
        """
        Add a window to an existing wall.
        
        Args:
            wall_name: Name of the wall to add the window to
            start_offset: Offset from wall corner (horizontal, vertical) in meters
            dimensions: Window dimensions (width, height) in meters
            is_open: Whether the window is open
            open_fraction: Fraction of window that is open (0.0 to 1.0)
            
        Returns:
            The created Window object if successful, None otherwise
        """
        wall = self.get_object(wall_name)
        if not isinstance(wall, Wall):
            logger.warning(f"Cannot add window: {wall_name} is not a wall")
            return None
            
        # Determine window position based on wall orientation
        wx1, wy1, wz1 = wall.start_point
        wx2, wy2, wz2 = wall.end_point
        
        # Determine which plane the wall is in
        if wall.thin_dim == 0:  # YZ plane (X is constant)
            x = wx1
            y_min, y_max = min(wy1, wy2), max(wy1, wy2)
            z_min, z_max = min(wz1, wz2), max(wz1, wz2)
            
            # Calculate window position
            h_offset, v_offset = start_offset
            width, height = dimensions
            
            window = Window(
                name=f"{wall_name}_window",
                material=Material.from_library("glass"),
                start_point=(x, y_min + h_offset, z_min + v_offset),
                end_point=(x, y_min + h_offset + width, z_min + v_offset + height),
                is_open=is_open,
                open_fraction=open_fraction
            )
            
        elif wall.thin_dim == 1:  # XZ plane (Y is constant)
            y = wy1
            x_min, x_max = min(wx1, wx2), max(wx1, wx2)
            z_min, z_max = min(wz1, wz2), max(wz1, wz2)
            
            # Calculate window position
            h_offset, v_offset = start_offset
            width, height = dimensions
            
            window = Window(
                name=f"{wall_name}_window",
                material=Material.from_library("glass"),
                start_point=(x_min + h_offset, y, z_min + v_offset),
                end_point=(x_min + h_offset + width, y, z_min + v_offset + height),
                is_open=is_open,
                open_fraction=open_fraction
            )
            
        else:  # XY plane (Z is constant)
            z = wz1
            x_min, x_max = min(wx1, wx2), max(wx1, wx2)
            y_min, y_max = min(wy1, wy2), max(wy1, wy2)
            
            # Calculate window position
            h_offset, v_offset = start_offset
            width, height = dimensions
            
            window = Window(
                name=f"{wall_name}_window",
                material=Material.from_library("glass"),
                start_point=(x_min + h_offset, y_min + v_offset, z),
                end_point=(x_min + h_offset + width, y_min + v_offset + height, z),
                is_open=is_open,
                open_fraction=open_fraction
            )
            
        self.add_object(window)
        return window
    
    def add_door(self, wall_name: str, 
                start_offset: float, 
                width: float,
                height: float = 2.0,
                is_open: bool = False) -> Optional[Door]:
        """
        Add a door to an existing wall.
        
        Args:
            wall_name: Name of the wall to add the door to
            start_offset: Horizontal offset from wall corner in meters
            width: Door width in meters
            height: Door height in meters (default 2.0m)
            is_open: Whether the door is open
            
        Returns:
            The created Door object if successful, None otherwise
        """
        wall = self.get_object(wall_name)
        if not isinstance(wall, Wall):
            logger.warning(f"Cannot add door: {wall_name} is not a wall")
            return None
            
        # Determine door position based on wall orientation
        wx1, wy1, wz1 = wall.start_point
        wx2, wy2, wz2 = wall.end_point
        
        # Determine which plane the wall is in
        if wall.thin_dim == 0:  # YZ plane (X is constant)
            x = wx1
            y_min, y_max = min(wy1, wy2), max(wy1, wy2)
            z_min, z_max = min(wz1, wz2), max(wz1, wz2)
            
            door = Door(
                name=f"{wall_name}_door",
                material=Material.from_library("wood"),
                start_point=(x, y_min + start_offset, z_min),
                end_point=(x, y_min + start_offset + width, z_min + height),
                is_open=is_open
            )
            
        elif wall.thin_dim == 1:  # XZ plane (Y is constant)
            y = wy1
            x_min, x_max = min(wx1, wx2), max(wx1, wx2)
            z_min, z_max = min(wz1, wz2), max(wz1, wz2)
            
            door = Door(
                name=f"{wall_name}_door",
                material=Material.from_library("wood"),
                start_point=(x_min + start_offset, y, z_min),
                end_point=(x_min + start_offset + width, y, z_min + height),
                is_open=is_open
            )
            
        else:  # XY plane (Z is constant) - horizontal surface, doors not typically added
            logger.warning(f"Cannot add door to {wall_name}: wall appears to be horizontal")
            return None
            
        self.add_object(door)
        return door
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert room to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the room
        """
        # Create a simplified representation for serialization
        return {
            "name": self.name,
            "dimensions": self.dimensions,
            "position": self.position,
            "objects": [
                {
                    "type": obj.__class__.__name__,
                    "name": obj.name,
                    "material": obj.material.name,
                    # Other properties would be added based on object type
                }
                for obj in self.objects.values()
            ]
        }
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Room':
        """
        Create a room from a JSON string.
        
        Args:
            json_str: JSON string representation of the room
            
        Returns:
            Room instance created from the JSON
        """
        # This is a simplified implementation - a full one would handle
        # all object types and their specific properties
        data = json.loads(json_str)
        room = cls(
            name=data["name"],
            dimensions=tuple(data["dimensions"]),
            position=tuple(data["position"])
        )
        
        # Add standard walls as a starting point
        room.create_standard_walls()
        
        # Additional logic would be needed to fully reconstruct all objects
        return room


class GeometryLoader:
    """
    Utility class for loading room definitions from configuration files.
    """
    
    @staticmethod
    def load_room_from_json(filepath: str) -> Room:
        """
        Load a room definition from a JSON file.
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            Room instance created from the JSON file
        """
        try:
            with open(filepath, 'r') as f:
                json_str = f.read()
            return Room.from_json(json_str)
        except Exception as e:
            logger.error(f"Failed to load room from {filepath}: {str(e)}")
            # Return a default room as fallback
            return Room("default_room", (5.0, 5.0, 2.5))
    
    @staticmethod
    def load_room_template(template_name: str) -> Room:
        """
        Load a predefined room template.
        
        Args:
            template_name: Name of the template to load
            
        Returns:
            Room instance created from the template
        """
        templates = {
            "office": {
                "dimensions": (4.0, 3.0, 2.7),
                "windows": [("east_wall", (1.0, 1.0), (1.5, 1.0))],
                "doors": [("south_wall", 1.5, 0.9)]
            },
            "bedroom": {
                "dimensions": (3.5, 4.0, 2.5),
                "windows": [("north_wall", (1.0, 1.0), (1.8, 1.2))],
                "doors": [("west_wall", 1.2, 0.8)]
            },
            "bathroom": {
                "dimensions": (2.0, 2.5, 2.5),
                "windows": [("east_wall", (0.5, 1.5), (0.8, 0.6))],
                "doors": [("south_wall", 0.7, 0.7)]
            },
            "living_room": {
                "dimensions": (6.0, 5.0, 2.8),
                "windows": [
                    ("north_wall", (1.0, 1.0), (2.0, 1.5)),
                    ("north_wall", (4.0, 1.0), (1.5, 1.5))
                ],
                "doors": [
                    ("south_wall", 2.5, 1.2),
                    ("east_wall", 2.0, 0.9)
                ]
            }
        }
        
        if template_name not in templates:
            logger.warning(f"Template '{template_name}' not found. Using 'office' as default.")
            template_name = "office"
            
        template = templates[template_name]
        room = Room(
            name=f"{template_name}_room",
            dimensions=template["dimensions"]
        )
        
        # Add standard walls
        room.create_standard_walls()
        
        # Add windows
        for wall_name, start_offset, dimensions in template["windows"]:
            room.add_window(wall_name, start_offset, dimensions)
            
        # Add doors
        for wall_name, offset, width in template["doors"]:
            room.add_door(wall_name, offset, width)
            
        return room
