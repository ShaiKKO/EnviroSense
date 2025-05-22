import abc
from typing import Dict, Any, Optional

# Forward declaration for type hinting if Environment3DOrchestrator is complex
# class Environment3DOrchestrator: pass
# For now, we'll use 'Any' for simplicity

class BaseScenario(abc.ABC):
    """
    Abstract base class for all simulation scenarios.

    A scenario defines the conditions, events, and ground truth labels for a
    specific simulation run, primarily for generating ML training data.
    """

    def __init__(self,
                 scenario_id: str,
                 name: str,
                 description: str,
                 category: str = "general",
                 difficulty_level: int = 1, # e.g., 1-5
                 expected_duration_seconds: Optional[float] = None):
        """
        Initializes the BaseScenario.

        Args:
            scenario_id: Unique identifier for the scenario.
            name: Human-readable name for the scenario.
            description: A brief description of the scenario.
            category: Category of the scenario (e.g., "fire_precursor", 
                      "electrical_fault", "normal_operation", "environmental_event").
            difficulty_level: An arbitrary measure of scenario complexity or subtlety.
            expected_duration_seconds: Estimated or typical duration of the scenario in seconds.
                                       Can be None for open-ended scenarios.
        """
        if not scenario_id or not isinstance(scenario_id, str):
            raise ValueError("scenario_id must be a non-empty string.")
        if not name or not isinstance(name, str):
            raise ValueError("name must be a non-empty string.")

        self.scenario_id = scenario_id
        self.name = name
        self.description = description
        self.category = category
        self.difficulty_level = difficulty_level
        self.expected_duration_seconds = expected_duration_seconds
        
        self.current_time_seconds: float = 0.0 # Internal clock for the scenario

    @abc.abstractmethod
    def setup_environment(self, environment_3d_orchestrator: Any) -> None:
        """
        Configures the initial state of the 3D environment for this scenario.
        This could involve setting initial chemical concentrations, thermal properties,
        activating specific sources, etc., via the environment_3d_orchestrator.

        Args:
            environment_3d_orchestrator: An object that manages and provides access
                                         to the 3D environmental simulation state.
        """
        pass

    @abc.abstractmethod
    def get_ground_truth_labels(self, environment_3d_state: Any) -> Dict[str, Any]:
        """
        Defines and returns the ground truth labels for the current state of the scenario.
        These labels are crucial for ML training.

        Args:
            environment_3d_state: The current state of the 3D environment.
                                  This might be used to determine labels based on conditions.

        Returns:
            A dictionary of ground truth labels (e.g., 
            {"event_type": "arcing", "severity_score": 0.8, "is_anomaly": True}).
        """
        pass

    @abc.abstractmethod
    def update(self, time_step_seconds: float, environment_3d_orchestrator: Any) -> None:
        """
        Evolves the scenario over a given time step.
        This method should update the internal state of the scenario and can
        also interact with the environment_3d_orchestrator to make changes
        to the simulated world (e.g., trigger an event, change a source's emission rate).

        Args:
            time_step_seconds: The duration of the current simulation step.
            environment_3d_orchestrator: The environment manager.
        """
        self.current_time_seconds += time_step_seconds
        pass

    @abc.abstractmethod
    def is_completed(self, environment_3d_state: Any) -> bool:
        """
        Checks if the scenario has reached its completion criteria.

        Args:
            environment_3d_state: The current state of the 3D environment.

        Returns:
            True if the scenario is completed, False otherwise.
        """
        # Example completion:
        # if self.expected_duration_seconds is not None and \
        #    self.current_time_seconds >= self.expected_duration_seconds:
        #     return True
        # return False # Or other scenario-specific logic
        pass
        
    def get_metadata(self) -> Dict[str, Any]:
        """Returns metadata about the scenario."""
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "difficulty_level": self.difficulty_level,
            "expected_duration_seconds": self.expected_duration_seconds,
            "current_time_seconds": self.current_time_seconds
        }

    def reset(self) -> None:
        """Resets the internal state of the scenario (e.g., current_time_seconds)."""
        self.current_time_seconds = 0.0

    def __repr__(self) -> str:
        return (f"<{self.__class__.__name__}(scenario_id='{self.scenario_id}', "
                f"name='{self.name}', category='{self.category}')>")

# Example of how scenario serialization might be approached (Task 2.1.3)
# This is conceptual and would need a proper implementation.
# 
# def scenario_to_dict(scenario: BaseScenario) -> Dict[str, Any]:
#     # Basic example, would need to handle specific scenario params
#     return {
#         "scenario_id": scenario.scenario_id,
#         "name": scenario.name,
#         "description": scenario.description,
#         "category": scenario.category,
#         "difficulty_level": scenario.difficulty_level,
#         "expected_duration_seconds": scenario.expected_duration_seconds,
#         "scenario_class": f"{scenario.__class__.__module__}.{scenario.__class__.__name__}",
#         # Add scenario-specific parameters here
#     }

# def scenario_from_dict(data: Dict[str, Any]) -> BaseScenario:
#     # Needs a registry or dynamic import to get the class
#     # module_name, class_name = data["scenario_class"].rsplit('.', 1)
#     # ScenarioClass = getattr(importlib.import_module(module_name), class_name)
#     # # Reconstruct specific_params for the ScenarioClass
#     # return ScenarioClass(**data_for_init)
#     pass