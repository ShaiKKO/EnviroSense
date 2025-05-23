"""
Unit tests for PrioritizationStrategy implementations.
"""
import unittest
from unittest.mock import patch, MagicMock
import uuid

from typing import Dict, Any, List, Optional

# Modules to be tested
from envirosense.simulation_engine.ml_training.prioritization_strategies import (
    PrioritizationStrategy,
    RealTimeSensorPrioritizationStrategy,
    HighFidelitySensorPrioritizationStrategy,
    HeterogeneousSensorPrioritizationStrategy,
    DEFAULT_SENSOR_ID_TO_TYPE_MAPPING,
    ModelPerformanceData, # TypedDict for mock data
    ProblematicSampleInfo, # TypedDict
    ClassMetrics # TypedDict
)
# MockModelInterface might be useful if strategies were to directly interact with it,
# but they primarily consume ModelPerformanceData.
# from envirosense.simulation_engine.ml_training.mock_components import MockModelInterface

TEST_SENSOR_MAP = DEFAULT_SENSOR_ID_TO_TYPE_MAPPING.copy()

class TestPrioritizationStrategyBase(unittest.TestCase):
    """
    Tests for the helper methods in the PrioritizationStrategy base class.
    """
    def setUp(self):
        # Use a concrete strategy to test base class methods
        self.strategy = RealTimeSensorPrioritizationStrategy(sensor_id_to_type_map=TEST_SENSOR_MAP)

    def test_generate_weakness_id(self):
        """Test the _generate_weakness_id helper method."""
        prefix = "test_prefix"
        base_id = "base123"
        
        # Test with base_id
        weakness_id_with_base = self.strategy._generate_weakness_id(prefix, base_id)
        self.assertTrue(weakness_id_with_base.startswith(prefix))
        self.assertIn(base_id, weakness_id_with_base)
        
        # Test without base_id (should generate a UUID part)
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = "abcdef1234567890"
            weakness_id_no_base = self.strategy._generate_weakness_id(prefix)
            self.assertTrue(weakness_id_no_base.startswith(prefix))
            self.assertIn("abcdef12", weakness_id_no_base) # Checks for the first 8 chars of hex

    def test_get_sensor_type_from_id(self):
        """Test the _get_sensor_type_from_id helper method."""
        self.assertEqual(self.strategy._get_sensor_type_from_id("U26_Lepton35"), "ThermalCamera")
        self.assertIsNone(self.strategy._get_sensor_type_from_id("UNKNOWN_ID"))
        self.assertIsNone(self.strategy._get_sensor_type_from_id(None))
        
        # Test with a custom map
        custom_map = {"custom_sensor_1": "CustomTypeA"}
        # Use a concrete strategy for this test as well
        strategy_custom_map = RealTimeSensorPrioritizationStrategy(sensor_id_to_type_map=custom_map)
        self.assertEqual(strategy_custom_map._get_sensor_type_from_id("custom_sensor_1"), "CustomTypeA")
        self.assertIsNone(strategy_custom_map._get_sensor_type_from_id("U26_Lepton35")) # Should not use default

    def test_validate_model_performance_data(self):
        """Test the _validate_model_performance_data helper method."""
        valid_data: ModelPerformanceData = {
            "model_version_evaluated": "v1", "dataset_identifier": "d1",
            "overall_metrics": {}, 
            "per_class_metrics": {}, # Required
            "uncertain_samples": [], # Required
            "misclassified_samples": [] # Required
        }
        self.assertTrue(self.strategy._validate_model_performance_data(valid_data))

        invalid_data_missing_key: ModelPerformanceData = { # type: ignore
            "model_version_evaluated": "v1", "dataset_identifier": "d1",
            "overall_metrics": {},
            # "per_class_metrics": {}, # Missing this
            "uncertain_samples": [],
            "misclassified_samples": []
        }
        with patch('builtins.print') as mock_print: # It prints a warning
            self.assertFalse(self.strategy._validate_model_performance_data(invalid_data_missing_key))
            mock_print.assert_any_call("Warning: ModelPerformanceData missing required key: per_class_metrics")

        invalid_data_empty: ModelPerformanceData = {} # type: ignore
        with patch('builtins.print') as mock_print:
            self.assertFalse(self.strategy._validate_model_performance_data(invalid_data_empty))
            # It will complain about the first missing key it checks
            # (order might matter if the check is sequential)


# Test classes for concrete strategies will follow here.

if __name__ == '__main__':
    unittest.main()
