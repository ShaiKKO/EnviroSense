import unittest
from unittest.mock import MagicMock, patch
import numpy as np # Added for new tests

from envirosense.simulation_engine.sensors.infrastructure import ThermalCameraSensor, EMFSensor
from envirosense.simulation_engine.environment.mock_utils import create_mock_environment_state
# from envirosense.simulation_engine.environment.state import Environment3DState # For type hinting - already present

# TestThermalCameraSensor class remains unchanged from the user-provided file content...
# (Assuming the ThermalCameraSensor tests are extensive and correct as they were)
# ... (ThermalCameraSensor test methods from line 8 to 455 of the provided file) ...

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
        with patch('envirosense.simulation_engine.sensors.infrastructure.logger.warning') as mock_logger_warning:
            gt_data = sensor.get_ground_truth(BadEnvState())
            self.assertIn("error", gt_data)
            self.assertTrue("Environment state does not support thermal field view queries." in gt_data["error"])
            mock_logger_warning.assert_any_call(f"environment_3d_state for ThermalCameraSensor {sensor.sensor_id} lacks 'get_thermal_field_view' method.")

    def test_get_ground_truth_env_method_raises_exception(self):
        sensor = ThermalCameraSensor("thermal_env_ex", (0,0,0), {}, {"resolution": [1,1]})
        mock_env_state = create_mock_environment_state()
        def raiser(*args, **kwargs): raise RuntimeError("Simulated thermal query failure")
        mock_env_state.get_thermal_field_view = raiser
        with patch('envirosense.simulation_engine.sensors.infrastructure.logger.error') as mock_logger_error:
            gt_data = sensor.get_ground_truth(mock_env_state)
            self.assertIn("error", gt_data)
            self.assertTrue("Failed to get thermal field view" in gt_data["error"])
            self.assertTrue("Simulated thermal query failure" in gt_data["error"])
            mock_logger_error.assert_any_call(f"Error querying thermal field view for {sensor.sensor_id}: Simulated thermal query failure", exc_info=True)
            
    def test_get_ground_truth_malformed_image_response(self):
        sensor = ThermalCameraSensor("thermal_malformed", (0,0,0), {}, {"resolution": [2,2]})
        mock_env_state = create_mock_environment_state()
        mock_env_state.get_thermal_field_view = MagicMock(return_value=[[1.0, 2.0]]) 
        with patch('envirosense.simulation_engine.sensors.infrastructure.logger.error') as mock_logger_error:
            gt_data = sensor.get_ground_truth(mock_env_state)
            self.assertIn("error", gt_data)
            self.assertTrue("malformed thermal image data" in gt_data["error"].lower())
            mock_logger_error.assert_any_call(f"Thermal field view from environment has unexpected dimensions for {sensor.sensor_id}.")

        mock_env_state.get_thermal_field_view = MagicMock(return_value=[[1.0],[2.0]])
        with patch('envirosense.simulation_engine.sensors.infrastructure.logger.error') as mock_logger_error: # Re-patch for second call
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
            sensor_case.noise_characteristics = {} 
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
            from scipy.ndimage import gaussian_filter # type: ignore
            scipy_present = True
        except ImportError:
            scipy_present = False
            # This print is fine for a test skip message
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
            # No need to mock print here, the logger.warning in infrastructure.py handles it
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
            noise_characteristics={}, calibration_artifacts={},
            optical_blur_config={}, dead_pixels=[], hot_pixels_config={}
        )

        value_before_this_comp = 50.0
        mock_intermediate_image = [[value_before_this_comp for _ in range(resolution[0])] for _ in range(resolution[1])]

        def mock_gt_for_env_comp(env_state):
            return {"thermal_image_celsius": [row[:] for row in mock_intermediate_image], "resolution": resolution}
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
        self.assertAlmostEqual(sample1["thermal_image_celsius"][0][0], value_before)

        sensor_valid_params_bad_env = ThermalCameraSensor(
            "thermal_env_comp_bad_env", (0,0,0), {},
            specific_params={"resolution": resolution, "response_time_alpha": 1.0},
            environmental_compensation_params={"temperature": {"reference_temp_c": 25.0, "global_offset_celsius_per_celsius": 0.1}}
        )
        sensor_valid_params_bad_env.get_ground_truth = mock_gt
        sensor_valid_params_bad_env._first_sample_taken = False
        
        class BasicEnvStateNoTemp: pass 
        
        with patch('envirosense.simulation_engine.sensors.infrastructure.logger.warning') as mock_logger_warning:
            sample3 = sensor_valid_params_bad_env.sample(BasicEnvStateNoTemp())
            self.assertAlmostEqual(sample3["thermal_image_celsius"][0][0], value_before)
            mock_logger_warning.assert_any_call(f"Thermal camera temp comp config exists for {sensor_valid_params_bad_env.sensor_id} but env_state lacks 'get_temperature_celsius'. Skipping.")


