"""
EnviroSense Physics Engine - Core Tests

This module provides simple tests for the core physical space modeling components.
"""

import unittest
import numpy as np
from envirosense.core.physics.space import SpatialGrid, GridCell
from envirosense.core.physics.geometry import Room, Material, Wall, GeometryLoader
from envirosense.core.physics.coordinates import Vector3D, CoordinateSystem, Transform
from envirosense.core.physics.airflow import VentilationSource, AirflowModel


class TestSpatialGrid(unittest.TestCase):
    """Tests for the SpatialGrid and GridCell classes."""
    
    def test_grid_creation(self):
        """Test creating a spatial grid."""
        grid = SpatialGrid((10, 10, 5), 0.1)
        self.assertEqual(grid.dimensions, (10, 10, 5))
        self.assertEqual(grid.cell_size, 0.1)
        self.assertEqual(len(grid.grid), 10 * 10 * 5)
    
    def test_cell_parameters(self):
        """Test setting and getting parameters in grid cells."""
        grid = SpatialGrid((5, 5, 5), 0.1)
        
        # Set a parameter
        position = (2, 2, 2)
        grid.set_parameter_at(position, "temperature", 25.0)
        
        # Get the parameter
        value = grid.get_parameter_at(position, "temperature")
        self.assertEqual(value, 25.0)
        
        # Get a non-existent parameter
        value = grid.get_parameter_at(position, "humidity", 50.0)
        self.assertEqual(value, 50.0)
    
    def test_cell_neighbors(self):
        """Test neighbor connections between cells."""
        grid = SpatialGrid((3, 3, 3), 0.1)
        
        # Get a cell and its neighbor
        cell = grid.get_cell((1, 1, 1))
        neighbor = cell.get_neighbor("east")
        
        # Check that the neighbor is correct
        self.assertIsNotNone(neighbor)
        self.assertEqual(neighbor.position, (2, 1, 1))
    
    def test_diffusion(self):
        """Test parameter diffusion across the grid."""
        grid = SpatialGrid((3, 3, 3), 0.1)
        
        # Set a high value at one point
        grid.set_parameter_at((0, 0, 0), "concentration", 100.0)
        
        # Diffuse the parameter
        grid.diffuse_parameter("concentration", 0.1)
        
        # Check that the parameter diffused to neighbors
        value_origin = grid.get_parameter_at((0, 0, 0), "concentration")
        value_neighbor = grid.get_parameter_at((1, 0, 0), "concentration")
        
        self.assertLess(value_origin, 100.0)  # Value decreased
        self.assertGreater(value_neighbor, 0.0)  # Neighbor received some value


class TestGeometry(unittest.TestCase):
    """Tests for the geometry classes."""
    
    def test_material_creation(self):
        """Test creating materials."""
        material = Material.from_library("concrete")
        self.assertEqual(material.name, "concrete")
        self.assertGreater(material.density, 0)
    
    def test_room_creation(self):
        """Test creating a room."""
        room = Room("test_room", (5.0, 4.0, 3.0))
        self.assertEqual(room.name, "test_room")
        self.assertEqual(room.dimensions, (5.0, 4.0, 3.0))
    
    def test_wall_creation(self):
        """Test creating walls."""
        material = Material.from_library("drywall")
        wall = Wall(
            name="north_wall",
            material=material,
            start_point=(0, 4, 0),
            end_point=(5, 4, 3),
            thickness=0.1
        )
        self.assertEqual(wall.name, "north_wall")
        self.assertTrue(wall.contains_point((2.5, 4, 1.5)))
        self.assertFalse(wall.contains_point((2.5, 2, 1.5)))
    
    def test_room_template(self):
        """Test loading a room template."""
        room = GeometryLoader.load_room_template("office")
        self.assertEqual(room.name, "office_room")
        self.assertEqual(len(room.get_all_objects()), 7)  # 6 standard walls + window


