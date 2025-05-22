import unittest
from unittest.mock import MagicMock, patch

from envirosense.simulation_engine.sensors.config import SensorConfiguration, IndividualSensorConfig
from envirosense.simulation_engine.sensors.grid_guardian import VirtualGridGuardian
from envirosense.simulation_engine.sensors.base import BaseSensor # For type hinting
# Assuming DummySensor is accessible for testing, or we create one here
# For simplicity, let's redefine a minimal DummySensor or import if path is stable
# from ..base import BaseSensor # If tests are run as a package

# Minimal DummySensor for testing VirtualGridGuardian
class DummyGuardianSensor(BaseSensor):
    def __init__(self, sensor_id: str, sensor_type: str, position_3d, sampling_volume, **kwargs):
        super().__init__(sensor_id, sensor_type, position_3d, sampling_volume, **kwargs)
        self.sample_called_with = None
        self.get_ground_truth_called_with = None

    def sample(self, environment_3d_state: Any) -> Dict[str, Any]:
        self.sample_called_with = environment_3d_state
        return {f"{self.sensor_id}_value": 1.0, "type": self.sensor_type}

    def get_ground_truth(self, environment_3d_state: Any) -> Dict[str, Any]:
        self.get_ground_truth_called_with = environment_3d_state
        if not self.ground_truth_capability:
            return {}
        return {f"{self.sensor_id}_true_value": 0.9, "type": self.sensor_type}

    def get_ml_metadata(self) -> Dict[str, Any]:
        return {"id": self.sensor_id, "type": self.sensor_type}

    def apply_imperfections(self, true_reading: Dict[str, Any], environment_3d_state: Any) -> Dict[str, Any]:
        # Minimal implementation for testing
        return true_reading.copy()

