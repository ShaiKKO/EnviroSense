"""
Core framework classes for EnviroSense testing

This module contains the base classes used throughout the testing framework
including test scenarios, test results, and other core functionality.
"""

import datetime
import json
import os
import random
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

class TestScenario:
    """
    Base class for all test scenarios.
    
    A TestScenario defines the parameters, initial conditions, and expected
    results for a specific test case, providing the foundation for automated
    testing of EnviroSense systems.
    """
    
    def __init__(self, 
                 name: str, 
                 description: Optional[str] = None, 
                 tags: Optional[List[str]] = None):
        """
        Initialize a test scenario.
        
        Args:
            name: Descriptive name for the scenario
            description: Detailed description of the scenario
            tags: List of tags for categorization
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description or ""
        self.tags = tags or []
        self.parameters = {}  # Test-specific parameters
        self.expected_results = {}  # Expected outputs for validation
        self.initial_conditions = {}  # Starting conditions for the test
        self.duration = 0  # Time duration for the test scenario
        self.time_step = 0  # Time step for simulation
        self.creation_time = datetime.datetime.now()
        self.last_modified = self.creation_time
        
    def set_parameter(self, name: str, value: Any) -> 'TestScenario':
        """
        Set a scenario parameter.
        
        Args:
            name: Parameter name
            value: Parameter value
        
        Returns:
            Self for method chaining
        """
        self.parameters[name] = value
        self.last_modified = datetime.datetime.now()
        return self
    
    def set_expected_result(self, 
                          parameter: str, 
                          value: Any, 
                          tolerance: Optional[float] = None) -> 'TestScenario':
        """
        Define an expected result for validation.
        
        Args:
            parameter: Name of the parameter to check
            value: Expected value
            tolerance: Acceptable deviation from expected value (for numeric results)
        
        Returns:
            Self for method chaining
        """
        self.expected_results[parameter] = {
            'value': value,
            'tolerance': tolerance
        }
        self.last_modified = datetime.datetime.now()
        return self
    
    def set_initial_condition(self, parameter: str, value: Any) -> 'TestScenario':
        """
        Set initial condition for the scenario.
        
        Args:
            parameter: Parameter name
            value: Initial value
        
        Returns:
            Self for method chaining
        """
        self.initial_conditions[parameter] = value
        self.last_modified = datetime.datetime.now()
        return self
    
    def set_duration(self, 
                   duration: float, 
                   time_step: float = 1.0) -> 'TestScenario':
        """
        Set scenario duration and time step.
        
        Args:
            duration: Total duration of the scenario
            time_step: Time step for simulation
        
        Returns:
            Self for method chaining
        """
        self.duration = duration
        self.time_step = time_step
        self.last_modified = datetime.datetime.now()
        return self
    
    def add_tag(self, tag: str) -> 'TestScenario':
        """
        Add a tag to the scenario.
        
        Args:
            tag: Tag to add
        
        Returns:
            Self for method chaining
        """
        if tag not in self.tags:
            self.tags.append(tag)
            self.last_modified = datetime.datetime.now()
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert scenario to dictionary for serialization.
        
        Returns:
            Dictionary representation of the scenario
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'tags': self.tags,
            'parameters': self.parameters,
            'expected_results': self.expected_results,
            'initial_conditions': self.initial_conditions,
            'duration': self.duration,
            'time_step': self.time_step,
            'creation_time': self.creation_time.isoformat(),
            'last_modified': self.last_modified.isoformat()
        }
    
    def to_json(self) -> str:
        """
        Convert scenario to JSON string.
        
        Returns:
            JSON string representation of the scenario
        """
        return json.dumps(self.to_dict(), indent=2)
    
    def save(self, file_path: str) -> None:
        """
        Save scenario to file.
        
        Args:
            file_path: Path to save the scenario
        """
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(self.to_json())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestScenario':
        """
        Create a scenario from dictionary data.
        
        Args:
            data: Dictionary containing scenario data
        
        Returns:
            TestScenario instance
        """
        scenario = cls(data['name'], data.get('description', ""),
                      data.get('tags', []))
        scenario.id = data.get('id', str(uuid.uuid4()))
        scenario.parameters = data.get('parameters', {})
        scenario.expected_results = data.get('expected_results', {})
        scenario.initial_conditions = data.get('initial_conditions', {})
        scenario.duration = data.get('duration', 0)
        scenario.time_step = data.get('time_step', 1.0)
        
        # Parse dates if they exist
        if 'creation_time' in data:
            scenario.creation_time = datetime.datetime.fromisoformat(data['creation_time'])
        if 'last_modified' in data:
            scenario.last_modified = datetime.datetime.fromisoformat(data['last_modified'])
            
        return scenario
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TestScenario':
        """
        Create a scenario from JSON string.
        
        Args:
            json_str: JSON string containing scenario data
        
        Returns:
            TestScenario instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def load(cls, file_path: str) -> 'TestScenario':
        """
        Load scenario from file.
        
        Args:
            file_path: Path to load the scenario from
        
        Returns:
            TestScenario instance
        """
        with open(file_path, 'r') as f:
            return cls.from_json(f.read())