class TestCoordinates(unittest.TestCase):
    """Tests for the coordinate transformation utilities."""
    
    def test_vector_operations(self):
        """Test vector operations."""
        v1 = Vector3D(1, 2, 3)
        v2 = Vector3D(4, 5, 6)
        
        # Test vector addition
        v3 = v1 + v2
        self.assertEqual(v3.to_tuple(), (5, 7, 9))
        
        # Test vector subtraction
        v4 = v2 - v1
        self.assertEqual(v4.to_tuple(), (3, 3, 3))
        
        # Test scalar multiplication
        v5 = v1 * 2
        self.assertEqual(v5.to_tuple(), (2, 4, 6))
        
        # Test dot product
        dot = v1.dot(v2)
        self.assertEqual(dot, 1*4 + 2*5 + 3*6)
        
        # Test cross product
        cross = v1.cross(v2)
        self.assertEqual(cross.to_tuple(), (2*6-3*5, 3*4-1*6, 1*5-2*4))
        
        # Test magnitude
        mag = v1.magnitude()
        self.assertAlmostEqual(mag, np.sqrt(1*1 + 2*2 + 3*3))
    
    def test_coordinate_system(self):
        """Test coordinate system transformations."""
        origin = Vector3D(1, 2, 3)
        cs = CoordinateSystem(
            system_type=CoordinateSystem.CARTESIAN,
            origin=origin,
            rotation=(0, 0, 0)
        )
        
        # Test local to global
        local_point = (2, 3, 4)
        global_point = cs.local_to_global(local_point)
        expected_global = (3, 5, 7)  # local + origin
        
        self.assertAlmostEqual(global_point[0], expected_global[0])
        self.assertAlmostEqual(global_point[1], expected_global[1])
        self.assertAlmostEqual(global_point[2], expected_global[2])
        
        # Test global to local
        local_point_2 = cs.global_to_local(global_point)
        self.assertAlmostEqual(local_point_2[0], local_point[0])
        self.assertAlmostEqual(local_point_2[1], local_point[1])
        self.assertAlmostEqual(local_point_2[2], local_point[2])


class TestAirflow(unittest.TestCase):
    """Tests for the airflow modeling components."""
    
    def test_ventilation_source(self):
        """Test creating a ventilation source."""
        source = VentilationSource(
            name="vent",
            position=(1, 2, 3),
            direction=(0, 0, 1),
            flow_rate=0.05,
            source_type=VentilationSource.TYPE_INLET,
            radius=0.15
        )
        
        self.assertEqual(source.name, "vent")
        self.assertEqual(source.position.to_tuple(), (1, 2, 3))
        self.assertEqual(source.direction.to_tuple(), (0, 0, 1))
        
        # Test velocity at source position
        velocity = source.get_velocity_at((1, 2, 3))
        self.assertGreater(velocity.magnitude(), 0)
        
        # Test velocity far from source
        velocity = source.get_velocity_at((10, 10, 10))
        self.assertAlmostEqual(velocity.magnitude(), 0)
    
    def test_airflow_model(self):
        """Test creating an airflow model."""
        grid = SpatialGrid((10, 10, 5), 0.1)
        room = Room("test_room", (1.0, 1.0, 0.5))
        
        airflow = AirflowModel(grid, room)
        
        # Add a source
        source = VentilationSource(
            name="vent",
            position=(0.5, 0.5, 0.4),
            direction=(0, 0, -1),
            flow_rate=0.01,
            source_type=VentilationSource.TYPE_INLET,
            radius=0.1
        )
        airflow.add_source(source)
        
        # Calculate velocity field
        velocity_field = airflow.calculate_velocity_field()
        self.assertEqual(len(velocity_field), 10 * 10 * 5)
        
        # Test velocity at a point
        velocity = airflow.get_velocity_at((5, 5, 2))
        self.assertIsNotNone(velocity)
        
        # Add a contaminant
        grid.set_parameter_at((5, 5, 2), "voc", 10.0)
        
        # Run a single airflow step
        airflow.apply_airflow_step(["voc"])
        
        # Contaminant should have diffused somewhat
        voc_original = grid.get_parameter_at((5, 5, 2), "voc")
        voc_nearby = grid.get_parameter_at((5, 5, 3), "voc")
        
        # Original value should have decreased
        self.assertLess(voc_original, 10.0)
        
        # Some contaminant should have reached nearby cells
        self.assertGreater(voc_nearby, 0.0)


if __name__ == "__main__":
    unittest.main()
