self.assertAlmostEqual(sum_blurred_image, sum_true_image, delta=0.1 * num_pixels) # Allow some tolerance

    def test_thermal_camera_no_blur_applied(self):
        """Test no blur if config is missing, sigma is zero, or scipy unavailable (mocked)."""
        resolution = [3,3]
        true_temp_val = 25.0
        mock_true_image = [[true_temp_val for _ in range(resolution[0])] for _ in range(resolution[1])]
        def mock_gt(env_state): return {"thermal_image_celsius": mock_true_image, "resolution": resolution}
        configs_for_no_blur = [{"optical_blur": None}, {"optical_blur": {}}, {"optical_blur": {"type": "gaussian", "sigma": 0.0}}, {"optical_blur": {"type": "other_blur_type_not_implemented"}}]
        for i, blur_config in enumerate(configs_for_no_blur):
            sensor = ThermalCameraSensor(f"thermal_no_blur_{i}", (0,0,0), {}, specific_params={"resolution": resolution, "response_time_alpha": 1.0, **blur_config}, noise_characteristics={})
            sensor.get_ground_truth = mock_gt
            sensor._first_sample_taken = False
            sample_data = sensor.sample(None)
            output_image = sample_data["thermal_image_celsius"]
            for r_idx in range(resolution[1]):
                for c_idx in range(resolution[0]):
                    self.assertAlmostEqual(output_image[r_idx][c_idx], true_temp_val, msg=f"Failed for blur_config: {blur_config}")
        with patch('envirosense.simulation_engine.sensors.infrastructure.SCIPY_AVAILABLE', False):
            with patch('builtins.print') as mock_print:
                sensor_no_scipy = ThermalCameraSensor("thermal_no_scipy", (0,0,0), {}, specific_params={"resolution": resolution, "response_time_alpha": 1.0, "optical_blur": {"type": "gaussian", "sigma": 1.0}}, noise_characteristics={})
                sensor_no_scipy.get_ground_truth = mock_gt
                sensor_no_scipy._first_sample_taken = False
                sample_data_no_scipy = sensor_no_scipy.sample(None)
                output_image_no_scipy = sample_data_no_scipy["thermal_image_celsius"]
                for r_idx in range(resolution[1]):
                    for c_idx in range(resolution[0]):
                        self.assertAlmostEqual(output_image_no_scipy[r_idx][c_idx], true_temp_val)

    def test_thermal_camera_global_calibration_artifacts(self):
        """Test global offset and gain calibration artifacts for ThermalCameraSensor."""
        resolution = [2, 2]
        cal_artifacts_config = {"global_offset_celsius": -1.5, "global_gain_factor": 1.1}
        sensor_with_cal_issues = ThermalCameraSensor("thermal_cal_test", (0,0,0), {}, specific_params={"resolution": resolution, "response_time_alpha": 1.0}, noise_characteristics={}, calibration_artifacts=cal_artifacts_config, ground_truth_capability=True)
        value_before_this_cal_step = 50.0 
        mock_intermediate_image = [[value_before_this_cal_step for _ in range(resolution[0])] for _ in range(resolution[1])]
        def mock_gt_for_cal_artifact_test(environment_3d_state): return {"thermal_image_celsius": [row[:] for row in mock_intermediate_image], "resolution": resolution}
        sensor_with_cal_issues.get_ground_truth = mock_gt_for_cal_artifact_test
        sensor_with_cal_issues._first_sample_taken = False
        sample_data = sensor_with_cal_issues.sample(None)
        calibrated_image = sample_data["thermal_image_celsius"]
        expected_calibrated_value = 53.5
        for r_idx in range(resolution[1]):
            for c_idx in range(resolution[0]):
                self.assertAlmostEqual(calibrated_image[r_idx][c_idx], expected_calibrated_value, places=2)

    def test_thermal_camera_no_global_calibration_artifacts(self):
        """Test behavior with no or neutral global calibration artifacts."""
        resolution = [2,2]
        sensor_no_cal = ThermalCameraSensor("thermal_no_cal", (0,0,0), {}, specific_params={"resolution": resolution, "response_time_alpha": 1.0}, calibration_artifacts=None)
        sensor_neutral_cal = ThermalCameraSensor("thermal_neutral_cal", (0,0,0), {}, specific_params={"resolution": resolution, "response_time_alpha": 1.0}, calibration_artifacts={"global_offset_celsius": 0.0, "global_gain_factor": 1.0})
        true_temp_val = 30.0
        mock_true_image = [[true_temp_val for _ in range(resolution[0])] for _ in range(resolution[1])]
        def mock_gt(env_state): return {"thermal_image_celsius": mock_true_image, "resolution": resolution}
        for sensor_case in [sensor_no_cal, sensor_neutral_cal]:
            sensor_case.get_ground_truth = mock_gt
            sensor_case._first_sample_taken = False
            sensor_case.noise_characteristics = {}
            sensor_case.optical_blur_config = {}
            sensor_case.dead_pixels = []
            sensor_case.hot_pixels_config = {}
            sample_data = sensor_case.sample(None)
            output_image = sample_data["thermal_image_celsius"]
            for r_idx in range(resolution[1]):
                for c_idx in range(resolution[0]):
                    self.assertAlmostEqual(output_image[r_idx][c_idx], true_temp_val)

    def test_thermal_camera_env_temp_compensation(self):
        """Test environmental temperature compensation for ThermalCameraSensor."""
        resolution = [2, 2]
        env_comp_config = {"temperature": {"reference_temp_c": 20.0, "global_offset_celsius_per_celsius": 0.1}}
        sensor_with_env_comp = ThermalCameraSensor("thermal_env_comp_test", (0,0,0), {}, specific_params={"resolution": resolution, "response_time_alpha": 1.0}, environmental_compensation_params=env_comp_config, noise_characteristics={}, calibration_artifacts={}, optical_blur_config={}, dead_pixels=[], hot_pixels_config={})
        value_before_this_comp = 50.0
        mock_intermediate_image = [[value_before_this_comp for _ in range(resolution[0])] for _ in range(resolution[1])]
        def mock_gt_for_env_comp(environment_3d_state): return {"thermal_image_celsius": [row[:] for row in mock_intermediate_image], "resolution": resolution}
        sensor_with_env_comp.get_ground_truth = mock_gt_for_env_comp
        sensor_with_env_comp._first_sample_taken = False
        env_state_ref_temp = create_mock_environment_state(default_temp_c=20.0)
        sample_ref = sensor_with_env_comp.sample(env_state_ref_temp)
        for r_idx in range(resolution[1]):
            for c_idx in range(resolution[0]):
                self.assertAlmostEqual(sample_ref["thermal_image_celsius"][r_idx][c_idx], value_before_this_comp, places=2)
        env_state_hot_temp = create_mock_environment_state(default_temp_c=30.0)
        sensor_with_env_comp._first_sample_taken = False
        sample_hot = sensor_with_env_comp.sample(env_state_hot_temp)
        expected_hot_val = 51.0
        for r_idx in range(resolution[1]):
            for c_idx in range(resolution[0]):
                self.assertAlmostEqual(sample_hot["thermal_image_celsius"][r_idx][c_idx], expected_hot_val, places=2)
        env_state_cold_temp = create_mock_environment_state(default_temp_c=10.0)
        sensor_with_env_comp._first_sample_taken = False
        sample_cold = sensor_with_env_comp.sample(env_state_cold_temp)
        expected_cold_val = 49.0
        for r_idx in range(resolution[1]):
            for c_idx in range(resolution[0]):
                self.assertAlmostEqual(sample_cold["thermal_image_celsius"][r_idx][c_idx], expected_cold_val, places=2)

    def test_thermal_env_comp_no_params_or_missing_temp_method(self):
        """Test thermal env compensation when params missing or env state lacks temp method."""
        resolution = [2,2]
        sensor_no_params = ThermalCameraSensor("thermal_env_comp_no_cfg", (0,0,0), {}, specific_params={"resolution": resolution, "response_time_alpha": 1.0}, environmental_compensation_params=None)
        value_before = 30.0
        mock_img = [[value_before for _ in range(resolution[0])] for _ in range(resolution[1])]
        def mock_gt(env): return {"thermal_image_celsius": mock_img, "resolution": resolution}
        sensor_no_params.get_ground_truth = mock_gt
        sensor_no_params._first_sample_taken = False
        env_state_with_temp = create_mock_environment_state(default_temp_c=35.0)
        sample1 = sensor_no_params.sample(env_state_with_temp)
        self.assertAlmostEqual(sample1["thermal_image_celsius"][0][0], value_before)
        sensor_valid_params_bad_env = ThermalCameraSensor("thermal_env_comp_bad_env", (0,0,0), {}, specific_params={"resolution": resolution, "response_time_alpha": 1.0}, environmental_compensation_params={"temperature": {"reference_temp_c": 25.0, "global_offset_celsius_per_celsius": 0.1}})
        sensor_valid_params_bad_env.get_ground_truth = mock_gt
        sensor_valid_params_bad_env._first_sample_taken = False
        class BasicEnvStateNoTemp: pass
        with patch('builtins.print') as mock_print:
            sample3 = sensor_valid_params_bad_env.sample(BasicEnvStateNoTemp())
            self.assertAlmostEqual(sample3["thermal_image_celsius"][0][0], value_before)
            mock_print.assert_any_call(f"Warning: Thermal camera temp comp config exists for {sensor_valid_params_bad_env.sensor_id} but env_state lacks 'get_temperature_celsius'. Skipping.")

