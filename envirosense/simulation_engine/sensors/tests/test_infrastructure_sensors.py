import unittest
from unittest.mock import MagicMock, patch

from envirosense.simulation_engine.sensors.infrastructure import ThermalCameraSensor, EMFSensor
from envirosense.simulation_engine.environment.mock_utils import create_mock_environment_state
from envirosense.simulation_engine.environment.state import Environment3DState # For type hinting

class TestThermalCameraSensor(unittest.TestCase):

    def test_get_ground_truth_success(self):
        """Test ThermalCameraSensor.get_ground_truth with a responsive mock environment."""
        sensor_id = "thermal_test_001"
        position = (5.0, 5.0, 2.0)
        sampling_vol = {"type": "frustum", "near_clip": 0.1, "far_clip": 100.0} # Example
        resolution = [80, 60]
        fov = [90.0, 60.0]
        specific_params = {
            "resolution": resolution,
            "fov_degrees": fov
        }

        sensor = ThermalCameraSensor(
            sensor_id=sensor_id,
            position_3d=position,
            sampling_volume=sampling_vol,
            specific_params=specific_params,
            ground_truth_capability=True
        )

        base_temp = 28.0
        mock_env_state = create_mock_environment_state(
            thermal_image_pattern="uniform",
            thermal_image_base_temp_c=base_temp,
            thermal_image_resolution=resolution
        )
        
        original_get_thermal_field_view = mock_env_state.get_thermal_field_view
        mock_env_state.get_thermal_field_view = MagicMock(wraps=original_get_thermal_field_view)

        ground_truth_data = sensor.get_ground_truth(mock_env_state)

        self.assertNotIn("error", ground_truth_data, msg=ground_truth_data.get("error"))
        self.assertEqual(ground_truth_data["resolution"], resolution)
        self.assertIn("thermal_image_celsius", ground_truth_data)
        
        image_array = ground_truth_data["thermal_image_celsius"]
        self.assertEqual(len(image_array), resolution[1]) 
        if resolution[1] > 0:
            self.assertEqual(len(image_array[0]), resolution[0]) 
            for r_idx in range(resolution[1]):
                for c_idx in range(resolution[0]):
                    self.assertAlmostEqual(image_array[r_idx][c_idx], base_temp)
        
        mock_env_state.get_thermal_field_view.assert_called_once_with(
            camera_position=position,
            camera_orientation={"yaw": 0.0, "pitch": 0.0, "roll": 0.0}, 
            fov_degrees=tuple(fov),
            resolution=tuple(resolution)
        )

    def test_get_ground_truth_hotspot_pattern(self):
        """Test with a hotspot pattern from the mock environment."""
        sensor = ThermalCameraSensor(
            "thermal_hotspot", (0,0,0), {}, 
            {"resolution": [10, 8], "fov_degrees": [60,40]}
        )
        mock_env_state = create_mock_environment_state(
            thermal_image_pattern="hotspot",
            thermal_image_base_temp_c=20.0,
            thermal_image_hotspot_temp_c=75.0,
            thermal_image_resolution=[10,8]
        )
        gt_data = sensor.get_ground_truth(mock_env_state)
        self.assertNotIn("error", gt_data)
        image = gt_data["thermal_image_celsius"]
        self.assertAlmostEqual(image[8//2][10//2], 75.0) 
        self.assertAlmostEqual(image[0][0], 20.0)    

    def test_get_ground_truth_no_capability(self):
        sensor = ThermalCameraSensor("thermal_gt_off", (0,0,0), {}, {"resolution": [1,1]}, ground_truth_capability=False)
        mock_env_state = create_mock_environment_state()
        gt_data = sensor.get_ground_truth(mock_env_state)
        self.assertIn("error", gt_data)
        self.assertTrue("not supported" in gt_data["error"].lower())

    def test_get_ground_truth_env_missing_method(self):
        sensor = ThermalCameraSensor("thermal_bad_env", (0,0,0), {}, {"resolution": [1,1]})
        class BadEnvState: pass
        with patch('builtins.print') as mock_print:
            gt_data = sensor.get_ground_truth(BadEnvState())
            self.assertIn("error", gt_data)
            self.assertTrue("Environment state does not support thermal field view queries." in gt_data["error"])
            mock_print.assert_any_call(f"Warning: environment_3d_state for ThermalCameraSensor {sensor.sensor_id} lacks 'get_thermal_field_view' method.")

    def test_get_ground_truth_env_method_raises_exception(self):
        sensor = ThermalCameraSensor("thermal_env_ex", (0,0,0), {}, {"resolution": [1,1]})
        mock_env_state = create_mock_environment_state()
        def raiser(*args, **kwargs): raise RuntimeError("Simulated thermal query failure")
        mock_env_state.get_thermal_field_view = raiser
        with patch('builtins.print') as mock_print:
            gt_data = sensor.get_ground_truth(mock_env_state)
            self.assertIn("error", gt_data)
            self.assertTrue("Failed to get thermal field view" in gt_data["error"])
            self.assertTrue("Simulated thermal query failure" in gt_data["error"])
            mock_print.assert_any_call(f"Error querying thermal field view for {sensor.sensor_id}: Simulated thermal query failure")
            
    def test_get_ground_truth_malformed_image_response(self):
        sensor = ThermalCameraSensor("thermal_malformed", (0,0,0), {}, {"resolution": [2,2]})
        mock_env_state = create_mock_environment_state()
        mock_env_state.get_thermal_field_view = MagicMock(return_value=[[1.0, 2.0]]) 
        with patch('builtins.print') as mock_print:
            gt_data = sensor.get_ground_truth(mock_env_state)
            self.assertIn("error", gt_data)
            self.assertTrue("malformed thermal image data" in gt_data["error"].lower())
            mock_print.assert_any_call(f"Error: Thermal field view from environment has unexpected dimensions for {sensor.sensor_id}.")

        mock_env_state.get_thermal_field_view = MagicMock(return_value=[[1.0],[2.0]])
        with patch('builtins.print') as mock_print:
            gt_data = sensor.get_ground_truth(mock_env_state)
            self.assertIn("error", gt_data)
            self.assertTrue("malformed thermal image data" in gt_data["error"].lower())

    def test_sample_calls_get_ground_truth_and_apply_imperfections(self):
        sensor = ThermalCameraSensor("thermal_sample_flow", (0,0,0), {}, {"resolution": [2,2]})
        mock_env_state = create_mock_environment_state()
        dummy_image = [[1.0, 1.0], [1.0, 1.0]]
        gt_return = {"thermal_image_celsius": dummy_image, "resolution": [2,2]}
        sensor.get_ground_truth = MagicMock(return_value=gt_return)
        sensor.apply_imperfections = MagicMock(side_effect=lambda x, env_state: x) 
        result = sensor.sample(mock_env_state)
        sensor.get_ground_truth.assert_called_once_with(mock_env_state)
        sensor.apply_imperfections.assert_called_once_with(gt_return, mock_env_state)
        self.assertEqual(result, gt_return)

    def test_sample_propagates_error_from_get_ground_truth(self):
        sensor = ThermalCameraSensor("thermal_sample_gt_error", (0,0,0), {}, {"resolution": [1,1]})
        mock_env_state = create_mock_environment_state()
        error_response = {"error": "GT acquisition failed"}
        sensor.get_ground_truth = MagicMock(return_value=error_response)
        sensor.apply_imperfections = MagicMock()
        result = sensor.sample(mock_env_state)
        self.assertEqual(result, error_response)
        sensor.apply_imperfections.assert_not_called()

    def test_thermal_camera_response_time_ema(self):
        """Test EMA filter for response time in ThermalCameraSensor."""
        resolution = [4, 3]
        sensor_fast = ThermalCameraSensor("thermal_ema_fast", (0,0,0), {}, {"resolution": resolution, "fov_degrees": [90,60], "response_time_alpha": 0.9})
        sensor_slow = ThermalCameraSensor("thermal_ema_slow", (0,0,0), {}, {"resolution": resolution, "fov_degrees": [90,60], "response_time_alpha": 0.2})
        true_image_val = 100.0
        mock_true_image = [[true_image_val for _ in range(resolution[0])] for _ in range(resolution[1])]
        def mock_gt_thermal(environment_3d_state): return {"thermal_image_celsius": mock_true_image, "resolution": resolution}
        sensor_fast.get_ground_truth = mock_gt_thermal
        sensor_slow.get_ground_truth = mock_gt_thermal
        sample1_fast = sensor_fast.sample(None)
        sample1_slow = sensor_slow.sample(None)
        for r_idx in range(resolution[1]):
            for c_idx in range(resolution[0]):
                self.assertAlmostEqual(sample1_fast["thermal_image_celsius"][r_idx][c_idx], true_image_val)
                self.assertAlmostEqual(sample1_slow["thermal_image_celsius"][r_idx][c_idx], true_image_val)
        new_true_image_val = 200.0
        mock_new_true_image = [[new_true_image_val for _ in range(resolution[0])] for _ in range(resolution[1])]
        def mock_gt_thermal_new(environment_3d_state): return {"thermal_image_celsius": mock_new_true_image, "resolution": resolution}
        sensor_fast.get_ground_truth = mock_gt_thermal_new
        sensor_slow.get_ground_truth = mock_gt_thermal_new
        expected_fast_val_s2 = 190.0
        sample2_fast = sensor_fast.sample(None)
        for r_idx in range(resolution[1]):
            for c_idx in range(resolution[0]):
                self.assertAlmostEqual(sample2_fast["thermal_image_celsius"][r_idx][c_idx], expected_fast_val_s2)
        expected_slow_val_s2 = 120.0
        sample2_slow = sensor_slow.sample(None)
        for r_idx in range(resolution[1]):
            for c_idx in range(resolution[0]):
                self.assertAlmostEqual(sample2_slow["thermal_image_celsius"][r_idx][c_idx], expected_slow_val_s2)
        expected_slow_val_s3 = 136.0
        sample3_slow = sensor_slow.sample(None)
        for r_idx in range(resolution[1]):
            for c_idx in range(resolution[0]):
                self.assertAlmostEqual(sample3_slow["thermal_image_celsius"][r_idx][c_idx], expected_slow_val_s3)

    def test_thermal_camera_alpha_validation(self):
        """Test validation of response_time_alpha for ThermalCameraSensor."""
        with self.assertRaises(ValueError): ThermalCameraSensor("tc_alpha_zero", (0,0,0), {}, {"response_time_alpha": 0.0})
        with self.assertRaises(ValueError): ThermalCameraSensor("tc_alpha_high", (0,0,0), {}, {"response_time_alpha": 1.1})
        try:
            ThermalCameraSensor("tc_alpha_valid1", (0,0,0), {}, {"response_time_alpha": 0.001})
            ThermalCameraSensor("tc_alpha_valid2", (0,0,0), {}, {"response_time_alpha": 1.0})
        except ValueError: self.fail("Valid response_time_alpha for ThermalCameraSensor raised ValueError.")

    def test_thermal_camera_gaussian_pixel_noise(self):
        """Test Gaussian pixel noise application in ThermalCameraSensor."""
        resolution = [10, 8]
        sensor_with_noise = ThermalCameraSensor("thermal_noise_test", (0,0,0), {}, specific_params={"resolution": resolution, "fov_degrees": [90,60], "response_time_alpha": 1.0}, noise_characteristics={"type": "gaussian_pixel", "mean": 0.0, "stddev_celsius": 0.5}, ground_truth_capability=True)
        true_temp_val = 50.0
        mock_true_image = [[true_temp_val for _ in range(resolution[0])] for _ in range(resolution[1])]
        def mock_gt_thermal_noise(environment_3d_state): return {"thermal_image_celsius": mock_true_image, "resolution": resolution}
        sensor_with_noise.get_ground_truth = mock_gt_thermal_noise
        sensor_with_noise._first_sample_taken = False
        sample_data = sensor_with_noise.sample(None)
        noisy_image = sample_data["thermal_image_celsius"]
        self.assertEqual(len(noisy_image), resolution[1], "Image height mismatch.")
        self.assertEqual(len(noisy_image[0]), resolution[0], "Image width mismatch.")
        all_match_true = True
        sum_of_pixels = 0
        num_pixels = resolution[0] * resolution[1]
        for r_idx in range(resolution[1]):
            for c_idx in range(resolution[0]):
                if abs(noisy_image[r_idx][c_idx] - true_temp_val) > 1e-7: all_match_true = False
                sum_of_pixels += noisy_image[r_idx][c_idx]
        if sensor_with_noise.noise_characteristics.get("stddev_celsius", 0) > 1e-9: self.assertFalse(all_match_true, "Noise was applied, so not all pixels should match true value exactly.")
        avg_pixel_value = sum_of_pixels / num_pixels
        self.assertAlmostEqual(avg_pixel_value, true_temp_val, delta=0.5)

    def test_thermal_camera_no_noise_applied(self):
        """Test no noise if config is missing or stddev is zero for ThermalCameraSensor."""
        resolution = [2,2]
        sensor_no_noise_cfg = ThermalCameraSensor("thermal_no_noise1", (0,0,0), {}, specific_params={"resolution": resolution, "response_time_alpha": 1.0}, noise_characteristics=None)
        sensor_zero_stddev = ThermalCameraSensor("thermal_no_noise2", (0,0,0), {}, specific_params={"resolution": resolution, "response_time_alpha": 1.0}, noise_characteristics={"type": "gaussian_pixel", "mean": 0.0, "stddev_celsius": 0.0})
        true_temp_val = 30.0
        mock_true_image = [[true_temp_val for _ in range(resolution[0])] for _ in range(resolution[1])]
        def mock_gt(env_state): return {"thermal_image_celsius": mock_true_image, "resolution": resolution}
        for sensor_case in [sensor_no_noise_cfg, sensor_zero_stddev]:
            sensor_case.get_ground_truth = mock_gt
            sensor_case._first_sample_taken = False
            sensor_case.noise_characteristics = {} # Turn off other effects for clarity
            sensor_case.optical_blur_config = {}
            sensor_case.dead_pixels = []
            sensor_case.hot_pixels_config = {}
            sample_data = sensor_case.sample(None)
            output_image = sample_data["thermal_image_celsius"]
            for r in range(resolution[1]):
                for c in range(resolution[0]):
                    self.assertAlmostEqual(output_image[r][c], true_temp_val)

    def test_thermal_camera_dead_hot_pixels(self):
        """Test dead and hot pixel simulation in ThermalCameraSensor."""
        resolution = [5, 4]
        dead_pixels_config = [[1, 1], [2, 3], [5,5]]
        hot_pixels_coords_config = [[0, 0], [3, 2], [0,6]]
        hot_value = 150.0
        dead_value = -10.0
        sensor_with_defects = ThermalCameraSensor("thermal_defects_test", (0,0,0), {}, specific_params={"resolution": resolution, "fov_degrees": [90,60], "response_time_alpha": 1.0, "dead_pixels": dead_pixels_config, "hot_pixels": {"coordinates": hot_pixels_coords_config, "hot_value_celsius": hot_value, "dead_value_celsius": dead_value}}, noise_characteristics={}, ground_truth_capability=True)
        self.assertEqual(sensor_with_defects.dead_pixel_value, dead_value)
        true_temp_val = 25.0
        mock_true_image = [[true_temp_val for _ in range(resolution[0])] for _ in range(resolution[1])]
        def mock_gt_thermal_defects(environment_3d_state): return {"thermal_image_celsius": mock_true_image, "resolution": resolution}
        sensor_with_defects.get_ground_truth = mock_gt_thermal_defects
        sensor_with_defects._first_sample_taken = False
        sample_data = sensor_with_defects.sample(None)
        defective_image = sample_data["thermal_image_celsius"]
        self.assertAlmostEqual(defective_image[1][1], dead_value)
        self.assertAlmostEqual(defective_image[2][3], dead_value)
        self.assertAlmostEqual(defective_image[0][0], hot_value)
        self.assertAlmostEqual(defective_image[3][2], hot_value)
        self.assertAlmostEqual(defective_image[0][1], true_temp_val) 
        self.assertAlmostEqual(defective_image[2][2], true_temp_val)

    def test_thermal_camera_no_dead_hot_pixels_config(self):
        """Test behavior when no dead/hot pixel config is provided."""
        resolution = [2,2]
        sensor_no_defects = ThermalCameraSensor("thermal_no_defects", (0,0,0), {}, specific_params={"resolution": resolution, "response_time_alpha": 1.0}, noise_characteristics={})
        true_temp_val = 30.0
        mock_true_image = [[true_temp_val for _ in range(resolution[0])] for _ in range(resolution[1])]
        def mock_gt(env_state): return {"thermal_image_celsius": mock_true_image, "resolution": resolution}
        sensor_no_defects.get_ground_truth = mock_gt
        sensor_no_defects._first_sample_taken = False
        sample_data = sensor_no_defects.sample(None)
        output_image = sample_data["thermal_image_celsius"]
        for r_idx in range(resolution[1]):
            for c_idx in range(resolution[0]):
                self.assertAlmostEqual(output_image[r_idx][c_idx], true_temp_val)

    def test_thermal_camera_optical_blur_gaussian(self):
        """Test Gaussian optical blur in ThermalCameraSensor."""
        resolution = [10, 10]
        blur_sigma = 1.0
        num_pixels = resolution[0] * resolution[1] 
        try:
            from scipy.ndimage import gaussian_filter
            scipy_present = True
        except ImportError:
            scipy_present = False
            print("Skipping test_thermal_camera_optical_blur_gaussian as SciPy is not available.")
            self.skipTest("SciPy not available, cannot test gaussian_filter.")
            return
        sensor_with_blur = ThermalCameraSensor("thermal_blur_test", (0,0,0), {}, specific_params={"resolution": resolution, "fov_degrees": [90,60], "response_time_alpha": 1.0, "optical_blur": {"type": "gaussian", "sigma": blur_sigma}}, noise_characteristics={}, ground_truth_capability=True)
        true_image = [[20.0 for _ in range(resolution[0])] for _ in range(resolution[1])]
        hot_pixel_val = 120.0
        center_r, center_c = resolution[1]//2, resolution[0]//2
        true_image[center_r][center_c] = hot_pixel_val
        def mock_gt_thermal_blur(environment_3d_state): return {"thermal_image_celsius": [row[:] for row in true_image], "resolution": resolution}
        sensor_with_blur.get_ground_truth = mock_gt_thermal_blur
        sensor_with_blur._first_sample_taken = False
        sample_data = sensor_with_blur.sample(None)
        blurred_image = sample_data["thermal_image_celsius"]
        self.assertLess(blurred_image[center_r][center_c], hot_pixel_val)
        if center_r > 0: self.assertGreater(blurred_image[center_r - 1][center_c], 20.0)
        if center_c > 0: self.assertGreater(blurred_image[center_r][center_c - 1], 20.0)
        sum_true_image = sum(sum(row) for row in true_image)
        sum_blurred_image = sum(sum(row) for row in blurred_image)
        self.assertAlmostEqual(sum_blurred_image, sum_true_image, delta=0.1 * num_pixels)

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
        env_comp_config = {
            "temperature": {
                "reference_temp_c": 20.0,
                "global_offset_celsius_per_celsius": 0.1
            }
        }
        sensor_with_env_comp = ThermalCameraSensor(
            "thermal_env_comp_test", (0,0,0), {},
            specific_params={"resolution": resolution, "response_time_alpha": 1.0},
            environmental_compensation_params=env_comp_config,
            # Turn off other imperfections for this test
            noise_characteristics={}, calibration_artifacts={},
            optical_blur_config={}, dead_pixels=[], hot_pixels_config={}
        )

        value_before_this_comp = 50.0
        mock_intermediate_image = [[value_before_this_comp for _ in range(resolution[0])] for _ in range(resolution[1])]

        def mock_gt_for_env_comp(env_state):
            return {"thermal_image_celsius": [row[:] for row in mock_intermediate_image], "resolution": resolution}
        sensor_with_env_comp.get_ground_truth = mock_gt_for_env_comp
        sensor_with_env_comp._first_sample_taken = False # Reset EMA

        # Case 1: Ambient temp = Reference temp (20 C) -> No change
        env_state_ref_temp = create_mock_environment_state(default_temp_c=20.0)
        sample_ref = sensor_with_env_comp.sample(env_state_ref_temp)
        for r_idx in range(resolution[1]):
            for c_idx in range(resolution[0]):
                self.assertAlmostEqual(sample_ref["thermal_image_celsius"][r_idx][c_idx], value_before_this_comp, places=2)

        # Case 2: Ambient temp = 30 C (delta = +10 C)
        env_state_hot_temp = create_mock_environment_state(default_temp_c=30.0)
        sensor_with_env_comp._first_sample_taken = False # Reset EMA
        sample_hot = sensor_with_env_comp.sample(env_state_hot_temp)
        # Expected offset = 0.1 * 10 = 1.0 C. So, 50.0 + 1.0 = 51.0
        expected_hot_val = 51.0
        for r_idx in range(resolution[1]):
            for c_idx in range(resolution[0]):
                self.assertAlmostEqual(sample_hot["thermal_image_celsius"][r_idx][c_idx], expected_hot_val, places=2)

        # Case 3: Ambient temp = 10 C (delta = -10 C)
        env_state_cold_temp = create_mock_environment_state(default_temp_c=10.0)
        sensor_with_env_comp._first_sample_taken = False # Reset EMA
        sample_cold = sensor_with_env_comp.sample(env_state_cold_temp)
        # Expected offset = 0.1 * -10 = -1.0 C. So, 50.0 - 1.0 = 49.0
        expected_cold_val = 49.0
        for r_idx in range(resolution[1]):
            for c_idx in range(resolution[0]):
                self.assertAlmostEqual(sample_cold["thermal_image_celsius"][r_idx][c_idx], expected_cold_val, places=2)

    def test_thermal_env_comp_no_params_or_missing_temp_method(self):
        """Test thermal env compensation when params missing or env state lacks temp method."""
        resolution = [2,2]
        sensor_no_params = ThermalCameraSensor(
            "thermal_env_comp_no_cfg", (0,0,0), {},
            specific_params={"resolution": resolution, "response_time_alpha": 1.0},
            environmental_compensation_params=None
        )
        value_before = 30.0
        mock_img = [[value_before for _ in range(resolution[0])] for _ in range(resolution[1])]
        def mock_gt(env): return {"thermal_image_celsius": mock_img, "resolution": resolution}
        sensor_no_params.get_ground_truth = mock_gt
        sensor_no_params._first_sample_taken = False

        env_state_with_temp = create_mock_environment_state(default_temp_c=35.0)
        sample1 = sensor_no_params.sample(env_state_with_temp)
        self.assertAlmostEqual(sample1["thermal_image_celsius"][0][0], value_before) # Unchanged

        # Test with env state missing get_temperature_celsius
        sensor_valid_params_bad_env = ThermalCameraSensor(
            "thermal_env_comp_bad_env", (0,0,0), {},
            specific_params={"resolution": resolution, "response_time_alpha": 1.0},
            environmental_compensation_params={"temperature": {"reference_temp_c": 25.0, "global_offset_celsius_per_celsius": 0.1}}
        )
        sensor_valid_params_bad_env.get_ground_truth = mock_gt
        sensor_valid_params_bad_env._first_sample_taken = False
        
        class BasicEnvStateNoTemp: pass # Lacks get_temperature_celsius
        
        with patch('builtins.print') as mock_print:
            sample3 = sensor_valid_params_bad_env.sample(BasicEnvStateNoTemp())
            self.assertAlmostEqual(sample3["thermal_image_celsius"][0][0], value_before) # Unchanged
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

    def test_emf_time_based_drift(self):
        """Test time-based baseline drift for EMFSensor."""
        drift_config = {
            "baseline_drift_v_per_m_per_hour": {"ac_field_strength_v_per_m": 0.01}
        }
        sensor = EMFSensor(
            "emf_drift_test", (0,0,0), {}, {},
            drift_parameters=drift_config
        )
        # Ensure other imperfections are off for this test
        sensor.noise_characteristics = {}
        sensor.calibration_artifacts = {}
        sensor.environmental_compensation_params = {}

        true_field_strength = 0.5 # V/m
        
        # Mock get_ground_truth to return a fixed true value
        def mock_gt_emf_drift(environment_3d_state):
            return {"ac_field_strength_v_per_m": true_field_strength, "dominant_frequency_hz": 60.0}
        sensor.get_ground_truth = mock_gt_emf_drift

        # --- Test at T=0 hours ---
        env_state_t0 = create_mock_environment_state(simulation_time_seconds=0.0)
        sample_t0 = sensor.sample(env_state_t0)
        self.assertAlmostEqual(sample_t0["ac_field_strength_v_per_m"], true_field_strength, places=4)

        # --- Test at T=1 hour (3600s) ---
        env_state_t1 = create_mock_environment_state(simulation_time_seconds=3600.0)
        sample_t1 = sensor.sample(env_state_t1)
        # Expected: 0.5 + (0.01 * 1) = 0.51
        self.assertAlmostEqual(sample_t1["ac_field_strength_v_per_m"], 0.51, places=4)
        
        # --- Test at T=10 hours (36000s) ---
        env_state_t10 = create_mock_environment_state(simulation_time_seconds=36000.0)
        sample_t10 = sensor.sample(env_state_t10)
        # Expected: 0.5 + (0.01 * 10) = 0.5 + 0.1 = 0.6
        self.assertAlmostEqual(sample_t10["ac_field_strength_v_per_m"], 0.6, places=4)

    def test_emf_drift_no_time_in_env(self):
        """Test EMFSensor drift behavior if environment_3d_state lacks simulation_time_seconds."""
        drift_config = {"baseline_drift_v_per_m_per_hour": {"ac_field_strength_v_per_m": 0.01}}
        sensor = EMFSensor("emf_drift_no_time", (0,0,0), {}, {}, drift_parameters=drift_config)
        sensor.noise_characteristics = {} # Turn off other effects
        
        true_val = 0.5
        def mock_gt(env): return {"ac_field_strength_v_per_m": true_val, "dominant_frequency_hz": 60.0}
        sensor.get_ground_truth = mock_gt
        
        class BasicEnvStateNoTime: # Lacks simulation_time_seconds
            # Minimal methods needed by EMFSensor's get_ground_truth if it were more complex
            def get_emf_field_strength(self, position, frequency_range_hz):
                return {"ac_field_strength_v_per_m": true_val, "dominant_frequency_hz": 60.0}
        
        with patch('builtins.print') as mock_print:
            sample = sensor.sample(BasicEnvStateNoTime())
            self.assertAlmostEqual(sample["ac_field_strength_v_per_m"], true_val)
            mock_print.assert_any_call(f"Warning: Drift params exist for EMFSensor {sensor.sensor_id} but env_state lacks 'simulation_time_seconds'. Skipping drift.")

    def test_emf_gaussian_noise(self):
        """Test Gaussian noise application for EMFSensor."""
        noise_config = {"type": "gaussian", "mean": 0.0, "stddev_v_per_m": 0.02}
        sensor = EMFSensor(
            "emf_noise_test", (0,0,0), {}, {},
            noise_characteristics=noise_config
        )
        # Turn off other imperfections
        sensor.drift_parameters = {}

        true_field_strength = 0.75 # V/m
        def mock_gt_emf_noise(env_state):
            return {"ac_field_strength_v_per_m": true_field_strength, "dominant_frequency_hz": 60.0}
        sensor.get_ground_truth = mock_gt_emf_noise
        
        env_state = create_mock_environment_state() # simulation_time_seconds is not used by noise

        num_samples = 500
        readings = []
        for _ in range(num_samples):
            sample_data = sensor.sample(env_state)
            readings.append(sample_data["ac_field_strength_v_per_m"])
            self.assertGreaterEqual(sample_data["ac_field_strength_v_per_m"], 0.0) # Check non-negativity

        avg_reading = sum(readings) / num_samples
        self.assertAlmostEqual(avg_reading, true_field_strength, delta=0.01) # Avg should be close to true + mean (0)

        # Check stddev (approximate)
        stddev_reading = (sum([(x - avg_reading) ** 2 for x in readings]) / num_samples) ** 0.5
        self.assertAlmostEqual(stddev_reading, noise_config["stddev_v_per_m"], delta=0.01)

    def test_emf_no_noise_applied(self):
        """Test EMFSensor no noise if config missing or stddev is zero."""
        sensor_no_cfg = EMFSensor("emf_no_noise1", (0,0,0), {}, {}, noise_characteristics=None)
        sensor_zero_std = EMFSensor(
            "emf_no_noise2", (0,0,0), {}, {},
            noise_characteristics={"type": "gaussian", "mean": 0.0, "stddev_v_per_m": 0.0}
        )
        
        true_val = 0.6
        def mock_gt(env): return {"ac_field_strength_v_per_m": true_val}

        for sensor_case in [sensor_no_cfg, sensor_zero_std]:
            sensor_case.get_ground_truth = mock_gt
            sensor_case.drift_parameters = {} # Turn off other effects
            sample_data = sensor_case.sample(create_mock_environment_state())
            self.assertAlmostEqual(sample_data["ac_field_strength_v_per_m"], true_val)


if __name__ == '__main__':
    unittest.main()