"""
EnviroSense Physics Engine - Coordinate Transformation Utilities

This module provides classes and functions for coordinate system transformations
in 3D space, essential for spatial modeling and environmental simulations.
"""

import numpy as np
from typing import Tuple, List, Optional, Dict, Any, Union
import math


class Vector3D:
    """
    Represents a 3D vector with common vector operations.
    
    This class provides a utility for working with 3D vectors in our spatial
    modeling system, with methods for common vector operations.
    """
    
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        """
        Initialize a 3D vector.
        
        Args:
            x: X component
            y: Y component
            z: Z component
        """
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
    
    @classmethod
    def from_tuple(cls, coords: Tuple[float, float, float]) -> 'Vector3D':
        """
        Create a Vector3D from a tuple of coordinates.
        
        Args:
            coords: Tuple of (x, y, z) coordinates
            
        Returns:
            A new Vector3D instance
        """
        return cls(coords[0], coords[1], coords[2])
    
    def to_tuple(self) -> Tuple[float, float, float]:
        """
        Convert the vector to a tuple.
        
        Returns:
            Tuple of (x, y, z) coordinates
        """
        return (self.x, self.y, self.z)
    
    def __add__(self, other: 'Vector3D') -> 'Vector3D':
        """
        Add two vectors.
        
        Args:
            other: The vector to add
            
        Returns:
            A new Vector3D representing the sum
        """
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Vector3D') -> 'Vector3D':
        """
        Subtract a vector from this one.
        
        Args:
            other: The vector to subtract
            
        Returns:
            A new Vector3D representing the difference
        """
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float) -> 'Vector3D':
        """
        Multiply the vector by a scalar.
        
        Args:
            scalar: The scalar value to multiply by
            
        Returns:
            A new Vector3D representing the scaled vector
        """
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def __truediv__(self, scalar: float) -> 'Vector3D':
        """
        Divide the vector by a scalar.
        
        Args:
            scalar: The scalar value to divide by
            
        Returns:
            A new Vector3D representing the scaled vector
        """
        if scalar == 0:
            raise ValueError("Cannot divide vector by zero")
        return Vector3D(self.x / scalar, self.y / scalar, self.z / scalar)
    
    def dot(self, other: 'Vector3D') -> float:
        """
        Calculate the dot product with another vector.
        
        Args:
            other: The vector to calculate dot product with
            
        Returns:
            The dot product (scalar)
        """
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def cross(self, other: 'Vector3D') -> 'Vector3D':
        """
        Calculate the cross product with another vector.
        
        Args:
            other: The vector to calculate cross product with
            
        Returns:
            A new Vector3D representing the cross product
        """
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )
    
    def magnitude(self) -> float:
        """
        Calculate the magnitude (length) of the vector.
        
        Returns:
            The magnitude as a scalar value
        """
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)
    
    def normalize(self) -> 'Vector3D':
        """
        Return a normalized (unit) vector in the same direction.
        
        Returns:
            A new Vector3D of unit length
        """
        mag = self.magnitude()
        if mag == 0:
            return Vector3D(0, 0, 0)
        return self / mag
    
    def distance_to(self, other: 'Vector3D') -> float:
        """
        Calculate the distance to another vector.
        
        Args:
            other: The vector to calculate distance to
            
        Returns:
            The distance as a scalar value
        """
        return (self - other).magnitude()
    
    def angle_to(self, other: 'Vector3D') -> float:
        """
        Calculate the angle to another vector in radians.
        
        Args:
            other: The vector to calculate angle to
            
        Returns:
            The angle in radians
        """
        if self.magnitude() == 0 or other.magnitude() == 0:
            return 0.0
            
        dot_product = self.dot(other)
        cos_angle = dot_product / (self.magnitude() * other.magnitude())
        # Handle floating point errors that could result in cos_angle outside [-1, 1]
        cos_angle = max(-1.0, min(1.0, cos_angle))
        return math.acos(cos_angle)
    
    def __str__(self) -> str:
        """String representation of the vector."""
        return f"Vector3D({self.x}, {self.y}, {self.z})"
    
    def __repr__(self) -> str:
        """Formal string representation of the vector."""
        return f"Vector3D(x={self.x}, y={self.y}, z={self.z})"


