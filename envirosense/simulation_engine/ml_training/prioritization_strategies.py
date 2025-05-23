"""
This module defines the PrioritizationStrategy interface and its concrete
implementations for the ActiveLearningManager. These strategies determine
how weak spots are identified and prioritized based on sensor characteristics
and model performance feedback.
"""
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TypedDict
import math # For isnan

# --- Configuration & Mappings ---
# TODO: In a production system, this mapping should be loaded from a configuration
# file, a database, or be dynamically discovered, rather than being hardcoded.
DEFAULT_SENSOR_ID_TO_TYPE_MAPPING: Dict[str, str] = {
    "U19_TFSGS": "VOCSensorArray",
    "U20_SPS30": "ParticulateMatterSensor",
    "U21_SHT85": "TempHumiditySensor",
    "U22_SHT85": "TempHumiditySensor",
    "U23_BMP388": "BarometricPressureSensor",
    "U24_FT205": "Anemometer",
    "U25_AS3935": "LightningDetector",
    "U26_Lepton35": "ThermalCamera",
    "U27_SPU0410HR5H": "AcousticSensor",
    "U28_SPU0410HR5H": "AcousticSensor",
    "U29_TFEMF": "EMFSensor",
    "U30_BMI270": "IMU",
}

# --- Type Definitions for Clarity (align with ModelInterface output) ---
# These TypedDicts help document the expected structure of model_performance_data.
# A more complete definition would reside with or be imported from the ModelInterface definition.

class SampleFeaturesSummary(TypedDict, total=False):
    method: str
    top_n_features: List[Dict[str, Any]] # Each dict: {"feature_path": str, "importance_score": float, "raw_value": Any}
    target_class_for_explanation: Optional[str]

class ProblematicSampleInfo(TypedDict, total=False):
    raw_sample_id: str
    sensor_id: str
    uncertainty_score: Optional[float]
    epistemic_uncertainty_score: Optional[float]
    aleatoric_uncertainty_score: Optional[float]
    disagreement_score: Optional[float]
    predicted_label_distribution: Optional[Dict[str, float]]
    sample_features_summary: Optional[SampleFeaturesSummary]
    original_scenario_id: Optional[str]
    scenario_timestep_seconds: Optional[float]
    # For misclassified
    true_label: Optional[str]
    predicted_label: Optional[str]
    confidence_of_prediction: Optional[float]


class ClassMetrics(TypedDict, total=False):
    recall: float
    precision: float
    f1_score: float
    support: int
    sensor_id: Optional[str] # If metrics are sensor-specific at this level

class SensorSpecificMetricsBundle(TypedDict, total=False):
    overall_accuracy_for_sensor_data: float # Example key
    # Key for per-class metrics should be consistent, e.g., "per_class_metrics"
    per_class_metrics: Dict[str, ClassMetrics]


class ModelPerformanceData(TypedDict, total=False):
    model_version_evaluated: str
    dataset_identifier: str
    overall_metrics: Dict[str, float]
    per_class_metrics: Dict[str, ClassMetrics] # Global per-class metrics
    sensor_specific_metrics: Dict[str, SensorSpecificMetricsBundle] # Keyed by sensor_id
    uncertain_samples: List[ProblematicSampleInfo]
    misclassified_samples: List[ProblematicSampleInfo]


# --- Strategy Interface and Implementations ---