class TestRealTimeSensorPrioritizationStrategy(unittest.TestCase):
    """
    Tests for the RealTimeSensorPrioritizationStrategy.
    """
    def setUp(self):
        self.default_map = TEST_SENSOR_MAP.copy()
        self.strategy = RealTimeSensorPrioritizationStrategy(sensor_id_to_type_map=self.default_map)
        # Default thresholds from strategy implementation:
        # uncertainty_threshold: float = 0.7
        # misclassification_priority_base: float = 0.8
        # low_recall_threshold: float = 0.6

    def test_initialization_default_params(self):
        """Test initialization with default parameters."""
        self.assertEqual(self.strategy.uncertainty_threshold, 0.7)
        self.assertEqual(self.strategy.misclassification_priority_base, 0.8)
        self.assertEqual(self.strategy.low_recall_threshold, 0.6)
        self.assertEqual(self.strategy.sensor_id_to_type_map, self.default_map)

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        custom_map = {"sensorX": "typeA"}
        strategy = RealTimeSensorPrioritizationStrategy(
            uncertainty_threshold=0.85,
            misclassification_priority_base=0.75,
            low_recall_threshold=0.55,
            sensor_id_to_type_map=custom_map
        )
        self.assertEqual(strategy.uncertainty_threshold, 0.85)
        self.assertEqual(strategy.misclassification_priority_base, 0.75)
        self.assertEqual(strategy.low_recall_threshold, 0.55)
        self.assertEqual(strategy.sensor_id_to_type_map, custom_map)

    # --- Tests for calculate_priority ---
    def test_calculate_priority_high_uncertainty(self):
        """Test priority calculation for high uncertainty samples."""
        sample_info_high_unc: ProblematicSampleInfo = {"uncertainty_score": 0.9}
        priority = self.strategy.calculate_priority(sample_info=sample_info_high_unc, weakness_type="high_uncertainty_sample")
        self.assertAlmostEqual(priority, 0.9)

        sample_info_low_unc: ProblematicSampleInfo = {"uncertainty_score": 0.5}
        priority = self.strategy.calculate_priority(sample_info=sample_info_low_unc, weakness_type="high_uncertainty_sample")
        self.assertAlmostEqual(priority, 0.5)
        
        priority_capped_high = self.strategy.calculate_priority(sample_info={"uncertainty_score": 1.5}, weakness_type="high_uncertainty_sample")
        self.assertAlmostEqual(priority_capped_high, 1.0)
        
        priority_capped_low = self.strategy.calculate_priority(sample_info={"uncertainty_score": -0.5}, weakness_type="high_uncertainty_sample")
        self.assertAlmostEqual(priority_capped_low, 0.0)

    def test_calculate_priority_misclassified_region(self):
        """Test priority calculation for misclassified regions."""
        # misclassification_priority_base = 0.8
        sample_info_high_conf: ProblematicSampleInfo = {"confidence_of_prediction": 0.9} # Confidence in wrong prediction
        priority = self.strategy.calculate_priority(sample_info=sample_info_high_conf, weakness_type="misclassified_region")
        # Expected: 0.8 + (0.9 * 0.1) = 0.8 + 0.09 = 0.89
        self.assertAlmostEqual(priority, 0.89)

        sample_info_low_conf: ProblematicSampleInfo = {"confidence_of_prediction": 0.2}
        priority = self.strategy.calculate_priority(sample_info=sample_info_low_conf, weakness_type="misclassified_region")
        # Expected: 0.8 + (0.2 * 0.1) = 0.8 + 0.02 = 0.82
        self.assertAlmostEqual(priority, 0.82)
        
        # Test capping
        priority_capped = self.strategy.calculate_priority(sample_info={"confidence_of_prediction": 3.0}, weakness_type="misclassified_region")
        # Expected: 0.8 + (3.0 * 0.1) = 1.1, capped to 1.0
        self.assertAlmostEqual(priority_capped, 1.0)


    def test_calculate_priority_low_recall_class(self):
        """Test priority calculation for low recall classes."""
        class_metrics_low_recall: ClassMetrics = {"recall": 0.4, "precision":0.0, "f1_score":0.0, "support":0} # only recall matters here
        priority = self.strategy.calculate_priority(class_metrics_info=class_metrics_low_recall, weakness_type="low_recall_class")
        # Expected: 1.0 - 0.4 = 0.6
        self.assertAlmostEqual(priority, 0.6)

        class_metrics_high_recall: ClassMetrics = {"recall": 0.9, "precision":0.0, "f1_score":0.0, "support":0}
        priority = self.strategy.calculate_priority(class_metrics_info=class_metrics_high_recall, weakness_type="low_recall_class")
        # Expected: 1.0 - 0.9 = 0.1
        self.assertAlmostEqual(priority, 0.1)

        # Test capping
        priority_capped_high = self.strategy.calculate_priority(class_metrics_info={"recall": -0.5, "precision":0.0, "f1_score":0.0, "support":0}, weakness_type="low_recall_class")
        # Expected: 1.0 - (-0.5) = 1.5, capped to 1.0
        self.assertAlmostEqual(priority_capped_high, 1.0)
        
        priority_capped_low = self.strategy.calculate_priority(class_metrics_info={"recall": 1.5, "precision":0.0, "f1_score":0.0, "support":0}, weakness_type="low_recall_class")
        # Expected: 1.0 - 1.5 = -0.5, capped to 0.0
        self.assertAlmostEqual(priority_capped_low, 0.0)

    def test_calculate_priority_unknown_type(self):
        """Test priority calculation for an unknown weakness type."""
        priority = self.strategy.calculate_priority(weakness_type="unknown_type")
        self.assertAlmostEqual(priority, 0.0) # Should default to 0 or a defined behavior

    # --- Tests for identify_weaknesses ---
    def test_identify_weaknesses_invalid_data(self):
        """Test identify_weaknesses with invalid (e.g., empty) performance data."""
        invalid_perf_data: ModelPerformanceData = {} # type: ignore
        with patch.object(self.strategy, '_validate_model_performance_data', return_value=False):
            weaknesses = self.strategy.identify_weaknesses(invalid_perf_data)
        self.assertEqual(weaknesses, [])

    def test_identify_weaknesses_no_problematic_samples_or_low_recall(self):
        """Test with performance data that has no issues meeting thresholds."""
        perf_data: ModelPerformanceData = {
            "model_version_evaluated": "v1", "dataset_identifier": "d_good",
            "overall_metrics": {"accuracy": 0.99},
            "per_class_metrics": {
                "classA": {"recall": 0.95, "precision": 0.95, "f1_score": 0.95, "support": 100},
                "classB": {"recall": 0.98, "precision": 0.98, "f1_score": 0.98, "support": 100}
            },
            "uncertain_samples": [ # Below threshold of 0.7
                {"raw_sample_id": "unc1", "sensor_id": "s1", "uncertainty_score": 0.5}
            ],
            "misclassified_samples": [] # None
        }
        weaknesses = self.strategy.identify_weaknesses(perf_data)
        self.assertEqual(weaknesses, [])

    def test_identify_weaknesses_high_uncertainty_samples(self):
        """Test identification of high uncertainty samples."""
        perf_data: ModelPerformanceData = {
            "model_version_evaluated": "v1", "dataset_identifier": "d_unc",
            "per_class_metrics": {}, "misclassified_samples": [], # Required but not focus
            "uncertain_samples": [
                {"raw_sample_id": "unc_ok", "sensor_id": "s1", "uncertainty_score": 0.6}, # Below threshold
                {"raw_sample_id": "unc_high1", "sensor_id": "s2", "uncertainty_score": 0.8, "original_scenario_id": "scen1"},
                {"raw_sample_id": "unc_high2", "sensor_id": "s3", "uncertainty_score": 0.75} # No scenario id
            ]
        }
        weaknesses = self.strategy.identify_weaknesses(perf_data)
        self.assertEqual(len(weaknesses), 2)
        
        # Check properties of identified weaknesses (order might vary due to sorting by priority)
        # Sort by raw_sample_id for consistent checking if priorities are equal
        weaknesses.sort(key=lambda x: str(x.get("raw_sample_id", ""))) # Ensure string keys for sorting

        self.assertEqual(weaknesses[0]["type"], "high_uncertainty_sample")
        self.assertEqual(weaknesses[0].get("raw_sample_id"), "unc_high1", "raw_sample_id mismatch or missing in first weakness.")
        self.assertAlmostEqual(weaknesses[0]["priority"], 0.8)
        self.assertEqual(weaknesses[0]["sensor_id"], "s2")
        self.assertEqual(weaknesses[0]["details"]["original_scenario_id"], "scen1")

        self.assertEqual(weaknesses[1]["type"], "high_uncertainty_sample")
        self.assertEqual(weaknesses[1].get("raw_sample_id"), "unc_high2", "raw_sample_id mismatch or missing in second weakness.")
        self.assertAlmostEqual(weaknesses[1]["priority"], 0.75)
        self.assertEqual(weaknesses[1]["sensor_id"], "s3")

    def test_identify_weaknesses_misclassified_samples(self):
        """Test identification of misclassified samples."""
        perf_data: ModelPerformanceData = {
            "model_version_evaluated": "v1", "dataset_identifier": "d_misc",
            "per_class_metrics": {}, "uncertain_samples": [], # Required
            "misclassified_samples": [
                {"raw_sample_id": "misc1", "sensor_id": "sA", "true_label": "X", "predicted_label": "Y", "confidence_of_prediction": 0.95},
                {"raw_sample_id": "misc2", "sensor_id": "sB", "true_label": "P", "predicted_label": "Q", "confidence_of_prediction": 0.60}
            ]
        }
        weaknesses = self.strategy.identify_weaknesses(perf_data)
        self.assertEqual(len(weaknesses), 2)
        weaknesses.sort(key=lambda x: str(x.get("raw_sample_id", ""))) # Ensure string keys for sorting

        self.assertEqual(weaknesses[0]["type"], "misclassified_region")
        self.assertEqual(weaknesses[0].get("raw_sample_id"), "misc1", "raw_sample_id mismatch or missing in first misclassified weakness.")
        self.assertAlmostEqual(weaknesses[0]["priority"], 0.8 + (0.95 * 0.1)) # 0.895
        self.assertEqual(weaknesses[0]["sensor_id"], "sA")

        self.assertEqual(weaknesses[1]["type"], "misclassified_region")
        self.assertEqual(weaknesses[1].get("raw_sample_id"), "misc2", "raw_sample_id mismatch or missing in second misclassified weakness.")
        self.assertAlmostEqual(weaknesses[1]["priority"], 0.8 + (0.60 * 0.1)) # 0.86
        self.assertEqual(weaknesses[1]["sensor_id"], "sB")

    def test_identify_weaknesses_low_recall_classes(self):
        """Test identification of low recall classes."""
        # low_recall_threshold = 0.6
        perf_data: ModelPerformanceData = {
            "model_version_evaluated": "v1", "dataset_identifier": "d_recall",
            "uncertain_samples": [], "misclassified_samples": [], # Required
            "per_class_metrics": {
                "class_good_recall": {"recall": 0.8, "precision":0.0, "f1_score":0.0, "support":10},
                "class_low_recall1": {"recall": 0.5, "precision":0.0, "f1_score":0.0, "support":20}, # Below 0.6
                "class_low_recall2": {"recall": 0.3, "precision":0.0, "f1_score":0.0, "support":30}  # Below 0.6
            }
        }
        weaknesses = self.strategy.identify_weaknesses(perf_data)
        self.assertEqual(len(weaknesses), 2)
        weaknesses.sort(key=lambda x: x["details"]["class_name"]) # Sort by class name

        self.assertEqual(weaknesses[0]["type"], "low_recall_class")
        self.assertEqual(weaknesses[0]["details"]["class_name"], "class_low_recall1")
        self.assertAlmostEqual(weaknesses[0]["priority"], 1.0 - 0.5) # 0.5
        self.assertIsNone(weaknesses[0]["sensor_id"]) # Global metric

        self.assertEqual(weaknesses[1]["type"], "low_recall_class")
        self.assertEqual(weaknesses[1]["details"]["class_name"], "class_low_recall2")
        self.assertAlmostEqual(weaknesses[1]["priority"], 1.0 - 0.3) # 0.7
        self.assertIsNone(weaknesses[1]["sensor_id"])

    def test_identify_weaknesses_mixed_issues_and_sorting(self):
        """Test with a mix of issues, ensuring correct identification and priority sorting."""
        perf_data: ModelPerformanceData = {
            "model_version_evaluated": "v1", "dataset_identifier": "d_mixed",
            "per_class_metrics": {
                "class_low_recall": {"recall": 0.4, "precision":0.0, "f1_score":0.0, "support":10} # Priority 0.6
            },
            "uncertain_samples": [
                {"raw_sample_id": "unc_high", "sensor_id": "s1", "uncertainty_score": 0.9} # Priority 0.9
            ],
            "misclassified_samples": [
                {"raw_sample_id": "misc_mod", "sensor_id": "s2", "true_label": "A", "predicted_label": "B", "confidence_of_prediction": 0.5} # Priority 0.8 + 0.05 = 0.85
            ]
        }
        weaknesses = self.strategy.identify_weaknesses(perf_data)
        self.assertEqual(len(weaknesses), 3)
        
        # Check if sorted by priority (descending)
        self.assertAlmostEqual(weaknesses[0]["priority"], 0.9) # unc_high
        self.assertEqual(weaknesses[0]["type"], "high_uncertainty_sample")

        self.assertAlmostEqual(weaknesses[1]["priority"], 0.85) # misc_mod
        self.assertEqual(weaknesses[1]["type"], "misclassified_region")
        
        self.assertAlmostEqual(weaknesses[2]["priority"], 0.6) # class_low_recall
        self.assertEqual(weaknesses[2]["type"], "low_recall_class")

    def test_identify_weaknesses_target_sensor_id_filter(self):
        """Test that target_sensor_id filters weaknesses correctly."""
        target_sid = "sensor_target"
        other_sid = "sensor_other"
        perf_data: ModelPerformanceData = {
            "model_version_evaluated": "v1", "dataset_identifier": "d_target",
            "per_class_metrics": { # Global, should not be filtered by target_sensor_id for this strategy
                "class_low_recall_global": {"recall": 0.5, "precision":0.0, "f1_score":0.0, "support":10}
            },
            "sensor_specific_metrics": { # This strategy uses global per_class_metrics unless target_sensor_id is specified
                target_sid: {
                    "per_class_metrics": {"class_low_recall_target": {"recall": 0.4, "precision":0.0, "f1_score":0.0, "support":5}}
                },
                other_sid: {
                     "per_class_metrics": {"class_low_recall_other": {"recall": 0.3, "precision":0.0, "f1_score":0.0, "support":5}}
                }
            },
            "uncertain_samples": [
                {"raw_sample_id": "unc_target", "sensor_id": target_sid, "uncertainty_score": 0.8},
                {"raw_sample_id": "unc_other", "sensor_id": other_sid, "uncertainty_score": 0.85}
            ],
            "misclassified_samples": [
                {"raw_sample_id": "misc_target", "sensor_id": target_sid, "true_label": "A", "predicted_label": "B", "confidence_of_prediction": 0.7},
                {"raw_sample_id": "misc_other", "sensor_id": other_sid, "true_label": "C", "predicted_label": "D", "confidence_of_prediction": 0.75}
            ]
        }
        weaknesses = self.strategy.identify_weaknesses(perf_data, target_sensor_id=target_sid)
        
        self.assertEqual(len(weaknesses), 3, f"Expected 3 weaknesses, got {len(weaknesses)}: {weaknesses}")
        
        unc_target_weakness = next((w for w in weaknesses if w.get("raw_sample_id") == "unc_target"), None)
        misc_target_weakness = next((w for w in weaknesses if w.get("raw_sample_id") == "misc_target"), None)
        recall_target_weakness = next((w for w in weaknesses if w.get("type") == "low_recall_class" and w["details"].get("class_name") == "class_low_recall_target"), None)
        
        self.assertIsNotNone(unc_target_weakness, f"Uncertain sample 'unc_target' not found. Weaknesses: {weaknesses}")
        if unc_target_weakness: self.assertEqual(unc_target_weakness["sensor_id"], target_sid)

        self.assertIsNotNone(misc_target_weakness, f"Misclassified sample 'misc_target' not found. Weaknesses: {weaknesses}")
        if misc_target_weakness: self.assertEqual(misc_target_weakness["sensor_id"], target_sid)
        
        self.assertIsNotNone(recall_target_weakness, f"Low recall class 'class_low_recall_target' not found. Weaknesses: {weaknesses}")
        if recall_target_weakness: self.assertEqual(recall_target_weakness["sensor_id"], target_sid)
