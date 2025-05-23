"""
Unit tests for the ActiveLearningManager class.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock # Added MagicMock for convenience

from typing import Dict, Any, List, Optional

# Modules to be tested
from envirosense.simulation_engine.ml_training.active_learning import ActiveLearningManager
from envirosense.simulation_engine.ml_training.prioritization_strategies import ModelPerformanceData # For type hinting mock data
from envirosense.simulation_engine.ml_training.prioritization_strategies import (
    PrioritizationStrategy, # Base class for typing
    RealTimeSensorPrioritizationStrategy,
    HighFidelitySensorPrioritizationStrategy,
    HeterogeneousSensorPrioritizationStrategy,
    DEFAULT_SENSOR_ID_TO_TYPE_MAPPING # For default map
)
from envirosense.simulation_engine.ml_training.mock_components import (
    MockModelInterface,
    MockScenarioRepository,
    MockMLDataGenerator
)

# Default sensor map for convenience in tests
TEST_SENSOR_ID_TO_TYPE_MAP = DEFAULT_SENSOR_ID_TO_TYPE_MAPPING.copy()


class TestActiveLearningManager(unittest.TestCase):
    """
    Test suite for the ActiveLearningManager.
    """

    def setUp(self):
        """
        Set up common resources for tests.
        This method is called before each test function execution.
        """
        self.mock_data_generator = MockMLDataGenerator()
        self.mock_scenario_repo = MockScenarioRepository()
        self.mock_model_interface = MockModelInterface()
        
        # Example: Using RealTimeSensorPrioritizationStrategy as a default for some tests
        self.mock_prioritization_strategy = RealTimeSensorPrioritizationStrategy(
            sensor_id_to_type_map=TEST_SENSOR_ID_TO_TYPE_MAP
        )

        self.alm = ActiveLearningManager(
            data_generator=self.mock_data_generator,
            scenario_repository=self.mock_scenario_repo,
            model_interface=self.mock_model_interface,
            prioritization_strategy=self.mock_prioritization_strategy,
            sensor_id_to_type_map=TEST_SENSOR_ID_TO_TYPE_MAP
        )
        print(f"TestActiveLearningManager.setUp completed for {self._testMethodName}")


    def tearDown(self):
        """
        Clean up resources after tests.
        This method is called after each test function execution.
        """
        # Reset mocks if they maintain state that could interfere between tests
        self.mock_data_generator.reset_calls()
        self.mock_data_generator.reset_behavior()
        # MockScenarioRepository might need a reset if scenarios are added/modified directly
        # For now, assume it's re-initialized or its state is managed per test.
        print(f"TestActiveLearningManager.tearDown completed for {self._testMethodName}")

    # --- Test Cases from Plan ---

    def test_initialization_default_strategy_and_map(self):
        """
        Test ALM initialization with default sensor map and a provided strategy.
        """
        strategy = RealTimeSensorPrioritizationStrategy() # Uses its own default map initially
        alm = ActiveLearningManager(
            data_generator=self.mock_data_generator,
            scenario_repository=self.mock_scenario_repo,
            model_interface=self.mock_model_interface,
            prioritization_strategy=strategy,
            sensor_id_to_type_map=None # ALM should use its default
        )
        self.assertIsNotNone(alm.sensor_id_to_type_map, "ALM sensor_id_to_type_map should not be None")
        self.assertEqual(alm.sensor_id_to_type_map, DEFAULT_SENSOR_ID_TO_TYPE_MAPPING)
        # Check if strategy's map was updated if it was None
        if hasattr(strategy, 'sensor_id_to_type_map') and strategy.sensor_id_to_type_map is None:
             # This case might not happen if strategy always initializes with default
            pass # Covered by next assertion
        self.assertEqual(strategy.sensor_id_to_type_map, DEFAULT_SENSOR_ID_TO_TYPE_MAPPING, "Strategy map should be updated by ALM if it was None")


    def test_initialization_custom_map_propagation(self):
        """
        Test ALM initialization with a custom sensor map and its propagation.
        """
        custom_map = {"sensorA": "typeX", "sensorB": "typeY"}
        # Mock a strategy that initially has no map or a different one
        # For this test, let's assume the strategy's map is None initially
        # We can achieve this by patching the strategy or using a custom mock strategy
        
        # Use a MagicMock for the strategy in this specific test
        # to precisely control its 'sensor_id_to_type_map' attribute for the test.
        mock_strategy = MagicMock(spec=PrioritizationStrategy)
        mock_strategy.sensor_id_to_type_map = None # Set the attribute to None

        # Verify precondition directly on the mock
        self.assertIsNone(mock_strategy.sensor_id_to_type_map)

        alm = ActiveLearningManager(
            data_generator=self.mock_data_generator,
            scenario_repository=self.mock_scenario_repo,
            model_interface=self.mock_model_interface,
            prioritization_strategy=mock_strategy, # Pass the mock strategy
            sensor_id_to_type_map=custom_map
        )
        self.assertEqual(alm.sensor_id_to_type_map, custom_map)
        # Check that the ALM updated the mock_strategy's map
        self.assertEqual(mock_strategy.sensor_id_to_type_map, custom_map, "Strategy map should be updated by ALM with the custom map")

    def test_get_sensor_type_from_id(self):
        """
        Test the _get_sensor_type_from_id method.
        """
        self.assertEqual(self.alm._get_sensor_type_from_id("U26_Lepton35"), "ThermalCamera")
        self.assertEqual(self.alm._get_sensor_type_from_id("U19_TFSGS"), "VOCSensorArray")
        self.assertIsNone(self.alm._get_sensor_type_from_id("UNKNOWN_SENSOR_ID"))
        self.assertIsNone(self.alm._get_sensor_type_from_id(None))

    def test_identify_weak_spots_no_model_interface(self):
        """
        Test identify_weak_spots when the model_interface is None.
        It should return an empty list and log an error (implicitly tested by print).
        """
        # Temporarily set model_interface to None for this test
        original_model_interface = self.alm.model_interface
        self.alm.model_interface = None # type: ignore
        
        # Providing a dummy ModelPerformanceData, though it shouldn't be used by ALM directly in this case
        dummy_performance_data: ModelPerformanceData = {
            "model_version_evaluated": "v1", 
            "dataset_identifier": "dummy",
            "overall_metrics": {}, "per_class_metrics": {}, # Ensure basic structure
            "uncertain_samples": [], "misclassified_samples": []
        }
        
        # Capture print output to check for error logging
        with patch('builtins.print') as mock_print:
            weak_spots = self.alm.identify_weak_spots(dummy_performance_data)
        
        self.assertEqual(weak_spots, [])
        mock_print.assert_any_call("Error: ModelInterface not available.")
        
        # Restore the original model_interface
        self.alm.model_interface = original_model_interface

    def test_identify_weak_spots_calls_strategy(self):
        """
        Test that identify_weak_spots correctly calls the prioritization strategy
        with the correct arguments.
        """
        mock_performance_data: ModelPerformanceData = {
            "model_version_evaluated": "mock_v1",
            "dataset_identifier": "eval_set_1",
            "overall_metrics": {"accuracy": 0.9},
            "per_class_metrics": {"classA": {"recall": 0.8, "support": 10, "precision": 0.7, "f1_score": 0.75}},
            "uncertain_samples": [{"raw_sample_id": "unc1", "sensor_id": "s1", "uncertainty_score": 0.8}],
            "misclassified_samples": [{"raw_sample_id": "misc1", "sensor_id": "s2", "true_label": "A", "predicted_label": "B"}]
        }
        # self.mock_model_interface.set_mock_performance_data(mock_performance_data) # ALM receives this as an argument

        # Mock the strategy's identify_weaknesses method
        expected_weaknesses = [{"weakness_id": "w1", "type": "high_uncertainty", "priority": 0.9, "details": {}, "sensor_id": "s1"}]
        
        # Replace the ALM's strategy with a MagicMock to track calls
        original_strategy = self.alm.prioritization_strategy
        self.alm.prioritization_strategy = MagicMock(spec=PrioritizationStrategy)
        self.alm.prioritization_strategy.identify_weaknesses.return_value = expected_weaknesses

        target_sensor_id = "s1"
        
        # Call the method under test
        returned_weak_spots = self.alm.identify_weak_spots(mock_performance_data, target_sensor_id=target_sensor_id)

        # Assert that the strategy's method was called once with the correct arguments
        self.alm.prioritization_strategy.identify_weaknesses.assert_called_once_with(
            mock_performance_data,
            target_sensor_id=target_sensor_id
        )
        
        # Assert that the returned value is what the strategy returned
        self.assertEqual(returned_weak_spots, expected_weaknesses)

        # Restore original strategy
        self.alm.prioritization_strategy = original_strategy

    def test_identify_weak_spots_with_different_strategies(self):
        """
        Test identify_weak_spots with different prioritization strategies to ensure
        the ALM correctly uses the injected strategy.
        """
        strategies_to_test = {
            "real_time": RealTimeSensorPrioritizationStrategy(sensor_id_to_type_map=TEST_SENSOR_ID_TO_TYPE_MAP),
            "high_fidelity": HighFidelitySensorPrioritizationStrategy(sensor_id_to_type_map=TEST_SENSOR_ID_TO_TYPE_MAP),
            "heterogeneous": HeterogeneousSensorPrioritizationStrategy(sensor_id_to_type_map=TEST_SENSOR_ID_TO_TYPE_MAP)
        }

        mock_performance_data: ModelPerformanceData = {
            "model_version_evaluated": "mock_v2", "dataset_identifier": "eval_set_2",
            "overall_metrics": {"accuracy": 0.7},
            "per_class_metrics": {
                "classX": {"recall": 0.5, "precision": 0.4, "f1_score": 0.45, "support": 50},
                "classY": {"recall": 0.9, "precision": 0.8, "f1_score": 0.85, "support": 100}
            },
            "uncertain_samples": [
                {"raw_sample_id": "unc_rt", "sensor_id": "U20_SPS30", "uncertainty_score": 0.75, "epistemic_uncertainty_score": 0.6}
            ],
            "misclassified_samples": [
                {"raw_sample_id": "misc_hf", "sensor_id": "U26_Lepton35", "true_label": "classX", "predicted_label": "classY"}
            ]
        }

        for strategy_name, strategy_instance in strategies_to_test.items():
            with self.subTest(strategy_name=strategy_name):
                self.alm.prioritization_strategy = strategy_instance
                
                # Spy on the strategy's identify_weaknesses method
                strategy_instance.identify_weaknesses = MagicMock(wraps=strategy_instance.identify_weaknesses)
                
                # Expected return value from the *actual* strategy logic (can be complex to precompute,
                # so we mainly check it's called and returns *something* plausible based on strategy type)
                # For a more robust test, one might precompute expected outputs for each strategy with this input.
                # Here, we'll just ensure it's called and returns a list.
                
                returned_weak_spots = self.alm.identify_weak_spots(mock_performance_data)
                
                strategy_instance.identify_weaknesses.assert_called_once_with(
                    mock_performance_data,
                    target_sensor_id=None # Default target_sensor_id
                )
                self.assertIsInstance(returned_weak_spots, list, f"Strategy {strategy_name} should return a list.")
                # Optionally, add more specific assertions about the content if feasible
                # For example, check if priorities are within [0,1]
                for spot in returned_weak_spots:
                    self.assertTrue(0.0 <= spot.get("priority", 0.0) <= 1.0)
# --- Tests for generate_targeted_samples ---

    def test_generate_targeted_samples_no_weak_spots(self):
        """
        Test generate_targeted_samples with an empty list of weak spots.
        No samples should be generated, and data generator should not be called.
        """
        with patch('builtins.print') as mock_print: # To check for "No weak spots provided"
            result = self.alm.generate_targeted_samples(weak_spots=[])
        
        self.assertIsNone(result)
        self.assertEqual(len(self.mock_data_generator.generate_training_dataset_calls), 0)
        self.assertEqual(len(self.mock_data_generator.export_data_calls), 0)
        mock_print.assert_any_call("No weak spots provided, no targeted samples will be generated.")

    def test_generate_targeted_samples_no_data_generator(self):
        """
        Test generate_targeted_samples when data_generator is None.
        """
        original_dg = self.alm.data_generator
        self.alm.data_generator = None # type: ignore
        weak_spots = [{"weakness_id": "w1", "type": "some_type", "details": {}}]
        
        with patch('builtins.print') as mock_print:
            result = self.alm.generate_targeted_samples(weak_spots=weak_spots)
        
        self.assertIsNone(result)
        mock_print.assert_any_call("Error: MLDataGenerator not available.")
        self.alm.data_generator = original_dg # Restore

    def test_generate_targeted_samples_no_scenario_repository(self):
        """
        Test generate_targeted_samples when scenario_repository is None.
        """
        original_sr = self.alm.scenario_repository
        self.alm.scenario_repository = None # type: ignore
        weak_spots = [{"weakness_id": "w1", "type": "some_type", "details": {}}]
        
        with patch('builtins.print') as mock_print:
            result = self.alm.generate_targeted_samples(weak_spots=weak_spots)
            
        self.assertIsNone(result)
        mock_print.assert_any_call("Error: ScenarioRepository not available.")
        self.alm.scenario_repository = original_sr # Restore

    def test_generate_targeted_samples_high_uncertainty_with_original_scenario(self):
        """
        Test targeting a 'high_uncertainty_sample' with an original_scenario_id.
        Should try to create a variation.
        """
        weak_spot = {
            "weakness_id": "unc_spot_1",
            "type": "high_uncertainty_sample",
            "sensor_id": "U26_Lepton35", # ThermalCamera
            "details": {
                "original_scenario_id": "scenario_heat_event",
                "sample_features_summary": {
                    "top_n_features": [{"feature_path": "temp_avg", "raw_value": 85.0}]
                }
            }
        }
        # Mock ScenarioRepository responses
        base_scenario_data = self.mock_scenario_repo.get_scenario_by_id("scenario_heat_event")
        self.mock_scenario_repo.get_scenario_by_id = MagicMock(return_value=base_scenario_data)
        
        variation_scenario_data = {"scenario_definition_id": "scenario_heat_event_alm_var_unc_spot_1", "name": "Variation"}
        self.mock_scenario_repo.create_scenario_variation = MagicMock(return_value=variation_scenario_data)

        # Mock DataGenerator response
        self.mock_data_generator.set_generate_training_dataset_return_values([
            [{"sample_id": "new_sample_1"}] # Mock generated samples
        ])
        self.mock_data_generator.set_export_data_return_values(["path/to/exported_data.avro"])

        result = self.alm.generate_targeted_samples(weak_spots=[weak_spot], num_samples_per_spot_type=10)

        self.assertIsNotNone(result)
        self.mock_scenario_repo.get_scenario_by_id.assert_called_once_with("scenario_heat_event")
        self.mock_scenario_repo.create_scenario_variation.assert_called_once()
        # Check some args of create_scenario_variation
        args, kwargs = self.mock_scenario_repo.create_scenario_variation.call_args
        self.assertEqual(kwargs['base_scenario'], base_scenario_data)
        self.assertIn("alm_triggering_weak_spot_id", kwargs['param_modifications'])
        self.assertEqual(kwargs['param_modifications']['alm_triggering_weak_spot_id'], "unc_spot_1")
        
        self.assertEqual(len(self.mock_data_generator.generate_training_dataset_calls), 1)
        call_args = self.mock_data_generator.generate_training_dataset_calls[0]
        self.assertEqual(len(call_args["scenarios"]), 1)
        self.assertEqual(call_args["scenarios"][0], variation_scenario_data)
        self.assertEqual(call_args["samples_per_scenario"], 10)
        
        self.assertEqual(len(self.mock_data_generator.export_data_calls), 1)
        self.assertEqual(self.mock_data_generator.export_data_calls[0]["data"], [{"sample_id": "new_sample_1"}])

    def test_generate_targeted_samples_high_uncertainty_no_original_scenario_crafts_new(self):
        """
        Test targeting 'high_uncertainty_sample' without original_scenario_id.
        Should try to craft a new scenario from features.
        """
        weak_spot = {
            "weakness_id": "unc_spot_2",
            "type": "high_uncertainty_sample",
            "sensor_id": "U19_TFSGS", # VOCSensorArray
            "details": {
                "original_scenario_id": None, # Key part of this test
                "sample_features_summary": {
                    "top_n_features": [{"feature_path": "voc_pattern_specific", "raw_value": "pattern_data_xyz"}]
                }
            }
        }
        # Mock ScenarioRepository responses
        self.mock_scenario_repo.get_scenario_by_id = MagicMock(return_value=None) # Ensure it's not found
        
        crafted_scenario_data = {"scenario_definition_id": "alm_crafted_unc_spot_2", "name": "Crafted for VOC"}
        self.mock_scenario_repo.craft_scenario_from_features = MagicMock(return_value=crafted_scenario_data)

        self.mock_data_generator.set_generate_training_dataset_return_values([
            [{"sample_id": "crafted_sample_1"}]
        ])
        self.mock_data_generator.set_export_data_return_values(["path/to/crafted_export.avro"])

        result = self.alm.generate_targeted_samples(weak_spots=[weak_spot], num_samples_per_spot_type=5)

        self.assertIsNotNone(result)
        self.mock_scenario_repo.craft_scenario_from_features.assert_called_once()
        args, kwargs = self.mock_scenario_repo.craft_scenario_from_features.call_args
        self.assertEqual(kwargs['features_summary'], weak_spot['details']['sample_features_summary'])
        self.assertEqual(kwargs['sensor_type'], "VOCSensorArray") # Derived from sensor_id

        self.assertEqual(len(self.mock_data_generator.generate_training_dataset_calls), 1)
        call_args_dg = self.mock_data_generator.generate_training_dataset_calls[0]
        self.assertEqual(call_args_dg["scenarios"][0], crafted_scenario_data)
        self.assertEqual(call_args_dg["samples_per_scenario"], 5)

    def test_generate_targeted_samples_low_recall_class(self):
        """
        Test targeting a 'low_recall_class'.
        Should try to get existing scenarios for that class.
        """
        weak_spot = {
            "weakness_id": "recall_spot_1",
            "type": "low_recall_class",
            "sensor_id": "U20_SPS30", # ParticulateMatterSensor
            "details": {"class_name": "smog_event_type_A"}
        }
        # Mock ScenarioRepository responses
        scenarios_for_class_data = [
            {"scenario_definition_id": "smog_scenario_1", "class_label_target": "smog_event_type_A"},
            {"scenario_definition_id": "smog_scenario_2", "class_label_target": "smog_event_type_A"}
        ]
        self.mock_scenario_repo.get_scenarios_by_class_label = MagicMock(return_value=scenarios_for_class_data)

        self.mock_data_generator.set_generate_training_dataset_return_values([
            [{"sample_id": "recall_sample_1"}, {"sample_id": "recall_sample_2"}] # Two samples per scenario in this mock
        ])
        self.mock_data_generator.set_export_data_return_values(["path/to/recall_export.avro"])

        result = self.alm.generate_targeted_samples(weak_spots=[weak_spot], num_samples_per_spot_type=2) # 2 samples per scenario

        self.assertIsNotNone(result)
        self.mock_scenario_repo.get_scenarios_by_class_label.assert_called_once_with(
            class_label="smog_event_type_A",
            sensor_type="ParticulateMatterSensor",
            num_to_get=2 # Default num_to_get in ALM for this path
        )
        
        self.assertEqual(len(self.mock_data_generator.generate_training_dataset_calls), 1)
        call_args_dg = self.mock_data_generator.generate_training_dataset_calls[0]
        self.assertEqual(len(call_args_dg["scenarios"]), 2) # Two scenarios found
        self.assertEqual(call_args_dg["scenarios"], scenarios_for_class_data)
        self.assertEqual(call_args_dg["samples_per_scenario"], 2) # As passed to ALM

    def test_generate_targeted_samples_no_scenario_found_uses_default_exploration(self):
        """
        Test when no specific scenario can be created/found, it falls back to default exploration.
        """
        weak_spot = { # A spot that won't lead to variation or crafting easily
            "weakness_id": "fallback_spot_1",
            "type": "high_uncertainty_sample",
            "sensor_id": "U21_SHT85", # TempHumiditySensor
            "details": {"original_scenario_id": None, "sample_features_summary": None}
        }
        # Mock ScenarioRepository to return no useful scenarios initially
        self.mock_scenario_repo.get_scenario_by_id = MagicMock(return_value=None)
        self.mock_scenario_repo.craft_scenario_from_features = MagicMock(return_value=None)
        
        default_exploration_scenario = {"scenario_definition_id": "alm_explore_fallback_spot_1", "category": "EXPLORATION"}
        self.mock_scenario_repo.get_default_exploration_scenario = MagicMock(return_value=default_exploration_scenario)

        self.mock_data_generator.set_generate_training_dataset_return_values([
            [{"sample_id": "explore_sample_1"}]
        ])
        self.mock_data_generator.set_export_data_return_values(["path/to/explore_export.avro"])

        result = self.alm.generate_targeted_samples(weak_spots=[weak_spot], num_samples_per_spot_type=3)

        self.assertIsNotNone(result)
        self.mock_scenario_repo.get_default_exploration_scenario.assert_called_once_with(
            scenario_id=f"alm_explore_{weak_spot['weakness_id']}",
            sensor_type="TempHumiditySensor"
        )
        self.assertEqual(len(self.mock_data_generator.generate_training_dataset_calls), 1)
        call_args_dg = self.mock_data_generator.generate_training_dataset_calls[0]
        self.assertEqual(call_args_dg["scenarios"][0], default_exploration_scenario)
        self.assertEqual(call_args_dg["samples_per_scenario"], 3)

    def test_generate_targeted_samples_data_generator_export_failure(self):
        """
        Test when MLDataGenerator._export_data returns None (simulating an export error).
        """
        weak_spot = {
            "weakness_id": "export_fail_spot", "type": "low_recall_class",
            "sensor_id": "U20_SPS30", "details": {"class_name": "rare_event"}
        }
        self.mock_scenario_repo.get_scenarios_by_class_label = MagicMock(return_value=[{"id": "s1"}])
        self.mock_data_generator.set_generate_training_dataset_return_values([ [{"sample_id": "s1_data"}] ])
        
        # Simulate export failure
        self.mock_data_generator.set_export_data_return_values([None]) 

        result = self.alm.generate_targeted_samples(weak_spots=[weak_spot])
        self.assertIsNone(result, "Result should be None if export fails")

    def test_generate_targeted_samples_data_generator_no_export_method_returns_raw_list(self):
        """
        Test when MLDataGenerator does not have _export_data, returns raw list if format is list_of_dicts.
        """
        weak_spot = {
            "weakness_id": "no_export_method_spot", "type": "low_recall_class",
            "sensor_id": "U20_SPS30", "details": {"class_name": "another_event"}
        }
        self.mock_scenario_repo.get_scenarios_by_class_label = MagicMock(return_value=[{"id": "s2"}])
        
        mock_generated_samples = [{"sample_id": "s2_data_raw"}]
        self.mock_data_generator.set_generate_training_dataset_return_values([mock_generated_samples])
        
        # Use patch.object to temporarily simulate the absence of _export_data
        # The create=True argument allows patching of attributes that might not exist yet,
        # and side_effect=AttributeError will make hasattr(self.data_generator, '_export_data') return False.
        with patch.object(self.mock_data_generator, '_export_data', side_effect=AttributeError("Simulated missing attribute"), create=True), \
             patch('builtins.print') as mock_print:
            result = self.alm.generate_targeted_samples(weak_spots=[weak_spot], output_format="list_of_dicts")
        
        self.assertEqual(result, mock_generated_samples)
        mock_print.assert_any_call("Warning: MLDataGenerator does not have _export_data. Returning raw list.")

    def test_generate_targeted_samples_data_generator_no_export_method_returns_none_for_other_formats(self):
        """
        Test when MLDataGenerator does not have _export_data, returns None for non-list_of_dicts format.
        """
        weak_spot = {
            "weakness_id": "no_export_method_spot_avro", "type": "low_recall_class",
            "sensor_id": "U20_SPS30", "details": {"class_name": "avro_event"}
        }
        self.mock_scenario_repo.get_scenarios_by_class_label = MagicMock(return_value=[{"id": "s3"}])
        self.mock_data_generator.set_generate_training_dataset_return_values([ [{"sample_id": "s3_data_avro"}] ])
        
        # Simulate _export_data attribute missing
        with patch.object(self.mock_data_generator, '_export_data', side_effect=AttributeError("Simulated missing attribute"), create=True), \
             patch('builtins.print') as mock_print:
            result = self.alm.generate_targeted_samples(weak_spots=[weak_spot], output_format="avro_file")
        
        self.assertIsNone(result)
        # The first print is from the hasattr check in ALM
        mock_print.assert_any_call("Warning: MLDataGenerator does not have _export_data. Returning raw list.")
        mock_print.assert_any_call("Error: Cannot provide avro_file as _export_data is missing.")
# --- Tests for suggest_scenario_modifications ---

    def test_suggest_scenario_modifications_empty_analysis(self):
        """
        Test suggest_scenario_modifications with an empty weakness analysis.
        Should return an empty list of suggestions.
        """
        suggestions = self.alm.suggest_scenario_modifications(weakness_analysis=[])
        self.assertEqual(suggestions, [])

    def test_suggest_scenario_modifications_high_uncertainty_with_original_scenario(self):
        """
        Test suggestion for 'high_uncertainty_sample' with an original_scenario_id.
        Should suggest 'modify_existing_scenario'.
        """
        weak_spot_analysis = [{
            "weakness_id": "unc_sugg_1",
            "type": "high_uncertainty_sample",
            "priority": 0.8,
            "sensor_id": "U26_Lepton35",
            "details": {
                "original_scenario_id": "scenario_heat_event",
                "sample_features_summary": {
                    "top_n_features": [
                        {"feature_path": "temp_avg", "raw_value": 85.0, "importance_score": 0.6},
                        {"feature_path": "temp_variance", "raw_value": 2.5, "importance_score": 0.3}
                    ]
                },
                "epistemic_uncertainty_score": 0.7
            }
        }]
        
        suggestions = self.alm.suggest_scenario_modifications(weakness_analysis=weak_spot_analysis)
        
        self.assertEqual(len(suggestions), 1)
        suggestion = suggestions[0]
        self.assertEqual(suggestion["suggestion_type"], "modify_existing_scenario")
        self.assertEqual(suggestion["target_scenario_definition_id"], "scenario_heat_event")
        self.assertIn("alm_focus_unc_sugg_1", suggestion["suggested_metadata_updates"]["tags"]["value"])
        self.assertTrue(len(suggestion["suggested_modifications_for_specific_params"]) > 0)
        self.assertEqual(suggestion["suggested_modifications_for_specific_params"][0]["param_path"], "heuristic_map(temp_avg)")
        self.assertEqual(suggestion["originating_weak_spot_ids"], ["unc_sugg_1"])
        self.assertAlmostEqual(suggestion["suggestion_confidence"], min(max(0.8 + 0.7*0.2 + 0.1, 0.0), 1.0) )


    def test_suggest_scenario_modifications_high_uncertainty_no_original_scenario(self):
        """
        Test suggestion for 'high_uncertainty_sample' without original_scenario_id.
        Should suggest 'create_new_scenario'.
        """
        weak_spot_analysis = [{
            "weakness_id": "unc_sugg_2",
            "type": "high_uncertainty_sample",
            "priority": 0.7,
            "sensor_id": "U19_TFSGS", # VOCSensorArray
            "details": {
                "original_scenario_id": None,
                "sample_features_summary": {
                    "top_n_features": [{"feature_path": "voc_peak_x", "raw_value": 120.0}]
                },
                "epistemic_uncertainty_score": 0.5
            }
        }]
        
        suggestions = self.alm.suggest_scenario_modifications(weakness_analysis=weak_spot_analysis)
        
        self.assertEqual(len(suggestions), 1)
        suggestion = suggestions[0]
        self.assertEqual(suggestion["suggestion_type"], "create_new_scenario")
        self.assertIn("basis_for_new_scenario", suggestion)
        basis = suggestion["basis_for_new_scenario"]
        self.assertEqual(basis["scenario_definition_id_suggestion"], "alm_new_unc_sugg_2")
        self.assertIn("type_VOCSensorArray", basis["tags"]) # Check for the tag "type_VOCSensorArray"
        self.assertEqual(basis["specific_params_json_template"]["alm_focus_features"], weak_spot_analysis[0]["details"]["sample_features_summary"])
        self.assertAlmostEqual(suggestion["suggestion_confidence"], min(max(0.7 + 0.5*0.2 + 0.1, 0.0), 1.0) )

    def test_suggest_scenario_modifications_misclassified_region(self):
        """
        Test suggestion for 'misclassified_region'.
        Can suggest 'modify_existing_scenario' if original_scenario_id exists,
        otherwise 'create_new_scenario'. This test covers with original_scenario_id.
        """
        weak_spot_analysis = [{
            "weakness_id": "misc_sugg_1",
            "type": "misclassified_region",
            "priority": 0.85,
            "sensor_id": "U30_BMI270", # IMU
            "details": {
                "original_scenario_id": "scenario_machine_A_running",
                "true_label": "class_OPERATIONAL",
                "predicted_label": "class_IDLE",
                "sample_features_summary": {
                    "top_n_features": [{"feature_path": "accel_z_peak", "raw_value": 0.5}]
                }
            }
        }]
        
        suggestions = self.alm.suggest_scenario_modifications(weakness_analysis=weak_spot_analysis)
        
        self.assertEqual(len(suggestions), 1)
        suggestion = suggestions[0]
        self.assertEqual(suggestion["suggestion_type"], "modify_existing_scenario")
        self.assertEqual(suggestion["target_scenario_definition_id"], "scenario_machine_A_running")
        self.assertAlmostEqual(suggestion["suggestion_confidence"], min(max(0.85 + 0.1, 0.0), 1.0) ) # No epistemic score in this mock spot

    def test_suggest_scenario_modifications_low_recall_class(self):
        """
        Test suggestion for 'low_recall_class'.
        Should suggest 'create_new_scenario'.
        """
        weak_spot_analysis = [{
            "weakness_id": "recall_sugg_1",
            "type": "low_recall_class",
            "priority": 0.6,
            "sensor_id": "U20_SPS30", # ParticulateMatterSensor
            "details": {"class_name": "rare_smog_event"}
        }]
        
        suggestions = self.alm.suggest_scenario_modifications(weakness_analysis=weak_spot_analysis)
        
        self.assertEqual(len(suggestions), 1)
        suggestion = suggestions[0]
        self.assertEqual(suggestion["suggestion_type"], "create_new_scenario")
        basis = suggestion["basis_for_new_scenario"]
        self.assertEqual(basis["scenario_definition_id_suggestion"], "alm_boost_rare_smog_event_U20_SPS30")
        self.assertIn("class_rare_smog_event", basis["tags"])
        self.assertEqual(basis["specific_params_json_template"]["target_class_to_boost"], "rare_smog_event")
        self.assertEqual(basis["specific_params_json_template"]["target_sensor_type"], "ParticulateMatterSensor")
        self.assertAlmostEqual(suggestion["suggestion_confidence"], 0.6) # Base priority, no other factors in this mock

    def test_suggest_scenario_modifications_multiple_spots(self):
        """
        Test that multiple weak spots generate multiple suggestions.
        """
        weak_spot_analysis = [
            {
                "weakness_id": "multi_spot_1", "type": "low_recall_class", "priority": 0.5,
                "sensor_id": "s1", "details": {"class_name": "class_A"}
            },
            {
                "weakness_id": "multi_spot_2", "type": "high_uncertainty_sample", "priority": 0.9,
                "sensor_id": "s2", "details": {"original_scenario_id": "orig_scen_2"}
            }
        ]
        suggestions = self.alm.suggest_scenario_modifications(weakness_analysis=weak_spot_analysis)
        self.assertEqual(len(suggestions), 2)
        # Basic check on types
        self.assertEqual(suggestions[0]["suggestion_type"], "create_new_scenario") # For low_recall_class
        self.assertEqual(suggestions[1]["suggestion_type"], "modify_existing_scenario") # For high_uncertainty with original_scenario_id

    # --- Test for process_real_world_feedback (Placeholder) ---
    def test_process_real_world_feedback_runs(self):
        """
        Test that the placeholder process_real_world_feedback method runs without error.
        """
        try:
            with patch('builtins.print') as mock_print:
                self.alm.process_real_world_feedback(feedback_data={"key": "value"})
            mock_print.assert_any_call("Processing real-world feedback: ['key']")
        except Exception as e:
            self.fail(f"process_real_world_feedback raised an exception: {e}")
    # More tests will be added here based on the plan...

if __name__ == '__main__':
    unittest.main()