class PrioritizationStrategy(ABC):
    """
    Abstract Base Class for defining different prioritization strategies
    used by the ActiveLearningManager.
    """

    def __init__(self, sensor_id_to_type_map: Optional[Dict[str, str]] = None):
        self.sensor_id_to_type_map = sensor_id_to_type_map or DEFAULT_SENSOR_ID_TO_TYPE_MAPPING

    def _generate_weakness_id(self, prefix: str, base_id: Optional[str] = None) -> str:
        """Helper to generate a unique weakness ID."""
        suffix = base_id if base_id else uuid.uuid4().hex[:8]
        return f"{prefix}_{suffix}"

    def _get_sensor_type_from_id(self, sensor_id: Optional[str]) -> Optional[str]:
        if not sensor_id:
            return None
        return self.sensor_id_to_type_map.get(sensor_id)
        
    def _validate_model_performance_data(self, data: ModelPerformanceData) -> bool:
        """Basic validation for the presence of expected top-level keys."""
        required_keys = ["uncertain_samples", "misclassified_samples", "per_class_metrics"]
        for key in required_keys:
            if key not in data:
                # In a real system, might log a warning or raise an error
                print(f"Warning: ModelPerformanceData missing required key: {key}")
                return False
        return True

    @abstractmethod
    def calculate_priority(
        self,
        sample_info: Optional[ProblematicSampleInfo] = None,
        class_metrics_info: Optional[ClassMetrics] = None, # Renamed for clarity
        weakness_type: Optional[str] = None,
        sensor_type: Optional[str] = None
    ) -> float:
        """
        Calculates a priority score (0.0 to 1.0) for an identified weakness.
        Implementations should strive for a consistent interpretation of the 0-1
        scale, where 1.0 represents the highest priority.
        """
        pass

    @abstractmethod
    def identify_weaknesses(
        self,
        model_performance_data: ModelPerformanceData,
        target_sensor_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Identifies and prioritizes weaknesses based on the provided model performance data.
        """
        pass


class RealTimeSensorPrioritizationStrategy(PrioritizationStrategy):
    """
    Prioritization strategy for high-velocity, low-latency sensors.
    Focuses on simpler, computationally less intensive metrics.
    """

    def __init__(self,
                 uncertainty_threshold: float = 0.7,
                 misclassification_priority_base: float = 0.8,
                 low_recall_threshold: float = 0.6,
                 sensor_id_to_type_map: Optional[Dict[str, str]] = None):
        super().__init__(sensor_id_to_type_map)
        self.uncertainty_threshold = uncertainty_threshold
        self.misclassification_priority_base = misclassification_priority_base
        self.low_recall_threshold = low_recall_threshold

    def calculate_priority(
        self,
        sample_info: Optional[ProblematicSampleInfo] = None,
        class_metrics_info: Optional[ClassMetrics] = None,
        weakness_type: Optional[str] = None,
        sensor_type: Optional[str] = None
    ) -> float:
        priority = 0.0
        if weakness_type == "high_uncertainty_sample" and sample_info:
            priority = sample_info.get("uncertainty_score", 0.0)
        elif weakness_type == "misclassified_region" and sample_info:
            priority = self.misclassification_priority_base + (sample_info.get("confidence_of_prediction", 0.0) * 0.1) # Higher if confident in wrong prediction
        elif weakness_type == "low_recall_class" and class_metrics_info:
            priority = 1.0 - class_metrics_info.get("recall", 1.0)
        return min(max(priority, 0.0), 1.0)

    def identify_weaknesses(
        self,
        model_performance_data: ModelPerformanceData,
        target_sensor_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not self._validate_model_performance_data(model_performance_data):
            return [] # Or raise error
            
        identified_weaknesses: List[Dict[str, Any]] = []
        strategy_prefix = "rt"

        for sample in model_performance_data.get("uncertain_samples", []):
            current_sensor_id = sample.get("sensor_id")
            if target_sensor_id and current_sensor_id != target_sensor_id:
                continue
            if sample.get("uncertainty_score", 0.0) >= self.uncertainty_threshold:
                priority = self.calculate_priority(sample_info=sample, weakness_type="high_uncertainty_sample")
                details = {k: v for k, v in sample.items() if k not in ["sensor_id", "raw_sample_id"]} # Exclude already top-level fields
                raw_id = sample.get("raw_sample_id")
                identified_weaknesses.append({
                    "weakness_id": self._generate_weakness_id(f"{strategy_prefix}_unc", raw_id),
                    "type": "high_uncertainty_sample", "priority": priority,
                    "sensor_id": current_sensor_id,
                    "raw_sample_id": raw_id, # Add raw_sample_id to top level
                    "details": details
                })

        for sample in model_performance_data.get("misclassified_samples", []):
            current_sensor_id = sample.get("sensor_id")
            if target_sensor_id and current_sensor_id != target_sensor_id:
                continue
            priority = self.calculate_priority(sample_info=sample, weakness_type="misclassified_region")
            details = {k: v for k, v in sample.items() if k not in ["sensor_id", "raw_sample_id"]}
            raw_id = sample.get("raw_sample_id")
            identified_weaknesses.append({
                "weakness_id": self._generate_weakness_id(f"{strategy_prefix}_misc", raw_id),
                "type": "misclassified_region", "priority": priority,
                "sensor_id": current_sensor_id,
                "raw_sample_id": raw_id, # Add raw_sample_id to top level
                "details": details
            })

        metrics_source = model_performance_data.get("per_class_metrics", {})
        source_sensor_id_for_metrics = None # Global metrics
        if target_sensor_id and "sensor_specific_metrics" in model_performance_data:
            sensor_metrics_bundle = model_performance_data["sensor_specific_metrics"].get(target_sensor_id, {})
            metrics_source = sensor_metrics_bundle.get("per_class_metrics", {})
            source_sensor_id_for_metrics = target_sensor_id
        
        for class_name, metrics_data in metrics_source.items():
            if metrics_data.get("recall", 1.0) < self.low_recall_threshold:
                priority = self.calculate_priority(class_metrics_info=metrics_data, weakness_type="low_recall_class")
                details = {"class_name": class_name, **metrics_data}
                identified_weaknesses.append({
                    "weakness_id": self._generate_weakness_id(f"{strategy_prefix}_recall_{class_name}", source_sensor_id_for_metrics),
                    "type": "low_recall_class", "priority": priority,
                    "sensor_id": source_sensor_id_for_metrics, "details": details
                })
        identified_weaknesses.sort(key=lambda x: x["priority"], reverse=True)
        return identified_weaknesses


class HighFidelitySensorPrioritizationStrategy(PrioritizationStrategy):
    """
    Prioritization strategy for low-frequency, high-value sensors.
    Employs robust metrics like epistemic uncertainty and model disagreement.
    Allows for class criticality weighting.
    """
    def __init__(self,
                 epistemic_threshold: float = 0.4,
                 disagreement_threshold: float = 0.3,
                 low_recall_threshold: float = 0.75,
                 epistemic_weight: float = 0.5, # Adjusted weights
                 disagreement_weight: float = 0.3,
                 misclassification_base_priority: float = 0.7,
                 class_criticality_map: Optional[Dict[str, float]] = None, # e.g., {"critical_event_A": 1.5}
                 sensor_id_to_type_map: Optional[Dict[str, str]] = None):
        super().__init__(sensor_id_to_type_map)
        self.epistemic_threshold = epistemic_threshold
        self.disagreement_threshold = disagreement_threshold
        self.low_recall_threshold = low_recall_threshold
        self.epistemic_weight = epistemic_weight
        self.disagreement_weight = disagreement_weight
        self.misclassification_base_priority = misclassification_base_priority
        self.class_criticality_map = class_criticality_map if class_criticality_map is not None else {}
        # Note: epistemic_weight + disagreement_weight do not need to sum to 1 if they are independent factors.
        # If they are meant to be parts of a whole, an assertion like:
        # assert math.isclose(epistemic_weight + disagreement_weight, 1.0), "Weights should sum to 1.0 for convex combination"
        # could be added if that's the design intent. Here, they are treated as contributing factors.

    def calculate_priority(
        self,
        sample_info: Optional[ProblematicSampleInfo] = None,
        class_metrics_info: Optional[ClassMetrics] = None,
        weakness_type: Optional[str] = None,
        sensor_type: Optional[str] = None
    ) -> float:
        priority = 0.0
        if weakness_type == "high_uncertainty_sample" and sample_info:
            epistemic = sample_info.get("epistemic_uncertainty_score", 0.0)
            disagreement = sample_info.get("disagreement_score", 0.0)
            aleatoric = sample_info.get("aleatoric_uncertainty_score", 0.0)
            priority = (epistemic * self.epistemic_weight) + \
                       (disagreement * self.disagreement_weight)
            priority *= (1.0 - aleatoric * 0.5) # Penalize if high aleatoric
        elif weakness_type == "misclassified_region" and sample_info:
            epistemic_contrib = sample_info.get("epistemic_uncertainty_score", 0.0) * 0.2
            priority = self.misclassification_base_priority + epistemic_contrib
            true_label = sample_info.get("true_label")
            if true_label and true_label in self.class_criticality_map:
                priority *= self.class_criticality_map[true_label]
        elif weakness_type == "low_recall_class" and class_metrics_info:
            priority = 1.0 - class_metrics_info.get("recall", 1.0)
            class_name = class_metrics_info.get("class_name") # Assuming class_name is in details
            if not class_name and sample_info: class_name = sample_info.get("true_label") # Fallback for context

            if class_name and class_name in self.class_criticality_map:
                priority *= self.class_criticality_map[class_name]
        return min(max(priority, 0.0), 1.0)

    def identify_weaknesses(
        self,
        model_performance_data: ModelPerformanceData,
        target_sensor_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not self._validate_model_performance_data(model_performance_data):
            return []
            
        identified_weaknesses: List[Dict[str, Any]] = []
        strategy_prefix = "hf"

        for sample in model_performance_data.get("uncertain_samples", []):
            current_sensor_id = sample.get("sensor_id")
            if target_sensor_id and current_sensor_id != target_sensor_id:
                continue
            is_weak_by_epistemic = sample.get("epistemic_uncertainty_score", 0.0) >= self.epistemic_threshold
            is_weak_by_disagreement = sample.get("disagreement_score", 0.0) >= self.disagreement_threshold
            if is_weak_by_epistemic or is_weak_by_disagreement:
                priority = self.calculate_priority(sample_info=sample, weakness_type="high_uncertainty_sample")
                details = {k: v for k, v in sample.items() if k not in ["sensor_id", "raw_sample_id"]}
                raw_id = sample.get("raw_sample_id")
                identified_weaknesses.append({
                    "weakness_id": self._generate_weakness_id(f"{strategy_prefix}_unc", raw_id),
                    "type": "high_uncertainty_sample", "priority": priority,
                    "sensor_id": current_sensor_id,
                    "raw_sample_id": raw_id, # Add raw_sample_id to top level
                    "details": details
                })
        
        for sample in model_performance_data.get("misclassified_samples", []):
            current_sensor_id = sample.get("sensor_id")
            if target_sensor_id and current_sensor_id != target_sensor_id:
                continue
            priority = self.calculate_priority(sample_info=sample, weakness_type="misclassified_region")
            details = {k: v for k, v in sample.items() if k not in ["sensor_id", "raw_sample_id"]}
            raw_id = sample.get("raw_sample_id")
            identified_weaknesses.append({
                "weakness_id": self._generate_weakness_id(f"{strategy_prefix}_misc", raw_id),
                "type": "misclassified_region", "priority": priority,
                "sensor_id": current_sensor_id,
                "raw_sample_id": raw_id, # Add raw_sample_id to top level
                "details": details
            })

        metrics_source = model_performance_data.get("per_class_metrics", {})
        source_sensor_id_for_metrics = None
        if target_sensor_id and "sensor_specific_metrics" in model_performance_data:
            sensor_metrics_bundle = model_performance_data["sensor_specific_metrics"].get(target_sensor_id, {})
            metrics_source = sensor_metrics_bundle.get("per_class_metrics", {})
            source_sensor_id_for_metrics = target_sensor_id

        for class_name, metrics_data in metrics_source.items():
            # Ensure class_name is part of metrics_data for calculate_priority
            metrics_data_with_class = {"class_name": class_name, **metrics_data}
            if metrics_data.get("recall", 1.0) < self.low_recall_threshold:
                priority = self.calculate_priority(class_metrics_info=metrics_data_with_class, weakness_type="low_recall_class")
                details = {"class_name": class_name, **metrics_data}
                identified_weaknesses.append({
                    "weakness_id": self._generate_weakness_id(f"{strategy_prefix}_recall_{class_name}", source_sensor_id_for_metrics),
                    "type": "low_recall_class", "priority": priority,
                    "sensor_id": source_sensor_id_for_metrics, "details": details
                })
        identified_weaknesses.sort(key=lambda x: x["priority"], reverse=True)
        return identified_weaknesses


class HeterogeneousSensorPrioritizationStrategy(PrioritizationStrategy):
    """
    Prioritization strategy for multi-modal sensor arrays.
    Balances informativeness and representativeness.
    Uses sensor type weighting and a simple diversity cap.
    Future enhancements: Advanced diversity metrics (e.g., feature space clustering).
    """
    def __init__(self,
                 sensor_type_weights: Optional[Dict[str, float]] = None,
                 default_sensor_weight: float = 1.0,
                 max_weaknesses_per_sensor: int = 5,
                 epistemic_threshold: float = 0.4,
                 disagreement_threshold: float = 0.3,
                 low_recall_threshold: float = 0.75,
                 epistemic_weight: float = 0.5,
                 disagreement_weight: float = 0.3,
                 misclassification_base_priority: float = 0.7,
                 class_criticality_map: Optional[Dict[str, float]] = None,
                 sensor_id_to_type_map: Optional[Dict[str, str]] = None):
        super().__init__(sensor_id_to_type_map)
        self.sensor_type_weights = sensor_type_weights if sensor_type_weights is not None else {}
        self.default_sensor_weight = default_sensor_weight
        self.max_weaknesses_per_sensor = max_weaknesses_per_sensor
        self.epistemic_threshold = epistemic_threshold
        self.disagreement_threshold = disagreement_threshold
        self.low_recall_threshold = low_recall_threshold
        self.epistemic_weight = epistemic_weight
        self.disagreement_weight = disagreement_weight
        self.misclassification_base_priority = misclassification_base_priority
        self.class_criticality_map = class_criticality_map if class_criticality_map is not None else {}

    def calculate_priority(
        self,
        sample_info: Optional[ProblematicSampleInfo] = None,
        class_metrics_info: Optional[ClassMetrics] = None,
        weakness_type: Optional[str] = None,
        sensor_type: Optional[str] = None # Explicitly passed sensor_type
    ) -> float:
        base_priority = 0.0
        current_sensor_type_for_weighting = sensor_type

        if weakness_type == "high_uncertainty_sample" and sample_info:
            epistemic = sample_info.get("epistemic_uncertainty_score", 0.0)
            disagreement = sample_info.get("disagreement_score", 0.0)
            aleatoric = sample_info.get("aleatoric_uncertainty_score", 0.0)
            base_priority = ((epistemic * self.epistemic_weight) + (disagreement * self.disagreement_weight)) * (1.0 - aleatoric * 0.5)
            if not current_sensor_type_for_weighting: current_sensor_type_for_weighting = self._get_sensor_type_from_id(sample_info.get("sensor_id"))
        elif weakness_type == "misclassified_region" and sample_info:
            epistemic_contrib = sample_info.get("epistemic_uncertainty_score", 0.0) * 0.2
            base_priority = self.misclassification_base_priority + epistemic_contrib
            true_label = sample_info.get("true_label")
            if true_label and true_label in self.class_criticality_map:
                base_priority *= self.class_criticality_map[true_label]
            if not current_sensor_type_for_weighting: current_sensor_type_for_weighting = self._get_sensor_type_from_id(sample_info.get("sensor_id"))
        elif weakness_type == "low_recall_class" and class_metrics_info:
            base_priority = 1.0 - class_metrics_info.get("recall", 1.0)
            class_name = class_metrics_info.get("class_name") # Assuming class_name is in details
            if class_name and class_name in self.class_criticality_map:
                base_priority *= self.class_criticality_map[class_name]
            if not current_sensor_type_for_weighting:
                # Try to get sensor_id from class_metrics_info if it was sensor-specific
                metric_sensor_id = class_metrics_info.get("sensor_id_scope") # A convention for this method
                current_sensor_type_for_weighting = self._get_sensor_type_from_id(metric_sensor_id)


        weight = self.default_sensor_weight
        if current_sensor_type_for_weighting and current_sensor_type_for_weighting in self.sensor_type_weights:
            weight = self.sensor_type_weights[current_sensor_type_for_weighting]
        
        return min(max(base_priority * weight, 0.0), 1.0)

    def identify_weaknesses(
        self,
        model_performance_data: ModelPerformanceData,
        target_sensor_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not self._validate_model_performance_data(model_performance_data):
            return []

        all_potential_weaknesses: List[Dict[str, Any]] = []
        strategy_prefix = "ht"

        for sample in model_performance_data.get("uncertain_samples", []):
            current_sensor_id = sample.get("sensor_id")
            if target_sensor_id and current_sensor_id != target_sensor_id:
                continue
            current_sensor_type = self._get_sensor_type_from_id(current_sensor_id)
            is_weak_by_epistemic = sample.get("epistemic_uncertainty_score", 0.0) >= self.epistemic_threshold
            is_weak_by_disagreement = sample.get("disagreement_score", 0.0) >= self.disagreement_threshold
            if is_weak_by_epistemic or is_weak_by_disagreement:
                priority = self.calculate_priority(sample_info=sample, weakness_type="high_uncertainty_sample", sensor_type=current_sensor_type)
                details = {k: v for k, v in sample.items() if k not in ["sensor_id", "raw_sample_id"]}
                raw_id = sample.get("raw_sample_id")
                all_potential_weaknesses.append({
                    "weakness_id": self._generate_weakness_id(f"{strategy_prefix}_unc", raw_id),
                    "type": "high_uncertainty_sample", "priority": priority,
                    "sensor_id": current_sensor_id,
                    "raw_sample_id": raw_id, # Add raw_sample_id to top level
                    "details": details
                })

        for sample in model_performance_data.get("misclassified_samples", []):
            current_sensor_id = sample.get("sensor_id")
            if target_sensor_id and current_sensor_id != target_sensor_id:
                continue
            current_sensor_type = self._get_sensor_type_from_id(current_sensor_id)
            priority = self.calculate_priority(sample_info=sample, weakness_type="misclassified_region", sensor_type=current_sensor_type)
            details = {k: v for k, v in sample.items() if k not in ["sensor_id", "raw_sample_id"]}
            raw_id = sample.get("raw_sample_id")
            all_potential_weaknesses.append({
                "weakness_id": self._generate_weakness_id(f"{strategy_prefix}_misc", raw_id),
                "type": "misclassified_region", "priority": priority,
                "sensor_id": current_sensor_id,
                "raw_sample_id": raw_id, # Add raw_sample_id to top level
                "details": details
            })

        metrics_to_process: List[Dict[str, Any]] = [] # List of (class_name, metrics_data, scope_sensor_id)
        if target_sensor_id:
            if "sensor_specific_metrics" in model_performance_data and \
               target_sensor_id in model_performance_data["sensor_specific_metrics"]:
                sensor_metrics_bundle = model_performance_data["sensor_specific_metrics"][target_sensor_id]
                for cn, mdata in sensor_metrics_bundle.get("per_class_metrics", {}).items():
                    metrics_to_process.append({"class_name": cn, "metrics": mdata, "scope_sensor_id": target_sensor_id})
        else:
            for cn, mdata in model_performance_data.get("per_class_metrics", {}).items(): # Global
                 metrics_to_process.append({"class_name": cn, "metrics": mdata, "scope_sensor_id": None})
            for s_id, s_metrics_bundle in model_performance_data.get("sensor_specific_metrics", {}).items():
                for cn, mdata in s_metrics_bundle.get("per_class_metrics", {}).items():
                    metrics_to_process.append({"class_name": cn, "metrics": mdata, "scope_sensor_id": s_id})
        
        for item in metrics_to_process:
            class_name, metrics_data, scope_sensor_id = item["class_name"], item["metrics"], item["scope_sensor_id"]
            current_sensor_type = self._get_sensor_type_from_id(scope_sensor_id)
            # Pass class_name into metrics_data for calculate_priority if it needs it
            metrics_data_with_class_name = {"class_name": class_name, **metrics_data, "sensor_id_scope": scope_sensor_id}

            if metrics_data.get("recall", 1.0) < self.low_recall_threshold:
                priority = self.calculate_priority(class_metrics_info=metrics_data_with_class_name, weakness_type="low_recall_class", sensor_type=current_sensor_type)
                details = {"class_name": class_name, **metrics_data}
                all_potential_weaknesses.append({
                    "weakness_id": self._generate_weakness_id(f"{strategy_prefix}_recall_{class_name}", scope_sensor_id),
                    "type": "low_recall_class", "priority": priority,
                    "sensor_id": scope_sensor_id, "details": details
                })
        
        all_potential_weaknesses.sort(key=lambda x: x["priority"], reverse=True)

        identified_weaknesses: List[Dict[str, Any]] = []
        sensor_weakness_counts: Dict[str, int] = {}
        for weak_spot in all_potential_weaknesses:
            s_id = weak_spot.get("sensor_id", "global_or_unspecified")
            if sensor_weakness_counts.get(s_id, 0) < self.max_weaknesses_per_sensor:
                identified_weaknesses.append(weak_spot)
                sensor_weakness_counts[s_id] = sensor_weakness_counts.get(s_id, 0) + 1
        
        return identified_weaknesses