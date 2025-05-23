"""
This module provides mock implementations of the interfaces defined in
interfaces.py (ModelInterface, ScenarioRepositoryInterface) for testing
the ActiveLearningManager and its strategies.
"""
from typing import Dict, Any, List, Union, Optional
import uuid

from .interfaces import ModelInterface, ScenarioRepositoryInterface, DatasetType, FilePathType
# ModelPerformanceData is defined in prioritization_strategies
from .prioritization_strategies import ModelPerformanceData
# Assuming BaseScenario would be defined or imported if concrete scenario objects were needed by mocks.
# For now, the repository methods can return Dict[str, Any] representing scenario data.
# from ..scenarios.base import BaseScenario # Example import

# Using the SENSOR_ID_TO_TYPE_MAPPING from prioritization_strategies for consistency in mocks
from .prioritization_strategies import DEFAULT_SENSOR_ID_TO_TYPE_MAPPING


class MockModelInterface(ModelInterface):
    """
    Mock implementation of the ModelInterface for testing purposes.
    Returns predefined or configurable model performance feedback.
    """
    def __init__(self, mock_performance_data: Optional[ModelPerformanceData] = None):
        self.mock_performance_data = mock_performance_data
        self.default_sensor_ids = ["U26_Lepton35", "U20_SPS30", "U30_BMI270", "U19_TFSGS"]

    def set_mock_performance_data(self, data: ModelPerformanceData):
        self.mock_performance_data = data

    def get_model_performance_feedback(
        self,
        evaluation_dataset: Union[DatasetType, FilePathType],
        model_version_tag: Optional[str] = None
    ) -> ModelPerformanceData:
        print(f"MockModelInterface: Received request for model performance feedback for dataset: {evaluation_dataset}, model_version: {model_version_tag}")
        if self.mock_performance_data:
            return self.mock_performance_data

        # Return a generic, somewhat detailed mock data structure if none is provided
        return {
            "model_version_evaluated": model_version_tag or "mock_model_v1.0",
            "dataset_identifier": str(evaluation_dataset)[:100], # Truncate if it's a long list
            "overall_metrics": {"accuracy": 0.85, "macro_f1_score": 0.82},
            "per_class_metrics": {
                "class_A": {"recall": 0.70, "precision": 0.65, "f1_score": 0.67, "support": 100},
                "class_B": {"recall": 0.90, "precision": 0.88, "f1_score": 0.89, "support": 150},
                "class_critical": {"recall": 0.55, "precision": 0.50, "f1_score": 0.52, "support": 20}
            },
            "sensor_specific_metrics": {
                self.default_sensor_ids[0]: {
                    "per_class_metrics": { # Simplified key for mock
                        "class_A": {"recall": 0.75, "precision": 0.70, "f1_score": 0.72, "support": 50}
                    }
                }
            },
            "uncertain_samples": [
                {
                    "raw_sample_id": "unc_sample_001", "sensor_id": self.default_sensor_ids[0],
                    "uncertainty_score": 0.8, "epistemic_uncertainty_score": 0.7, "aleatoric_uncertainty_score": 0.1, "disagreement_score": 0.6,
                    "predicted_label_distribution": {"class_A": 0.4, "class_B": 0.3, "class_C": 0.3},
                    "sample_features_summary": {"method": "SHAP", "top_n_features": [{"feature_path": f"sensor_readings_map.{self.default_sensor_ids[0]}.temp_avg", "importance_score": 0.5, "raw_value": 75.0}]},
                    "original_scenario_id": "scenario_heat_event", "scenario_timestep_seconds": 30.0
                },
                {
                    "raw_sample_id": "unc_sample_002", "sensor_id": self.default_sensor_ids[1],
                    "uncertainty_score": 0.75, "epistemic_uncertainty_score": 0.6, "aleatoric_uncertainty_score": 0.15,
                    "sample_features_summary": {"method": "SHAP", "top_n_features": [{"feature_path": f"sensor_readings_map.{self.default_sensor_ids[1]}.pm2_5", "importance_score": 0.4, "raw_value": 180.0}]},
                    "original_scenario_id": "scenario_smoky_condition", "scenario_timestep_seconds": 120.5
                }
            ],
            "misclassified_samples": [
                {
                    "raw_sample_id": "misc_sample_001", "sensor_id": self.default_sensor_ids[2],
                    "true_label": "class_B", "predicted_label": "class_A", "confidence_of_prediction": 0.9,
                    "epistemic_uncertainty_score": 0.2, # Low epistemic, but still misclassified
                    "sample_features_summary": {"method": "LIME", "top_n_features": [{"feature_path": f"sensor_readings_map.{self.default_sensor_ids[2]}.vibration_peak", "importance_score": 0.6, "raw_value": 5.5}]},
                    "original_scenario_id": "scenario_machine_A_running", "scenario_timestep_seconds": 10.0
                },
                 {
                    "raw_sample_id": "misc_sample_002_critical", "sensor_id": self.default_sensor_ids[3],
                    "true_label": "class_critical", "predicted_label": "class_A", "confidence_of_prediction": 0.7,
                    "sample_features_summary": {"method": "SHAP", "top_n_features": [{"feature_path": f"sensor_readings_map.{self.default_sensor_ids[3]}.voc_pattern_xyz", "importance_score": 0.8, "raw_value": "complex_pattern_data"}]},
                    "original_scenario_id": "scenario_subtle_leak", "scenario_timestep_seconds": 180.0
                }
            ]
        }