class TestHighFidelitySensorPrioritizationStrategy(unittest.TestCase):
    """
    Tests for the HighFidelitySensorPrioritizationStrategy.
    """
    def setUp(self):
        self.default_map = TEST_SENSOR_MAP.copy()
        self.strategy = HighFidelitySensorPrioritizationStrategy(sensor_id_to_type_map=self.default_map)
        # Default thresholds/weights from strategy:
        # epistemic_threshold: float = 0.4
        # disagreement_threshold: float = 0.3
        # low_recall_threshold: float = 0.75
        # epistemic_weight: float = 0.5
        # disagreement_weight: float = 0.3
        # misclassification_base_priority: float = 0.7
        # class_criticality_map: Optional[Dict[str, float]] = None

    def test_initialization_default_params(self):
        """Test initialization with default parameters."""
        self.assertEqual(self.strategy.epistemic_threshold, 0.4)
        self.assertEqual(self.strategy.disagreement_threshold, 0.3)
        self.assertEqual(self.strategy.low_recall_threshold, 0.75)
        self.assertEqual(self.strategy.epistemic_weight, 0.5)
        self.assertEqual(self.strategy.disagreement_weight, 0.3)
        self.assertEqual(self.strategy.misclassification_base_priority, 0.7)
        self.assertEqual(self.strategy.class_criticality_map, {})
        self.assertEqual(self.strategy.sensor_id_to_type_map, self.default_map)

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        custom_map = {"sensorY": "typeB"}
        custom_criticality = {"critical_A": 1.5, "critical_B": 2.0}
        strategy = HighFidelitySensorPrioritizationStrategy(
            epistemic_threshold=0.5, disagreement_threshold=0.25, low_recall_threshold=0.8,
            epistemic_weight=0.6, disagreement_weight=0.2, misclassification_base_priority=0.65,
            class_criticality_map=custom_criticality, sensor_id_to_type_map=custom_map
        )
        self.assertEqual(strategy.epistemic_threshold, 0.5)
        self.assertEqual(strategy.disagreement_threshold, 0.25)
        self.assertEqual(strategy.low_recall_threshold, 0.8)
        self.assertEqual(strategy.epistemic_weight, 0.6)
        self.assertEqual(strategy.disagreement_weight, 0.2)
        self.assertEqual(strategy.misclassification_base_priority, 0.65)
        self.assertEqual(strategy.class_criticality_map, custom_criticality)
        self.assertEqual(strategy.sensor_id_to_type_map, custom_map)

    # --- Tests for calculate_priority ---
    def test_calculate_priority_high_uncertainty(self):
        """Test priority for high uncertainty (epistemic, disagreement, aleatoric)."""
        # epistemic_weight: 0.5, disagreement_weight: 0.3
        sample_info: ProblematicSampleInfo = {
            "epistemic_uncertainty_score": 0.8, # Contrib: 0.8 * 0.5 = 0.4
            "disagreement_score": 0.6,          # Contrib: 0.6 * 0.3 = 0.18
            "aleatoric_uncertainty_score": 0.2  # Penalty factor: (1.0 - 0.2 * 0.5) = 0.9
        } # Total base = 0.4 + 0.18 = 0.58. Final = 0.58 * 0.9 = 0.522
        priority = self.strategy.calculate_priority(sample_info=sample_info, weakness_type="high_uncertainty_sample")
        self.assertAlmostEqual(priority, 0.522)

        sample_info_no_aleatoric: ProblematicSampleInfo = {
             "epistemic_uncertainty_score": 0.7, # Contrib: 0.35
             "disagreement_score": 0.5           # Contrib: 0.15
        } # Total base = 0.5. Final = 0.5 * (1.0 - 0*0.5) = 0.5
        priority = self.strategy.calculate_priority(sample_info=sample_info_no_aleatoric, weakness_type="high_uncertainty_sample")
        self.assertAlmostEqual(priority, 0.5)
        
        # Test capping
        sample_info_very_high: ProblematicSampleInfo = {
            "epistemic_uncertainty_score": 1.0, "disagreement_score": 1.0, "aleatoric_uncertainty_score": 0.0
        } # Base = 0.5 + 0.3 = 0.8. Final = 0.8
        priority = self.strategy.calculate_priority(sample_info=sample_info_very_high, weakness_type="high_uncertainty_sample")
        self.assertAlmostEqual(priority, 0.8) # (0.5*1 + 0.3*1) * (1-0) = 0.8. Max is 1.0.

    def test_calculate_priority_misclassified_region(self):
        """Test priority for misclassified regions, with and without criticality."""
        # misclassification_base_priority = 0.7
        sample_info_no_crit: ProblematicSampleInfo = {
            "epistemic_uncertainty_score": 0.5, # Contrib: 0.5 * 0.2 = 0.1
            "true_label": "normal_class"
        } # Expected: 0.7 + 0.1 = 0.8
        priority = self.strategy.calculate_priority(sample_info=sample_info_no_crit, weakness_type="misclassified_region")
        self.assertAlmostEqual(priority, 0.8)

        custom_criticality = {"critical_class": 1.5}
        self.strategy.class_criticality_map = custom_criticality
        sample_info_crit: ProblematicSampleInfo = {
            "epistemic_uncertainty_score": 0.5, # Contrib: 0.1
            "true_label": "critical_class"
        } # Expected: (0.7 + 0.1) * 1.5 = 0.8 * 1.5 = 1.2, capped to 1.0
        priority = self.strategy.calculate_priority(sample_info=sample_info_crit, weakness_type="misclassified_region")
        self.assertAlmostEqual(priority, 1.0)
        self.strategy.class_criticality_map = {} # Reset

    def test_calculate_priority_low_recall_class(self):
        """Test priority for low recall classes, with and without criticality."""
        class_metrics_no_crit: ClassMetrics = {"recall": 0.5, "class_name": "normal_recall_class", "precision":0.0, "f1_score":0.0, "support":0}
        # Expected: 1.0 - 0.5 = 0.5
        priority = self.strategy.calculate_priority(class_metrics_info=class_metrics_no_crit, weakness_type="low_recall_class")
        self.assertAlmostEqual(priority, 0.5)

        custom_criticality = {"critical_recall_class": 2.0}
        self.strategy.class_criticality_map = custom_criticality
        class_metrics_crit: ClassMetrics = {"recall": 0.6, "class_name": "critical_recall_class", "precision":0.0, "f1_score":0.0, "support":0}
        # Expected: (1.0 - 0.6) * 2.0 = 0.4 * 2.0 = 0.8
        priority = self.strategy.calculate_priority(class_metrics_info=class_metrics_crit, weakness_type="low_recall_class")
        self.assertAlmostEqual(priority, 0.8)
        self.strategy.class_criticality_map = {} # Reset

    # --- Tests for identify_weaknesses ---
    def test_identify_weaknesses_epistemic_or_disagreement(self):
        """Test identification based on epistemic or disagreement thresholds."""
        # epistemic_threshold: 0.4, disagreement_threshold: 0.3
        perf_data: ModelPerformanceData = {
            "model_version_evaluated": "v1", "dataset_identifier": "d_hf_unc",
            "per_class_metrics": {}, "misclassified_samples": [],
            "uncertain_samples": [
                {"raw_sample_id": "s_epistemic", "sensor_id": "hf1", "epistemic_uncertainty_score": 0.5, "disagreement_score": 0.1}, # Meets epistemic
                {"raw_sample_id": "s_disagree", "sensor_id": "hf2", "epistemic_uncertainty_score": 0.2, "disagreement_score": 0.35}, # Meets disagreement
                {"raw_sample_id": "s_both", "sensor_id": "hf3", "epistemic_uncertainty_score": 0.45, "disagreement_score": 0.32}, # Meets both
                {"raw_sample_id": "s_neither", "sensor_id": "hf4", "epistemic_uncertainty_score": 0.1, "disagreement_score": 0.1}  # Meets neither
            ]
        }
        weaknesses = self.strategy.identify_weaknesses(perf_data)
        self.assertEqual(len(weaknesses), 3)
        weakness_ids = {w.get("raw_sample_id", w["details"].get("raw_sample_id")) for w in weaknesses}
        self.assertIn("s_epistemic", weakness_ids)
        self.assertIn("s_disagree", weakness_ids)
        self.assertIn("s_both", weakness_ids)
        self.assertNotIn("s_neither", weakness_ids)

    def test_identify_weaknesses_low_recall_with_criticality(self):
        """Test low recall identification considering class criticality."""
        # low_recall_threshold = 0.75
        self.strategy.class_criticality_map = {"critical_low_recall": 1.8}
        perf_data: ModelPerformanceData = {
            "model_version_evaluated": "v1", "dataset_identifier": "d_hf_recall",
            "uncertain_samples": [], "misclassified_samples": [],
            "per_class_metrics": {
                "normal_high_recall": {"recall": 0.9, "precision":0.0, "f1_score":0.0, "support":10},
                "normal_low_recall": {"recall": 0.7, "precision":0.0, "f1_score":0.0, "support":10}, # Below threshold 0.75
                "critical_low_recall": {"recall": 0.72, "precision":0.0, "f1_score":0.0, "support":10} # Below threshold 0.75
            }
        }
        weaknesses = self.strategy.identify_weaknesses(perf_data)
        self.assertEqual(len(weaknesses), 2) # normal_low_recall and critical_low_recall
        
        # Check priorities (higher for critical)
        # P_normal_low = 1 - 0.7 = 0.3
        # P_critical_low = (1 - 0.72) * 1.8 = 0.28 * 1.8 = 0.504
        # So critical_low_recall should have higher priority
        weaknesses.sort(key=lambda x: x["priority"], reverse=True)
        self.assertEqual(weaknesses[0]["details"]["class_name"], "critical_low_recall")
        self.assertAlmostEqual(weaknesses[0]["priority"], 0.504)
        
        self.assertEqual(weaknesses[1]["details"]["class_name"], "normal_low_recall")
        self.assertAlmostEqual(weaknesses[1]["priority"], 0.3)
        
        self.strategy.class_criticality_map = {} # Reset

    def test_identify_weaknesses_target_sensor_id_hf(self):
        """Test target_sensor_id filtering for HighFidelity strategy."""
        target_sid = "hf_target_sensor"
        other_sid = "hf_other_sensor"
        perf_data: ModelPerformanceData = {
            "model_version_evaluated": "v1", "dataset_identifier": "d_hf_target",
            "per_class_metrics": { # Global metrics
                "global_class_low_recall": {"recall": 0.6, "precision":0.0, "f1_score":0.0, "support":10} # Below 0.75
            },
            "sensor_specific_metrics": {
                target_sid: {
                    "per_class_metrics": {"target_class_low_recall": {"recall": 0.5, "precision":0.0, "f1_score":0.0, "support":5}} # Below 0.75
                },
                other_sid: {
                    "per_class_metrics": {"other_class_low_recall": {"recall": 0.4, "precision":0.0, "f1_score":0.0, "support":5}} # Below 0.75
                }
            },
            "uncertain_samples": [
                {"raw_sample_id": "unc_target_hf", "sensor_id": target_sid, "epistemic_uncertainty_score": 0.5}, # Qualifies
                {"raw_sample_id": "unc_other_hf", "sensor_id": other_sid, "epistemic_uncertainty_score": 0.5}    # Qualifies
            ],
            "misclassified_samples": [
                {"raw_sample_id": "misc_target_hf", "sensor_id": target_sid, "true_label": "X", "predicted_label": "Y"},
                {"raw_sample_id": "misc_other_hf", "sensor_id": other_sid, "true_label": "P", "predicted_label": "Q"}
            ]
        }
        weaknesses = self.strategy.identify_weaknesses(perf_data, target_sensor_id=target_sid)
        
        # Expected: unc_target_hf, misc_target_hf, target_class_low_recall
        self.assertEqual(len(weaknesses), 3, f"Expected 3 weaknesses (HF), got {len(weaknesses)}: {weaknesses}")
        
        unc_target_weakness_hf = next((w for w in weaknesses if w.get("raw_sample_id") == "unc_target_hf"), None)
        misc_target_weakness_hf = next((w for w in weaknesses if w.get("raw_sample_id") == "misc_target_hf"), None)
        recall_target_weakness_hf = next((w for w in weaknesses if w.get("type") == "low_recall_class" and w["details"].get("class_name") == "target_class_low_recall"), None)

        self.assertIsNotNone(unc_target_weakness_hf, f"Uncertain sample 'unc_target_hf' not found. Weaknesses: {weaknesses}")
        if unc_target_weakness_hf: self.assertEqual(unc_target_weakness_hf["sensor_id"], target_sid)

        self.assertIsNotNone(misc_target_weakness_hf, f"Misclassified sample 'misc_target_hf' not found. Weaknesses: {weaknesses}")
        if misc_target_weakness_hf: self.assertEqual(misc_target_weakness_hf["sensor_id"], target_sid)

        self.assertIsNotNone(recall_target_weakness_hf, f"Low recall class 'target_class_low_recall' (HF) not found. Weaknesses: {weaknesses}")
        if recall_target_weakness_hf: self.assertEqual(recall_target_weakness_hf["sensor_id"], target_sid)
