import unittest
from unittest.mock import MagicMock, patch

from envirosense.simulation_engine.sensors.environmental import VOCArraySensor
from envirosense.simulation_engine.environment.mock_utils import create_mock_environment_state
from envirosense.simulation_engine.environment.state import Environment3DState # For type hinting

class TestVOCArraySensor(unittest.TestCase):

    def test_get_ground_truth_success(self):
        """Test VOCArraySensor.get_ground_truth with a responsive mock environment."""
        
        # Define specific parameters for this sensor instance
        sensor_id = "voc_test_001"
        position = (1.0, 2.0, 3.0)
        sampling_vol = {"shape": "cube", "size_m": 0.1}
        channels = ["CO", "NO2", "SO2"]
        specific_params = {
            "channels": channels,
            "channel_units": "ppb"
        }

        sensor = VOCArraySensor(
            sensor_id=sensor_id,
            position_3d=position,
            sampling_volume=sampling_vol,
            specific_params=specific_params,
            ground_truth_capability=True # Explicitly set for clarity
        )

        # Create a mock environment that will return specific values for these chemicals
        mock_chem_concentrations = {"CO": 100.555, "NO2": 50.222, "SO2": 10.777, "O3": 5.0} # O3 not in channels
        
        # Mock the get_chemical_concentration method of the Environment3DState instance
        # that will be passed to the sensor.
        mock_env_state = create_mock_environment_state(
            chemical_concentrations=mock_chem_concentrations
        )
        
        # Override the mock_env_state's method to check call arguments if needed
        # For this test, create_mock_environment_state already sets up a callable mock.
        # We can also add a spy if we want to assert call parameters precisely.
        
        # Spy on the mock_env_state's get_chemical_concentration
        # to verify it's called correctly for each channel.
        # The mock_utils.create_mock_environment_state already replaces the method.
        # We can access it if we want to add assertions on its calls.
        
        # For this test, we'll rely on the output.
        ground_truth_data = sensor.get_ground_truth(mock_env_state)

        self.assertNotIn("error", ground_truth_data)
        self.assertEqual(ground_truth_data["unit"], "ppb")
        self.assertIn("concentrations_ppb", ground_truth_data)
        
        expected_concentrations = {
            "CO": 100.555, # create_mock_environment_state returns the value directly
            "NO2": 50.222,
            "SO2": 10.777
        }
        # The sensor's get_ground_truth rounds to 3 decimal places
        rounded_expected = {k: round(v, 3) for k, v in expected_concentrations.items()}

        self.assertEqual(ground_truth_data["concentrations_ppb"], rounded_expected)

    def test_get_ground_truth_no_capability(self):
        """Test get_ground_truth when ground_truth_capability is False."""
        sensor = VOCArraySensor(
            sensor_id="voc_gt_disabled",
            position_3d=(0,0,0),
            sampling_volume={},
            specific_params={"channels": ["CO"]},
            ground_truth_capability=False 
        )
        mock_env_state = create_mock_environment_state()
        gt_data = sensor.get_ground_truth(mock_env_state)
        self.assertIn("error", gt_data)
        self.assertTrue("not supported" in gt_data["error"].lower())

    def test_get_ground_truth_env_missing_method(self):
        """Test get_ground_truth if environment state lacks the query method."""
        sensor = VOCArraySensor(
            sensor_id="voc_bad_env",
            position_3d=(0,0,0),
            sampling_volume={},
            specific_params={"channels": ["CO"]}
        )
        # Create a very basic mock environment state that doesn't have the method
        class BadEnvState: pass
        bad_env = BadEnvState()
        
        # Patch print to suppress the warning during this test
        with patch('builtins.print') as mock_print:
            gt_data = sensor.get_ground_truth(bad_env)
            self.assertIn("error", gt_data)
            self.assertTrue("does not support chemical concentration queries" in gt_data["error"])
            mock_print.assert_any_call(f"Warning: environment_3d_state for VOCArraySensor {sensor.sensor_id} lacks 'get_chemical_concentration' method.")

    def test_get_ground_truth_env_method_raises_exception(self):
        """Test get_ground_truth if environment's query method raises an exception."""
        sensor = VOCArraySensor(
            sensor_id="voc_env_exception",
            position_3d=(0,0,0),
            sampling_volume={},
            specific_params={"channels": ["CO"]}
        )
        mock_env_state = create_mock_environment_state()
        
        # Make the mocked get_chemical_concentration raise an error
        def raiser(chemical_id, position, sampling_volume):
            raise RuntimeError("Simulated environment query failure")
        mock_env_state.get_chemical_concentration = raiser
        
        with patch('builtins.print') as mock_print:
            gt_data = sensor.get_ground_truth(mock_env_state)
            self.assertIn("error", gt_data)
            self.assertTrue("Failed to get chemical concentrations" in gt_data["error"])
            self.assertTrue("Simulated environment query failure" in gt_data["error"])
            mock_print.assert_any_call(f"Error querying chemical concentrations for {sensor.sensor_id}: Simulated environment query failure")

    def test_sample_calls_get_ground_truth_and_apply_imperfections(self):
        """Test that sample() calls get_ground_truth and apply_imperfections."""
        sensor = VOCArraySensor(
            sensor_id="voc_sample_flow",
            position_3d=(0,0,0),
            sampling_volume={},
            specific_params={"channels": ["CO"]}
        )
        mock_env_state = create_mock_environment_state(chemical_concentrations={"CO": 10.0})
        
        # Mock the sub-methods
        sensor.get_ground_truth = MagicMock(return_value={"concentrations_ppb": {"CO": 10.0}, "unit": "ppb"})
        sensor.apply_imperfections = MagicMock(side_effect=lambda x: x) # Just return input for this test

        result = sensor.sample(mock_env_state)

        sensor.get_ground_truth.assert_called_once_with(mock_env_state)
        sensor.apply_imperfections.assert_called_once_with({"concentrations_ppb": {"CO": 10.0}, "unit": "ppb"})
        self.assertEqual(result, {"concentrations_ppb": {"CO": 10.0}, "unit": "ppb"})

    def test_sample_propagates_error_from_get_ground_truth(self):
        sensor = VOCArraySensor(
            sensor_id="voc_sample_gt_error",
            position_3d=(0,0,0),
            sampling_volume={},
            specific_params={"channels": ["CO"]}
        )
        mock_env_state = create_mock_environment_state()
        
        error_response = {"error": "GT failed"}
        sensor.get_ground_truth = MagicMock(return_value=error_response)
        sensor.apply_imperfections = MagicMock() # Should not be called

        result = sensor.sample(mock_env_state)
        self.assertEqual(result, error_response)
        sensor.apply_imperfections.assert_not_called()

    def test_gaussian_noise_application(self):
        """Test Gaussian noise application in VOCArraySensor."""
        channels = ["CO", "NO2"]
        sensor_with_noise = VOCArraySensor(
            sensor_id="voc_noise_test", position_3d=(0,0,0), sampling_volume={},
            specific_params={"channels": channels, "response_time_alpha": 1.0}, # Instant response for easier noise test
            noise_characteristics={
                "type": "gaussian",
                "mean": 0.0, # Global mean
                "stddev": 1.0, # Global stddev
                "CO": {"stddev": 0.5}, # Channel-specific stddev for CO
                "NO2": {"mean": 0.1, "stddev": 0.2} # Channel-specific mean and stddev for NO2
            },
            ground_truth_capability=True
        )

        # Mock environment returning fixed true values
        true_concentrations = {"CO": 100.0, "NO2": 50.0}
        mock_env_state = create_mock_environment_state(chemical_concentrations=true_concentrations)

        # Run sample multiple times to see noise effect (average should be around true + mean)
        num_samples = 1000
        co_readings = []
        no2_readings = []

        for _ in range(num_samples):
            sample_data = sensor_with_noise.sample(mock_env_state)
            co_readings.append(sample_data["concentrations_ppb"]["CO"])
            no2_readings.append(sample_data["concentrations_ppb"]["NO2"])
            # Check non-negativity
            self.assertGreaterEqual(sample_data["concentrations_ppb"]["CO"], 0.0)
            self.assertGreaterEqual(sample_data["concentrations_ppb"]["NO2"], 0.0)

        # Check if mean of noisy readings is close to (true_value + noise_mean)
        # CO: true=100, noise_mean=0.0 (global)
        avg_co = sum(co_readings) / num_samples
        self.assertAlmostEqual(avg_co, 100.0, delta=0.5) # Delta allows for statistical variation

        # NO2: true=50, noise_mean=0.1 (channel-specific)
        avg_no2 = sum(no2_readings) / num_samples
        self.assertAlmostEqual(avg_no2, 50.1, delta=0.2)

        # Check if stddev of noisy readings is roughly as expected (harder to test precisely)
        # This is a basic check; more rigorous statistical tests could be used.
        stddev_co = (sum([(x - avg_co) ** 2 for x in co_readings]) / num_samples) ** 0.5
        self.assertAlmostEqual(stddev_co, 0.5, delta=0.15) # CO specific stddev

        stddev_no2 = (sum([(x - avg_no2) ** 2 for x in no2_readings]) / num_samples) ** 0.5
        self.assertAlmostEqual(stddev_no2, 0.2, delta=0.1) # NO2 specific stddev

    def test_no_noise_applied(self):
        """Test that no noise is applied if characteristics are missing or stddev is zero."""
        channels = ["CO"]
        sensor_no_noise_cfg = VOCArraySensor(
            "voc_no_noise1", (0,0,0), {}, {"channels": channels, "response_time_alpha": 1.0},
            noise_characteristics=None # No noise config
        )
        sensor_zero_stddev = VOCArraySensor(
            "voc_no_noise2", (0,0,0), {}, {"channels": channels, "response_time_alpha": 1.0},
            noise_characteristics={"type": "gaussian", "mean": 0, "stddev": 0.0} # Zero stddev
        )

        mock_env_state = create_mock_environment_state(chemical_concentrations={"CO": 75.0})

        sample1 = sensor_no_noise_cfg.sample(mock_env_state)
        self.assertAlmostEqual(sample1["concentrations_ppb"]["CO"], 75.0)

        sample2 = sensor_zero_stddev.sample(mock_env_state)
        self.assertAlmostEqual(sample2["concentrations_ppb"]["CO"], 75.0)

    def test_response_time_ema_filter(self):
        """Test the EMA filter for response time modeling in VOCArraySensor."""
        channels = ["CO", "NO2"]
        sensor_fast_response = VOCArraySensor(
            sensor_id="voc_ema_fast", position_3d=(0,0,0), sampling_volume={},
            specific_params={"channels": channels, "response_time_alpha": 0.9}, # Fast response
            ground_truth_capability=True
        )
        sensor_slow_response = VOCArraySensor(
            sensor_id="voc_ema_slow", position_3d=(0,0,0), sampling_volume={},
            specific_params={"channels": channels, "response_time_alpha": 0.2}, # Slow response
            ground_truth_capability=True
        )

        # Mock environment that returns consistent true values
        mock_env_state = create_mock_environment_state(
            chemical_concentrations={"CO": 100.0, "NO2": 50.0}
        )

        # --- Test First Sample (Initialization of EMA) ---
        # Fast sensor
        sample1_fast = sensor_fast_response.sample(mock_env_state)
        self.assertAlmostEqual(sample1_fast["concentrations_ppb"]["CO"], 100.0)
        self.assertAlmostEqual(sample1_fast["concentrations_ppb"]["NO2"], 50.0)
        
        # Slow sensor
        sample1_slow = sensor_slow_response.sample(mock_env_state)
        self.assertAlmostEqual(sample1_slow["concentrations_ppb"]["CO"], 100.0)
        self.assertAlmostEqual(sample1_slow["concentrations_ppb"]["NO2"], 50.0)

        # --- Test Second Sample (EMA calculation) ---
        # True values remain the same, so EMA should move towards them
        # Fast sensor: EMA_new = (100 * 0.9) + (100 * 0.1) = 90 + 10 = 100
        sample2_fast = sensor_fast_response.sample(mock_env_state)
        self.assertAlmostEqual(sample2_fast["concentrations_ppb"]["CO"], 100.0)
        self.assertAlmostEqual(sample2_fast["concentrations_ppb"]["NO2"], 50.0)

        # Slow sensor: EMA_new = (100 * 0.2) + (100 * 0.8) = 20 + 80 = 100
        # Oh, if true value is same as previous EMA, EMA stays same. Let's change true value.
        mock_env_state_changed = create_mock_environment_state(
            chemical_concentrations={"CO": 200.0, "NO2": 100.0} # New true values
        )

        # Fast sensor with changed true value:
        # Prev EMA for CO was 100.0. New true is 200.0. Alpha = 0.9
        # EMA_new_co = (200.0 * 0.9) + (100.0 * 0.1) = 180.0 + 10.0 = 190.0
        # Prev EMA for NO2 was 50.0. New true is 100.0. Alpha = 0.9
        # EMA_new_no2 = (100.0 * 0.9) + (50.0 * 0.1) = 90.0 + 5.0 = 95.0
        sample2_fast_changed = sensor_fast_response.sample(mock_env_state_changed)
        self.assertAlmostEqual(sample2_fast_changed["concentrations_ppb"]["CO"], 190.0)
        self.assertAlmostEqual(sample2_fast_changed["concentrations_ppb"]["NO2"], 95.0)
        
        # Slow sensor with changed true value:
        # Prev EMA for CO was 100.0. New true is 200.0. Alpha = 0.2
        # EMA_new_co = (200.0 * 0.2) + (100.0 * 0.8) = 40.0 + 80.0 = 120.0
        # Prev EMA for NO2 was 50.0. New true is 100.0. Alpha = 0.2
        # EMA_new_no2 = (100.0 * 0.2) + (50.0 * 0.8) = 20.0 + 40.0 = 60.0
        sample2_slow_changed = sensor_slow_response.sample(mock_env_state_changed)
        self.assertAlmostEqual(sample2_slow_changed["concentrations_ppb"]["CO"], 120.0)
        self.assertAlmostEqual(sample2_slow_changed["concentrations_ppb"]["NO2"], 60.0)

        # --- Test Third Sample (Further EMA convergence) ---
        # Slow sensor, true values still 200 (CO) and 100 (NO2)
        # Prev EMA for CO was 120.0. Alpha = 0.2
        # EMA_new_co = (200.0 * 0.2) + (120.0 * 0.8) = 40.0 + 96.0 = 136.0
        # Prev EMA for NO2 was 60.0. Alpha = 0.2
        # EMA_new_no2 = (100.0 * 0.2) + (60.0 * 0.8) = 20.0 + 48.0 = 68.0
        sample3_slow_changed = sensor_slow_response.sample(mock_env_state_changed)
        self.assertAlmostEqual(sample3_slow_changed["concentrations_ppb"]["CO"], 136.0)
        self.assertAlmostEqual(sample3_slow_changed["concentrations_ppb"]["NO2"], 68.0)

    def test_response_time_alpha_validation(self):
        """Test validation of response_time_alpha."""
        with self.assertRaises(ValueError):
            VOCArraySensor("voc_alpha_zero", (0,0,0), {}, {"response_time_alpha": 0.0})
        with self.assertRaises(ValueError):
            VOCArraySensor("voc_alpha_high", (0,0,0), {}, {"response_time_alpha": 1.1})
        try: # Should not raise
            VOCArraySensor("voc_alpha_valid_edge", (0,0,0), {}, {"response_time_alpha": 0.00001})
            VOCArraySensor("voc_alpha_valid_one", (0,0,0), {}, {"response_time_alpha": 1.0})
        except ValueError:
            self.fail("Valid response_time_alpha raised ValueError unexpectedly.")

    def test_time_based_drift_application(self):
        """Test time-based drift application in VOCArraySensor."""
        channels = ["CO", "NO2"]
        drift_params_config = {
            "baseline_drift_ppb_per_hour": {"CO": 1.0, "NO2": -0.5},
            "sensitivity_drift_percent_per_hour": {"CO": 0.1, "NO2": -0.2} # 0.1% and -0.2%
        }
        # Note: drift_parameters is a kwarg to BaseSensor, accessed via self.drift_parameters
        sensor_with_drift = VOCArraySensor(
            sensor_id="voc_drift_test", position_3d=(0,0,0), sampling_volume={},
            specific_params={"channels": channels, "response_time_alpha": 1.0}, # Instant response
            drift_parameters=drift_params_config,
            ground_truth_capability=True
        )

        # Initial true values
        true_co = 100.0
        true_no2 = 50.0
        
        # --- Test at T=0 hours ---
        env_state_t0 = create_mock_environment_state(
            simulation_time_seconds=0.0,
            chemical_concentrations={"CO": true_co, "NO2": true_no2}
        )
        # For drift test, ensure no noise is added by default from mock or sensor
        sensor_with_drift.noise_characteristics = {} # Disable noise for this specific test

        sample_t0 = sensor_with_drift.sample(env_state_t0)
        self.assertAlmostEqual(sample_t0["concentrations_ppb"]["CO"], true_co)
        self.assertAlmostEqual(sample_t0["concentrations_ppb"]["NO2"], true_no2)

        # --- Test at T=1 hour ---
        env_state_t1 = create_mock_environment_state(
            simulation_time_seconds=3600.0, # 1 hour
            chemical_concentrations={"CO": true_co, "NO2": true_no2}
        )
        sample_t1 = sensor_with_drift.sample(env_state_t1)
        
        # CO: baseline_drift = 1.0 * 1 = 1.0 ppb
        #     sensitivity_drift_factor = (0.1 / 100) * 1 = 0.001
        #     new_sensitivity = 1.0 + 0.001 = 1.001
        #     expected_co = (true_co) * 1.001 + 1.0 = 100.0 * 1.001 + 1.0 = 100.1 + 1.0 = 101.1
        self.assertAlmostEqual(sample_t1["concentrations_ppb"]["CO"], 101.1, places=3)

        # NO2: baseline_drift = -0.5 * 1 = -0.5 ppb
        #      sensitivity_drift_factor = (-0.2 / 100) * 1 = -0.002
        #      new_sensitivity = 1.0 - 0.002 = 0.998
        #      expected_no2 = (true_no2) * 0.998 - 0.5 = 50.0 * 0.998 - 0.5 = 49.9 - 0.5 = 49.4
        self.assertAlmostEqual(sample_t1["concentrations_ppb"]["NO2"], 49.4, places=3)

        # --- Test at T=10 hours ---
        env_state_t10 = create_mock_environment_state(
            simulation_time_seconds=36000.0, # 10 hours
            chemical_concentrations={"CO": true_co, "NO2": true_no2}
        )
        sample_t10 = sensor_with_drift.sample(env_state_t10)

        # CO: baseline_drift = 1.0 * 10 = 10.0 ppb
        #     sensitivity_drift_factor = (0.1 / 100) * 10 = 0.01
        #     new_sensitivity = 1.0 + 0.01 = 1.01
        #     expected_co = (true_co) * 1.01 + 10.0 = 100.0 * 1.01 + 10.0 = 101.0 + 10.0 = 111.0
        self.assertAlmostEqual(sample_t10["concentrations_ppb"]["CO"], 111.0, places=3)

        # NO2: baseline_drift = -0.5 * 10 = -5.0 ppb
        #      sensitivity_drift_factor = (-0.2 / 100) * 10 = -0.02
        #      new_sensitivity = 1.0 - 0.02 = 0.98
        #      expected_no2 = (true_no2) * 0.98 - 5.0 = 50.0 * 0.98 - 5.0 = 49.0 - 5.0 = 44.0
        self.assertAlmostEqual(sample_t10["concentrations_ppb"]["NO2"], 44.0, places=3)

    def test_drift_no_params_or_zero_rate(self):
        """Test drift behavior when parameters are missing or rates are zero."""
        channels = ["CO"]
        sensor_no_drift_params = VOCArraySensor(
            "voc_no_drift", (0,0,0), {}, {"channels": channels, "response_time_alpha": 1.0},
            drift_parameters=None # No drift params
        )
        sensor_zero_drift_rate = VOCArraySensor(
            "voc_zero_drift", (0,0,0), {}, {"channels": channels, "response_time_alpha": 1.0},
            drift_parameters={
                "baseline_drift_ppb_per_hour": {"CO": 0.0},
                "sensitivity_drift_percent_per_hour": {"CO": 0.0}
            }
        )
        true_co = 100.0
        env_state = create_mock_environment_state(
            simulation_time_seconds=100000.0, # Long time
            chemical_concentrations={"CO": true_co}
        )
        sensor_no_drift_params.noise_characteristics = {} # Disable noise
        sensor_zero_drift_rate.noise_characteristics = {} # Disable noise
        
        sample1 = sensor_no_drift_params.sample(env_state)
        self.assertAlmostEqual(sample1["concentrations_ppb"]["CO"], true_co)

        sample2 = sensor_zero_drift_rate.sample(env_state)
        self.assertAlmostEqual(sample2["concentrations_ppb"]["CO"], true_co)

    def test_drift_env_missing_time(self):
        """Test drift behavior if environment_3d_state lacks simulation_time_seconds."""
        sensor_with_drift = VOCArraySensor(
            "voc_drift_no_time", (0,0,0), {}, {"channels": ["CO"], "response_time_alpha": 1.0},
            drift_parameters={"baseline_drift_ppb_per_hour": {"CO": 1.0}}
        )
        sensor_with_drift.noise_characteristics = {} # Disable noise
        true_co = 100.0
        
        # Create a mock env state that doesn't have simulation_time_seconds
        class BasicEnvState: # Minimal state for this test
            def get_chemical_concentration(self, chemical_id, position, sampling_volume):
                return {"CO": true_co}.get(chemical_id, 0.0)
        
        basic_env_state = BasicEnvState()

        with patch('builtins.print') as mock_print:
            sample = sensor_with_drift.sample(basic_env_state)
            # Value should be unchanged as drift is skipped
            self.assertAlmostEqual(sample["concentrations_ppb"]["CO"], true_co)
            mock_print.assert_any_call(f"Warning: Drift parameters exist for {sensor_with_drift.sensor_id} but environment_3d_state lacks 'simulation_time_seconds'. Skipping drift.")

    def test_calibration_artifacts_application(self):
        """Test calibration artifacts (offset and gain) in VOCArraySensor."""
        channels = ["CO", "NO2"]
        cal_artifacts_config = {
            "offset_ppb": {"CO": 2.0, "NO2": -1.0},
            "gain_factor": {"CO": 1.1, "NO2": 0.95}
        }
        sensor_with_cal_issues = VOCArraySensor(
            sensor_id="voc_cal_test", position_3d=(0,0,0), sampling_volume={},
            specific_params={"channels": channels, "response_time_alpha": 1.0}, # Instant response
            drift_parameters={}, # No drift for this test
            noise_characteristics={}, # No noise for this test
            calibration_artifacts=cal_artifacts_config, # Passed to BaseSensor
            ground_truth_capability=True
        )

        # True values (these would be after EMA, noise, drift if they were active)
        # For this test, we assume the value going into calibration stage is known.
        # Let's simulate that the value after EMA/Noise/Drift (but before cal) is:
        value_before_cal_co = 100.0
        value_before_cal_no2 = 50.0

        # To test calibration in isolation, we need to control the input to its stage.
        # The `apply_imperfections` method applies EMA, then noise, then drift, then calibration.
        # So, we need to ensure EMA results in our `value_before_cal`, and noise/drift are neutral.
        
        # We'll mock get_ground_truth to return these `value_before_cal` values,
        # and ensure other imperfections are off.
        
        # The sensor's apply_imperfections will first do EMA.
        # Since alpha=1 and we'll set _first_sample_taken=False before each "effective" sample,
        # the EMA output will be the true_value from get_ground_truth.
        
        def mock_gt_for_cal_test(environment_3d_state):
            return {"concentrations_ppb": {"CO": value_before_cal_co, "NO2": value_before_cal_no2}, "unit": "ppb"}

        sensor_with_cal_issues.get_ground_truth = mock_gt_for_cal_test
        
        # --- Test Calibration ---
        sensor_with_cal_issues._first_sample_taken = False # Ensure EMA initializes to GT
        sample_cal = sensor_with_cal_issues.sample(None) # Env state not used by GT mock here

        # CO: value_after_ema_noise_drift = 100.0
        #     calibrated_co = (100.0 * 1.1) + 2.0 = 110.0 + 2.0 = 112.0
        self.assertAlmostEqual(sample_cal["concentrations_ppb"]["CO"], 112.0, places=3)

        # NO2: value_after_ema_noise_drift = 50.0
        #      calibrated_no2 = (50.0 * 0.95) - 1.0 = 47.5 - 1.0 = 46.5
        self.assertAlmostEqual(sample_cal["concentrations_ppb"]["NO2"], 46.5, places=3)

    def test_calibration_artifacts_no_params(self):
        """Test calibration behavior when no artifact parameters are provided."""
        channels = ["CO"]
        sensor_no_cal_issues = VOCArraySensor(
            "voc_no_cal_issues", (0,0,0), {},
            specific_params={"channels": channels, "response_time_alpha": 1.0},
            drift_parameters={}, noise_characteristics={}, calibration_artifacts=None
        )
        value_before_cal_co = 100.0
        def mock_gt(env_state): return {"concentrations_ppb": {"CO": value_before_cal_co}, "unit": "ppb"}
        sensor_no_cal_issues.get_ground_truth = mock_gt
        sensor_no_cal_issues._first_sample_taken = False

        sample = sensor_no_cal_issues.sample(None)
        self.assertAlmostEqual(sample["concentrations_ppb"]["CO"], value_before_cal_co)

    def test_calibration_artifacts_neutral_params(self):
        """Test calibration with neutral artifact parameters (0 offset, 1.0 gain)."""
        channels = ["CO"]
        neutral_cal_artifacts = {
            "offset_ppb": {"CO": 0.0},
            "gain_factor": {"CO": 1.0}
        }
        sensor_neutral_cal = VOCArraySensor(
            "voc_neutral_cal", (0,0,0), {},
            specific_params={"channels": channels, "response_time_alpha": 1.0},
            drift_parameters={}, noise_characteristics={}, calibration_artifacts=neutral_cal_artifacts
        )
        value_before_cal_co = 100.0
        def mock_gt(env_state): return {"concentrations_ppb": {"CO": value_before_cal_co}, "unit": "ppb"}
        sensor_neutral_cal.get_ground_truth = mock_gt
        sensor_neutral_cal._first_sample_taken = False
        
        sample = sensor_neutral_cal.sample(None)
        self.assertAlmostEqual(sample["concentrations_ppb"]["CO"], value_before_cal_co)

    def test_environmental_temp_compensation(self):
        """Test temperature compensation for VOCArraySensor."""
        channels = ["CO", "NO2"]
        env_comp_params = {
            "temperature": {
                "reference_temp_c": 25.0,
                "offset_ppb_per_celsius": {"CO": 0.5, "NO2": -0.2}
            }
        }
        sensor_with_env_comp = VOCArraySensor(
            sensor_id="voc_env_comp_test", position_3d=(0,0,0), sampling_volume={},
            specific_params={"channels": channels, "response_time_alpha": 1.0}, # Instant response
            drift_parameters={}, noise_characteristics={}, calibration_artifacts={}, # No other imperfections
            environmental_compensation_params=env_comp_params, # Passed to BaseSensor
            ground_truth_capability=True
        )

        # Value before this compensation stage
        value_before_env_comp_co = 100.0
        value_before_env_comp_no2 = 50.0

        def mock_gt_for_env_comp_test(environment_3d_state): # environment_3d_state is passed but not used by this mock
            return {"concentrations_ppb": {"CO": value_before_env_comp_co, "NO2": value_before_env_comp_no2}, "unit": "ppb"}
        
        sensor_with_env_comp.get_ground_truth = mock_gt_for_env_comp_test
        
        # --- Test Case 1: Ambient temp = Reference temp (25 C) ---
        env_state_ref_temp = create_mock_environment_state(default_temp_c=25.0)
        sensor_with_env_comp._first_sample_taken = False # Reset EMA for clean test point
        sample_ref = sensor_with_env_comp.sample(env_state_ref_temp)
        # No compensation should occur
        self.assertAlmostEqual(sample_ref["concentrations_ppb"]["CO"], value_before_env_comp_co, places=3)
        self.assertAlmostEqual(sample_ref["concentrations_ppb"]["NO2"], value_before_env_comp_no2, places=3)

        # --- Test Case 2: Ambient temp > Reference temp (e.g., 35 C, delta = +10 C) ---
        env_state_hot_temp = create_mock_environment_state(default_temp_c=35.0)
        sensor_with_env_comp._first_sample_taken = False # Reset EMA
        sample_hot = sensor_with_env_comp.sample(env_state_hot_temp)
        # CO: 100.0 + (0.5 ppb/C * 10 C) = 100.0 + 5.0 = 105.0
        # NO2: 50.0 + (-0.2 ppb/C * 10 C) = 50.0 - 2.0 = 48.0
        self.assertAlmostEqual(sample_hot["concentrations_ppb"]["CO"], 105.0, places=3)
        self.assertAlmostEqual(sample_hot["concentrations_ppb"]["NO2"], 48.0, places=3)

        # --- Test Case 3: Ambient temp < Reference temp (e.g., 15 C, delta = -10 C) ---
        env_state_cold_temp = create_mock_environment_state(default_temp_c=15.0)
        sensor_with_env_comp._first_sample_taken = False # Reset EMA
        sample_cold = sensor_with_env_comp.sample(env_state_cold_temp)
        # CO: 100.0 + (0.5 ppb/C * -10 C) = 100.0 - 5.0 = 95.0
        # NO2: 50.0 + (-0.2 ppb/C * -10 C) = 50.0 + 2.0 = 52.0
        self.assertAlmostEqual(sample_cold["concentrations_ppb"]["CO"], 95.0, places=3)
        self.assertAlmostEqual(sample_cold["concentrations_ppb"]["NO2"], 52.0, places=3)

    def test_env_comp_no_params_or_missing_temp_method(self):
        """Test env compensation when params are missing or env state lacks temp method."""
        channels = ["CO"]
        sensor_no_params = VOCArraySensor(
            "voc_env_comp_no_param", (0,0,0), {},
            specific_params={"channels": channels, "response_time_alpha": 1.0},
            environmental_compensation_params=None # No params
        )
        sensor_empty_params = VOCArraySensor(
            "voc_env_comp_empty_param", (0,0,0), {},
            specific_params={"channels": channels, "response_time_alpha": 1.0},
            environmental_compensation_params={} # Empty params
        )
        
        value_co = 100.0
        def mock_gt(env_state): return {"concentrations_ppb": {"CO": value_co}, "unit": "ppb"}
        
        for sensor_case in [sensor_no_params, sensor_empty_params]:
            sensor_case.get_ground_truth = mock_gt
            sensor_case._first_sample_taken = False
            sensor_case.noise_characteristics={} # ensure no other effects
            sensor_case.drift_parameters={}
            sensor_case.calibration_artifacts={}


        env_state_with_temp = create_mock_environment_state(default_temp_c=30.0)
        
        sample1 = sensor_no_params.sample(env_state_with_temp)
        self.assertAlmostEqual(sample1["concentrations_ppb"]["CO"], value_co) # Should be unchanged

        sample2 = sensor_empty_params.sample(env_state_with_temp)
        self.assertAlmostEqual(sample2["concentrations_ppb"]["CO"], value_co) # Should be unchanged

        # Test with env state missing get_temperature_celsius
        sensor_valid_params_bad_env = VOCArraySensor(
            "voc_env_comp_bad_env", (0,0,0), {},
            specific_params={"channels": channels, "response_time_alpha": 1.0},
            environmental_compensation_params={"temperature": {"reference_temp_c": 25.0, "offset_ppb_per_celsius": {"CO": 0.5}}}
        )
        sensor_valid_params_bad_env.get_ground_truth = mock_gt
        sensor_valid_params_bad_env._first_sample_taken = False
        sensor_valid_params_bad_env.noise_characteristics={}
        sensor_valid_params_bad_env.drift_parameters={}
        sensor_valid_params_bad_env.calibration_artifacts={}

        
        class BasicEnvStateNoTemp: # Lacks get_temperature_celsius
             # Add other necessary methods if VOCArraySensor's get_ground_truth calls them
             def get_chemical_concentration(self, chemical_id, position, sampling_volume): return {"CO":value_co}.get(chemical_id,0.0)

        
        with patch('builtins.print') as mock_print:
            sample3 = sensor_valid_params_bad_env.sample(BasicEnvStateNoTemp())
            self.assertAlmostEqual(sample3["concentrations_ppb"]["CO"], value_co) # Unchanged
            mock_print.assert_any_call(f"Warning: Temp compensation config exists for {sensor_valid_params_bad_env.sensor_id} but env_state lacks 'get_temperature_celsius'. Skipping.")

    def test_cross_sensitivity_application(self):
        """Test cross-sensitivity modeling in VOCArraySensor."""
        channels = ["CO", "NO2", "SO2"]
        cross_sensitivity_config = {
            "CO": {"NO2": 0.1, "SO2": 0.05},  # CO sensor reads 10% of NO2, 5% of SO2
            "NO2": {"CO": 0.02}               # NO2 sensor reads 2% of CO
            # SO2 sensor has no defined cross-sensitivities in this config
        }
        sensor_with_cross_sens = VOCArraySensor(
            sensor_id="voc_cross_sens_test", position_3d=(0,0,0), sampling_volume={},
            specific_params={
                "channels": channels,
                "response_time_alpha": 1.0, # Instant response
                "cross_sensitivity_matrix": cross_sensitivity_config
            },
            drift_parameters={}, noise_characteristics={}, calibration_artifacts={}, environmental_compensation_params={}, # No other imperfections
            ground_truth_capability=True
        )

        # True concentrations of chemicals in the environment
        true_co_conc = 100.0
        true_no2_conc = 50.0
        true_so2_conc = 20.0

        mock_env_state = create_mock_environment_state(
            chemical_concentrations={"CO": true_co_conc, "NO2": true_no2_conc, "SO2": true_so2_conc}
        )
        
        # --- Test Cross-Sensitivity ---
        # Ensure EMA is initialized correctly for this test by controlling _first_sample_taken
        sensor_with_cross_sens._first_sample_taken = False
        sample_data = sensor_with_cross_sens.sample(mock_env_state)
        
        # Expected perceived values (before other imperfections, which are off for this test)
        # CO reading = true_CO + (true_NO2 * 0.1) + (true_SO2 * 0.05)
        #            = 100.0   + (50.0 * 0.1)    + (20.0 * 0.05)
        #            = 100.0   + 5.0             + 1.0 = 106.0
        expected_co_reading = 106.0
        self.assertAlmostEqual(sample_data["concentrations_ppb"]["CO"], expected_co_reading, places=3)

        # NO2 reading = true_NO2 + (true_CO * 0.02)
        #             = 50.0     + (100.0 * 0.02)
        #             = 50.0     + 2.0 = 52.0
        expected_no2_reading = 52.0
        self.assertAlmostEqual(sample_data["concentrations_ppb"]["NO2"], expected_no2_reading, places=3)

        # SO2 reading = true_SO2 (no cross-sensitivity defined for SO2 channel or from other chems to SO2)
        #             = 20.0
        expected_so2_reading = 20.0
        self.assertAlmostEqual(sample_data["concentrations_ppb"]["SO2"], expected_so2_reading, places=3)

    def test_cross_sensitivity_no_matrix_or_empty(self):
        """Test cross-sensitivity when matrix is not provided or empty."""
        channels = ["CO"]
        sensor_no_cs_matrix = VOCArraySensor(
            "voc_no_cs", (0,0,0), {},
            specific_params={"channels": channels, "response_time_alpha": 1.0, "cross_sensitivity_matrix": None},
            noise_characteristics={}, drift_parameters={}, calibration_artifacts={}, environmental_compensation_params={}
        )
        sensor_empty_cs_matrix = VOCArraySensor(
            "voc_empty_cs", (0,0,0), {},
            specific_params={"channels": channels, "response_time_alpha": 1.0, "cross_sensitivity_matrix": {}},
            noise_characteristics={}, drift_parameters={}, calibration_artifacts={}, environmental_compensation_params={}
        )

        true_co_conc = 100.0
        mock_env_state = create_mock_environment_state(chemical_concentrations={"CO": true_co_conc, "NO2": 50.0}) # NO2 present but no CS defined

        for sensor_case in [sensor_no_cs_matrix, sensor_empty_cs_matrix]:
            sensor_case._first_sample_taken = False
            sample_data = sensor_case.sample(mock_env_state)
            self.assertAlmostEqual(sample_data["concentrations_ppb"]["CO"], true_co_conc, places=3)


if __name__ == '__main__':
    unittest.main()