class TestResult:
    """
    Container for test execution results.
    
    A TestResult stores all data related to a test execution, including
    generated test data, simulation results, validation outcomes, and
    performance metrics.
    """
    
    def __init__(self, scenario: TestScenario):
        """
        Initialize a test result.
        
        Args:
            scenario: The scenario this result is for
        """
        self.id = str(uuid.uuid4())
        self.scenario_id = scenario.id
        self.scenario_name = scenario.name
        self.execution_time = datetime.datetime.now()
        self.duration_ms = 0
        self.status = "pending"  # pending, running, completed, failed, error
        self.generated_data = {}  # Data generated for the test
        self.simulation_result = {}  # Results from simulation
        self.validation_results = {}  # Results from validation
        self.metrics = {}  # Performance metrics
        self.artifacts = {}  # Paths to generated files (plots, logs, etc.)
        self.error = None  # Error information if test failed
    
    def start_execution(self) -> None:
        """Mark the test as running and record the start time."""
        self.status = "running"
        self.start_time = datetime.datetime.now()
    
    def complete_execution(self, status: str = "completed") -> None:
        """
        Mark the test as complete and calculate duration.
        
        Args:
            status: Final status (completed, failed, error)
        """
        self.status = status
        end_time = datetime.datetime.now()
        self.duration_ms = (end_time - self.start_time).total_seconds() * 1000
    
    def add_generated_data(self, generator_name: str, data: Any) -> None:
        """
        Add generated data to the result.
        
        Args:
            generator_name: Name of the generator that produced the data
            data: The generated data
        """
        self.generated_data[generator_name] = data
    
    def set_simulation_result(self, result: Any) -> None:
        """
        Set the simulation result.
        
        Args:
            result: Result from the simulation
        """
        self.simulation_result = result
    
    def add_validation_result(self, validator_name: str, result: Any) -> None:
        """
        Add validation result to the test.
        
        Args:
            validator_name: Name of the validator
            result: Validation result
        """
        self.validation_results[validator_name] = result
    
    def add_metric(self, name: str, value: Any) -> None:
        """
        Add a performance metric.
        
        Args:
            name: Metric name
            value: Metric value
        """
        self.metrics[name] = value
    
    def add_artifact(self, name: str, path: str) -> None:
        """
        Add a test artifact.
        
        Args:
            name: Artifact name
            path: Path to the artifact
        """
        self.artifacts[name] = path
    
    def set_error(self, error_type: str, message: str, details: Optional[Any] = None) -> None:
        """
        Set error information if test failed.
        
        Args:
            error_type: Type of error
            message: Error message
            details: Additional error details
        """
        self.error = {
            'type': error_type,
            'message': message,
            'details': details
        }
        self.status = "error"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert result to dictionary for serialization.
        
        Returns:
            Dictionary representation of the result
        """
        return {
            'id': self.id,
            'scenario_id': self.scenario_id,
            'scenario_name': self.scenario_name,
            'execution_time': self.execution_time.isoformat(),
            'duration_ms': self.duration_ms,
            'status': self.status,
            'metrics': self.metrics,
            'artifacts': self.artifacts,
            'error': self.error
            # Note: generated_data, simulation_result, and validation_results
            # might be too large or complex for direct serialization
            # Consider adding methods to store them separately
        }
    
    def to_json(self) -> str:
        """
        Convert result to JSON string.
        
        Returns:
            JSON string representation of the result
        """
        return json.dumps(self.to_dict(), indent=2)
    
    def save(self, file_path: str) -> None:
        """
        Save result to file.
        
        Args:
            file_path: Path to save the result
        """
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(self.to_json())


class DataGenerator:
    """
    Base class for all data generators.
    
    A DataGenerator produces synthetic test data based on scenario parameters,
    providing realistic inputs for testing EnviroSense systems.
    """
    
    def __init__(self):
        """Initialize the data generator."""
        self.parameters = {}
        self.random_seed = None
        self.rng = random.Random()
        
    def set_parameter(self, name: str, value: Any) -> 'DataGenerator':
        """
        Set a generator parameter.
        
        Args:
            name: Parameter name
            value: Parameter value
        
        Returns:
            Self for method chaining
        """
        self.parameters[name] = value
        return self
    
    def set_seed(self, seed: int) -> 'DataGenerator':
        """
        Set random seed for reproducibility.
        
        Args:
            seed: Random seed
        
        Returns:
            Self for method chaining
        """
        self.random_seed = seed
        self.rng.seed(seed)
        return self
    
    def generate(self, scenario: TestScenario, **kwargs) -> Any:
        """
        Generate data based on scenario.
        
        Args:
            scenario: Test scenario to generate data for
            **kwargs: Additional parameters
        
        Returns:
            Generated data
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement generate()")