class MockScenarioRepository(ScenarioRepositoryInterface):
    """
    Mock implementation of the ScenarioRepositoryInterface for testing.
    Uses an in-memory dictionary to store scenario definitions.
    """
    def __init__(self, sensor_id_to_type_map: Optional[Dict[str, str]] = None):
        self.scenarios: Dict[str, Dict[str, Any]] = {} # scenario_id -> scenario_definition_dict
        self.sensor_id_to_type_map = sensor_id_to_type_map or DEFAULT_SENSOR_ID_TO_TYPE_MAPPING
        self._init_default_scenarios()

    def _init_default_scenarios(self):
        # Add a few default scenarios for testing
        self.scenarios["scenario_heat_event"] = {
            "scenario_definition_id": "scenario_heat_event", "name": "High Heat Event",
            "category": "ENVIRONMENTAL_EXTREME", "sensor_type_focus": "ThermalCamera",
            "specific_params_json": {"target_temp_c": 80, "duration_s": 60}
        }
        self.scenarios["scenario_smoky_condition"] = {
            "scenario_definition_id": "scenario_smoky_condition", "name": "Smoky Condition",
            "category": "HAZARD", "sensor_type_focus": "ParticulateMatterSensor",
            "specific_params_json": {"pm2_5_concentration_ug_m3": 200}
        }
        self.scenarios["scenario_machine_A_running"] = {
            "scenario_definition_id": "scenario_machine_A_running", "name": "Machine A Normal Operation",
            "category": "NORMAL_OPERATION", "sensor_type_focus": "IMU",
            "specific_params_json": {"machine_id": "A", "rpm": 1200}
        }
        self.scenarios["scenario_subtle_leak"] = {
            "scenario_definition_id": "scenario_subtle_leak", "name": "Subtle VOC Leak",
            "category": "HAZARD_PRECURSOR", "sensor_type_focus": "VOCSensorArray", "class_label_target": "class_critical",
            "specific_params_json": {"leak_rate_ppb_s": 5, "compound": "methane"}
        }
        self.scenarios["default_exploration_thermal"] = {
            "scenario_definition_id": "default_exploration_thermal", "name": "Default Thermal Exploration",
            "category": "EXPLORATION", "sensor_type_focus": "ThermalCamera",
            "specific_params_json": {"temp_range_c": [0,100]}
        }

    def _get_sensor_type_from_id(self, sensor_id: Optional[str]) -> Optional[str]:
        if not sensor_id: return None
        return self.sensor_id_to_type_map.get(sensor_id)

    def get_scenario_by_id(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        print(f"MockScenarioRepository: get_scenario_by_id called for ID: {scenario_id}")
        return self.scenarios.get(scenario_id) # Returns a dict, not BaseScenario object for mock

    def get_scenarios_by_category(self, category: str, sensor_type: Optional[str] = None, num_to_get: int = 5) -> List[Dict[str, Any]]:
        print(f"MockScenarioRepository: get_scenarios_by_category: {category}, sensor_type: {sensor_type}")
        matched = []
        for scen_id, scen_def in self.scenarios.items():
            if scen_def.get("category") == category:
                if sensor_type and scen_def.get("sensor_type_focus") != sensor_type:
                    continue
                matched.append(scen_def)
        return matched[:num_to_get]

    def get_scenarios_by_class_label(self, class_label: str, sensor_type: Optional[str] = None, num_to_get: int = 5) -> List[Dict[str, Any]]:
        print(f"MockScenarioRepository: get_scenarios_by_class_label: {class_label}, sensor_type: {sensor_type}")
        matched = []
        for scen_id, scen_def in self.scenarios.items():
            if scen_def.get("class_label_target") == class_label: # Assuming a field for this in mock
                if sensor_type and scen_def.get("sensor_type_focus") != sensor_type:
                    continue
                matched.append(scen_def)
        return matched[:num_to_get]

    def create_scenario_variation(
        self, base_scenario_data: Dict[str, Any], new_id_suffix: str,
        param_modifications: Dict[str, Any], sensor_context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        print(f"MockScenarioRepository: create_scenario_variation for base: {base_scenario_data.get('scenario_definition_id')}, suffix: {new_id_suffix}")
        new_id = f"{base_scenario_data.get('scenario_definition_id', 'base')}{new_id_suffix}"
        # Deep copy and modify for mock. In reality, this would involve BaseScenario.clone() etc.
        import copy
        variation_def = copy.deepcopy(base_scenario_data)
        variation_def["scenario_definition_id"] = new_id
        variation_def["name"] = f"{variation_def.get('name', 'Scenario')} Variation {new_id_suffix}"
        
        # Apply param_modifications (simplified for mock)
        current_specific_params = variation_def.get("specific_params_json", {})
        if isinstance(current_specific_params, dict): # Assuming it's already a dict for mock
            current_specific_params.update(param_modifications)
            variation_def["specific_params_json"] = current_specific_params
        
        self.scenarios[new_id] = variation_def
        return variation_def

    def craft_scenario_from_features(
        self, features_summary: Dict[str, Any], base_id: str,
        target_class: Optional[str] = None, sensor_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        print(f"MockScenarioRepository: craft_scenario_from_features for base_id: {base_id}, sensor_type: {sensor_type}")
        new_id = f"crafted_{base_id}"
        crafted_def = {
            "scenario_definition_id": new_id,
            "name": f"Crafted Scenario {base_id} for {sensor_type or 'Generic'}",
            "category": "ACTIVE_LEARNING_CRAFTED",
            "sensor_type_focus": sensor_type,
            "class_label_target": target_class,
            "specific_params_json": {
                "alm_triggering_features": features_summary,
                "note": "Parameters here would be derived by inverse design heuristics."
            }
        }
        self.scenarios[new_id] = crafted_def
        return crafted_def

    def get_default_exploration_scenario(
        self, scenario_id: str, sensor_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        print(f"MockScenarioRepository: get_default_exploration_scenario for ID: {scenario_id}, sensor_type: {sensor_type}")
        if sensor_type == "ThermalCamera" and "default_exploration_thermal" in self.scenarios:
            return self.scenarios["default_exploration_thermal"]
        
        # Generic default
        default_def = {
            "scenario_definition_id": scenario_id,
            "name": f"Default Exploration for {sensor_type or 'Any Sensor'}",
            "category": "EXPLORATION",
            "sensor_type_focus": sensor_type,
            "specific_params_json": {"exploration_param": "wide_range"}
        }
        self.scenarios[scenario_id] = default_def # Save it if created
        return default_def

    def save_scenario_definition(self, scenario_def: Dict[str, Any]) -> str:
        scen_id = scenario_def.get("scenario_definition_id", f"scen_{uuid.uuid4().hex[:8]}")
        scenario_def["scenario_definition_id"] = scen_id # Ensure it has an ID
        self.scenarios[scen_id] = scenario_def
        print(f"MockScenarioRepository: Saved scenario definition with ID: {scen_id}")
        return scen_id

    def update_scenario_definition(self, scenario_def_id: str, updates: Dict[str, Any]) -> bool:
        if scenario_def_id in self.scenarios:
            self.scenarios[scenario_def_id].update(updates) # Simple dict update for mock
            print(f"MockScenarioRepository: Updated scenario definition ID: {scenario_def_id}")
            return True
        print(f"MockScenarioRepository: Update failed, scenario ID not found: {scenario_def_id}")
        return False
class MockMLDataGenerator:
    """
    Mock implementation of the MLDataGenerator for testing purposes.
    Allows configuration of return values and tracks method calls.
    """
    def __init__(self,
                 default_sample_output: Optional[List[Dict[str, Any]]] = None,
                 default_export_output: Optional[Any] = None):
        """
        Initializes the MockMLDataGenerator.

        Args:
            default_sample_output: Default list of dicts for generate_training_dataset.
            default_export_output: Default output for _export_data.
        """
        self.default_sample_output = default_sample_output if default_sample_output is not None else []
        self.default_export_output = default_export_output

        self.generate_training_dataset_calls: List[Dict[str, Any]] = []
        self.export_data_calls: List[Dict[str, Any]] = []

        self.generate_training_dataset_return_values: List[Any] = []
        self.generate_training_dataset_side_effects: List[Union[Exception, Any]] = []
        self.export_data_return_values: List[Any] = []
        self.export_data_side_effects: List[Union[Exception, Any]] = []

    def generate_training_dataset(self,
                                  scenarios: List[Any],
                                  samples_per_scenario: int,
                                  output_format: str) -> Optional[Any]:
        """Mocks the generation of a training dataset."""
        self.generate_training_dataset_calls.append({
            "scenarios": scenarios,
            "samples_per_scenario": samples_per_scenario,
            "output_format": output_format
        })

        if self.generate_training_dataset_side_effects:
            effect = self.generate_training_dataset_side_effects.pop(0)
            if isinstance(effect, Exception):
                raise effect
            return effect
        
        if self.generate_training_dataset_return_values:
            return self.generate_training_dataset_return_values.pop(0)
        
        # Default behavior: return a list of mock samples if scenarios are provided
        if scenarios:
            mock_samples = []
            for i, scenario in enumerate(scenarios):
                for j in range(samples_per_scenario):
                    scenario_id_val = scenario.get("scenario_definition_id", f"unknown_scenario_{i}") if isinstance(scenario, dict) else f"unknown_scenario_obj_{i}"
                    mock_samples.append({
                        "sample_id": f"mock_sample_{uuid.uuid4().hex[:6]}_{i}_{j}",
                        "feature_vector": [0.1, 0.2, 0.3 + (i*0.1) + (j*0.01)], # Make them slightly unique
                        "label": f"mock_label_for_{scenario_id_val}",
                        "generating_scenario_id": scenario_id_val
                    })
            if output_format == "list_of_dicts": # As used by ActiveLearningManager internally
                 return mock_samples
            # If other formats were expected, they could be handled here or return default
        
        return self.default_sample_output # Fallback to default_sample_output

    def _export_data(self,
                     data: List[Dict[str, Any]],
                     output_format: str,
                     dataset_name: str) -> Optional[Any]:
        """Mocks the export of data."""
        self.export_data_calls.append({
            "data": data,
            "output_format": output_format,
            "dataset_name": dataset_name
        })

        if self.export_data_side_effects:
            effect = self.export_data_side_effects.pop(0)
            if isinstance(effect, Exception):
                raise effect
            return effect
        
        if self.export_data_return_values:
            return self.export_data_return_values.pop(0)
        
        if output_format == "list_of_dicts": # If ALM requests this format directly
            return data
            
        # Default behavior for export could be returning a path or the data itself
        return self.default_export_output if self.default_export_output is not None else f"{dataset_name}.mocked_{output_format}"


    # Configuration methods
    def set_generate_training_dataset_return_values(self, values: List[Any]):
        self.generate_training_dataset_return_values = list(values)

    def add_generate_training_dataset_return_value(self, value: Any):
        self.generate_training_dataset_return_values.append(value)

    def set_generate_training_dataset_side_effects(self, effects: List[Union[Exception, Any]]):
        self.generate_training_dataset_side_effects = list(effects)

    def add_generate_training_dataset_side_effect(self, effect: Union[Exception, Any]):
        self.generate_training_dataset_side_effects.append(effect)

    def set_export_data_return_values(self, values: List[Any]):
        self.export_data_return_values = list(values)

    def add_export_data_return_value(self, value: Any):
        self.export_data_return_values.append(value)
    
    def set_export_data_side_effects(self, effects: List[Union[Exception, Any]]):
        self.export_data_side_effects = list(effects)

    def add_export_data_side_effect(self, effect: Union[Exception, Any]):
        self.export_data_side_effects.append(effect)

    def reset_calls(self):
        """Resets the call history for all mocked methods."""
        self.generate_training_dataset_calls = []
        self.export_data_calls = []

    def reset_behavior(self):
        """Resets configured return values and side effects for all mocked methods."""
        self.generate_training_dataset_return_values = []
        self.generate_training_dataset_side_effects = []
        self.export_data_return_values = []
        self.export_data_side_effects = []
        # Note: default_sample_output and default_export_output are not reset by this method