class TestHeterogeneousSensorPrioritizationStrategy(unittest.TestCase):
    """
    Tests for the HeterogeneousSensorPrioritizationStrategy.
    """
    def setUp(self):
        self.default_map = TEST_SENSOR_MAP.copy()
        self.strategy = HeterogeneousSensorPrioritizationStrategy(sensor_id_to_type_map=self.default_map)
        # Default params from strategy:
        # sensor_type_weights: Optional[Dict[str, float]] = None -> {}
        # default_sensor_weight: float = 1.0
        # max_weaknesses_per_sensor: int = 5
        # (plus thresholds from HighFidelity strategy)

    def test_initialization_default_params(self):
        """Test initialization with default parameters."""
        self.assertEqual(self.strategy.sensor_type_weights, {})
        self.assertEqual(self.strategy.default_sensor_weight, 1.0)
        self.assertEqual(self.strategy.max_weaknesses_per_sensor, 5)
        self.assertEqual(self.strategy.epistemic_threshold, 0.4) # Inherited defaults
        self.assertEqual(self.strategy.sensor_id_to_type_map, self.default_map)

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        custom_map = {"sensorZ": "typeC"}
        custom_weights = {"typeC": 1.5, "typeD": 0.8}
        custom_criticality = {"critical_het": 1.2}
        strategy = HeterogeneousSensorPrioritizationStrategy(
            sensor_type_weights=custom_weights,
            default_sensor_weight=0.9,
            max_weaknesses_per_sensor=3,
            epistemic_threshold=0.45,
            disagreement_threshold=0.35,
            low_recall_threshold=0.70,
            epistemic_weight=0.55,
            disagreement_weight=0.25,
            misclassification_base_priority=0.72,
            class_criticality_map=custom_criticality,
            sensor_id_to_type_map=custom_map
        )
        self.assertEqual(strategy.sensor_type_weights, custom_weights)
        self.assertEqual(strategy.default_sensor_weight, 0.9)
        self.assertEqual(strategy.max_weaknesses_per_sensor, 3)
        self.assertEqual(strategy.epistemic_threshold, 0.45)
        self.assertEqual(strategy.class_criticality_map, custom_criticality)
        self.assertEqual(strategy.sensor_id_to_type_map, custom_map)

    # --- Tests for calculate_priority ---
    def test_calculate_priority_with_sensor_type_weights(self):
        """Test priority calculation considering sensor_type_weights."""
        self.strategy.sensor_type_weights = {"VOCSensorArray": 1.5, "ThermalCamera": 0.5}
        self.strategy.default_sensor_weight = 1.0 # Explicitly set for clarity

        # VOCSensorArray (U19_TFSGS) should get 1.5x weight
        sample_info_voc: ProblematicSampleInfo = {
            "sensor_id": "U19_TFSGS", # VOCSensorArray
            "epistemic_uncertainty_score": 0.6, # Base contrib: 0.6 * 0.5 = 0.3
            "disagreement_score": 0.4,          # Base contrib: 0.4 * 0.3 = 0.12
            "aleatoric_uncertainty_score": 0.1  # Penalty factor: (1.0 - 0.1 * 0.5) = 0.95
        } # Base priority = (0.3 + 0.12) * 0.95 = 0.42 * 0.95 = 0.399
          # Weighted priority = 0.399 * 1.5 = 0.5985
        priority_voc = self.strategy.calculate_priority(sample_info=sample_info_voc, weakness_type="high_uncertainty_sample", sensor_type="VOCSensorArray")
        self.assertAlmostEqual(priority_voc, 0.5985)

        # ThermalCamera (U26_Lepton35) should get 0.5x weight
        sample_info_thermal: ProblematicSampleInfo = {
            "sensor_id": "U26_Lepton35", # ThermalCamera
            "epistemic_uncertainty_score": 0.8, # Base contrib: 0.8 * 0.5 = 0.4
            "disagreement_score": 0.7,          # Base contrib: 0.7 * 0.3 = 0.21
            "aleatoric_uncertainty_score": 0.0  # Penalty factor: 1.0
        } # Base priority = (0.4 + 0.21) * 1.0 = 0.61
          # Weighted priority = 0.61 * 0.5 = 0.305
        priority_thermal = self.strategy.calculate_priority(sample_info=sample_info_thermal, weakness_type="high_uncertainty_sample", sensor_type="ThermalCamera")
        self.assertAlmostEqual(priority_thermal, 0.305)
        
        # Unweighted sensor type (e.g. IMU - U30_BMI270) should use default_sensor_weight (1.0)
        sample_info_imu: ProblematicSampleInfo = {
            "sensor_id": "U30_BMI270", # IMU
            "epistemic_uncertainty_score": 0.5, # Base contrib: 0.25
            "disagreement_score": 0.5,          # Base contrib: 0.15
            "aleatoric_uncertainty_score": 0.0
        } # Base priority = (0.25 + 0.15) * 1.0 = 0.4
          # Weighted priority = 0.4 * 1.0 = 0.4
        priority_imu = self.strategy.calculate_priority(sample_info=sample_info_imu, weakness_type="high_uncertainty_sample", sensor_type="IMU")
        self.assertAlmostEqual(priority_imu, 0.4)
        
        self.strategy.sensor_type_weights = {} # Reset

    def test_calculate_priority_low_recall_with_sensor_type_and_criticality(self):
        """Test low recall priority with sensor type weight and class criticality."""
        self.strategy.sensor_type_weights = {"ParticulateMatterSensor": 1.2}
        self.strategy.class_criticality_map = {"critical_pm_event": 1.5}
        
        # U20_SPS30 is ParticulateMatterSensor
        class_metrics: ClassMetrics = {
            "recall": 0.6, "class_name": "critical_pm_event", "sensor_id_scope": "U20_SPS30", # Custom key for test
            "precision":0.0, "f1_score":0.0, "support":0
        }
        # Base priority (recall part): 1.0 - 0.6 = 0.4
        # Criticality factor: 1.5
        # Sensor type weight: 1.2
        # Expected: (0.4 * 1.5) * 1.2 = 0.6 * 1.2 = 0.72
        priority = self.strategy.calculate_priority(
            class_metrics_info=class_metrics,
            weakness_type="low_recall_class",
            sensor_type="ParticulateMatterSensor" # Explicitly pass sensor_type
        )
        self.assertAlmostEqual(priority, 0.72)
        
        self.strategy.sensor_type_weights = {}
        self.strategy.class_criticality_map = {}


    # --- Tests for identify_weaknesses ---
    def test_identify_weaknesses_max_per_sensor_cap(self):
        """Test the max_weaknesses_per_sensor capping logic."""
        self.strategy.max_weaknesses_per_sensor = 2
        sensor1_id = "cap_sensor_1"
        sensor2_id = "cap_sensor_2"
        
        # Ensure these sensor IDs map to some types for the strategy to use them
        self.strategy.sensor_id_to_type_map[sensor1_id] = "TypeCap1"
        self.strategy.sensor_id_to_type_map[sensor2_id] = "TypeCap2"

        perf_data: ModelPerformanceData = {
            "model_version_evaluated": "v_cap", "dataset_identifier": "d_cap",
            "per_class_metrics": {}, "misclassified_samples": [],
            "uncertain_samples": [ # All qualify by default thresholds, priorities will be their scores
                {"raw_sample_id": "s1_unc1", "sensor_id": sensor1_id, "epistemic_uncertainty_score": 0.9}, # P=0.45
                {"raw_sample_id": "s1_unc2", "sensor_id": sensor1_id, "epistemic_uncertainty_score": 0.8}, # P=0.40
                {"raw_sample_id": "s1_unc3", "sensor_id": sensor1_id, "epistemic_uncertainty_score": 0.7}, # P=0.35 (should be capped)
                {"raw_sample_id": "s2_unc1", "sensor_id": sensor2_id, "epistemic_uncertainty_score": 0.85},# P=0.425
            ]
        }
        weaknesses = self.strategy.identify_weaknesses(perf_data)
        
        # Expected: s1_unc1, s1_unc2 (from sensor1), s2_unc1 (from sensor2)
        # Total 3 weaknesses, not 4.
        self.assertEqual(len(weaknesses), 3)
        
        sensor1_weakness_count = sum(1 for w in weaknesses if w["sensor_id"] == sensor1_id)
        sensor2_weakness_count = sum(1 for w in weaknesses if w["sensor_id"] == sensor2_id)
        
        self.assertEqual(sensor1_weakness_count, 2)
        self.assertEqual(sensor2_weakness_count, 1)
        
        weakness_ids = {w.get("raw_sample_id", w["details"].get("raw_sample_id")) for w in weaknesses}
        self.assertIn("s1_unc1", weakness_ids)
        self.assertIn("s1_unc2", weakness_ids)
        self.assertNotIn("s1_unc3", weakness_ids, "s1_unc3 should have been capped for sensor1")
        self.assertIn("s2_unc1", weakness_ids)
        
        # Clean up map for other tests
        del self.strategy.sensor_id_to_type_map[sensor1_id]
        del self.strategy.sensor_id_to_type_map[sensor2_id]
        self.strategy.max_weaknesses_per_sensor = 5 # Reset

    def test_identify_weaknesses_heterogeneous_target_sensor_id(self):
        """Test target_sensor_id filtering for Heterogeneous strategy."""
        target_sid = "het_target_s"
        other_sid = "het_other_s"
        self.strategy.sensor_id_to_type_map[target_sid] = "TypeTargetHet"
        self.strategy.sensor_id_to_type_map[other_sid] = "TypeOtherHet"

        perf_data: ModelPerformanceData = {
            "model_version_evaluated": "v_het_target", "dataset_identifier": "d_het_target",
            "per_class_metrics": { # Global
                "global_low": {"recall": 0.6, "precision":0.0, "f1_score":0.0, "support":10} # Qualifies (0.75 threshold)
            },
            "sensor_specific_metrics": {
                target_sid: {"per_class_metrics": {"target_low": {"recall": 0.5, "precision":0.0, "f1_score":0.0, "support":5}}}, # Qualifies
                other_sid: {"per_class_metrics": {"other_low": {"recall": 0.4, "precision":0.0, "f1_score":0.0, "support":5}}}    # Qualifies
            },
            "uncertain_samples": [
                {"raw_sample_id": "unc_target_het", "sensor_id": target_sid, "epistemic_uncertainty_score": 0.5}, # Qualifies
                {"raw_sample_id": "unc_other_het", "sensor_id": other_sid, "epistemic_uncertainty_score": 0.5}    # Qualifies
            ],
            "misclassified_samples": [
                {"raw_sample_id": "misc_target_het", "sensor_id": target_sid, "true_label": "X", "predicted_label": "Y"},
                {"raw_sample_id": "misc_other_het", "sensor_id": other_sid, "true_label": "P", "predicted_label": "Q"}
            ]
        }
        weaknesses = self.strategy.identify_weaknesses(perf_data, target_sensor_id=target_sid)
        
        # Expected: unc_target_het, misc_target_het, target_low (from sensor-specific)
        # Global low recall should NOT appear if target_sensor_id is specified and sensor-specific metrics for that sensor exist.
        self.assertEqual(len(weaknesses), 3, f"Expected 3 weaknesses (Het), got {len(weaknesses)}: {weaknesses}")
        
        unc_target_weakness_het = next((w for w in weaknesses if w.get("raw_sample_id") == "unc_target_het"), None)
        misc_target_weakness_het = next((w for w in weaknesses if w.get("raw_sample_id") == "misc_target_het"), None)
        recall_target_weakness_het = next((w for w in weaknesses if w.get("type") == "low_recall_class" and w["details"].get("class_name") == "target_low"), None)

        self.assertIsNotNone(unc_target_weakness_het, f"Uncertain sample 'unc_target_het' not found. Weaknesses: {weaknesses}")
        if unc_target_weakness_het: self.assertEqual(unc_target_weakness_het["sensor_id"], target_sid)
        
        self.assertIsNotNone(misc_target_weakness_het, f"Misclassified sample 'misc_target_het' not found. Weaknesses: {weaknesses}")
        if misc_target_weakness_het: self.assertEqual(misc_target_weakness_het["sensor_id"], target_sid)

        self.assertIsNotNone(recall_target_weakness_het, f"Low recall class 'target_low' (Het) not found. Weaknesses: {weaknesses}")
        if recall_target_weakness_het: self.assertEqual(recall_target_weakness_het["sensor_id"], target_sid)
        
        # Check that items from other_sid or global (if not overridden by target_sid specific) are not present
        global_low_present = any(w.get("type") == "low_recall_class" and w["details"].get("class_name") == "global_low" for w in weaknesses)
        other_low_present = any(w.get("type") == "low_recall_class" and w["details"].get("class_name") == "other_low" for w in weaknesses)
        unc_other_present = any(w.get("raw_sample_id") == "unc_other_het" for w in weaknesses)
        misc_other_present = any(w.get("raw_sample_id") == "misc_other_het" for w in weaknesses)

        self.assertFalse(global_low_present, f"Global low recall class should not be present when target_sid is specified and has its own recall metric. Weaknesses: {weaknesses}")
        self.assertFalse(other_low_present, f"Other sensor's low recall class should not be present. Weaknesses: {weaknesses}")
        self.assertFalse(unc_other_present, f"Other sensor's uncertain sample should not be present. Weaknesses: {weaknesses}")
        self.assertFalse(misc_other_present, f"Other sensor's misclassified sample should not be present. Weaknesses: {weaknesses}")
        
        del self.strategy.sensor_id_to_type_map[target_sid]
        del self.strategy.sensor_id_to_type_map[other_sid]

    def test_identify_weaknesses_heterogeneous_no_target_sensor_id_uses_all_metrics(self):
        """Test Heterogeneous strategy uses global and all sensor-specific metrics when no target_sensor_id."""
        sensor_a_id = "het_A_s"
        sensor_b_id = "het_B_s"
        self.strategy.sensor_id_to_type_map[sensor_a_id] = "TypeA_Het"
        self.strategy.sensor_id_to_type_map[sensor_b_id] = "TypeB_Het"

        perf_data: ModelPerformanceData = {
            "model_version_evaluated": "v_het_all", "dataset_identifier": "d_het_all",
            "per_class_metrics": { # Global
                "global_recall_low": {"recall": 0.6, "precision":0.0, "f1_score":0.0, "support":10} # Qualifies
            },
            "sensor_specific_metrics": {
                sensor_a_id: {"per_class_metrics": {"sensor_A_recall_low": {"recall": 0.5, "precision":0.0, "f1_score":0.0, "support":5}}}, # Qualifies
                sensor_b_id: {"per_class_metrics": {"sensor_B_recall_high": {"recall": 0.9, "precision":0.0, "f1_score":0.0, "support":5}}} # Does not qualify
            },
            "uncertain_samples": [
                {"raw_sample_id": "unc_A_het", "sensor_id": sensor_a_id, "epistemic_uncertainty_score": 0.5}, # Qualifies
            ],
            "misclassified_samples": []
        }
        weaknesses = self.strategy.identify_weaknesses(perf_data, target_sensor_id=None)
        
        # Expected: global_recall_low, sensor_A_recall_low, unc_A_het
        self.assertEqual(len(weaknesses), 3)
        
        class_weakness_names = {w["details"]["class_name"] for w in weaknesses if w["type"] == "low_recall_class"}
        sample_weakness_ids = {w.get("raw_sample_id", w["details"].get("raw_sample_id")) for w in weaknesses if w["type"] != "low_recall_class"}

        self.assertIn("global_recall_low", class_weakness_names)
        self.assertIn("sensor_A_recall_low", class_weakness_names)
        self.assertNotIn("sensor_B_recall_high", class_weakness_names)
        self.assertIn("unc_A_het", sample_weakness_ids)

        del self.strategy.sensor_id_to_type_map[sensor_a_id]
        del self.strategy.sensor_id_to_type_map[sensor_b_id]