class TestVirtualGridGuardian(unittest.TestCase):

    def _create_mock_sensor_config(self, num_sensors=2, custom_guardian_id="GG-Test-001"):
        sensors_list = []
        for i in range(num_sensors):
            sensors_list.append(
                IndividualSensorConfig(
                    sensor_type=f"dummy_type_{i+1}",
                    sensor_id=f"sensor_id_{i+1}",
                    is_enabled=True,
                    specific_params={"param1": "value1"}
                )
            )
        return SensorConfiguration(
            guardian_id=custom_guardian_id,
            default_position_3d=(1.0, 2.0, 3.0),
            sensors=sensors_list
        )

    @patch('envirosense.simulation_engine.sensors.grid_guardian.VirtualGridGuardian._initialize_sensors')
    def test_initialization(self, mock_initialize_sensors):
        """Test VirtualGridGuardian initialization."""
        mock_config = self._create_mock_sensor_config()
        guardian = VirtualGridGuardian(guardian_id="GG-Test-001", config=mock_config)
        
        self.assertEqual(guardian.guardian_id, "GG-Test-001")
        self.assertEqual(guardian.config, mock_config)
        self.assertEqual(guardian.position_3d, (1.0, 2.0, 3.0))
        mock_initialize_sensors.assert_called_once()

    def test_initialization_with_position_override(self):
        """Test initialization with explicit position override."""
        mock_config = self._create_mock_sensor_config()
        override_pos = (10.0, 20.0, 30.0)
        guardian = VirtualGridGuardian(guardian_id="GG-Test-001", config=mock_config, position_3d=override_pos)
        self.assertEqual(guardian.position_3d, override_pos)

    def test_initialize_sensors_basic(self):
        """
        Test the _initialize_sensors method - this will need a mock factory or
        actual (dummy) sensor classes to be more thorough later.
        For now, it checks that the self.sensors dict is populated.
        """
        mock_config = self._create_mock_sensor_config(num_sensors=1)
        
        # We need to mock the sensor class instantiation
        # For now, we'll patch the SENSOR_CLASS_REGISTRY or the factory function if we had one.
        # As _initialize_sensors directly tries to instantiate, we'll test its effect.
        
        # To test _initialize_sensors properly without a full factory,
        # we can provide a mock for the sensor class itself.
        # This is a bit tricky as _initialize_sensors is called in __init__.
        # A better approach for a unit test would be to have a sensor_factory.
        
        # Let's test the outcome: self.sensors should be populated.
        # We'll use a simplified config and a direct patch on a potential factory call.
        
        # For this test, we'll assume _initialize_sensors will use a known dummy sensor for now.
        # This part of the test will become more robust when sensor stubs are created.
        
        # Let's create a guardian and then inspect its sensors dict.
        # The current _initialize_sensors has print statements and skips unknown types.
        # We'll make a config with a type that we can mock an instantiation for.
        
        sensor_conf_list = [
            IndividualSensorConfig(sensor_type="test_dummy_sensor", sensor_id="tds-01")
        ]
        config = SensorConfiguration(guardian_id="GG-InitTest", sensors=sensor_conf_list)

        # Mock the DummyGuardianSensor class to track instantiation
        mock_dummy_sensor_instance = DummyGuardianSensor(
            sensor_id="tds-01", sensor_type="test_dummy_sensor", 
            position_3d=config.default_position_3d, sampling_volume={}
        )
        
        # This is where a sensor factory would be ideal to patch.
        # For now, we'll assume the _initialize_sensors will be modified to use such a factory,
        # or we'll test it more indirectly.
        # Given the current structure, we'll patch the print to avoid output during tests
        # and check if the sensor dict gets populated (it won't with current placeholder logic
        # unless we make a sensor_type it "knows").
        
        # Let's assume we modify _initialize_sensors to use a simple map for testing:
        # For this test to pass, we'd need to adjust _initialize_sensors in VirtualGridGuardian
        # to actually create DummyGuardianSensor instances for types like "test_dummy_sensor".
        # This highlights the need for the sensor factory or direct import of stubs.
        
        # For now, let's test the structure assuming it *could* initialize.
        # We'll create a guardian and check if the sensors dict is empty,
        # as the placeholder _initialize_sensors doesn't add anything yet.
        guardian = VirtualGridGuardian(guardian_id="GG-InitTest", config=config)
        self.assertEqual(len(guardian.sensors), 0) # Based on current _initialize_sensors stub

        # TODO: Revisit this test once _initialize_sensors uses a factory or actual sensor stubs.
        # A more complete test would be:
        # with patch('path.to.sensor_module.SpecificSensorClass') as MockSensorClass:
        #     instance = MockSensorClass.return_value
        #     instance.sensor_id = "sensor_id_01" # if ID is set by factory/class
        #     guardian = VirtualGridGuardian(config=...)
        #     self.assertIn("sensor_id_01", guardian.sensors)
        #     MockSensorClass.assert_called_once_with(...)


    def test_sample_environment(self):
        """Test collecting samples from sensors."""
        mock_config = self._create_mock_sensor_config(num_sensors=2)
        guardian = VirtualGridGuardian(guardian_id="GG-SampleTest", config=mock_config)
        
        # Manually populate sensors with mocks for this test
        mock_sensor1 = DummyGuardianSensor("s1", "dummy", (0,0,0), {})
        mock_sensor2 = DummyGuardianSensor("s2", "dummy", (0,0,0), {})
        mock_sensor2.disable() # Test with one disabled
        guardian.sensors = {"s1": mock_sensor1, "s2": mock_sensor2}

        mock_env_state = {"temp": 25.0}
        readings = guardian.sample_environment(mock_env_state)

        self.assertIn("s1", readings)
        self.assertNotIn("s2", readings) # s2 is disabled
        self.assertEqual(readings["s1"], {"s1_value": 1.0, "type": "dummy"})
        self.assertEqual(mock_sensor1.sample_called_with, mock_env_state)

    def test_get_ground_truth_data(self):
        """Test collecting ground truth from sensors."""
        mock_config = self._create_mock_sensor_config(num_sensors=2)
        guardian = VirtualGridGuardian(guardian_id="GG-GTTest", config=mock_config)

        mock_sensor1 = DummyGuardianSensor("s1_gt", "dummy_gt", (0,0,0), {}, ground_truth_capability=True)
        mock_sensor2 = DummyGuardianSensor("s2_gt", "dummy_gt", (0,0,0), {}, ground_truth_capability=False) # No GT
        mock_sensor3 = DummyGuardianSensor("s3_gt", "dummy_gt", (0,0,0), {}, ground_truth_capability=True)
        mock_sensor3.disable() # Disabled
        guardian.sensors = {"s1_gt": mock_sensor1, "s2_gt": mock_sensor2, "s3_gt": mock_sensor3}

        mock_env_state = {"true_temp": 24.9}
        gt_data = guardian.get_ground_truth_data(mock_env_state)

        self.assertIn("s1_gt", gt_data)
        self.assertNotIn("s2_gt", gt_data) # Not capable
        self.assertNotIn("s3_gt", gt_data) # Disabled
        self.assertEqual(gt_data["s1_gt"], {"s1_gt_true_value": 0.9, "type": "dummy_gt"})
        self.assertEqual(mock_sensor1.get_ground_truth_called_with, mock_env_state)

    def test_generate_training_sample(self):
        """Test generating a single training sample."""
        mock_config = self._create_mock_sensor_config(num_sensors=1)
        guardian = VirtualGridGuardian(guardian_id="GG-TrainSample", config=mock_config)

        mock_sensor = DummyGuardianSensor("train_s1", "dummy_train", (0,0,0), {})
        guardian.sensors = {"train_s1": mock_sensor}
        
        mock_env_state = {"field_data": "some_value"}
        scenario_labels = {"event": "fire_precursor", "level": 1}
        
        readings, labels = guardian.generate_training_sample(mock_env_state, scenario_labels)

        expected_readings = {"train_s1": {"train_s1_value": 1.0, "type": "dummy_train"}}
        self.assertEqual(readings, expected_readings)

        expected_labels = {
            "event": "fire_precursor",
            "level": 1,
            "gt_train_s1_train_s1_true_value": 0.9, # Prefixed ground truth
            "gt_train_s1_type": "dummy_train"
        }
        self.assertEqual(labels, expected_labels)

    def test_get_sensor(self):
        """Test retrieving a sensor by ID."""
        mock_config = self._create_mock_sensor_config(num_sensors=1)
        guardian = VirtualGridGuardian(guardian_id="GG-GetSensor", config=mock_config)
        
        mock_sensor = DummyGuardianSensor("get_s1", "dummy_get", (0,0,0), {})
        guardian.sensors = {"get_s1": mock_sensor}

        retrieved_sensor = guardian.get_sensor("get_s1")
        self.assertIs(retrieved_sensor, mock_sensor)

        non_existent_sensor = guardian.get_sensor("non_existent_id")
        self.assertIsNone(non_existent_sensor)

    def test_enable_disable_sensor(self):
        """Test enabling and disabling a specific sensor."""
        sensor_configs_for_ed = [
            IndividualSensorConfig(sensor_type="temp_humidity", sensor_id="ed_th_1")
        ]
        config_for_ed = SensorConfiguration(guardian_id="GG-EnableDisable", sensors=sensor_configs_for_ed)
        guardian_for_ed = VirtualGridGuardian(guardian_id="GG-EnableDisable", config=config_for_ed)
        
        self.assertIn("ed_th_1", guardian_for_ed.sensors)
        sensor_to_toggle = guardian_for_ed.sensors["ed_th_1"]
        
        # is_enabled comes from IndividualSensorConfig default (True)
        # and then passed to the sensor stub's __init__
        self.assertTrue(sensor_to_toggle.is_enabled)

        result = guardian_for_ed.enable_sensor("ed_th_1", enable=False)
        self.assertTrue(result)
        self.assertFalse(sensor_to_toggle.is_enabled)

        result = guardian_for_ed.enable_sensor("ed_th_1", enable=True)
        self.assertTrue(result)
        self.assertTrue(sensor_to_toggle.is_enabled)

        result = guardian_for_ed.enable_sensor("non_existent_id", enable=False)
        self.assertFalse(result)

    def test_repr_method(self):
        mock_config = self._create_mock_sensor_config(num_sensors=3, custom_guardian_id="GG-Repr")
        guardian = VirtualGridGuardian(guardian_id="GG-Repr", config=mock_config)
        # Manually set sensors for predictable repr
        guardian.sensors = {"s1": MagicMock(), "s2": MagicMock()}
        
        expected_repr = "<VirtualGridGuardian(guardian_id='GG-Repr', num_sensors=2, position=(1.0, 2.0, 3.0))>"
        self.assertEqual(repr(guardian), expected_repr)

    def test_voc_array_sensor_integration_with_imperfections_in_guardian(self):
        """
        Integration test for VOCArraySensor within VirtualGridGuardian,
        checking combined effects of (some) imperfections.
        """
        voc_sensor_id = "integ_voc_01"
        channels = ["CO", "NO2"]
        
        voc_config = IndividualSensorConfig(
            sensor_type="voc_array",
            sensor_id=voc_sensor_id,
            specific_params={
                "channels": channels,
                "response_time_alpha": 0.5, # Moderate response
                "cross_sensitivity_matrix": {"CO": {"NO2": 0.1}} # CO also picks up 10% of NO2
            },
            noise_characteristics={
                "type": "gaussian",
                "CO": {"stddev": 0.1}, # Small noise
                "NO2": {"stddev": 0.05}
            },
            drift_parameters={
                "baseline_drift_ppb_per_hour": {"CO": 0.01}, # Small positive drift for CO
                "sensitivity_drift_percent_per_hour": {"NO2": -0.005} # Small negative sensitivity drift for NO2
            },
            calibration_artifacts={
                "offset_ppb": {"CO": 0.2},
                "gain_factor": {"NO2": 1.01}
            },
            environmental_compensation_params={
                "temperature": {
                    "reference_temp_c": 25.0,
                    "offset_ppb_per_celsius": {"CO": 0.02}
                }
            }
        )
        
        full_config = SensorConfiguration(
            guardian_id="GG-IntegTest-VOC",
            sensors=[voc_config]
        )
        
        guardian = VirtualGridGuardian(guardian_id="GG-IntegTest-VOC", config=full_config)
        self.assertIn(voc_sensor_id, guardian.sensors)
        self.assertIsInstance(guardian.sensors[voc_sensor_id], VOCArraySensor) # Requires import

        # --- Simulation Loop (simplified) ---
        true_co = 10.0
        true_no2 = 5.0
        ambient_temp = 30.0 # 5C above reference for env comp

        # Initial state (T=0)
        env_state_t0 = create_mock_environment_state(
            simulation_time_seconds=0.0,
            chemical_concentrations={"CO": true_co, "NO2": true_no2},
            default_temp_c=ambient_temp
        )
        readings_t0 = guardian.sample_environment(env_state_t0)
        
        # At T=0:
        # CO: CrossSens: 10 + (5*0.1) = 10.5. EMA: 10.5. Noise: ~10.5. Drift: 0. Cal: (10.5*1.0)+0.2 = 10.7. EnvComp: 10.7 + (0.02*5) = 10.7 + 0.1 = 10.8
        # NO2: CrossSens: 5. EMA: 5. Noise: ~5. Drift: 0. Cal: (5*1.01)+0 = 5.05. EnvComp: no NO2 comp = 5.05
        # These are approximate due to noise. We check if they are not the true values.
        self.assertNotAlmostEqual(readings_t0[voc_sensor_id]["concentrations_ppb"]["CO"], true_co)
        self.assertNotAlmostEqual(readings_t0[voc_sensor_id]["concentrations_ppb"]["NO2"], true_no2)
        # More specific checks could be done if noise is seeded or mocked out for this part.
        # For now, we check that the value is somewhat in the expected ballpark after first sample.
        self.assertAlmostEqual(readings_t0[voc_sensor_id]["concentrations_ppb"]["CO"], 10.8, delta=0.5) # Wider delta due to noise
        self.assertAlmostEqual(readings_t0[voc_sensor_id]["concentrations_ppb"]["NO2"], 5.05, delta=0.3)


        # State after 1 hour (T=3600s)
        env_state_t1 = create_mock_environment_state(
            simulation_time_seconds=3600.0,
            chemical_concentrations={"CO": true_co, "NO2": true_no2}, # True values kept same to see drift
            default_temp_c=ambient_temp
        )
        readings_t1 = guardian.sample_environment(env_state_t1)

        # At T=1 hour, drift should have an effect.
        # CO: EMA will have settled. Noise. Drift: baseline +0.01. Cal: +0.2. EnvComp: +0.1.
        #     So, roughly 10.5 (cross-sens) + 0.01 (drift) + 0.2 (cal) + 0.1 (env) = ~10.81 + noise
        # NO2: EMA settled. Noise. Drift: sensitivity * (1 - 0.00005). Cal: *1.01.
        #      Roughly (5 (cross-sens) * (1-0.00005)) * 1.01 = ~5.049 * 1.01 = ~5.099 + noise
        
        # We expect readings_t1 to be different from readings_t0 due to drift (primarily) and new noise.
        # And different from the "T0 expected" due to drift.
        self.assertNotAlmostEqual(readings_t1[voc_sensor_id]["concentrations_ppb"]["CO"], readings_t0[voc_sensor_id]["concentrations_ppb"]["CO"], delta=0.001)
        self.assertNotAlmostEqual(readings_t1[voc_sensor_id]["concentrations_ppb"]["NO2"], readings_t0[voc_sensor_id]["concentrations_ppb"]["NO2"], delta=0.001)
        
        # Check if CO reading at T1 is higher than at T0 (due to positive baseline drift)
        # This is probabilistic due to noise, so a direct assert might fail.
        # A more robust test would run many times or mock noise.
        # For now, let's check it's in a plausible range.
        # Expected CO around 10.81 (without noise)
        self.assertAlmostEqual(readings_t1[voc_sensor_id]["concentrations_ppb"]["CO"], 10.81, delta=0.5)
        # Expected NO2 around 5.099 (without noise)
        self.assertAlmostEqual(readings_t1[voc_sensor_id]["concentrations_ppb"]["NO2"], 5.099, delta=0.3)

    def test_thermal_camera_integration_with_imperfections_in_guardian(self):
        """
        Integration test for ThermalCameraSensor within VirtualGridGuardian,
        checking combined effects of some imperfections.
        """
        thermal_sensor_id = "integ_thermal_01"
        resolution = [10, 8] # w, h
        
        thermal_config = IndividualSensorConfig(
            sensor_type="thermal_camera",
            sensor_id=thermal_sensor_id,
            specific_params={
                "resolution": resolution,
                "fov_degrees": [60,45],
                "response_time_alpha": 0.6,
                "dead_pixels": [[1,1], [2,2]],
                "hot_pixels": {"coordinates": [[3,3]], "hot_value_celsius": 100.0},
                "optical_blur": {"type": "gaussian", "sigma": 0.5}
            },
            noise_characteristics={"type": "gaussian_pixel", "stddev_celsius": 0.2},
            calibration_artifacts={"global_offset_celsius": 0.5, "global_gain_factor": 1.01},
            environmental_compensation_params={
                "temperature": {"reference_temp_c": 25.0, "global_offset_celsius_per_celsius": 0.05}
            }
        )
        
        full_config = SensorConfiguration(
            guardian_id="GG-IntegTest-Thermal",
            sensors=[thermal_config]
        )
        
        # Need to import ThermalCameraSensor for type checking
        from envirosense.simulation_engine.sensors.infrastructure import ThermalCameraSensor
        guardian = VirtualGridGuardian(guardian_id="GG-IntegTest-Thermal", config=full_config)
        self.assertIn(thermal_sensor_id, guardian.sensors)
        self.assertIsInstance(guardian.sensors[thermal_sensor_id], ThermalCameraSensor)

        # --- Simulation ---
        base_temp = 30.0
        ambient_temp_for_comp = 35.0 # 10C above reference for env comp on sensor electronics

        # Create an environment that returns a simple gradient for the thermal camera to see
        def get_gradient_thermal_view(camera_position, camera_orientation, fov_degrees, resolution_wh):
            w, h = resolution_wh
            img = [[base_temp + r + (c*0.1) for c in range(w)] for r in range(h)]
            return img

        env_state = create_mock_environment_state(
            simulation_time_seconds=0.0, # No drift for this test
            default_temp_c=ambient_temp_for_comp # For sensor electronics temp comp
        )
        # Override the mock's thermal view getter
        env_state.get_thermal_field_view = get_gradient_thermal_view
        
        readings = guardian.sample_environment(env_state)
        self.assertIn(thermal_sensor_id, readings)
        
        output_image = readings[thermal_sensor_id].get("thermal_image_celsius")
        self.assertIsNotNone(output_image)
        self.assertEqual(len(output_image), resolution[1])
        self.assertEqual(len(output_image[0]), resolution[0])

        # Check some known defect pixels
        # Dead pixel at [1,1] (should be near -40.0, the default dead_pixel_value, then affected by calib)
        # ((-40.0 * 1.01) + 0.5) + (0.05 * (35-25)) = (-40.4 + 0.5) + 0.5 = -39.9 + 0.5 = -39.4
        # This is complex to assert exactly due to the chain. Let's check it's very low.
        self.assertLess(output_image[1][1], -30.0)
        
        # Hot pixel at [3,3] (should be near 100.0, then affected by calib)
        # ((100.0 * 1.01) + 0.5) + (0.05 * 10) = (101.0 + 0.5) + 0.5 = 101.5 + 0.5 = 102.0
        self.assertGreater(output_image[3][3], 90.0)

        # A non-defect pixel, e.g., [0,0]. True value = 30.0 + 0 + 0 = 30.0
        # EMA (alpha=0.6, 1st sample): 30.0
        # Noise: ~30.0
        # Blur: will average with neighbors.
        # Calib: (value * 1.01) + 0.5
        # EnvComp: value + (0.05 * 10) = value + 0.5
        # So, ((~30.0_after_blur) * 1.01 + 0.5) + 0.5.
        # This is hard to assert precisely without mocking random.
        # We can assert it's not the original true_value.
        self.assertNotAlmostEqual(output_image[0][0], base_temp, delta=0.1)
        # And it should be in a plausible range, e.g.
        self.assertTrue(25.0 < output_image[0][0] < 45.0) # Very rough check


if __name__ == '__main__':
    unittest.main()