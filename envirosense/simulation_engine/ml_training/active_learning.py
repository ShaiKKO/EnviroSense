"""
This module contains the ActiveLearningManager class, responsible for
guiding the data generation process based on model performance and uncertainty,
to continuously improve ML models in an adaptive, sensor-specific manner.
"""
import time
import uuid
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .data_generator import MLDataGenerator
    from .interfaces import ModelInterface, ScenarioRepositoryInterface, ModelPerformanceData
    from .prioritization_strategies import PrioritizationStrategy, RealTimeSensorPrioritizationStrategy, SENSOR_ID_TO_TYPE_MAPPING
    # from ..scenarios.base import BaseScenario # Using Any for now for BaseScenario type hints


class ActiveLearningManager:
    """
    Manages active learning loops by analyzing model weaknesses and
    guiding the generation of targeted training data. It uses adaptive
    strategies based on sensor types and performance feedback.
    """

    def __init__(self,
                 data_generator: 'MLDataGenerator',
                 scenario_repository: 'ScenarioRepositoryInterface',
                 model_interface: 'ModelInterface',
                 prioritization_strategy: 'PrioritizationStrategy',
                 sensor_id_to_type_map: Optional[Dict[str, str]] = None):
        """
        Initializes the ActiveLearningManager.

        Args:
            data_generator: An instance of MLDataGenerator to request new samples.
            scenario_repository: An implementation of ScenarioRepositoryInterface.
            model_interface: An implementation of ModelInterface.
            prioritization_strategy: An instance of a PrioritizationStrategy.
            sensor_id_to_type_map: Optional. Overrides the default sensor ID to type mapping.
        """
        self.data_generator = data_generator
        self.scenario_repository = scenario_repository
        self.model_interface = model_interface
        self.prioritization_strategy = prioritization_strategy
        self.sensor_id_to_type_map = sensor_id_to_type_map or SENSOR_ID_TO_TYPE_MAPPING # Use default if None
        
        # Ensure the strategy also has access to the map if it needs its own copy or different one
        if hasattr(self.prioritization_strategy, 'sensor_id_to_type_map') and \
           self.prioritization_strategy.sensor_id_to_type_map is None: # type: ignore
            self.prioritization_strategy.sensor_id_to_type_map = self.sensor_id_to_type_map


        print(f"ActiveLearningManager initialized with strategy: {type(prioritization_strategy).__name__}")

    def _get_sensor_type_from_id(self, sensor_id: Optional[str]) -> Optional[str]:
        if not sensor_id:
            return None
        return self.sensor_id_to_type_map.get(sensor_id)

    def _generate_suggestion_id(self) -> str:
        return f"sugg_{uuid.uuid4().hex[:12]}"

    def identify_weak_spots(self,
                            model_performance_data: 'ModelPerformanceData',
                            target_sensor_id: Optional[str] = None
                           ) -> List[Dict[str, Any]]:
        """
        Analyzes model performance data using the configured prioritization strategy
        to identify areas for new data.

        Args:
            model_performance_data: Structured feedback from the ModelInterface.
            target_sensor_id: Optional. Focus analysis on a specific sensor.

        Returns:
            A list of identified weak spot dictionaries, structured as per the plan.
        """
        print(f"Identifying weak spots using {type(self.prioritization_strategy).__name__}...")
        if not self.model_interface:
            print("Error: ModelInterface not available.")
            return []
        
        weaknesses = self.prioritization_strategy.identify_weaknesses(
            model_performance_data,
            target_sensor_id=target_sensor_id
        )
        print(f"Identified {len(weaknesses)} weak spots.")
        return weaknesses

    def generate_targeted_samples(self,
                                  weak_spots: List[Dict[str, Any]],
                                  num_samples_per_spot_type: int = 50, # Samples per identified weakness type/scenario
                                  output_format: str = "list_of_dicts",
                                  dataset_name_prefix: str = "alm_targeted"
                                 ) -> Optional[Any]:
        """
        Generates new training samples specifically targeting the identified weak spots.
        This involves creating or modifying scenarios based on weak spots and then
        using the MLDataGenerator.

        Args:
            weak_spots: A list of refined weakness dictionaries from identify_weak_spots.
            num_samples_per_spot_type: Target number of samples per generated/selected scenario.
            output_format: Desired output format for the generated data (passed to MLDataGenerator).
            dataset_name_prefix: Prefix for the output dataset name.

        Returns:
            Combined dataset from all targeted generation runs, or None if errors occur.
        """
        if not self.data_generator:
            print("Error: MLDataGenerator not available.")
            return None
        if not self.scenario_repository:
            print("Error: ScenarioRepository not available.")
            return None
        if not weak_spots:
            print("No weak spots provided, no targeted samples will be generated.")
            return None

        print(f"Generating targeted samples for {len(weak_spots)} identified weak spots...")
        all_new_samples: List[Dict[str, Any]] = []
        
        for i, spot in enumerate(weak_spots):
            spot_type = spot.get("type")
            spot_details = spot.get("details", {})
            spot_sensor_id = spot.get("sensor_id")
            spot_sensor_type = self._get_sensor_type_from_id(spot_sensor_id)

            print(f"  Targeting weakness ({i+1}/{len(weak_spots)}): ID '{spot.get('weakness_id')}', Type '{spot_type}', Sensor '{spot_sensor_id}'")
            
            targeted_scenarios_for_spot: List[Any] = [] # Should be List[BaseScenario]

            if spot_type == "high_uncertainty_sample" or spot_type == "misclassified_region":
                original_scenario_id = spot_details.get("original_scenario_id")
                features_summary = spot_details.get("sample_features_summary")

                if original_scenario_id:
                    base_scenario = self.scenario_repository.get_scenario_by_id(original_scenario_id)
                    if base_scenario:
                        # Heuristic for param_mods based on features_summary
                        # This is a simplified placeholder for the complex "inverse design"
                        param_mods = {"alm_triggering_weak_spot_id": spot.get("weakness_id")}
                        if features_summary and features_summary.get("top_n_features"):
                            param_mods["alm_focus_feature"] = features_summary["top_n_features"][0].get("feature_path")
                            param_mods["alm_focus_feature_value"] = features_summary["top_n_features"][0].get("raw_value")
                        
                        sensor_context_for_repo = {"sensor_id": spot_sensor_id, "sensor_type": spot_sensor_type} if spot_sensor_id else None
                        
                        try:
                            variation_scenario = self.scenario_repository.create_scenario_variation(
                                base_scenario=base_scenario,
                                new_id_suffix=f"_alm_var_{spot.get('weakness_id', i)}",
                                param_modifications=param_mods,
                                sensor_context=sensor_context_for_repo
                            )
                            if variation_scenario:
                                targeted_scenarios_for_spot.append(variation_scenario)
                                print(f"    Created variation for scenario ID '{original_scenario_id}'.")
                        except Exception as e_var:
                            print(f"    Could not create variation for {original_scenario_id}: {e_var}")
                
                if not targeted_scenarios_for_spot and features_summary: # If no base or variation failed
                    try:
                        crafted_scenario = self.scenario_repository.craft_scenario_from_features(
                            features_summary=features_summary,
                            base_id=f"alm_crafted_{spot.get('weakness_id', i)}",
                            target_class=spot_details.get("true_label") or spot_details.get("predicted_label"), # if misclassified
                            sensor_type=spot_sensor_type
                        )
                        if crafted_scenario:
                            targeted_scenarios_for_spot.append(crafted_scenario)
                            print(f"    Crafted new scenario based on features for sensor type '{spot_sensor_type}'.")
                    except Exception as e_craft:
                         print(f"    Could not craft scenario from features: {e_craft}")

            elif spot_type == "low_recall_class":
                class_name = spot_details.get("class_name")
                if class_name:
                    try:
                        scenarios_for_class = self.scenario_repository.get_scenarios_by_class_label(
                            class_label=class_name,
                            sensor_type=spot_sensor_type,
                            num_to_get=2 # Get a couple of base scenarios for this class
                        )
                        targeted_scenarios_for_spot.extend(scenarios_for_class)
                        print(f"    Selected {len(scenarios_for_class)} existing scenarios for class '{class_name}', sensor type '{spot_sensor_type}'.")
                    except Exception as e_class_scen:
                        print(f"    Error getting scenarios by class label: {e_class_scen}")
            
            if not targeted_scenarios_for_spot:
                print(f"    No specific scenario generated/selected, attempting default exploration for sensor type '{spot_sensor_type}'.")
                try:
                    default_scenario = self.scenario_repository.get_default_exploration_scenario(
                        scenario_id=f"alm_explore_{spot.get('weakness_id', i)}",
                        sensor_type=spot_sensor_type
                    )
                    if default_scenario:
                        targeted_scenarios_for_spot.append(default_scenario)
                except Exception as e_def_scen:
                    print(f"    Error getting default exploration scenario: {e_def_scen}")

            if targeted_scenarios_for_spot:
                print(f"    Attempting to generate data for {len(targeted_scenarios_for_spot)} scenario(s) for this spot.")
                # samples_per_scenario_run = max(10, num_samples_per_spot_type // len(targeted_scenarios_for_spot))
                samples_per_scenario_run = num_samples_per_spot_type # Generate N for each scenario found/created for the spot
                
                dataset_chunk = self.data_generator.generate_training_dataset(
                    scenarios=targeted_scenarios_for_spot,
                    samples_per_scenario=samples_per_scenario_run,
                    output_format="list_of_dicts", # Internal format for aggregation
                )
                if isinstance(dataset_chunk, list):
                    all_new_samples.extend(dataset_chunk)
                    print(f"    Generated {len(dataset_chunk)} samples for this spot.")
                elif dataset_chunk is None: # If generator returns None on error
                     print(f"    MLDataGenerator returned None for this spot's scenarios.")
            else:
                print(f"    Could not generate/select any scenarios for spot: {spot.get('weakness_id')}")
        
        if not all_new_samples:
            print("No new targeted samples were generated in this cycle.")
            return None
            
        print(f"Total new targeted samples generated across all spots: {len(all_new_samples)}")
        
        final_dataset_name = f"{dataset_name_prefix}_{time.strftime('%Y%m%d_%H%M%S')}"
        # _export_data is an internal method of MLDataGenerator, ensure it's accessible or use public API
        if hasattr(self.data_generator, '_export_data'):
             return self.data_generator._export_data(all_new_samples, output_format, final_dataset_name) # type: ignore
        else:
            print("Warning: MLDataGenerator does not have _export_data. Returning raw list.")
            if output_format == "list_of_dicts":
                return all_new_samples
            else:
                print(f"Error: Cannot provide {output_format} as _export_data is missing.")
                return None


    def suggest_scenario_modifications(self, weakness_analysis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Suggests modifications to existing scenario parameters or new scenario
        configurations based on identified weaknesses.

        Args:
            weakness_analysis: Output from `identify_weak_spots`.

        Returns:
            A list of dictionaries, each suggesting a scenario modification or creation,
            structured as per the active-learning-enhancement-plan.md.
        """
        print(f"Suggesting scenario modifications based on {len(weakness_analysis)} weak spots...")
        suggestions: List[Dict[str, Any]] = []

        for spot in weakness_analysis:
            suggestion_id = self._generate_suggestion_id()
            spot_priority = spot.get("priority", 0.0)
            spot_details = spot.get("details", {})
            spot_sensor_id = spot.get("sensor_id")
            spot_sensor_type = self._get_sensor_type_from_id(spot_sensor_id)

            # Heuristic for suggestion_confidence
            suggestion_confidence = spot_priority # Start with weak spot priority
            if spot.get("type") == "high_uncertainty_sample":
                suggestion_confidence += spot_details.get("epistemic_uncertainty_score", 0.0) * 0.2
            if spot_details.get("sample_features_summary"):
                suggestion_confidence += 0.1 # Bonus if features are available
            suggestion_confidence = min(max(suggestion_confidence, 0.0), 1.0)

            suggestion_base = {
                "suggestion_id": suggestion_id,
                "reason": f"Addressing weakness ID: {spot.get('weakness_id')}, Type: {spot.get('type')}, Sensor: {spot_sensor_id}",
                "priority": spot_priority,
                "suggestion_confidence": suggestion_confidence,
                "originating_weak_spot_ids": [spot.get("weakness_id")],
                "original_weak_spot_info": spot
            }

            current_suggestion: Dict[str, Any] = {}

            if spot.get("type") == "high_uncertainty_sample" or spot.get("type") == "misclassified_region":
                original_scenario_id = spot_details.get("original_scenario_id")
                features_summary = spot_details.get("sample_features_summary")

                if original_scenario_id:
                    current_suggestion = {
                        **suggestion_base,
                        "suggestion_type": "modify_existing_scenario",
                        "target_scenario_definition_id": original_scenario_id,
                        "suggested_modifications_for_specific_params": [],
                        "suggested_metadata_updates": {
                            "tags": {"operation": "add_if_not_exists", "value": f"alm_focus_{spot.get('weakness_id')}"}
                        }
                    }
                    if features_summary and features_summary.get("top_n_features"):
                        for feat in features_summary["top_n_features"][:2]: # Suggest for top 2 features
                            current_suggestion["suggested_modifications_for_specific_params"].append({
                                "param_path": f"heuristic_map({feat.get('feature_path')})", # Needs actual mapping logic
                                "operation": "vary_around_value",
                                "value": feat.get("raw_value"),
                                "comment": f"Feature '{feat.get('feature_path')}' (value: {feat.get('raw_value')}) had importance {feat.get('importance_score', 'N/A')}"
                            })
                else: # No original scenario, or suggest creating new even if original exists
                    current_suggestion = {
                        **suggestion_base,
                        "suggestion_type": "create_new_scenario",
                        "basis_for_new_scenario": {
                            "scenario_definition_id_suggestion": f"alm_new_{spot.get('weakness_id')}",
                            "name": f"ALM New Scenario for Weakness {spot.get('weakness_id')}",
                            "description": f"Auto-generated by ALM to address {spot.get('type')} on sensor {spot_sensor_id} related to features: {str(features_summary)[:100]}...",
                            "category": "ACTIVE_LEARNING_TARGETED",
                            "tags": [f"alm_generated", f"sensor_{spot_sensor_id or 'any'}", f"type_{spot_sensor_type or 'any'}"],
                            "specific_params_json_template": {"alm_focus_features": features_summary}, # Heuristic
                            "author": "ActiveLearningManager"
                        }
                    }
            elif spot.get("type") == "low_recall_class":
                class_name = spot_details.get("class_name")
                current_suggestion = {
                    **suggestion_base,
                    "suggestion_type": "create_new_scenario", # Or could be "modify_existing_scenario_to_increase_class_yield"
                    "basis_for_new_scenario": {
                        "scenario_definition_id_suggestion": f"alm_boost_{class_name}_{spot_sensor_id or 'any'}",
                        "name": f"ALM Scenario to Boost Class: {class_name} for Sensor: {spot_sensor_id or 'any'}",
                        "description": f"Auto-generated by ALM to increase data for class '{class_name}' on sensor {spot_sensor_id}, due to low recall.",
                        "category": "ACTIVE_LEARNING_CLASS_BOOST",
                        "tags": [f"alm_generated", f"class_{class_name}", f"sensor_{spot_sensor_id or 'any'}"],
                        "specific_params_json_template": {"target_class_to_boost": class_name, "target_sensor_type": spot_sensor_type}, # Heuristic
                        "author": "ActiveLearningManager"
                    }
                }
            
            if current_suggestion:
                suggestions.append(current_suggestion)
            else:
                 print(f"  Could not formulate a suggestion for weakness: {spot.get('weakness_id')}")


        return suggestions

    def process_real_world_feedback(self, feedback_data: Dict[str, Any]):
        """
        Processes feedback from real-world model deployment to inform
        future data generation and scenario creation. (Placeholder)
        """
        print(f"Processing real-world feedback: {list(feedback_data.keys())}")
        # Future implementation:
        # - Identify discrepancies between simulation and real-world.
        # - Update scenario parameters or create new scenarios to better match reality.
        # - Log areas where simulation needs improvement.
        pass

# Main execution block for conceptual testing (to be replaced by proper unit/integration tests)
if __name__ == '__main__':
    print("ActiveLearningManager module loaded. Conceptual __main__ block.")
    # This block would require mock implementations of MLDataGenerator,
    # ModelInterface, ScenarioRepositoryInterface, and a PrioritizationStrategy
    # to demonstrate a full conceptual run.
    # For now, it serves as a basic check that the file is syntactically valid.

    # Example:
    # mock_dg = ...
    # mock_sr = ...
    # mock_mi = ...
    # rt_strategy = RealTimeSensorPrioritizationStrategy()
    # alm = ActiveLearningManager(mock_dg, mock_sr, mock_mi, rt_strategy)
    #
    # mock_perf_data = mock_mi.get_model_performance_feedback("dummy_dataset")
    # weak_spots = alm.identify_weak_spots(mock_perf_data)
    # if weak_spots:
    #    suggestions = alm.suggest_scenario_modifications(weak_spots)
    #    print(f"Suggestions: {suggestions}")
    #    new_data = alm.generate_targeted_samples(weak_spots)
    #    print(f"New data generated (path/list): {new_data}")