class TestEMFSensor(unittest.TestCase):

    def test_get_ground_truth_success(self):
        """Test EMFSensor.get_ground_truth with a responsive mock environment."""
        sensor = EMFSensor(sensor_id="emf_gt_test1", position_3d=(1,1,1), sampling_volume={}, specific_params={"frequency_range_hz": [50, 60]})
        mock_emf_data = {"ac_field_strength_v_per_m": 1.23, "dominant_frequency_hz": 55.0, "extra_param": "test"}
        mock_env_state = create_mock_environment_state(emf_details=mock_emf_data)
        original_get_emf = mock_env_state.get_emf_field_strength
        mock_env_state.get_emf_field_strength = MagicMock(wraps=original_get_emf)
        gt_data = sensor.get_ground_truth(mock_env_state)
        self.assertNotIn("error", gt_data, msg=gt_data.get("error"))
        self.assertEqual(gt_data, mock_emf_data) 
        mock_env_state.get_emf_field_strength.assert_called_once_with(position=(1,1,1), frequency_range_hz=(50.0, 60.0))

    def test_get_ground_truth_no_capability(self):
        sensor = EMFSensor("emf_gt_off", (0,0,0), {}, {}, ground_truth_capability=False)
        gt_data = sensor.get_ground_truth(create_mock_environment_state())
        self.assertIn("error", gt_data)
        self.assertTrue("not supported" in gt_data["error"].lower())

    def test_get_ground_truth_env_missing_method(self):
        """Test EMFSensor.get_ground_truth when environment lacks the required method."""
        sensor = EMFSensor("emf_bad_env", (0,0,0), {}, {})
        class BadEnvState: pass
        with patch('builtins.print') as mock_print:
            gt_data = sensor.get_ground_truth(BadEnvState())
            self.assertIn("error", gt_data)
            self.assertTrue("lacks 'get_emf_field_strength' method" in gt_data["error"]) 
            mock_print.assert_any_call(f"Warning: environment_3d_state for EMFSensor {sensor.sensor_id} lacks 'get_emf_field_strength' method.")

    def test_get_ground_truth_env_method_raises_exception(self):
        """Test EMFSensor.get_ground_truth when the environment method raises an exception."""
        sensor = EMFSensor("emf_env_ex", (0,0,0), {}, {})
        mock_env_state = create_mock_environment_state()
        def raiser(*args, **kwargs): raise RuntimeError("Simulated EMF query failure")
        mock_env_state.get_emf_field_strength = raiser
        with patch('builtins.print') as mock_print:
            gt_data = sensor.get_ground_truth(mock_env_state)
            self.assertIn("error", gt_data)
            self.assertTrue("Failed to get EMF field strength" in gt_data["error"])
            self.assertTrue("Simulated EMF query failure" in gt_data["error"])
            mock_print.assert_any_call(f"Error querying EMF field strength for {sensor.sensor_id}: Simulated EMF query failure")

    def test_get_ground_truth_malformed_data_response(self):
        """Test EMFSensor.get_ground_truth with malformed data from the environment."""
        sensor = EMFSensor("emf_malformed_res", (0,0,0), {}, {})
        mock_env_state = create_mock_environment_state()
        mock_env_state.get_emf_field_strength = MagicMock(return_value={"dominant_frequency_hz": 60.0})
        with patch('builtins.print') as mock_print:
            gt_data = sensor.get_ground_truth(mock_env_state)
            self.assertIn("error", gt_data)
            self.assertTrue("malformed EMF data" in gt_data["error"].lower())
            mock_print.assert_any_call(f"Error: EMF field strength data from environment has unexpected format for {sensor.sensor_id}.")
        mock_env_state.get_emf_field_strength = MagicMock(return_value="not_a_dict")
        with patch('builtins.print') as mock_print:
            gt_data = sensor.get_ground_truth(mock_env_state)
            self.assertIn("error", gt_data)
            self.assertTrue("malformed EMF data" in gt_data["error"].lower())
            mock_print.assert_any_call(f"Error: EMF field strength data from environment has unexpected format for {sensor.sensor_id}.")

    def test_sample_calls_get_ground_truth_and_apply_imperfections(self):
        sensor = EMFSensor("emf_sample_flow", (0,0,0), {}, {})
        mock_env_state = create_mock_environment_state()
        gt_return = {"ac_field_strength_v_per_m": 0.5}
        sensor.get_ground_truth = MagicMock(return_value=gt_return)
        sensor.apply_imperfections = MagicMock(side_effect=lambda x, env_state: x)
        result = sensor.sample(mock_env_state)
        sensor.get_ground_truth.assert_called_once_with(mock_env_state)
        sensor.apply_imperfections.assert_called_once_with(gt_return, mock_env_state)
        self.assertEqual(result, gt_return)

    def test_sample_propagates_error_from_get_ground_truth(self):
        sensor = EMFSensor("emf_sample_gt_error", (0,0,0), {}, {})
        mock_env_state = create_mock_environment_state()
        error_response = {"error": "GT acquisition failed for EMF"}
        sensor.get_ground_truth = MagicMock(return_value=error_response)
        sensor.apply_imperfections = MagicMock()
        result = sensor.sample(mock_env_state)
        self.assertEqual(result, error_response)
        sensor.apply_imperfections.assert_not_called()

    def test_emf_sensor_init_validation(self):
        """Test initialization validation for EMFSensor specific_params."""
        base_args = {"sensor_id": "emf_init_valid_test", "position_3d": (0,0,0), "sampling_volume": {}}
        
        with self.assertRaisesRegex(ValueError, "frequency_tolerance_hz .* must be a non-negative number"):
            EMFSensor(**base_args, specific_params={"frequency_tolerance_hz": -0.1})
        with self.assertRaisesRegex(ValueError, "frequency_tolerance_hz .* must be a non-negative number"):
            EMFSensor(**base_args, specific_params={"frequency_tolerance_hz": "invalid"})
        try:
            EMFSensor(**base_args, specific_params={"frequency_tolerance_hz": 0.0})
            EMFSensor(**base_args, specific_params={"frequency_tolerance_hz": 2.0})
        except ValueError:
            self.fail("Valid frequency_tolerance_hz raised ValueError during EMFSensor init.")

        with self.assertRaisesRegex(ValueError, "default_frequency_gain .* must be a number"):
            EMFSensor(**base_args, specific_params={"default_frequency_gain": "invalid"})
        try:
            EMFSensor(**base_args, specific_params={"default_frequency_gain": 0.9})
            EMFSensor(**base_args, specific_params={"default_frequency_gain": 1.0})
        except ValueError:
            self.fail("Valid default_frequency_gain raised ValueError during EMFSensor init.")

    def test_emf_time_based_drift(self):
        """Test time-based baseline drift for EMFSensor."""
        drift_config = {"baseline_drift_v_per_m_per_hour": {"ac_field_strength_v_per_m": 0.01}}
        sensor = EMFSensor("emf_drift_test", (0,0,0), {}, {}, drift_parameters=drift_config)
        sensor.noise_characteristics = {}
        sensor.calibration_artifacts = {}
        sensor.environmental_compensation_params = {}
        true_field_strength = 0.5 
        def mock_gt_emf_drift(environment_3d_state): return {"ac_field_strength_v_per_m": true_field_strength, "dominant_frequency_hz": 60.0}
        sensor.get_ground_truth = mock_gt_emf_drift
        env_state_t0 = create_mock_environment_state(simulation_time_seconds=0.0)
        sample_t0 = sensor.sample(env_state_t0)
        self.assertAlmostEqual(sample_t0["ac_field_strength_v_per_m"], true_field_strength, places=4)
        env_state_t1 = create_mock_environment_state(simulation_time_seconds=3600.0)
        sample_t1 = sensor.sample(env_state_t1)
        self.assertAlmostEqual(sample_t1["ac_field_strength_v_per_m"], 0.51, places=4)
        env_state_t10 = create_mock_environment_state(simulation_time_seconds=36000.0)
        sample_t10 = sensor.sample(env_state_t10)
        self.assertAlmostEqual(sample_t10["ac_field_strength_v_per_m"], 0.6, places=4)

    def test_emf_drift_no_time_in_env(self):
        """Test EMFSensor drift behavior if environment_3d_state lacks simulation_time_seconds."""
        drift_config = {"baseline_drift_v_per_m_per_hour": {"ac_field_strength_v_per_m": 0.01}}
        sensor = EMFSensor("emf_drift_no_time", (0,0,0), {}, {}, drift_parameters=drift_config)
        sensor.noise_characteristics = {}
        true_val = 0.5
        def mock_gt(env): return {"ac_field_strength_v_per_m": true_val, "dominant_frequency_hz": 60.0}
        sensor.get_ground_truth = mock_gt
        class BasicEnvStateNoTime: 
             def get_emf_field_strength(self, position, frequency_range_hz): return {"ac_field_strength_v_per_m": true_val, "dominant_frequency_hz": 60.0}
        with patch('builtins.print') as mock_print:
            sample = sensor.sample(BasicEnvStateNoTime())
            self.assertAlmostEqual(sample["ac_field_strength_v_per_m"], true_val)
            mock_print.assert_any_call(f"Warning: Drift params exist for EMFSensor {sensor.sensor_id} but env_state lacks 'simulation_time_seconds'. Skipping drift.")

    def test_emf_gaussian_noise(self):
        """Test Gaussian noise application for EMFSensor."""
        noise_config = {"type": "gaussian", "mean": 0.0, "stddev_v_per_m": 0.02}
        sensor = EMFSensor("emf_noise_test", (0,0,0), {}, {}, noise_characteristics=noise_config)
        sensor.drift_parameters = {}
        true_field_strength = 0.75 
        def mock_gt_emf_noise(env_state): return {"ac_field_strength_v_per_m": true_field_strength, "dominant_frequency_hz": 60.0}
        sensor.get_ground_truth = mock_gt_emf_noise
        env_state = create_mock_environment_state() 
        num_samples = 500
        readings = []
        for _ in range(num_samples):
            sample_data = sensor.sample(env_state)
            readings.append(sample_data["ac_field_strength_v_per_m"])
            self.assertGreaterEqual(sample_data["ac_field_strength_v_per_m"], 0.0) 
        avg_reading = sum(readings) / num_samples
        self.assertAlmostEqual(avg_reading, true_field_strength, delta=0.01) 
        stddev_reading = (sum([(x - avg_reading) ** 2 for x in readings]) / num_samples) ** 0.5
        self.assertAlmostEqual(stddev_reading, noise_config["stddev_v_per_m"], delta=0.01)

    def test_emf_no_noise_applied(self):
        """Test EMFSensor no noise if config missing or stddev is zero."""
        sensor_no_cfg = EMFSensor("emf_no_noise1", (0,0,0), {}, {}, noise_characteristics=None)
        sensor_zero_std = EMFSensor("emf_no_noise2", (0,0,0), {}, {}, noise_characteristics={"type": "gaussian", "mean": 0.0, "stddev_v_per_m": 0.0})
        true_val = 0.6
        def mock_gt(env): return {"ac_field_strength_v_per_m": true_val}
        for sensor_case in [sensor_no_cfg, sensor_zero_std]:
            sensor_case.get_ground_truth = mock_gt
            sensor_case.drift_parameters = {} 
            sample_data = sensor_case.sample(create_mock_environment_state())
            self.assertAlmostEqual(sample_data["ac_field_strength_v_per_m"], true_val)

if __name__ == '__main__':
    unittest.main()