class TestEMFSensor(unittest.TestCase):
    """Test suite for the EMFSensor class, covering its initialization,
    ground truth retrieval, imperfection modeling, and metadata generation."""

    def test_get_ground_truth_success(self):
        """
        Test EMFSensor.get_ground_truth with a responsive mock environment.
        Ensures that the method correctly queries the environment and structures
        the ground truth data, including anomaly labels and spectrum.
        """
        sensor_id = "emf_gt_test_success"
        position = (1.0, 1.0, 1.0)
        freq_range = [50.0, 60.0]
        sensor = EMFSensor(
            sensor_id=sensor_id,
            position_3d=position,
            sampling_volume={},
            specific_params={"frequency_range_hz": freq_range}
        )
        
        # Define mock data returned by the environment
        mock_emf_data_from_env = {
            "ac_field_strength_v_per_m": 1.23,
            "dominant_frequency_hz": 55.0,
            "ac_field_vector_v_per_m": [0.5, 0.5, 1.0] # Example vector
        }
        
        # Setup mock environment to return specific EMF details and no active anomalies
        mock_env_state = create_mock_environment_state(
            emf_details=mock_emf_data_from_env, 
            fields_values={ # Ensure no anomalies are active for this baseline test
                ('corona_discharge', position): 0.0,
                ('arcing_intensity', position): 0.0
            }
        )
        
        # Mock the environment's method to trace calls and ensure it's called correctly
        original_get_emf_characteristics = mock_env_state.get_emf_characteristics_at_point
        mock_env_state.get_emf_characteristics_at_point = MagicMock(wraps=original_get_emf_characteristics)
        
        # Call the method under test
        gt_data = sensor.get_ground_truth(mock_env_state)

        # Assertions for successful ground truth retrieval
        self.assertNotIn("error", gt_data, msg=f"Error in ground truth: {gt_data.get('error')}")
        self.assertEqual(gt_data["ac_field_strength_v_per_m"], mock_emf_data_from_env["ac_field_strength_v_per_m"])
        self.assertEqual(gt_data["dominant_frequency_hz"], mock_emf_data_from_env["dominant_frequency_hz"])
        self.assertIn("anomaly_labels", gt_data, "Anomaly labels missing from ground truth.")
        self.assertEqual(gt_data["anomaly_labels"]["anomaly_type"], "none", "Expected no anomaly for baseline.")
        self.assertIn("spectrum_truth", gt_data, "Spectrum truth missing from ground truth.")
        self.assertIn("fundamental", gt_data["spectrum_truth"])
        self.assertAlmostEqual(gt_data["spectrum_truth"]["fundamental"], mock_emf_data_from_env["ac_field_strength_v_per_m"])
        self.assertIn("harmonics", gt_data["spectrum_truth"])
        
        # Verify the environment was called correctly
        mock_env_state.get_emf_characteristics_at_point.assert_called_once_with(
            position=position, 
            frequency_range_hz=freq_range
        )

    def test_get_ground_truth_no_capability(self):
        """Test EMFSensor.get_ground_truth when ground_truth_capability is False."""
        sensor = EMFSensor("emf_gt_off", (0,0,0), {}, {}, ground_truth_capability=False)
        gt_data = sensor.get_ground_truth(create_mock_environment_state())
        self.assertIn("error", gt_data)
        self.assertIn("not supported", gt_data["error"].lower())

    def test_get_ground_truth_env_missing_method(self):
        """Test EMFSensor.get_ground_truth when environment lacks the required 'get_emf_characteristics_at_point' method."""
        sensor = EMFSensor("emf_bad_env", (0,0,0), {}, {})
        class BadEnvState: pass # Dummy environment state without the necessary method
        
        # Patch the logger to check for the warning
        with patch('envirosense.simulation_engine.sensors.infrastructure.logger.warning') as mock_logger_warning:
            gt_data = sensor.get_ground_truth(BadEnvState())
            self.assertIn("error", gt_data)
            self.assertIn("Environment state does not support EMF characteristics queries.", gt_data["error"])
            # Verify that the specific warning was logged
            mock_logger_warning.assert_any_call(f"environment_state for EMFSensor {sensor.sensor_id} lacks 'get_emf_characteristics_at_point' method.")

    def test_get_ground_truth_env_method_raises_exception(self):
        """Test EMFSensor.get_ground_truth when the environment's 'get_emf_characteristics_at_point' method raises an exception."""
        sensor = EMFSensor("emf_env_ex", (0,0,0), {}, {})
        mock_env_state = create_mock_environment_state()
        # Configure the mock environment method to raise a specific error
        def raiser(*args, **kwargs): raise RuntimeError("Simulated EMF query failure from environment")
        mock_env_state.get_emf_characteristics_at_point = raiser
        
        # Patch the logger to check for the error log
        with patch('envirosense.simulation_engine.sensors.infrastructure.logger.error') as mock_logger_error:
            gt_data = sensor.get_ground_truth(mock_env_state)
            self.assertIn("error", gt_data)
            self.assertIn("Failed to get EMF characteristics", gt_data["error"])
            self.assertIn("Simulated EMF query failure from environment", gt_data["error"])
            # Verify that the error was logged with exception info
            mock_logger_error.assert_any_call(f"Error querying EMF characteristics for {sensor.sensor_id}: Simulated EMF query failure from environment", exc_info=True)

    def test_get_ground_truth_malformed_data_response(self):
        """Test EMFSensor.get_ground_truth with various malformed data responses from the environment."""
        sensor = EMFSensor("emf_malformed_data_test", (0,0,0), {}, {})
        mock_env_state = create_mock_environment_state()
        
        # Case 1: Environment returns a non-dictionary response
        mock_env_state.get_emf_characteristics_at_point = MagicMock(return_value="this_is_not_a_dictionary")
        with patch('envirosense.simulation_engine.sensors.infrastructure.logger.error') as mock_logger_error:
            gt_data_case1 = sensor.get_ground_truth(mock_env_state)
            self.assertIn("error", gt_data_case1)
            self.assertIn("malformed emf data", gt_data_case1["error"].lower())
            mock_logger_error.assert_any_call(f"EMF data from environment for {sensor.sensor_id} has unexpected format or is missing 'ac_field_strength_v_per_m'. Data: this_is_not_a_dictionary")

        # Case 2: Environment returns a dictionary but missing the essential 'ac_field_strength_v_per_m' key
        malformed_dict = {"some_other_key": 123, "dominant_frequency_hz": 60.0}
        mock_env_state.get_emf_characteristics_at_point = MagicMock(return_value=malformed_dict)
        with patch('envirosense.simulation_engine.sensors.infrastructure.logger.error') as mock_logger_error:
            gt_data_case2 = sensor.get_ground_truth(mock_env_state)
            self.assertIn("error", gt_data_case2)
            self.assertIn("malformed emf data", gt_data_case2["error"].lower())
            mock_logger_error.assert_any_call(f"EMF data from environment for {sensor.sensor_id} has unexpected format or is missing 'ac_field_strength_v_per_m'. Data: {malformed_dict}")

    def test_sample_calls_get_ground_truth_and_apply_imperfections(self):
        """Test the main sample() method flow: ensures it calls get_ground_truth and then apply_imperfections."""
        sensor = EMFSensor("emf_sample_flow_test", (0,0,0), {}, {})
        mock_env_state = create_mock_environment_state()
        # Define a simple, valid ground truth dictionary that get_ground_truth would return
        gt_return_value = {"ac_field_strength_v_per_m": 1.0, "anomaly_labels": {}, "spectrum_truth": {}}
        sensor.get_ground_truth = MagicMock(return_value=gt_return_value)
        # Mock apply_imperfections to simply pass through its input, to isolate testing the flow of sample()
        sensor.apply_imperfections = MagicMock(side_effect=lambda true_reading, env_state: true_reading) 
        
        result = sensor.sample(mock_env_state)
        
        # Verify that get_ground_truth was called correctly
        sensor.get_ground_truth.assert_called_once_with(mock_env_state)
        # Verify that apply_imperfections was called with the result of get_ground_truth
        sensor.apply_imperfections.assert_called_once_with(gt_return_value, mock_env_state)
        # Check that the final result is what apply_imperfections (mocked) returned
        self.assertEqual(result, gt_return_value)

    def test_sample_propagates_error_from_get_ground_truth(self):
        """Test that sample() correctly propagates an error dictionary if get_ground_truth returns one."""
        sensor = EMFSensor("emf_sample_gt_error_prop", (0,0,0), {}, {})
        mock_env_state = create_mock_environment_state()
        # Define an error response from get_ground_truth
        error_response_from_gt = {"error": "Ground truth acquisition failed critically"}
        sensor.get_ground_truth = MagicMock(return_value=error_response_from_gt)
        sensor.apply_imperfections = MagicMock() # This should not be called if get_ground_truth fails
        
        result = sensor.sample(mock_env_state)
        
        # The error dictionary from get_ground_truth should be returned directly by sample()
        self.assertEqual(result, error_response_from_gt)
        # apply_imperfections should not have been called in this case
        sensor.apply_imperfections.assert_not_called()

    def test_emf_time_based_drift(self):
        """
        Test time-based drift for EMFSensor.
        Focuses on 'baseline_drift_v_per_m_per_hour' affecting 'ac_field_strength_v_per_m'.
        Other imperfection effects are mocked to isolate drift.
        """
        # Define drift parameters for the sensor
        drift_params_config = {"baseline_drift_v_per_m_per_hour": {"ac_field_strength_v_per_m": 0.1}} # 0.1 V/m per hour
        sensor = EMFSensor("emf_drift_test_isolated", (0,0,0), {}, {"drift_parameters": drift_params_config})
        
        # Create mock environment states for different simulation times
        mock_env_state_1hr = create_mock_environment_state(simulation_time_s=3600) # 1 hour
        mock_env_state_2hr = create_mock_environment_state(simulation_time_s=7200) # 2 hours

        initial_field_strength = 10.0
        # Simplified true_reading, as other components are mocked out or not relevant to this specific drift
        true_reading = {"ac_field_strength_v_per_m": initial_field_strength}

        # Patch other internal imperfection methods to be neutral, isolating the baseline drift effect
        with patch.object(sensor, '_apply_directional_sensitivity', side_effect=lambda x, **kwargs: x if kwargs.get('field_magnitude_override') is None else kwargs.get('field_magnitude_override') ):
            with patch.object(sensor, '_apply_frequency_response', side_effect=lambda x, env: x):
                with patch.object(sensor, '_apply_calibration_errors', side_effect=lambda x, env: x): # Calibration drift is separate
                    with patch.object(sensor, '_apply_emi_effects', side_effect=lambda x, env: x):
                        # Test after 1 hour
                        result_1hr = sensor.apply_imperfections(true_reading.copy(), mock_env_state_1hr)
                        expected_val_1hr = initial_field_strength + (0.1 * 1) # 0.1 V/m drift
                        self.assertAlmostEqual(result_1hr["ac_field_strength_v_per_m"], expected_val_1hr, msg="Drift after 1hr incorrect.")

                        # Test after 2 hours (drift should be based on the original true value)
                        result_2hr = sensor.apply_imperfections(true_reading.copy(), mock_env_state_2hr)
                        expected_val_2hr = initial_field_strength + (0.1 * 2) # 0.2 V/m drift
                        self.assertAlmostEqual(result_2hr["ac_field_strength_v_per_m"], expected_val_2hr, msg="Drift after 2hr incorrect.")

    def test_emf_drift_no_time_in_env(self):
        """
        Test EMFSensor drift behavior if environment_state lacks 'simulation_time_seconds'.
        Ensures drift is not applied and appropriate debug messages are logged.
        """
        drift_params_config = {"baseline_drift_v_per_m_per_hour": {"ac_field_strength_v_per_m": 0.1}}
        sensor = EMFSensor("emf_no_time_drift_test", (0,0,0), {}, {"drift_parameters": drift_params_config})
        
        class EnvStateWithoutTime: pass # Dummy environment lacking simulation_time_seconds
        mock_env_no_time = EnvStateWithoutTime()
        
        initial_field_strength = 10.0
        true_reading = {"ac_field_strength_v_per_m": initial_field_strength}

        with patch('envirosense.simulation_engine.sensors.infrastructure.logger.debug') as mock_logger_debug:
            # Patch other imperfection methods to isolate drift logic
            with patch.object(sensor, '_apply_directional_sensitivity', side_effect=lambda x, **kwargs: x if kwargs.get('field_magnitude_override') is None else kwargs.get('field_magnitude_override') ):
                with patch.object(sensor, '_apply_frequency_response', side_effect=lambda x, env: x):
                    # _apply_calibration_errors itself calls _calculate_drift, so its behavior without time is also implicitly tested
                    with patch.object(sensor, '_apply_calibration_errors', side_effect=lambda x, env: x): 
                        with patch.object(sensor, '_apply_emi_effects', side_effect=lambda x, env: x):
                            result = sensor.apply_imperfections(true_reading.copy(), mock_env_no_time)
                            # Expect no drift if simulation_time_seconds is not available
                            self.assertAlmostEqual(result["ac_field_strength_v_per_m"], initial_field_strength, msg="Field strength changed despite no time for drift.")
                            # Check for specific debug logs
                            # _calculate_drift is called by _apply_calibration_errors for gain and offset drift
                            mock_logger_debug.assert_any_call(f"Drift calculation for {sensor.sensor_id} (gain) skipped: env_state lacks 'simulation_time_seconds'.")
                            mock_logger_debug.assert_any_call(f"Drift calculation for {sensor.sensor_id} (offset) skipped: env_state lacks 'simulation_time_seconds'.")
                            # Check for debug log from the baseline_drift_v_per_m_per_hour part in apply_imperfections
                            mock_logger_debug.assert_any_call(f"Drift params for baseline_drift_v_per_m_per_hour exist for EMFSensor {sensor.sensor_id} but env_state lacks 'simulation_time_seconds'. Skipping this drift.")

    def test_emf_gaussian_noise(self):
        """
        Test Gaussian noise application for EMFSensor.
        Checks if the mean and standard deviation of noisy readings are statistically close to expected values.
        """
        noise_config = {"type": "gaussian", "mean": 0.0, "stddev_v_per_m": 0.05}
        sensor = EMFSensor("emf_noise_gaussian_test", (0,0,0), {}, {"noise_characteristics": noise_config})
        
        true_field_strength = 5.0
        true_reading = {"ac_field_strength_v_per_m": true_field_strength}
        mock_env_state = create_mock_environment_state() # Basic environment state

        # Patch other imperfection methods to isolate the noise effect
        with patch.object(sensor, '_apply_directional_sensitivity', side_effect=lambda x, **kwargs: x if kwargs.get('field_magnitude_override') is None else kwargs.get('field_magnitude_override') ):
            with patch.object(sensor, '_apply_frequency_response', side_effect=lambda x, env: x):
                with patch.object(sensor, '_apply_calibration_errors', side_effect=lambda x, env: x):
                    with patch.object(sensor, '_apply_emi_effects', side_effect=lambda x, env: x):
                        # Generate a number of samples to check statistical properties
                        num_samples = 1000
                        results = [sensor.apply_imperfections(true_reading.copy(), mock_env_state)["ac_field_strength_v_per_m"] for _ in range(num_samples)]
                        
                        mean_of_results = np.mean(results)
                        std_dev_of_results = np.std(results)

                        # Mean should be close to the true value plus the noise mean (which is 0 here)
                        self.assertAlmostEqual(mean_of_results, true_field_strength + noise_config["mean"], delta=0.02, msg="Mean of noisy readings deviates too much.")
                        # Standard deviation should be close to the configured stddev
                        self.assertAlmostEqual(std_dev_of_results, noise_config["stddev_v_per_m"], delta=0.01, msg="Std dev of noisy readings deviates too much.")

    def test_emf_no_noise_applied(self):
        """Test EMFSensor behavior when no noise configuration is provided or when stddev is zero."""
        sensor_no_noise_config = EMFSensor("emf_no_noise_cfg_test", (0,0,0), {}, {"noise_characteristics": None})
        sensor_zero_stddev_config = EMFSensor("emf_zero_stddev_test", (0,0,0), {}, {"noise_characteristics": {"type": "gaussian", "mean": 0.0, "stddev_v_per_m": 0.0}})
        
        true_field_val = 10.0
        true_reading = {"ac_field_strength_v_per_m": true_field_val}
        mock_env = create_mock_environment_state()

        for sensor_case in [sensor_no_noise_config, sensor_zero_stddev_config]:
            # Patch other imperfections to ensure only noise (or lack thereof) is being tested
            with patch.object(sensor_case, '_apply_directional_sensitivity', side_effect=lambda x, **kwargs: x if kwargs.get('field_magnitude_override') is None else kwargs.get('field_magnitude_override') ):
                with patch.object(sensor_case, '_apply_frequency_response', side_effect=lambda x, env: x):
                    with patch.object(sensor_case, '_apply_calibration_errors', side_effect=lambda x, env: x):
                        with patch.object(sensor_case, '_apply_emi_effects', side_effect=lambda x, env: x):
                            result = sensor_case.apply_imperfections(true_reading.copy(), mock_env)
                            self.assertAlmostEqual(result["ac_field_strength_v_per_m"], true_field_val, msg=f"Field strength changed for sensor: {sensor_case.sensor_id} when no noise expected.")

    def test_emf_sensor_init_validation(self):
        """Test initialization validation for EMFSensor specific_params, particularly for frequency response settings."""
        base_pos = (0,0,0)
        base_sv = {}
        # Test valid configurations
        try:
            EMFSensor("emf_valid_init1", base_pos, base_sv, {"frequency_tolerance_hz": 0.5, "default_frequency_gain": 0.9})
            EMFSensor("emf_valid_init2", base_pos, base_sv, {"frequency_tolerance_hz": 0}) # Zero tolerance is acceptable
        except ValueError:
            self.fail("Valid EMFSensor initialization raised ValueError unexpectedly.")

        # Test invalid frequency_tolerance_hz
        with self.assertRaisesRegex(ValueError, "frequency_tolerance_hz .* must be a non-negative number", msg="Negative tolerance not caught."):
            EMFSensor("emf_invalid_tol1", base_pos, base_sv, {"frequency_tolerance_hz": -0.1})
        with self.assertRaisesRegex(ValueError, "frequency_tolerance_hz .* must be a non-negative number", msg="Non-numeric tolerance not caught."):
            EMFSensor("emf_invalid_tol2", base_pos, base_sv, {"frequency_tolerance_hz": "not_a_number"})

        # Test invalid default_frequency_gain
        with self.assertRaisesRegex(ValueError, "default_frequency_gain .* must be a number", msg="Non-numeric default gain not caught."):
            EMFSensor("emf_invalid_gain_type", base_pos, base_sv, {"default_frequency_gain": "not_a_gain_value"})
            
    def test_emf_frequency_dependent_response(self):
        """
        Test frequency-dependent gain application in EMFSensor's get_frequency_gain method.
        Covers exact matches, tolerance matches, default gain usage, and handling of non-numeric inputs/config.
        """
        freq_response_gain_config = {
            "50.0": 0.9,  # 90% gain at 50Hz
            "60": 1.1,    # 110% gain at 60Hz (using an integer string as key)
            "100.0": 0.5  # 50% gain at 100Hz
        }
        sensor_params_config = {
            "frequency_response_gain": freq_response_gain_config,
            "frequency_tolerance_hz": 0.5, # Hz tolerance for matching frequencies
            "default_frequency_gain": 0.1  # Default gain if no specific frequency matches
        }
        sensor = EMFSensor("emf_freq_resp_detailed_test", (0,0,0), {}, sensor_params_config)

        # Test exact matches for configured frequencies
        self.assertAlmostEqual(sensor.get_frequency_gain(50.0), 0.9, msg="Exact match for 50.0 Hz failed.")
        self.assertAlmostEqual(sensor.get_frequency_gain(60.0), 1.1, msg="Exact match for 60.0 Hz (float input, int key in config) failed.")
        self.assertAlmostEqual(sensor.get_frequency_gain(60), 1.1, msg="Exact match for int 60 Hz input failed.")
        self.assertAlmostEqual(sensor.get_frequency_gain(100.0), 0.5, msg="Exact match for 100.0 Hz failed.")

        # Test matches within the defined tolerance
        self.assertAlmostEqual(sensor.get_frequency_gain(50.4), 0.9, msg="Tolerance match for 50.4 Hz (near 50.0) failed.")
        self.assertAlmostEqual(sensor.get_frequency_gain(59.6), 1.1, msg="Tolerance match for 59.6 Hz (near 60.0) failed.")
        self.assertAlmostEqual(sensor.get_frequency_gain(100.49), 0.5, msg="Tolerance match for 100.49 Hz (near 100.0) failed.")

        # Test frequencies outside tolerance, expecting default gain
        self.assertAlmostEqual(sensor.get_frequency_gain(51.0), 0.1, msg="Outside tolerance (51.0 Hz) should use default gain.")
        self.assertAlmostEqual(sensor.get_frequency_gain(70.0), 0.1, msg="Unconfigured frequency (70.0 Hz) should use default gain.")
        self.assertAlmostEqual(sensor.get_frequency_gain(40.0), 0.1, msg="Unconfigured frequency (40.0 Hz) should use default gain.")

        # Test non-numeric input for dominant frequency
        self.assertAlmostEqual(sensor.get_frequency_gain("not_a_frequency"), 0.1, msg="Non-numeric string input failed to use default gain.")
        self.assertAlmostEqual(sensor.get_frequency_gain(None), 0.1, msg="None input failed to use default gain.")

        # Test scenario with non-numeric keys in the frequency_response_gain config (they should be ignored)
        sensor_params_with_bad_keys = {
            "frequency_response_gain": {"50.0": 0.9, "bad_key_string": 2.0, "60": 1.1}, # "bad_key_string" should be skipped
            "frequency_tolerance_hz": 0.5,
            "default_frequency_gain": 0.1
        }
        sensor_with_bad_keys_in_config = EMFSensor("emf_bad_keys_in_cfg", (0,0,0), {}, sensor_params_with_bad_keys)
        self.assertAlmostEqual(sensor_with_bad_keys_in_config.get_frequency_gain(50.0), 0.9) # Valid key
        self.assertAlmostEqual(sensor_with_bad_keys_in_config.get_frequency_gain(60.0), 1.1) # Valid key
        self.assertAlmostEqual(sensor_with_bad_keys_in_config.get_frequency_gain(70.0), 0.1, msg="'bad_key_string' in config incorrectly influenced unrelated match.")
        # Check if logger.debug was called for the bad key (requires patching logger)
        with patch('envirosense.simulation_engine.sensors.infrastructure.logger.debug') as mock_logger_debug_for_bad_key:
            sensor_with_bad_keys_in_config.get_frequency_gain(70.0) # Call again to ensure the iteration over keys happens
            mock_logger_debug_for_bad_key.assert_any_call(f"Non-numeric key 'bad_key_string' in frequency_response_gain for EMFSensor {sensor_with_bad_keys_in_config.sensor_id}. Skipping for tolerance match.")

    def test_emf_frequency_spectrum_analysis(self):
        """
        Test EMF sensor's _analyze_frequency_spectrum method.
        Checks calculation of fundamental, harmonics, and high-frequency noise for corona.
        Also verifies if spectrum is included/excluded in apply_imperfections based on `enable_spectrum_output`.
        """
        sensor_config_params = {
            'base_frequency': 60.0,
            'harmonic_3_ratio': 0.15, # Custom ratio for 3rd harmonic
            'harmonic_5_ratio': 0.08, # Custom ratio for 5th harmonic
            'frequency_noise': False,  # Disable random noise for predictable harmonic calculation in this test
            'corona_hf_noise_factor': 0.20, # Custom factor for high-frequency noise due to corona
            'enable_spectrum_output': True # Ensure spectrum output is enabled for part of the test
        }
        sensor = EMFSensor("emf_spectrum_analysis_test", (0,0,0), {}, sensor_config_params)
        
        field_strength_fundamental = 100.0
        
        # Case 1: No corona discharge present
        mock_env_no_corona_discharge = create_mock_environment_state(fields_values={('corona_discharge', (0,0,0)): 0.0})
        spectrum_no_corona = sensor._analyze_frequency_spectrum(field_strength_fundamental, mock_env_no_corona_discharge)
        
        self.assertAlmostEqual(spectrum_no_corona['fundamental'], field_strength_fundamental)
        self.assertIn('harmonics', spectrum_no_corona)
        self.assertAlmostEqual(spectrum_no_corona['harmonics']['3th'], field_strength_fundamental * (1/3) * 0.15)
        self.assertAlmostEqual(spectrum_no_corona['harmonics']['5th'], field_strength_fundamental * (1/5) * 0.08)
        self.assertAlmostEqual(spectrum_no_corona['harmonics']['7th'], field_strength_fundamental * (1/7) * 0.1) # Default ratio for 7th
        self.assertNotIn('high_frequency_noise', spectrum_no_corona, "High frequency noise should not be present without corona.")

        # Case 2: With corona discharge present
        mock_env_with_corona_discharge = create_mock_environment_state(fields_values={('corona_discharge', (0,0,0)): 50.0}) # Corona value > 0
        spectrum_with_corona = sensor._analyze_frequency_spectrum(field_strength_fundamental, mock_env_with_corona_discharge)
        self.assertIn('high_frequency_noise', spectrum_with_corona, "High frequency noise expected when corona is present.")
        self.assertAlmostEqual(spectrum_with_corona['high_frequency_noise'], field_strength_fundamental * 0.20)

        # Test apply_imperfections to verify spectrum inclusion/exclusion based on `enable_spectrum_output`
        true_reading_for_imperfections = {"ac_field_strength_v_per_m": field_strength_fundamental, "spectrum_truth": spectrum_no_corona.copy()}
        # Mock away other effects to focus on spectrum output behavior
        with patch.object(sensor, '_apply_directional_sensitivity', side_effect=lambda x, **kwargs: x if kwargs.get('field_magnitude_override') is None else kwargs.get('field_magnitude_override') ):
            with patch.object(sensor, '_apply_calibration_errors', side_effect=lambda x, env: x):
                with patch.object(sensor, '_apply_emi_effects', side_effect=lambda x, env: x):
                    # Test when spectrum output is enabled
                    sensor.enable_spectrum_output = True 
                    imperfections_applied_spectrum_enabled = sensor.apply_imperfections(true_reading_for_imperfections.copy(), mock_env_no_corona_discharge)
                    self.assertIn('spectrum', imperfections_applied_spectrum_enabled, "Spectrum should be in output when enable_spectrum_output is True.")
                    self.assertAlmostEqual(imperfections_applied_spectrum_enabled['spectrum']['fundamental'], spectrum_no_corona['fundamental']) # Assuming neutral freq response for this check
        
                    # Test when spectrum output is disabled
                    sensor.enable_spectrum_output = False
                    imperfections_applied_spectrum_disabled = sensor.apply_imperfections(true_reading_for_imperfections.copy(), mock_env_no_corona_discharge)
                    self.assertNotIn('spectrum', imperfections_applied_spectrum_disabled, "Spectrum should NOT be in output when enable_spectrum_output is False.")
        sensor.enable_spectrum_output = True # Reset for subsequent tests if any

    def test_emf_directional_sensitivity(self):
        """
        Test directional sensitivity of the EMF sensor using the _apply_directional_sensitivity helper.
        Checks alignment with sensor orientation, perpendicular fields, and handling of zero vectors.
        """
        # Sensor oriented along Z-axis, no orientation uncertainty for predictable results
        sensor_z_oriented = EMFSensor("emf_dir_sens_z_axis", (0,0,0), {}, {"orientation": [0,0,1], "orientation_uncertainty": False})
        # Sensor oriented along X-axis
        sensor_x_oriented = EMFSensor("emf_dir_sens_x_axis", (0,0,0), {}, {"orientation": [1,0,0], "orientation_uncertainty": False})

        field_vector_z_axis = np.array([0,0,10.0]) # Field purely along Z-axis
        field_vector_x_axis = np.array([5.0,0,0])  # Field purely along X-axis
        field_vector_xy_plane = np.array([3.0,4.0,0]) # Field in XY plane, magnitude 5
        field_vector_xyz_angled = np.array([1.0,1.0,np.sqrt(2)]) # Magnitude 2, angled at 45 deg to Z-axis

        # --- Tests for Z-oriented sensor ---
        self.assertAlmostEqual(sensor_z_oriented._apply_directional_sensitivity(field_vector_z_axis), 10.0, msg="Z-sensor, Z-field (aligned) failed.")
        self.assertAlmostEqual(sensor_z_oriented._apply_directional_sensitivity(field_vector_x_axis), 0.0,  msg="Z-sensor, X-field (perpendicular) failed.")
        self.assertAlmostEqual(sensor_z_oriented._apply_directional_sensitivity(field_vector_xy_plane), 0.0, msg="Z-sensor, XY-field (perpendicular) failed.")
        # For field_vector_xyz_angled, dot([0,0,1], [1,1,sqrt(2)]/2) * 2 = (sqrt(2)/2) * 2 = sqrt(2)
        self.assertAlmostEqual(sensor_z_oriented._apply_directional_sensitivity(field_vector_xyz_angled), np.sqrt(2), msg="Z-sensor, XYZ-angled field projection failed.")

        # --- Tests for X-oriented sensor ---
        self.assertAlmostEqual(sensor_x_oriented._apply_directional_sensitivity(field_vector_z_axis), 0.0, msg="X-sensor, Z-field (perpendicular) failed.")
        self.assertAlmostEqual(sensor_x_oriented._apply_directional_sensitivity(field_vector_x_axis), 5.0, msg="X-sensor, X-field (aligned) failed.")
        # For field_vector_xy_plane, dot([1,0,0], [3,4,0]/5) * 5 = (3/5) * 5 = 3
        self.assertAlmostEqual(sensor_x_oriented._apply_directional_sensitivity(field_vector_xy_plane), 3.0, msg="X-sensor, XY-field projection failed.")
        self.assertAlmostEqual(sensor_x_oriented._apply_directional_sensitivity(field_vector_xyz_angled), 1.0, msg="X-sensor, XYZ-angled field projection failed.")

        # Test with magnitude_override: direction vector is unit, magnitude provided separately
        self.assertAlmostEqual(sensor_z_oriented._apply_directional_sensitivity(np.array([0,0,1.0]), field_magnitude_override=10.0), 10.0, msg="Magnitude override with Z-alignment failed.")
        
        # Test zero field vector input
        self.assertAlmostEqual(sensor_z_oriented._apply_directional_sensitivity(np.array([0.0,0.0,0.0])), 0.0, msg="Zero field vector input failed.")

        # Test zero sensor orientation (should log a warning and return 0.0)
        sensor_zero_orientation = EMFSensor("emf_zero_orientation_test", (0,0,0), {}, {"orientation": [0,0,0], "orientation_uncertainty": False})
        with patch('envirosense.simulation_engine.sensors.infrastructure.logger.warning') as mock_logger_warning_zero_orient:
            self.assertAlmostEqual(sensor_zero_orientation._apply_directional_sensitivity(field_vector_z_axis), 0.0, msg="Zero sensor orientation did not return 0.")
            mock_logger_warning_zero_orient.assert_called_once_with(f"EMFSensor {sensor_zero_orientation.sensor_id} has zero vector orientation. Directional sensitivity will result in 0 field strength.")

    def test_emf_emi_interference(self):
        """
        Test EMI (Electromagnetic Interference) effects on EMFSensor readings.
        Verifies impact on spectrum noise floor and overall field strength based on mock EMI sources.
        """
        sensor_config_params = {
            "emi_sources_config": {"radius_m": 10.0}, # Search radius for EMI sources
            "base_frequency": 60.0,                   # Sensor's operating frequency for coupling calculation
            "emi_frequency_coupling_factor": 500.0,   # Factor for frequency coupling calculation
            "emi_spectrum_impact_factor": 0.2,        # How much EMI contributes to spectrum noise floor
            "emi_field_strength_impact_factor": 0.5,  # How much EMI directly adds to field strength reading
            "emi_field_strength_random_stddev": 0.0,  # Disable random component of EMI for predictable test results
            "enable_spectrum_output": True            # Ensure spectrum is part of the output for testing
        }
        sensor = EMFSensor("emf_emi_effects_test", (0,0,0), {}, sensor_config_params)
        
        # Define mock EMI sources that the environment will return
        mock_emi_sources = [
            {"position": [1.0,0,0], "strength": 10.0, "frequency": 60.0},  # Close source, same frequency as sensor
            {"position": [8.0,0,0], "strength": 100.0, "frequency": 1000.0} # Further source, different frequency
        ]
        mock_env_state_with_emi = create_mock_environment_state()
        # Mock the environment's method to return our defined EMI sources
        mock_env_state_with_emi.get_nearby_sources = MagicMock(return_value=mock_emi_sources)

        initial_field_strength_value = 5.0
        initial_reading_dict = {"ac_field_strength_v_per_m": initial_field_strength_value, "spectrum": {"fundamental": initial_field_strength_value, "harmonics": {}}}
        
        # Patch away other imperfection effects to isolate EMI effect within apply_imperfections
        with patch.object(sensor, '_apply_directional_sensitivity', side_effect=lambda x, **kwargs: x if kwargs.get('field_magnitude_override') is None else kwargs.get('field_magnitude_override') ):
            with patch.object(sensor, '_apply_frequency_response', side_effect=lambda x, env: x): # Neutral frequency response
                 with patch.object(sensor, '_apply_calibration_errors', side_effect=lambda x, env: x): # No calibration errors
                    result_with_emi = sensor.apply_imperfections(initial_reading_dict.copy(), mock_env_state_with_emi)

                    # Calculate expected total interference field strength based on the formula in _apply_emi_effects
                    # Source 1: dist=1, freq_diff=0, coupling=exp(0)=1. Interference_contrib = 10*1 / (1^2+1) = 5.0
                    # Source 2: dist=8, freq_diff=940, coupling=exp(-940/500) approx 0.1525. Interference_contrib = 100*0.1525 / (8^2+1) = 15.25/65 approx 0.2346
                    expected_interference_s1 = (10.0 * np.exp(-abs(60.0-60.0)/500.0) / (1**2+1.0))
                    expected_interference_s2 = (100.0 * np.exp(-abs(1000.0-60.0)/500.0) / (8**2+1.0))
                    expected_total_interference_field = expected_interference_s1 + expected_interference_s2
                    
                    self.assertIn("spectrum", result_with_emi, "Spectrum missing from EMI test result.")
                    self.assertIn("emi_noise_floor_contribution", result_with_emi["spectrum"], "EMI noise floor contribution missing from spectrum.")
                    self.assertAlmostEqual(result_with_emi["spectrum"]["emi_noise_floor_contribution"], expected_total_interference_field * 0.2, places=3, msg="EMI noise floor contribution incorrect.")
                    
                    # random_interference_effect is 1.0 due to emi_field_strength_random_stddev = 0.0
                    expected_final_field_strength = initial_field_strength_value + (expected_total_interference_field * 0.5 * 1.0) 
                    self.assertAlmostEqual(result_with_emi["ac_field_strength_v_per_m"], expected_final_field_strength, places=3, msg="Final field strength after EMI incorrect.")

    def test_emf_calibration_errors(self):
        """
        Test calibration errors (gain, offset, non-linearity, and their drift components).
        Verifies that these errors are applied correctly to the field strength.
        """
        calibration_config_params = {
            'calibration_gain_error_factor': 1.05, # +5% base gain error
            'calibration_gain_drift_percent_per_hour': 0.1, # 0.1% per hour gain drift
            'calibration_offset_v_per_m': 0.2,      # Base offset error in V/m
            'calibration_offset_drift_v_per_m_per_hour': 0.05, # Offset drift in V/m per hour
            'calibration_nonlinearity_factor': 0.001, # Quadratic non-linearity factor
            'enable_spectrum_output': False # Disable spectrum to focus on field strength modifications
        }
        sensor = EMFSensor("emf_calibration_errors_test", (0,0,0), {}, specific_params=calibration_config_params)
        
        mock_env_sim_time_1hr = create_mock_environment_state(simulation_time_s=3600) # 1 hour simulation time
        
        initial_field_strength = 10.0
        # Simplified reading, as spectrum and other parts are less relevant here or mocked away
        reading_before_calibration = {"ac_field_strength_v_per_m": initial_field_strength} 
        
        # Isolate calibration errors by mocking other imperfection steps that precede or follow it in apply_imperfections
        with patch.object(sensor, '_apply_directional_sensitivity', side_effect=lambda x, **kwargs: x if kwargs.get('field_magnitude_override') is None else kwargs.get('field_magnitude_override') ):
            with patch.object(sensor, '_apply_frequency_response', side_effect=lambda x, env: x): 
                with patch.object(sensor, '_apply_emi_effects', side_effect=lambda x, env: x): 
                    # Note: General drift (from self.drift_parameters) and noise are applied *after* _apply_calibration_errors.
                    # We'll neutralize them by setting their configs on the sensor instance for this test.
                    sensor.noise_characteristics = {} 
                    sensor.drift_parameters = {} # Neutralize general drift to focus on calibration drift
                    
                    result_at_1hr = sensor.apply_imperfections(reading_before_calibration.copy(), mock_env_sim_time_1hr)
                    
                    # Expected calculations for 1 hour:
                    # Gain drift factor = (0.1 / 100.0) * 1 hour = 0.001
                    # Actual gain = BaseGainFactor * (1 + GainDriftFactor) = 1.05 * (1 + 0.001) = 1.05 * 1.001 = 1.05105
                    # Offset drift amount = OffsetDriftRate * 1 hour = 0.05 * 1 = 0.05 V/m
                    # Actual offset = BaseOffset + OffsetDriftAmount = 0.2 + 0.05 = 0.25 V/m
                    # Calibrated field (linear part) = ActualGain * InitialField + ActualOffset
                    #                               = 1.05105 * 10.0 + 0.25 = 10.5105 + 0.25 = 10.7605
                    # Non-linearity part = NonlinearityFactor * (InitialField^2) = 0.001 * (10.0**2) = 0.001 * 100 = 0.1
                    # Final expected value = LinearPart + NonlinearityPart = 10.7605 + 0.1 = 10.8605
                    expected_field_strength_at_1hr = (1.05 * 1.001 * initial_field_strength) + (0.2 + 0.05) + (0.001 * initial_field_strength**2)
                    self.assertAlmostEqual(result_at_1hr["ac_field_strength_v_per_m"], expected_field_strength_at_1hr, places=4, msg="Calibrated field strength at 1hr incorrect.")

        # Test with no calibration errors configured (should not change value from these specific effects)
        sensor_no_calibration_errors = EMFSensor("emf_no_cal_errors_test", (0,0,0), {}, {"enable_spectrum_output": False}) # Empty calibration params
        with patch.object(sensor_no_calibration_errors, '_apply_directional_sensitivity', side_effect=lambda x, **kwargs: x if kwargs.get('field_magnitude_override') is None else kwargs.get('field_magnitude_override') ):
            with patch.object(sensor_no_calibration_errors, '_apply_frequency_response', side_effect=lambda x, env: x):
                with patch.object(sensor_no_calibration_errors, '_apply_emi_effects', side_effect=lambda x, env: x):
                    sensor_no_calibration_errors.noise_characteristics = {}
                    sensor_no_calibration_errors.drift_parameters = {}
                    result_no_cal_errors = sensor_no_calibration_errors.apply_imperfections(reading_before_calibration.copy(), mock_env_sim_time_1hr)
                    self.assertAlmostEqual(result_no_cal_errors["ac_field_strength_v_per_m"], initial_field_strength, msg="Field strength changed when no calibration errors were configured.")

    def test_emf_axis_misalignment_spectrum_effect(self):
        """
        Test the effect of axis misalignment on the spectrum components.
        This specific effect is handled within the _apply_calibration_errors method.
        """
        sensor_config_params = {
            "axis_misalignment_effect_on_spectrum": True,
            "axis_misalignment_degrees": 30.0, # cos(30deg) is approx 0.866025
            "enable_spectrum_output": True     # Spectrum must be enabled to see this effect
        }
        sensor = EMFSensor("emf_axis_misalignment_test", (0,0,0), {}, specific_params=sensor_config_params)
        
        initial_spectrum_values = {
            "fundamental": 100.0,
            "harmonics": {"3th": 10.0, "5th": 5.0},
            "other_component": 20.0 # A generic component to ensure it's also affected
        }
        # Prepare a reading dictionary as it would be *before* the misalignment part of _apply_calibration_errors
        # The ac_field_strength_v_per_m is also needed as _apply_calibration_errors might modify it due to other cal errors (though neutralized here)
        reading_input_to_calibration = {
            "ac_field_strength_v_per_m": 100.0, 
            "spectrum": initial_spectrum_values.copy()
        }
        mock_env_state_for_cal = create_mock_environment_state(simulation_time_s=0) # Time needed for drift calculations within _apply_calibration_errors

        # Isolate axis misalignment by neutralizing other calibration effects within the sensor's config for this test
        sensor.config['calibration_gain_error_factor'] = 1.0
        sensor.config['calibration_gain_drift_percent_per_hour'] = 0.0
        sensor.config['calibration_offset_v_per_m'] = 0.0
        sensor.config['calibration_offset_drift_v_per_m_per_hour'] = 0.0
        sensor.config['calibration_nonlinearity_factor'] = 0.0

        # Call _apply_calibration_errors directly to specifically test its spectrum modification part due to misalignment
        result_after_calibration_step = sensor._apply_calibration_errors(reading_input_to_calibration.copy(), mock_env_state_for_cal)
        resulting_spectrum = result_after_calibration_step['spectrum']
        
        expected_reduction_factor = np.cos(np.radians(30.0))
        self.assertAlmostEqual(resulting_spectrum["fundamental"], initial_spectrum_values["fundamental"] * expected_reduction_factor, msg="Fundamental component misalignment effect incorrect.")
        self.assertAlmostEqual(resulting_spectrum["harmonics"]["3th"], initial_spectrum_values["harmonics"]["3th"] * expected_reduction_factor, msg="3rd harmonic misalignment effect incorrect.")
        self.assertAlmostEqual(resulting_spectrum["harmonics"]["5th"], initial_spectrum_values["harmonics"]["5th"] * expected_reduction_factor, msg="5th harmonic misalignment effect incorrect.")
        self.assertAlmostEqual(resulting_spectrum["other_component"], initial_spectrum_values["other_component"] * expected_reduction_factor, msg="Other spectrum component misalignment effect incorrect.")

        # Test when the axis misalignment effect is disabled in config
        sensor_config_params_no_misalign_effect = sensor_config_params.copy()
        sensor_config_params_no_misalign_effect["axis_misalignment_effect_on_spectrum"] = False
        sensor_no_misalign_effect = EMFSensor("emf_no_misalign_effect_test", (0,0,0), {}, specific_params=sensor_config_params_no_misalign_effect)
        # Neutralize other cal effects for this sensor instance too
        sensor_no_misalign_effect.config['calibration_gain_error_factor'] = 1.0
        sensor_no_misalign_effect.config['calibration_gain_drift_percent_per_hour'] = 0.0
        # ... (neutralize other cal effects as above if they were not part of specific_params)

        result_spectrum_no_misalign = sensor_no_misalign_effect._apply_calibration_errors(reading_input_to_calibration.copy(), mock_env_state_for_cal)['spectrum']
        
        self.assertAlmostEqual(result_spectrum_no_misalign["fundamental"], initial_spectrum_values["fundamental"], msg="Fundamental component changed when misalignment effect was disabled.")
        self.assertAlmostEqual(result_spectrum_no_misalign["harmonics"]["3th"], initial_spectrum_values["harmonics"]["3th"], msg="3rd harmonic changed when misalignment effect was disabled.")

if __name__ == '__main__':
    unittest.main()