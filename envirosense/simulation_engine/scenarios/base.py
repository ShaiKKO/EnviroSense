import abc
import json
import importlib
import datetime # Added for ScenarioJsonEncoder and creation_timestamp_utc
from enum import Enum
from typing import Dict, Any, Optional, Type, List # Added List

# Forward declaration for type hinting if Environment3DOrchestrator is complex
# class Environment3DOrchestrator: pass
# For now, we'll use 'Any' for simplicity

class ScenarioComplexity(Enum):
    """Defines the complexity level of a scenario."""
    VERY_LOW = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    VERY_HIGH = 5

class ScenarioJsonEncoder(json.JSONEncoder):
    """Custom JSON encoder for scenario parameters to handle complex types."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date):
            return obj.isoformat()
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, ScenarioComplexity):
            return obj.name
        # Add other custom types as needed (e.g., numpy arrays if used directly)
        try:
            return json.JSONEncoder.default(self, obj)
        except TypeError:
            # Fallback for objects that might have a to_dict method or similar
            if hasattr(obj, 'to_dict') and callable(obj.to_dict):
                return obj.to_dict()
            elif hasattr(obj, '__dict__'): # Last resort, might expose too much
                return obj.__dict__
            raise # Reraise if no suitable representation found


class BaseScenario(abc.ABC):
    """
    Abstract base class for all simulation scenarios.

    A scenario defines the conditions, events, and ground truth labels for a
    specific simulation run, primarily for generating ML training data.
    """

    def __init__(self,
                 scenario_id: str, # Corresponds to scenario_instance_id in Avro if this is an instance
                 name: str,
                 description: str,
                 category: str = "general",
                 difficulty_level: ScenarioComplexity = ScenarioComplexity.MEDIUM,
                 expected_duration_seconds: Optional[float] = None,
                 tags: Optional[List[str]] = None,
                 version: int = 1,
                 creation_timestamp_utc: Optional[datetime.datetime] = None,
                 author: Optional[str] = None,
                 related_scenario_ids: Optional[List[str]] = None,
                 # scenario_definition_id: Optional[str] = None # ID of the definition itself
                 **kwargs: Any): # Allow kwargs for subclasses
        """
        Initializes the BaseScenario.

        Args:
            scenario_id: Unique identifier for this scenario instance.
            name: Human-readable name for the scenario.
            description: A brief description of the scenario.
            category: Category of the scenario.
            difficulty_level: The complexity level of the scenario.
            expected_duration_seconds: Estimated duration in seconds.
            tags: List of descriptive tags.
            version: Version of this scenario's definition logic.
            creation_timestamp_utc: Timestamp of scenario definition creation.
            author: Author of the scenario definition.
            related_scenario_ids: List of related scenario definition IDs.
            kwargs: Additional keyword arguments for subclasses or future expansion.
        """
        if not scenario_id or not isinstance(scenario_id, str):
            raise ValueError("scenario_id must be a non-empty string.")
        if not name or not isinstance(name, str):
            raise ValueError("name must be a non-empty string.")

        self.scenario_id = scenario_id # Maps to scenario_instance_id in Avro
        self.name = name
        self.description = description
        self.category = category
        if not isinstance(difficulty_level, ScenarioComplexity):
            # Allow string conversion for flexibility if loaded from simple JSON
            if isinstance(difficulty_level, str):
                try:
                    difficulty_level = ScenarioComplexity[difficulty_level.upper()]
                except KeyError:
                    raise ValueError(f"Invalid difficulty_level string: {difficulty_level}")
            else:
                raise TypeError("difficulty_level must be an instance of ScenarioComplexity Enum or a valid string name.")
        self.difficulty_level = difficulty_level
        self.expected_duration_seconds = expected_duration_seconds
        
        self.tags: List[str] = tags if tags is not None else []
        self.version: int = version
        self.creation_timestamp_utc: Optional[datetime.datetime] = creation_timestamp_utc
        self.author: Optional[str] = author
        self.related_scenario_ids: List[str] = related_scenario_ids if related_scenario_ids is not None else []
        
        # self.scenario_definition_id = scenario_definition_id # If needed to store the definition's ID

        self._kwargs = kwargs # Store any extra kwargs for subclasses or _get_specific_params

        self.current_time_seconds: float = 0.0 # Internal clock for the scenario

    @abc.abstractmethod
    def _get_specific_params(self) -> Dict[str, Any]:
        """
        Subclasses MUST override this method to return a dictionary of
        all parameters unique to their constructor that are needed for
        re-instantiation and are not already handled by BaseScenario's __init__
        (i.e., not scenario_id, name, description, category, etc.).
        The values in the returned dictionary must be JSON serializable,
        potentially using the ScenarioJsonEncoder.
        """
        raise NotImplementedError("Subclasses must implement _get_specific_params to return their unique constructor arguments.")

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

    def validate(self) -> List[str]:
        """
        Validates the scenario's configuration.
        Subclasses should extend this to validate their specific parameters.

        Returns:
            A list of error messages. An empty list indicates success.
        """
        errors = []
        if not self.scenario_id:
            errors.append("scenario_id cannot be empty.")
        if not self.name:
            errors.append("name cannot be empty.")
        # Add more common validations if needed
        return errors
        
    def get_metadata(self) -> Dict[str, Any]:
        """Returns metadata about the scenario."""
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "difficulty_level": self.difficulty_level.name, # Return name of enum member
            "difficulty_value": self.difficulty_level.value, # Also return value
            "expected_duration_seconds": self.expected_duration_seconds,
            "current_time_seconds": self.current_time_seconds,
            "tags": self.tags,
            "version": self.version,
            "author": self.author,
            "related_scenario_ids": self.related_scenario_ids,
            "creation_timestamp_utc": self.creation_timestamp_utc.isoformat() if self.creation_timestamp_utc else None
        }

    def reset(self) -> None:
        """Resets the internal state of the scenario (e.g., current_time_seconds)."""
        self.current_time_seconds = 0.0

    def __repr__(self) -> str:
        return (f"<{self.__class__.__name__}(scenario_id='{self.scenario_id}', "
                f"name='{self.name}', category='{self.category}')>")

    def to_scenario_definition_dict(self, scenario_definition_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Serializes the scenario to a dictionary conforming to ScenarioDefinition.avsc.
        This represents the definition of the scenario.
        """
        specific_params = self._get_specific_params()
        try:
            specific_params_json_str = json.dumps(specific_params, cls=ScenarioJsonEncoder)
        except TypeError as e:
            params_str = {k: str(type(v)) for k, v in specific_params.items()}
            raise TypeError(
                f"Specific parameters for scenario {self.scenario_id} ('{self.name}') "
                f"are not JSON serializable with ScenarioJsonEncoder. "
                f"Problematic params (types shown): {params_str}. Original error: {e}"
            ) from e

        creation_ts = self.creation_timestamp_utc
        if creation_ts is None:
            creation_ts = datetime.datetime.now(datetime.timezone.utc)
        
        definition_id_to_use = scenario_definition_id if scenario_definition_id else self.scenario_id

        data = {
            "scenario_definition_id": definition_id_to_use,
            "scenario_class_module": self.__class__.__module__,
            "scenario_class_name": self.__class__.__name__,
            "scenario_instance_id": self.scenario_id, 
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tags": self.tags,
            "difficulty_level": self.difficulty_level.name,
            "expected_duration_seconds": self.expected_duration_seconds,
            "version": self.version,
            "creation_timestamp_utc": int(creation_ts.timestamp() * 1000), 
            "specific_params_json": specific_params_json_str,
            "author": self.author,
            "related_scenario_ids": self.related_scenario_ids
        }
        return data

    @classmethod
    def from_scenario_definition_dict(cls: Type['BaseScenario'], scenario_def_dict: Dict[str, Any]) -> 'BaseScenario':
        """
        Deserializes a scenario from a dictionary conforming to ScenarioDefinition.avsc.
        """
        module_name = scenario_def_dict["scenario_class_module"]
        class_name = scenario_def_dict["scenario_class_name"]
        
        try:
            module = importlib.import_module(module_name)
            ScenarioSpecificClass = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Could not load scenario class {module_name}.{class_name}: {e}")

        difficulty_level_str = scenario_def_dict["difficulty_level"]
        try:
            difficulty_level_enum = ScenarioComplexity[difficulty_level_str.upper()]
        except KeyError:
            raise ValueError(f"Invalid difficulty_level string '{difficulty_level_str}' in scenario definition.")

        specific_params = {}
        if "specific_params_json" in scenario_def_dict and scenario_def_dict["specific_params_json"]:
            try:
                specific_params = json.loads(scenario_def_dict["specific_params_json"])
            except json.JSONDecodeError as e:
                raise ValueError(f"Error decoding specific_params_json for scenario {scenario_def_dict.get('scenario_instance_id', 'Unknown')}: {e}")

        init_args = {
            "scenario_id": scenario_def_dict["scenario_instance_id"],
            "name": scenario_def_dict["name"],
            "description": scenario_def_dict["description"],
            "category": scenario_def_dict["category"],
            "difficulty_level": difficulty_level_enum,
            "expected_duration_seconds": scenario_def_dict.get("expected_duration_seconds"),
            "tags": scenario_def_dict.get("tags", []),
            "version": scenario_def_dict.get("version", 1),
            "author": scenario_def_dict.get("author"),
            "related_scenario_ids": scenario_def_dict.get("related_scenario_ids", [])
        }
        
        creation_ts_ms = scenario_def_dict.get("creation_timestamp_utc")
        if creation_ts_ms is not None:
            init_args["creation_timestamp_utc"] = datetime.datetime.fromtimestamp(creation_ts_ms / 1000.0, tz=datetime.timezone.utc)

        init_args.update(specific_params)

        try:
            instance = ScenarioSpecificClass(**init_args)
        except TypeError as e:
            raise ValueError(f"Error instantiating {class_name} with combined args {init_args}: {e}")
            
        return instance

def save_scenario_definition_to_json(scenario: BaseScenario, file_path: str, scenario_definition_id: Optional[str] = None) -> None:
    """Saves a scenario's definition to a JSON file."""
    with open(file_path, 'w') as f:
        json.dump(scenario.to_scenario_definition_dict(scenario_definition_id=scenario_definition_id), f, indent=4, cls=ScenarioJsonEncoder)

def load_scenario_from_definition_json(file_path: str) -> BaseScenario:
    """Loads a scenario instance from a scenario definition JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return BaseScenario.from_scenario_definition_dict(data)