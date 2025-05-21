"""
EnviroSense Time Series Generator - Main Generator Class

This module provides the TimeSeriesGenerator class for generating time series
data based on parameters with constraints and relationships.
"""

from typing import Dict, Any, List, Optional, Callable, Union, Tuple, Set
import numpy as np
from datetime import datetime, timedelta
import copy
import json
import csv
import matplotlib.pyplot as plt
from collections import defaultdict

from envirosense.core.time_series.parameters import (
    Parameter, 
    ParameterType,
    Distribution,
    Pattern,
    PatternType,
    ParameterRelationship
)

# Define relationship functions for use in parameter relationships
def linear_relationship(x, params=None):
    """
    Apply a linear relationship: y = ax + b
    
    Args:
        x: Input value
        params: Dictionary with 'a' (slope) and 'b' (intercept)
        
    Returns:
        Transformed value
    """
    params = params or {}
    a = params.get('a', 1.0)
    b = params.get('b', 0.0)
    return a * x + b

def exponential_relationship(x, params=None):
    """
    Apply an exponential relationship: y = a * e^(bx)
    
    Args:
        x: Input value
        params: Dictionary with 'a' (coefficient) and 'b' (exponent factor)
        
    Returns:
        Transformed value
    """
    params = params or {}
    a = params.get('a', 1.0)
    b = params.get('b', 1.0)
    return a * np.exp(b * x)

def power_relationship(x, params=None):
    """
    Apply a power relationship: y = a * x^b
    
    Args:
        x: Input value
        params: Dictionary with 'a' (coefficient) and 'b' (exponent)
        
    Returns:
        Transformed value
    """
    params = params or {}
    a = params.get('a', 1.0)
    b = params.get('b', 1.0)
    return a * (x ** b)

def logarithmic_relationship(x, params=None):
    """
    Apply a logarithmic relationship: y = a * log(x) + b
    
    Args:
        x: Input value
        params: Dictionary with 'a' (coefficient), 'b' (intercept), and 'base' (log base)
        
    Returns:
        Transformed value
    """
    params = params or {}
    a = params.get('a', 1.0)
    b = params.get('b', 0.0)
    base = params.get('base', np.e)
    
    # Ensure x is positive for log
    x = max(x, 1e-10)
    
    if base == np.e:
        return a * np.log(x) + b
    else:
        return a * np.log(x) / np.log(base) + b

def threshold_relationship(x, params=None):
    """
    Apply a threshold relationship where output changes at threshold values
    
    Args:
        x: Input value
        params: Dictionary with 'thresholds' (list of thresholds) and 'values' (list of values)
        
    Returns:
        Transformed value based on thresholds
    """
    params = params or {}
    thresholds = params.get('thresholds', [0.0])
    values = params.get('values', [0.0, 1.0])
    
    if len(values) != len(thresholds) + 1:
        # Default case if the parameters are invalid
        return x
    
    # Find the right threshold segment
    for i, threshold in enumerate(thresholds):
        if x < threshold:
            return values[i]
    
    # If x is greater than all thresholds
    return values[-1]

def custom_relationship(x, params=None):
    """
    Apply a custom relationship defined by a formula in the params
    
    Args:
        x: Input value
        params: Dictionary with 'formula' (string formula with 'x' as the variable)
        
    Returns:
        Transformed value based on the formula
    """
    params = params or {}
    formula = params.get('formula', 'x')  # Default to identity
    
    # Replace 'x' in the formula with the actual value
    # Note: This is a simple implementation and might not be secure
    # For production, consider using a safer approach
    try:
        result = eval(formula.replace('x', str(float(x))))
        return float(result)
    except:
        return x  # Return input if evaluation fails


