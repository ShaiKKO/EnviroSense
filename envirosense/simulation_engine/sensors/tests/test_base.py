import unittest
from typing import Dict, Any, Tuple

from envirosense.simulation_engine.sensors.base import BaseSensor

# A minimal concrete implementation for testing BaseSensor
class DummySensor(BaseSensor):
    def sample(self, environment_3d_state: Any) -> Dict[str, Any]:
        return {"dummy_value": 1.0, "raw_env_state": environment_3d_state}

    def get_ground_truth(self, environment_3d_state: Any) -> Dict[str, Any]:
        if not self.ground_truth_capability:
            return {}
        return {"true_dummy_value": 0.9, "raw_env_state": environment_3d_state}

    def get_ml_metadata(self) -> Dict[str, Any]:
        return {"model": "DummySensor_v1", "status": "testing"}

    def apply_imperfections(self, true_reading: Dict[str, Any], environment_3d_state: Any) -> Dict[str, Any]:
        # Minimal implementation for testing base class
        return true_reading.copy()

class TestBaseSensor(unittest.TestCase):

    def test_initialization_valid(self):
        """Test valid BaseSensor initialization via DummySensor."""
        sensor = DummySensor(
            sensor_id="dummy-001",
            sensor_type="dummy",
            position_3d=(1.0, 2.0, 3.0),
            sampling_volume={"shape": "point"},
            is_enabled=True,
            ground_truth_capability=True,
            noise_characteristics={"type": "gaussian", "stddev": 0.05},
            drift_parameters={"rate": 0.01, "unit": "per_hour"}
        )
        self.assertEqual(sensor.sensor_id, "dummy-001")
        self.assertEqual(sensor.sensor_type, "dummy")
        self.assertTrue(sensor.is_enabled)
        self.assertEqual(sensor.position_3d, (1.0, 2.0, 3.0))
        self.assertEqual(sensor.sampling_volume, {"shape": "point"})
        self.assertTrue(sensor.ground_truth_capability)
        self.assertEqual(sensor.noise_characteristics, {"type": "gaussian", "stddev": 0.05})
        self.assertEqual(sensor.drift_parameters, {"rate": 0.01, "unit": "per_hour"})

    def test_initialization_default_values(self):
        """Test BaseSensor initialization with default optional values."""
        sensor = DummySensor(
            sensor_id="dummy-002",
            sensor_type="dummy_basic",
            position_3d=(0,0,0),
            sampling_volume={}
        )
        self.assertTrue(sensor.is_enabled) # Default
        self.assertTrue(sensor.ground_truth_capability) # Default in BaseSensor __init__
        self.assertEqual(sensor.noise_characteristics, {}) # Default
        self.assertEqual(sensor.drift_parameters, {}) # Default

    def test_initialization_invalid_sensor_id(self):
        """Test BaseSensor initialization with invalid sensor_id."""
        with self.assertRaises(ValueError):
            DummySensor(sensor_id="", sensor_type="dummy", position_3d=(0,0,0), sampling_volume={})
        with self.assertRaises(ValueError):
            DummySensor(sensor_id=None, sensor_type="dummy", position_3d=(0,0,0), sampling_volume={})

    def test_initialization_invalid_sensor_type(self):
        """Test BaseSensor initialization with invalid sensor_type."""
        with self.assertRaises(ValueError):
            DummySensor(sensor_id="test", sensor_type="", position_3d=(0,0,0), sampling_volume={})
        with self.assertRaises(ValueError):
            DummySensor(sensor_id="test", sensor_type=None, position_3d=(0,0,0), sampling_volume={})

    def test_enable_disable(self):
        """Test the enable and disable methods."""
        sensor = DummySensor("dummy-003", "dummy", (0,0,0), {})
        self.assertTrue(sensor.is_enabled) # Default

        sensor.disable()
        self.assertFalse(sensor.is_enabled)

        sensor.enable()
        self.assertTrue(sensor.is_enabled)

    def test_update_position(self):
        """Test the update_position method."""
        initial_pos: Tuple[float, float, float] = (1.1, 2.2, 3.3)
        sensor = DummySensor("dummy-004", "dummy", initial_pos, {})
        self.assertEqual(sensor.position_3d, initial_pos)

        new_pos: Tuple[float, float, float] = (4.4, 5.5, 6.6)
        sensor.update_position(new_pos)
        self.assertEqual(sensor.position_3d, new_pos)

    def test_repr_method(self):
        """Test the __repr__ method for a basic representation."""
        sensor = DummySensor(
            sensor_id="repr-test-001",
            sensor_type="dummy_repr",
            position_3d=(10, 20, 30),
            sampling_volume={"shape": "sphere", "radius": 0.5}
        )
        expected_repr = (
            "DummySensor(sensor_id='repr-test-001', sensor_type='dummy_repr', "
            "is_enabled=True, position_3d=(10, 20, 30))"
        )
        self.assertEqual(repr(sensor), expected_repr)

    def test_apply_imperfections_base(self):
        """Test the base apply_imperfections method (should just return copy)."""
        sensor = DummySensor("dummy-005", "dummy", (0,0,0), {})
        true_reading = {"value": 10.0, "unit": "C"}
        imperfect_reading = sensor.apply_imperfections(true_reading)
        self.assertEqual(imperfect_reading, true_reading)
        self.assertNotEqual(id(imperfect_reading), id(true_reading)) # Should be a copy

if __name__ == '__main__':
    unittest.main()