class CoordinateSystem:
    """
    Defines a coordinate system with transformations between different systems.
    
    This class handles conversions between Cartesian, cylindrical, and spherical
    coordinate systems, as well as transformations between local and global coordinates.
    """
    
    # Coordinate system types
    CARTESIAN = "cartesian"
    CYLINDRICAL = "cylindrical"
    SPHERICAL = "spherical"
    
    def __init__(self, system_type: str = CARTESIAN, 
                origin: Optional[Vector3D] = None,
                rotation: Optional[Tuple[float, float, float]] = None):
        """
        Initialize a coordinate system.
        
        Args:
            system_type: Type of coordinate system (cartesian, cylindrical, spherical)
            origin: Origin of the coordinate system in global coordinates
            rotation: Rotation angles in radians around x, y, and z axes
        """
        valid_types = [self.CARTESIAN, self.CYLINDRICAL, self.SPHERICAL]
        if system_type not in valid_types:
            raise ValueError(f"Invalid coordinate system type: {system_type}. "
                            f"Must be one of {valid_types}")
        
        self.system_type = system_type
        self.origin = origin or Vector3D(0, 0, 0)
        self.rotation = rotation or (0, 0, 0)
        
        # Precompute rotation matrices for efficiency
        self._update_rotation_matrix()
    
    def _update_rotation_matrix(self) -> None:
        """
        Update the rotation matrix based on current rotation angles.
        """
        rx, ry, rz = self.rotation
        
        # Rotation matrix around X axis
        Rx = np.array([
            [1, 0, 0],
            [0, math.cos(rx), -math.sin(rx)],
            [0, math.sin(rx), math.cos(rx)]
        ])
        
        # Rotation matrix around Y axis
        Ry = np.array([
            [math.cos(ry), 0, math.sin(ry)],
            [0, 1, 0],
            [-math.sin(ry), 0, math.cos(ry)]
        ])
        
        # Rotation matrix around Z axis
        Rz = np.array([
            [math.cos(rz), -math.sin(rz), 0],
            [math.sin(rz), math.cos(rz), 0],
            [0, 0, 1]
        ])
        
        # Combined rotation matrix: R = Rz * Ry * Rx
        self.rotation_matrix = Rz @ Ry @ Rx
        self.inverse_rotation_matrix = np.linalg.inv(self.rotation_matrix)
    
    def set_rotation(self, rotation: Tuple[float, float, float]) -> None:
        """
        Set the rotation of the coordinate system.
        
        Args:
            rotation: Rotation angles in radians around x, y, and z axes
        """
        self.rotation = rotation
        self._update_rotation_matrix()
    
    def set_origin(self, origin: Vector3D) -> None:
        """
        Set the origin of the coordinate system.
        
        Args:
            origin: New origin point in global coordinates
        """
        self.origin = origin
    
    def local_to_global(self, local_coords: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """
        Convert local coordinates to global coordinates.
        
        Args:
            local_coords: Coordinates in the local system
            
        Returns:
            Coordinates in the global Cartesian system
        """
        # First convert to local Cartesian if needed
        local_cartesian = self._to_cartesian(local_coords)
        
        # Apply rotation
        x, y, z = local_cartesian
        local_vec = np.array([x, y, z])
        rotated_vec = self.rotation_matrix @ local_vec
        
        # Apply translation
        global_vec = Vector3D(
            rotated_vec[0] + self.origin.x,
            rotated_vec[1] + self.origin.y,
            rotated_vec[2] + self.origin.z
        )
        
        return global_vec.to_tuple()
    
    def global_to_local(self, global_coords: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """
        Convert global coordinates to local coordinates.
        
        Args:
            global_coords: Coordinates in the global Cartesian system
            
        Returns:
            Coordinates in the local system
        """
        # Translate from global origin to local origin
        x, y, z = global_coords
        translated_vec = Vector3D(
            x - self.origin.x,
            y - self.origin.y,
            z - self.origin.z
        )
        
        # Apply inverse rotation to get to local Cartesian
        local_vec = self.inverse_rotation_matrix @ np.array([translated_vec.x, translated_vec.y, translated_vec.z])
        local_cartesian = (local_vec[0], local_vec[1], local_vec[2])
        
        # Convert from local Cartesian to the desired local system
        return self._from_cartesian(local_cartesian)
    
    def _to_cartesian(self, coords: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """
        Convert coordinates from current system to Cartesian.
        
        Args:
            coords: Coordinates in the current system
            
        Returns:
            Cartesian coordinates
        """
        if self.system_type == self.CARTESIAN:
            return coords
            
        elif self.system_type == self.CYLINDRICAL:
            # Cylindrical (r, θ, z) -> Cartesian (x, y, z)
            r, theta, z = coords
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            return (x, y, z)
            
        elif self.system_type == self.SPHERICAL:
            # Spherical (r, θ, φ) -> Cartesian (x, y, z)
            r, theta, phi = coords
            x = r * math.sin(phi) * math.cos(theta)
            y = r * math.sin(phi) * math.sin(theta)
            z = r * math.cos(phi)
            return (x, y, z)
    
    def _from_cartesian(self, coords: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """
        Convert Cartesian coordinates to current system.
        
        Args:
            coords: Cartesian coordinates
            
        Returns:
            Coordinates in the current system
        """
        if self.system_type == self.CARTESIAN:
            return coords
            
        elif self.system_type == self.CYLINDRICAL:
            # Cartesian (x, y, z) -> Cylindrical (r, θ, z)
            x, y, z = coords
            r = math.sqrt(x**2 + y**2)
            theta = math.atan2(y, x)
            return (r, theta, z)
            
        elif self.system_type == self.SPHERICAL:
            # Cartesian (x, y, z) -> Spherical (r, θ, φ)
            x, y, z = coords
            r = math.sqrt(x**2 + y**2 + z**2)
            theta = math.atan2(y, x)
            phi = math.acos(z / r) if r > 0 else 0
            return (r, theta, phi)
            
    @staticmethod
    def cartesian_to_cylindrical(x: float, y: float, z: float) -> Tuple[float, float, float]:
        """
        Convert Cartesian coordinates to cylindrical coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            z: Z coordinate
            
        Returns:
            Tuple of (r, theta, z) in cylindrical coordinates
        """
        r = math.sqrt(x**2 + y**2)
        theta = math.atan2(y, x)
        return (r, theta, z)
    
    @staticmethod
    def cylindrical_to_cartesian(r: float, theta: float, z: float) -> Tuple[float, float, float]:
        """
        Convert cylindrical coordinates to Cartesian coordinates.
        
        Args:
            r: Radial distance
            theta: Azimuthal angle (in radians)
            z: Height
            
        Returns:
            Tuple of (x, y, z) in Cartesian coordinates
        """
        x = r * math.cos(theta)
        y = r * math.sin(theta)
        return (x, y, z)
    
    @staticmethod
    def cartesian_to_spherical(x: float, y: float, z: float) -> Tuple[float, float, float]:
        """
        Convert Cartesian coordinates to spherical coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            z: Z coordinate
            
        Returns:
            Tuple of (r, theta, phi) in spherical coordinates
        """
        r = math.sqrt(x**2 + y**2 + z**2)
        theta = math.atan2(y, x)
        phi = math.acos(z / r) if r > 0 else 0
        return (r, theta, phi)
    
    @staticmethod
    def spherical_to_cartesian(r: float, theta: float, phi: float) -> Tuple[float, float, float]:
        """
        Convert spherical coordinates to Cartesian coordinates.
        
        Args:
            r: Radial distance
            theta: Azimuthal angle (in radians)
            phi: Polar angle (in radians)
            
        Returns:
            Tuple of (x, y, z) in Cartesian coordinates
        """
        x = r * math.sin(phi) * math.cos(theta)
        y = r * math.sin(phi) * math.sin(theta)
        z = r * math.cos(phi)
        return (x, y, z)


class Transform:
    """
    Represents a transformation in 3D space.
    
    This class handles translations, rotations, and scaling in 3D space,
    and supports hierarchical transformations through a parent-child relationship.
    """
    
    def __init__(self, 
                position: Optional[Vector3D] = None,
                rotation: Optional[Tuple[float, float, float]] = None,
                scale: Optional[Vector3D] = None,
                parent: Optional['Transform'] = None):
        """
        Initialize a transform.
        
        Args:
            position: Position vector
            rotation: Rotation angles in radians around x, y, and z axes
            scale: Scale vector
            parent: Parent transform
        """
        self.position = position or Vector3D(0, 0, 0)
        self.rotation = rotation or (0, 0, 0)
        self.scale = scale or Vector3D(1, 1, 1)
        self.parent = parent
        
        # Precompute matrices for efficiency
        self._update_matrices()
    
    def _update_matrices(self) -> None:
        """
        Update transformation matrices based on current position, rotation, and scale.
        """
        # Translation matrix
        self.translation_matrix = np.array([
            [1, 0, 0, self.position.x],
            [0, 1, 0, self.position.y],
            [0, 0, 1, self.position.z],
            [0, 0, 0, 1]
        ])
        
        # Rotation matrices
        rx, ry, rz = self.rotation
        
        # Rotation around X axis
        Rx = np.array([
            [1, 0, 0, 0],
            [0, math.cos(rx), -math.sin(rx), 0],
            [0, math.sin(rx), math.cos(rx), 0],
            [0, 0, 0, 1]
        ])
        
        # Rotation around Y axis
        Ry = np.array([
            [math.cos(ry), 0, math.sin(ry), 0],
            [0, 1, 0, 0],
            [-math.sin(ry), 0, math.cos(ry), 0],
            [0, 0, 0, 1]
        ])
        
        # Rotation around Z axis
        Rz = np.array([
            [math.cos(rz), -math.sin(rz), 0, 0],
            [math.sin(rz), math.cos(rz), 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        
        # Combined rotation matrix: R = Rz * Ry * Rx
        self.rotation_matrix = Rz @ Ry @ Rx
        
        # Scale matrix
        self.scale_matrix = np.array([
            [self.scale.x, 0, 0, 0],
            [0, self.scale.y, 0, 0],
            [0, 0, self.scale.z, 0],
            [0, 0, 0, 1]
        ])
        
        # Combined transformation matrix: M = T * R * S
        self.matrix = self.translation_matrix @ self.rotation_matrix @ self.scale_matrix
        
        # Calculate inverse for reverse transformations
        try:
            self.inverse_matrix = np.linalg.inv(self.matrix)
        except np.linalg.LinAlgError:
            # Handle potential singular matrix (e.g. if scale is zero)
            self.inverse_matrix = np.eye(4)
    
    def set_position(self, position: Vector3D) -> None:
        """
        Set the position of the transform.
        
        Args:
            position: New position vector
        """
        self.position = position
        self._update_matrices()
    
    def set_rotation(self, rotation: Tuple[float, float, float]) -> None:
        """
        Set the rotation of the transform.
        
        Args:
            rotation: New rotation angles in radians (x, y, z)
        """
        self.rotation = rotation
        self._update_matrices()
    
    def set_scale(self, scale: Vector3D) -> None:
        """
        Set the scale of the transform.
        
        Args:
            scale: New scale vector
        """
        self.scale = scale
        self._update_matrices()
    
    def set_parent(self, parent: Optional['Transform']) -> None:
        """
        Set the parent of the transform.
        
        Args:
            parent: Parent transform or None to clear parent
        """
        self.parent = parent
    
    def transform_point(self, point: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """
        Transform a point from local space to world space.
        
        Args:
            point: Point in local space
            
        Returns:
            Transformed point in world space
        """
        # Convert to homogeneous coordinates
        x, y, z = point
        point_h = np.array([x, y, z, 1.0])
        
        # Apply local transformation
        transformed = self.matrix @ point_h
        
        # Apply parent transformations if any
        if self.parent:
            parent_point = (transformed[0], transformed[1], transformed[2])
            transformed_point = self.parent.transform_point(parent_point)
            return transformed_point
        
        # Convert back to Cartesian coordinates
        return (transformed[0], transformed[1], transformed[2])
    
    def inverse_transform_point(self, point: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """
        Transform a point from world space to local space.
        
        Args:
            point: Point in world space
            
        Returns:
            Transformed point in local space
        """
        # If there's a parent, apply its inverse transformation first
        current_point = point
        if self.parent:
            current_point = self.parent.inverse_transform_point(point)
        
        # Convert to homogeneous coordinates
        x, y, z = current_point
        point_h = np.array([x, y, z, 1.0])
        
        # Apply inverse transformation
        transformed = self.inverse_matrix @ point_h
        
        # Convert back to Cartesian coordinates
        return (transformed[0], transformed[1], transformed[2])
    
    def transform_vector(self, vector: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """
        Transform a vector from local space to world space.
        
        This method applies rotation but not translation to the vector.
        
        Args:
            vector: Vector in local space
            
        Returns:
            Transformed vector in world space
        """
        # Create rotation-only matrix (3x3)
        rot_matrix = self.rotation_matrix[:3, :3]
        
        # Apply local rotation
        x, y, z = vector
        vector_np = np.array([x, y, z])
        transformed = rot_matrix @ vector_np
        
        # Apply parent transformations for rotation only
        if self.parent:
            parent_vector = (transformed[0], transformed[1], transformed[2])
            transformed_vector = self.parent.transform_vector(parent_vector)
            return transformed_vector
        
        return (transformed[0], transformed[1], transformed[2])
