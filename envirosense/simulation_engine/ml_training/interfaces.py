"""
This module defines abstract base classes for interfaces used by the
ActiveLearningManager, such as the ModelInterface and ScenarioRepositoryInterface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Union, Optional

# Represents a list of MLDataSample-like dictionaries or a file path
DatasetType = List[Dict[str, Any]]
FilePathType = str
# BaseScenario type hint will be imported where needed, using forward reference if necessary
# from envirosense.simulation_engine.scenarios.base import BaseScenario


class ModelInterface(ABC):
    """
    Abstract Base Class for interfacing with an ML model.
    This interface allows the ActiveLearningManager to get performance feedback,
    predictions, and uncertainty scores without needing to know the specifics
    of the model's implementation or framework.
    """

    @abstractmethod
    def get_model_performance_feedback(
        self,
        evaluation_dataset: Union[DatasetType, FilePathType],
        model_version_tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates the model on the provided dataset and returns structured feedback.

        Args:
            evaluation_dataset: Either a list of MLDataSample-like dictionaries
                                or a file path to a dataset (e.g., an Avro file).
            model_version_tag: Optional. Specifies a particular version/checkpoint of the
                               model to use for evaluation. If None, uses the current/default.

        Returns:
            A dictionary structured as specified in the
            active-learning-enhancement-plan.md, including overall_metrics,
            per_class_metrics, sensor_specific_metrics (optional),
            uncertain_samples (with sample_features_summary using Feature Importance),
            and misclassified_samples (with sample_features_summary).
            Uncertainty scores may include epistemic, aleatoric, and disagreement scores.
        """
        pass


class ScenarioRepositoryInterface(ABC):
    """
    Abstract Base Class for a repository that manages scenario definitions.
    This allows the ActiveLearningManager to retrieve, create, and modify
    scenarios in a sensor-adaptive manner.
    """

    @abstractmethod
    def get_scenario_by_id(self, scenario_id: str) -> Optional[Any]: # -> Optional[BaseScenario]
        """Retrieves a scenario by its unique identifier."""
        pass

    @abstractmethod
    def get_scenarios_by_category(self, category: str, sensor_type: Optional[str] = None, num_to_get: int = 5) -> List[Any]: # -> List[BaseScenario]
        """Retrieves scenarios by category, optionally filtered by sensor_type."""
        pass

    @abstractmethod
    def get_scenarios_by_class_label(self, class_label: str, sensor_type: Optional[str] = None, num_to_get: int = 5) -> List[Any]: # -> List[BaseScenario]
        """Retrieves scenarios known to produce a given class label, optionally filtered by sensor_type."""
        pass

    @abstractmethod
    def create_scenario_variation(
        self,
        base_scenario: Any, # BaseScenario object
        new_id_suffix: str,
        param_modifications: Dict[str, Any],
        sensor_context: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]: # -> Optional[BaseScenario]
        """
        Creates a variation of a base scenario with modified parameters,
        potentially guided by sensor_context.
        """
        pass

    @abstractmethod
    def craft_scenario_from_features(
        self,
        features_summary: Dict[str, Any], # From ModelInterface's sample_features_summary
        base_id: str,
        target_class: Optional[str] = None,
        sensor_type: Optional[str] = None
    ) -> Optional[Any]: # -> Optional[BaseScenario]
        """
        Crafts a new scenario definition based on problematic features,
        potentially using a Builder Pattern internally and tailored for a sensor_type.
        """
        pass

    @abstractmethod
    def get_default_exploration_scenario(
        self,
        scenario_id: str,
        sensor_type: Optional[str] = None
    ) -> Optional[Any]: # -> Optional[BaseScenario]
        """Gets a default scenario for general exploration, optionally for a sensor_type."""
        pass

    @abstractmethod
    def save_scenario_definition(self, scenario_def: Dict[str, Any]) -> str:
        """
        Saves a scenario definition (conforming to ScenarioDefinition.avsc)
        and returns its unique identifier.
        """
        pass

    @abstractmethod
    def update_scenario_definition(self, scenario_def_id: str, updates: Dict[str, Any]) -> bool:
        """
        Updates an existing scenario definition.
        'updates' could be a partial ScenarioDefinition structure or specific modification instructions.
        Returns True if successful, False otherwise.
        """
        pass