class TimeSeriesGenerator:
    """
    Generates time series data for multiple parameters with constraints and relationships.
    
    This class manages a set of parameters and their relationships, and generates
    time series data based on their properties, constraints, and relationships.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize a time series generator.
        
        Args:
            config: Configuration dictionary with options for the generator
        """
        self.config = config or {}
        self.parameters = {}  # Maps parameter name to Parameter object
        self.relationships = []  # List of ParameterRelationship objects
        self.current_time = 0.0  # Current simulation time in hours
        self.start_time = datetime.now()  # Reference start time
        self.event_queue = []  # List of (time, event_function) tuples
        self.seed = self.config.get("seed")
        
        # Set random seed if specified
        if self.seed is not None:
            np.random.seed(self.seed)
        
        # Track dependency graph to detect cycles
        self.dependency_graph = defaultdict(set)
        
        # Initialize from config if provided
        if "parameters" in self.config:
            for param_config in self.config["parameters"]:
                self.add_parameter_from_dict(param_config)
        
        if "relationships" in self.config:
            for rel_config in self.config["relationships"]:
                self.add_relationship_from_dict(rel_config)
    
    def add_parameter(self, parameter: Parameter) -> None:
        """
        Add a parameter to the generator.
        
        Args:
            parameter: Parameter object to add
            
        Raises:
            ValueError: If a parameter with the same name already exists
        """
        if parameter.name in self.parameters:
            raise ValueError(f"Parameter with name '{parameter.name}' already exists")
        
        self.parameters[parameter.name] = parameter
    
    def add_parameter_from_dict(self, config: Dict[str, Any]) -> Parameter:
        """
        Add a parameter from a dictionary configuration.
        
        Args:
            config: Dictionary with parameter configuration
            
        Returns:
            The created Parameter object
            
        Raises:
            ValueError: If a parameter with the same name already exists
            KeyError: If required configuration fields are missing
        """
        param = Parameter.from_dict(config)
        self.add_parameter(param)
        return param
    
    def create_parameter(
        self,
        name: str,
        parameter_type: ParameterType,
        initial_value: Any,
        **kwargs
    ) -> Parameter:
        """
        Create and add a new parameter.
        
        Args:
            name: Name of the parameter
            parameter_type: Type of the parameter
            initial_value: Initial value of the parameter
            **kwargs: Additional arguments for the Parameter constructor
            
        Returns:
            The created Parameter object
            
        Raises:
            ValueError: If a parameter with the same name already exists
        """
        param = Parameter(
            name=name,
            parameter_type=parameter_type,
            initial_value=initial_value,
            **kwargs
        )
        self.add_parameter(param)
        return param
    
    def get_parameter(self, name: str) -> Optional[Parameter]:
        """
        Get a parameter by name.
        
        Args:
            name: Name of the parameter
            
        Returns:
            The parameter, or None if not found
        """
        return self.parameters.get(name)
    
    def get_parameter_value(self, name: str) -> Any:
        """
        Get the current value of a parameter.
        
        Args:
            name: Name of the parameter
            
        Returns:
            Current value of the parameter
            
        Raises:
            KeyError: If the parameter does not exist
        """
        param = self.get_parameter(name)
        if param is None:
            raise KeyError(f"Parameter '{name}' does not exist")
        
        return param.value
    
    def set_parameter_value(self, name: str, value: Any) -> None:
        """
        Set the value of a parameter.
        
        Args:
            name: Name of the parameter
            value: New value for the parameter
            
        Raises:
            KeyError: If the parameter does not exist
            ValueError: If the value violates constraints
        """
        param = self.get_parameter(name)
        if param is None:
            raise KeyError(f"Parameter '{name}' does not exist")
        
        param.value = value
        
        # Update dependent parameters
        self._update_dependent_parameters(name)
    
    def _update_dependent_parameters(self, source_name: str, visited: Optional[Set[str]] = None) -> None:
        """
        Update parameters that depend on a source parameter.
        
        This will recursively update all parameters that depend on the source parameter
        or on parameters that depend on the source parameter.
        
        Args:
            source_name: Name of the source parameter
            visited: Set of parameter names that have already been visited (to avoid cycles)
        """
        if visited is None:
            visited = set()
        
        # Avoid cycles
        if source_name in visited:
            return
        
        visited.add(source_name)
        
        # Update parameters that directly depend on the source parameter
        for rel in self.relationships:
            # Check for direct dependency
            if rel.source_parameter == source_name:
                target_name = rel.target_parameter
                target_param = self.get_parameter(target_name)
                
                if target_param:
                    try:
                        # Calculate new value based on the relationship
                        source_value = self.get_parameter_value(source_name)
                        new_value = rel.apply(source_value)
                        
                        # Set the value without triggering updates
                        target_param.value = new_value
                        
                        # Recursively update parameters that depend on the target
                        self._update_dependent_parameters(target_name, visited)
                    except Exception as e:
                        print(f"Warning: Could not update {target_name} based on {source_name}: {str(e)}")
            
            # Check for bidirectional dependency
            elif rel.bidirectional and rel.target_parameter == source_name:
                # This is a bidirectional relationship and we need to update the source
                target_name = rel.source_parameter
                target_param = self.get_parameter(target_name)
                
                if target_param:
                    try:
                        # Calculate new value using the reverse function
                        source_value = self.get_parameter_value(source_name)
                        new_value = rel.apply_reverse(source_value)
                        
                        # Set the value without triggering updates
                        target_param.value = new_value
                        
                        # Recursively update parameters that depend on the target
                        self._update_dependent_parameters(target_name, visited)
                    except Exception as e:
                        print(f"Warning: Could not update {target_name} based on {source_name} (reverse): {str(e)}")
    
    def add_relationship(self, relationship: ParameterRelationship) -> None:
        """
        Add a relationship between parameters.
        
        Args:
            relationship: ParameterRelationship object to add
            
        Raises:
            ValueError: If the source or target parameter does not exist
            ValueError: If adding the relationship would create a cycle
        """
        source = relationship.source_parameter
        target = relationship.target_parameter
        
        # Check that the parameters exist
        if source not in self.parameters:
            raise ValueError(f"Source parameter '{source}' does not exist")
        
        if target not in self.parameters:
            raise ValueError(f"Target parameter '{target}' does not exist")
        
        # Check for cycles
        if relationship.bidirectional:
            # For bidirectional relationships, there's automatically a cycle,
            # but we allow exactly one bidirectional relationship between two parameters
            if target in self.dependency_graph[source] or source in self.dependency_graph[target]:
                raise ValueError(f"Adding a bidirectional relationship between {source} and {target} would create a cycle")
            
            # Add edges in both directions
            self.dependency_graph[source].add(target)
            self.dependency_graph[target].add(source)
        else:
            # Check if there's already a path from target to source
            if target in self.dependency_graph and self._has_path(target, source):
                raise ValueError(f"Adding a relationship from {source} to {target} would create a cycle")
            
            # Add edge from source to target
            self.dependency_graph[source].add(target)
        
        # Add the relationship
        self.relationships.append(relationship)
        
        # Update the target parameter based on the current value of the source
        try:
            source_value = self.get_parameter_value(source)
            new_target_value = relationship.apply(source_value)
            self.set_parameter_value(target, new_target_value)
        except Exception as e:
            print(f"Warning: Could not initialize relationship from {source} to {target}: {str(e)}")
    
    def _has_path(self, start: str, end: str, visited: Optional[Set[str]] = None) -> bool:
        """
        Check if there is a path from start to end in the dependency graph.
        
        Args:
            start: Starting node
            end: Ending node
            visited: Set of visited nodes
            
        Returns:
            True if there is a path, False otherwise
        """
        if visited is None:
            visited = set()
        
        if start == end:
            return True
        
        if start in visited:
            return False
        
        visited.add(start)
        
        for neighbor in self.dependency_graph.get(start, set()):
            if self._has_path(neighbor, end, visited):
                return True
        
        return False
    
    def add_relationship_from_dict(self, config: Dict[str, Any]) -> ParameterRelationship:
        """
        Add a relationship from a dictionary configuration.
        
        Args:
            config: Dictionary with relationship configuration
            
        Returns:
            The created ParameterRelationship object
            
        Raises:
            ValueError: If required configuration fields are missing
            ValueError: If the source or target parameter does not exist
        """
        source = config.get("source_parameter")
        target = config.get("target_parameter")
        
        if not source or not target:
            raise ValueError("Relationship configuration must include source_parameter and target_parameter")
        
        # Get the relationship function
        rel_function_name = config.get("function", "linear_relationship")
        rel_function = globals().get(rel_function_name)
        
        if not rel_function:
            raise ValueError(f"Unknown relationship function: {rel_function_name}")
        
        # Get the reverse function if bidirectional
        bidirectional = config.get("bidirectional", False)
        reverse_function = None
        
        if bidirectional:
            reverse_function_name = config.get("reverse_function", rel_function_name)
            reverse_function = globals().get(reverse_function_name)
            
            if not reverse_function:
                raise ValueError(f"Unknown reverse function: {reverse_function_name}")
        
        # Create the relationship
        rel = ParameterRelationship(
            source_parameter=source,
            target_parameter=target,
            relationship_function=rel_function,
            bidirectional=bidirectional,
            reverse_function=reverse_function,
            params=config.get("params", {}),
            description=config.get("description")
        )
        
        # Add the relationship
        self.add_relationship(rel)
        
        return rel
    
    def step(self, time_delta: float = 1.0) -> Dict[str, Any]:
        """
        Advance the simulation by a time step.
        
        This updates all parameters based on their distributions and relationships.
        
        Args:
            time_delta: Time step for the simulation (in hours)
            
        Returns:
            Dictionary mapping parameter names to their new values
        """
        # Update the current time
        self.current_time += time_delta
        
        # Process events that should trigger at or before the current time
        self._process_events()
        
        # Update parameters without dependencies first
        independent_params = self._get_independent_parameters()
        
        for param_name in independent_params:
            param = self.parameters[param_name]
            param.update(time_delta)
        
        # Update parameters with dependencies in topological order
        sorted_params = self._topological_sort()
        
        for param_name in sorted_params:
            if param_name not in independent_params:
                # Skip parameters that have already been updated
                self._update_dependent_parameters(param_name)
        
        # Return the current values of all parameters
        return self.get_current_values()
    
    def _process_events(self) -> None:
        """Process events in the event queue that should trigger at the current time."""
        # Sort events by time
        self.event_queue.sort(key=lambda x: x[0])
        
        # Process events that should trigger at or before the current time
        while self.event_queue and self.event_queue[0][0] <= self.current_time:
            _, event_func = self.event_queue.pop(0)
            event_func(self)
    
    def _get_independent_parameters(self) -> List[str]:
        """
        Get the names of parameters that don't depend on other parameters.
        
        Returns:
            List of parameter names
        """
        # Get all parameters that are never a target in any relationship
        target_params = {rel.target_parameter for rel in self.relationships}
        return [name for name in self.parameters if name not in target_params]
    
    def _topological_sort(self) -> List[str]:
        """
        Sort parameters in topological order based on their dependencies.
        
        Returns:
            List of parameter names sorted by dependency order
        """
        # Map of parameter name to parameters that depend on it
        depends_on = defaultdict(set)
        
        # Count of dependencies for each parameter
        num_dependencies = defaultdict(int)
        
        # Initialize the dependency counts
        for rel in self.relationships:
            source = rel.source_parameter
            target = rel.target_parameter
            
            depends_on[source].add(target)
            num_dependencies[target] += 1
        
        # Parameters with no dependencies
        no_dependencies = [name for name in self.parameters if num_dependencies[name] == 0]
        
        # Topological sort
        sorted_params = []
        
        while no_dependencies:
            # Get a parameter with no dependencies
            param_name = no_dependencies.pop(0)
            sorted_params.append(param_name)
            
            # Update dependencies
            for dependent in depends_on[param_name]:
                num_dependencies[dependent] -= 1
                
                if num_dependencies[dependent] == 0:
                    no_dependencies.append(dependent)
        
        # If there are parameters with unresolved dependencies, there must be cycles
        if len(sorted_params) < len(self.parameters):
            print("Warning: Dependency cycles detected in parameters")
            
            # Add remaining parameters in arbitrary order
            for name in self.parameters:
                if name not in sorted_params:
                    sorted_params.append(name)
        
        return sorted_params
    
    def schedule_event(self, time: float, event_func: Callable[['TimeSeriesGenerator'], None]) -> None:
        """
        Schedule an event to occur at a specific time.
        
        Args:
            time: Time at which the event should occur (in hours from start)
            event_func: Function to call when the event occurs
        """
        self.event_queue.append((time, event_func))
    
    def generate_series(
        self,
        duration: float,
        time_delta: float = 1.0,
        include_timestamps: bool = True
    ) -> Dict[str, List[Any]]:
        """
        Generate a time series for a specified duration.
        
        Args:
            duration: Duration of the time series (in hours)
            time_delta: Time step for the simulation (in hours)
            include_timestamps: Whether to include timestamps in the output
            
        Returns:
            Dictionary mapping parameter names to lists of values
        """
        # Initialize the result
        result = {}
        
        if include_timestamps:
            result["timestamp"] = []
        
        for name in self.parameters:
            result[name] = []
        
        # Generate the time series
        start_time = self.current_time
        
        while self.current_time < start_time + duration:
            # Record the current time
            if include_timestamps:
                result["timestamp"].append(
                    self.start_time + timedelta(hours=self.current_time)
                )
            
            # Record the current values
            current_values = self.get_current_values()
            
            for name, value in current_values.items():
                result[name].append(value)
            
            # Step the simulation
            self.step(time_delta)
        
        return result
    
    def get_current_values(self) -> Dict[str, Any]:
        """
        Get the current values of all parameters.
        
        Returns:
            Dictionary mapping parameter names to their current values
        """
        return {name: param.value for name, param in self.parameters.items()}
    
    def reset(self) -> None:
        """
        Reset the generator to its initial state.
        
        This resets all parameters to their initial values and clears the event queue.
        """
        # Reset the time
        self.current_time = 0.0
        self.start_time = datetime.now()
        
        # Reset all parameters
        for param in self.parameters.values():
            param.reset()
        
        # Clear the event queue
        self.event_queue = []
    
    def export_to_csv(self, filepath: str, series: Optional[Dict[str, List[Any]]] = None) -> None:
        """
        Export a time series to a CSV file.
        
        Args:
            filepath: Path of the CSV file to create
            series: Time series data to export, or None to generate a new series
        """
        if series is None:
            # Generate a default time series
            series = self.generate_series(24.0, 1.0)
        
        # Open the file
        with open(filepath, 'w', newline='') as f:
            # Get the column names
            fieldnames = list(series.keys())
            
            # Create the CSV writer
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # Write the header
            writer.writeheader()
            
            # Write the rows
            for i in range(len(series[fieldnames[0]])):
                row = {name: values[i] for name, values in series.items()}
                writer.writerow(row)
    
    def export_to_json(self, filepath: str, series: Optional[Dict[str, List[Any]]] = None) -> None:
        """
        Export a time series to a JSON file.
        
        Args:
            filepath: Path of the JSON file to create
            series: Time series data to export, or None to generate a new series
        """
        if series is None:
            # Generate a default time series
            series = self.generate_series(24.0, 1.0)
        
        # Convert timestamp objects to strings
        if "timestamp" in series:
            series["timestamp"] = [str(ts) for ts in series["timestamp"]]
        
        # Write the JSON file
        with open(filepath, 'w') as f:
            json.dump(series, f, indent=2)
    
    def plot(
        self,
        series: Optional[Dict[str, List[Any]]] = None,
        parameters: Optional[List[str]] = None,
        title: Optional[str] = None,
        xlabel: str = "Time",
        ylabel: str = "Value",
        figsize: Tuple[int, int] = (10, 6),
        show: bool = True,
        save_path: Optional[str] = None
    ) -> None:
        """
        Plot a time series.
        
        Args:
            series: Time series data to plot, or None to generate a new series
            parameters: List of parameter names to plot, or None for all parameters
            title: Title of the plot, or None for a default title
            xlabel: Label for the x-axis
            ylabel: Label for the y-axis
            figsize: Figure size as (width, height) in inches
            show: Whether to show the plot
            save_path: Path to save the plot, or None to not save
        """
        if series is None:
            # Generate a default time series
            series = self.generate_series(24.0, 1.0)
        
        # Get the parameter names to plot
        if parameters is None:
            parameters = [name for name in series.keys() if name != "timestamp"]
        
        # Create the figure
        plt.figure(figsize=figsize)
        
        # Get the x-axis values
        if "timestamp" in series:
            x = series["timestamp"]
            if isinstance(x[0], str):
                # Convert string timestamps to datetime objects
                x = [datetime.fromisoformat(ts) for ts in x]
        else:
            x = range(len(series[parameters[0]]))
        
        # Plot each parameter
        for name in parameters:
            if name in series:
                plt.plot(x, series[name], label=name)
        
        # Add labels and title
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        
        if title:
            plt.title(title)
        else:
            plt.title("Time Series Plot")
        
        # Add legend
        plt.legend()
        
        # Rotate x-axis labels if they are timestamps
        if "timestamp" in series:
            plt.xticks(rotation=45)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save the plot
        if save_path:
            plt.savefig(save_path)
        
        # Show the plot
        if show:
            plt.show()
        else:
            plt.close()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the generator to a dictionary representation.
        
        Returns:
            Dictionary representation of the generator
        """
        return {
            "config": self.config,
            "parameters": [param.to_dict() for param in self.parameters.values()],
            "relationships": [rel.to_dict() for rel in self.relationships],
            "current_time": self.current_time,
            "start_time": str(self.start_time),
            "seed": self.seed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimeSeriesGenerator':
        """
        Create a generator from a dictionary representation.
        
        Args:
            data: Dictionary representation of the generator
            
        Returns:
            New TimeSeriesGenerator instance
        """
        # Extract the configuration
        config = data.get("config", {})
        
        # Create the generator
        generator = cls(config)
        
        # Set the seed
        generator.seed = data.get("seed")
        
        # Set the current time
        generator.current_time = data.get("current_time", 0.0)
        
        # Set the start time
        if "start_time" in data:
            try:
                generator.start_time = datetime.fromisoformat(data["start_time"])
            except:
                # Fallback to current time
                generator.start_time = datetime.now()
        
        # Add parameters
        for param_data in data.get("parameters", []):
            generator.add_parameter_from_dict(param_data)
        
        # Add relationships
        for rel_data in data.get("relationships", []):
            generator.add_relationship_from_dict(rel_data)
        
        return generator
    
    def save(self, filepath: str) -> None:
        """
        Save the generator to a file.
        
        Args:
            filepath: Path of the file to create
        """
        # Convert to dictionary
        data = self.to_dict()
        
        # Write to file
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'TimeSeriesGenerator':
        """
        Load a generator from a file.
        
        Args:
            filepath: Path of the file to load
            
        Returns:
            New TimeSeriesGenerator instance
        """
        # Read the file
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Create from dictionary
        return cls.from_dict(data)