class Validator:
    """
    Base class for all validators.
    
    A Validator checks if test results match expected outcomes, providing
    detailed analysis of discrepancies and validation metrics.
    """
    
    def __init__(self):
        """Initialize the validator."""
        self.parameters = {}
    
    def set_parameter(self, name: str, value: Any) -> 'Validator':
        """
        Set a validator parameter.
        
        Args:
            name: Parameter name
            value: Parameter value
        
        Returns:
            Self for method chaining
        """
        self.parameters[name] = value
        return self
    
    def validate(self, 
                result: Any, 
                expected: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate results against expected values.
        
        Args:
            result: Result to validate
            expected: Expected values
        
        Returns:
            Validation results
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement validate()")


class TestRunner:
    """
    Orchestrates test execution.
    
    A TestRunner coordinates the execution of test scenarios, including data
    generation, simulation, validation, and result collection.
    """
    
    def __init__(self, 
                data_generators: Optional[Dict[str, DataGenerator]] = None, 
                validators: Optional[Dict[str, Validator]] = None):
        """
        Initialize the test runner.
        
        Args:
            data_generators: Dict of data generator instances
            validators: Dict of validator instances
        """
        self.data_generators = data_generators or {}
        self.validators = validators or {}
        self.results = {}
        
    def add_generator(self, name: str, generator: DataGenerator) -> 'TestRunner':
        """
        Add a data generator.
        
        Args:
            name: Generator name
            generator: Generator instance
        
        Returns:
            Self for method chaining
        """
        self.data_generators[name] = generator
        return self
    
    def add_validator(self, name: str, validator: Validator) -> 'TestRunner':
        """
        Add a result validator.
        
        Args:
            name: Validator name
            validator: Validator instance
        
        Returns:
            Self for method chaining
        """
        self.validators[name] = validator
        return self
    
    def run_scenario(self, 
                   scenario: TestScenario, 
                   output_dir: Optional[str] = None) -> TestResult:
        """
        Run a test scenario and collect results.
        
        Args:
            scenario: TestScenario instance
            output_dir: Directory for output files
        
        Returns:
            TestResult instance
        """
        # Create result object
        result = TestResult(scenario)
        result.start_execution()
        
        try:
            # Generate test data using appropriate generators
            for generator_name, generator in self.data_generators.items():
                generator_data = generator.generate(scenario)
                result.add_generated_data(generator_name, generator_data)
            
            # Run the simulation using the generated data
            simulation_result = self._run_simulation(scenario, result.generated_data)
            result.set_simulation_result(simulation_result)
            
            # Validate results against expected outcomes
            for validator_name, validator in self.validators.items():
                validation_result = validator.validate(
                    simulation_result, scenario.expected_results)
                result.add_validation_result(validator_name, validation_result)
            
            result.complete_execution("completed")
            
        except Exception as e:
            result.set_error(
                error_type=type(e).__name__,
                message=str(e),
                details=None  # Could add traceback info here
            )
            result.complete_execution("error")
            
        # Save results if output directory specified
        if output_dir:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            result.save(os.path.join(output_dir, f"result_{result.id}.json"))
            
        self.results[result.id] = result
        return result
    
    def _run_simulation(self, 
                      scenario: TestScenario, 
                      generated_data: Dict[str, Any]) -> Any:
        """
        Run simulation for the scenario.
        
        Args:
            scenario: Scenario to simulate
            generated_data: Data for the simulation
        
        Returns:
            Simulation result
            
        Raises:
            NotImplementedError: Must be implemented by subclasses or overridden
        """
        raise NotImplementedError("Subclasses must implement _run_simulation() or override run_scenario()")


class ScenarioLibrary:
    """
    Manages a collection of test scenarios.
    
    A ScenarioLibrary provides facilities for storing, retrieving, and
    managing test scenarios, including searching and filtering.
    """
    
    def __init__(self, directory: Optional[str] = None):
        """
        Initialize the scenario library.
        
        Args:
            directory: Directory to load scenarios from
        """
        self.scenarios = {}  # id -> scenario
        self.directory = directory
        
        if directory and os.path.exists(directory):
            self.load_from_directory(directory)
    
    def add_scenario(self, scenario: TestScenario) -> None:
        """
        Add a scenario to the library.
        
        Args:
            scenario: Scenario to add
        """
        self.scenarios[scenario.id] = scenario
    
    def get_scenario(self, scenario_id: str) -> Optional[TestScenario]:
        """
        Get a scenario by ID.
        
        Args:
            scenario_id: ID of the scenario
        
        Returns:
            TestScenario if found, None otherwise
        """
        return self.scenarios.get(scenario_id)
    
    def find_scenarios(self, 
                     tags: Optional[List[str]] = None, 
                     name_contains: Optional[str] = None) -> List[TestScenario]:
        """
        Find scenarios matching criteria.
        
        Args:
            tags: List of tags to match (scenario must have all tags)
            name_contains: String that must be in the name
        
        Returns:
            List of matching scenarios
        """
        results = []
        
        for scenario in self.scenarios.values():
            # Check tags if specified
            if tags and not all(tag in scenario.tags for tag in tags):
                continue
            
            # Check name if specified
            if name_contains and name_contains.lower() not in scenario.name.lower():
                continue
            
            results.append(scenario)
        
        return results
    
    def load_from_directory(self, directory: str) -> None:
        """
        Load scenarios from a directory.
        
        Args:
            directory: Directory containing scenario files
        """
        if not os.path.exists(directory):
            raise ValueError(f"Directory does not exist: {directory}")
            
        for filename in os.listdir(directory):
            if filename.endswith('.json'):
                file_path = os.path.join(directory, filename)
                try:
                    scenario = TestScenario.load(file_path)
                    self.add_scenario(scenario)
                except Exception as e:
                    print(f"Error loading scenario {filename}: {e}")
    
    def save_to_directory(self, directory: str) -> None:
        """
        Save all scenarios to a directory.
        
        Args:
            directory: Directory to save scenarios to
        """
        if not os.path.exists(directory):
            os.makedirs(directory)
            
        for scenario in self.scenarios.values():
            file_path = os.path.join(directory, f"scenario_{scenario.id}.json")
            scenario.save(file_path)
    
    def __len__(self) -> int:
        """Get the number of scenarios in the library."""
        return len(self.scenarios)
    
    def __iter__(self):
        """Iterate over scenarios in the library."""
        return iter(self.scenarios.values())
