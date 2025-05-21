"""
EnviroSense Time Series Generator - Parameter Definition System

This module provides classes and functions for defining parameters with constraints
and relationships for use in the TimeSeriesGenerator.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
import numpy as np
from datetime import datetime

from envirosense.core.time_series.patterns import Pattern, PatternType


class ParameterType(Enum):
    """Types of parameters that can be defined."""
    CONTINUOUS = "continuous"  # Continuous values (float)
    DISCRETE = "discrete"      # Discrete values (int)
    CATEGORICAL = "categorical"  # Categorical values (string or enum)
    BOOLEAN = "boolean"        # Boolean values (True/False)


class Distribution(Enum):
    """Types of statistical distributions for parameter randomization."""
    UNIFORM = "uniform"         # Uniform distribution
    NORMAL = "normal"           # Normal (Gaussian) distribution
    EXPONENTIAL = "exponential" # Exponential distribution
    POISSON = "poisson"         # Poisson distribution
    BINOMIAL = "binomial"       # Binomial distribution
    CUSTOM = "custom"           # Custom distribution defined by a function


class ConstraintType(Enum):
    """Types of constraints that can be applied to parameters."""
    RANGE = "range"               # Minimum and maximum values
    RATE_OF_CHANGE = "rate_of_change"  # Maximum change between consecutive values
    ALLOWED_VALUES = "allowed_values"  # List of allowed values (for discrete/categorical)
    PATTERN = "pattern"           # Time-based pattern (diurnal, seasonal, etc.)
    CUSTOM = "custom"             # Custom constraint defined by a function


class Parameter:
    """
    Represents a parameter in the time series generation system.
    
    Parameters can be continuous, discrete, categorical, or boolean,
    and can have various constraints and behaviors.
    """
    
    def __init__(
        self,
        name: str,
        parameter_type: ParameterType,
        initial_value: Any,
        units: Optional[str] = None,
        description: Optional[str] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        allowed_values: Optional[List[Any]] = None,
        distribution: Optional[Distribution] = None,
        distribution_params: Optional[Dict[str, Any]] = None,
        custom_distribution: Optional[Callable] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a parameter with its properties and constraints.
        
        Args:
            name: Name of the parameter
            parameter_type: Type of the parameter (continuous, discrete, etc.)
            initial_value: Initial value of the parameter
            units: Units of measurement (e.g., "°C", "ppm")
            description: Description of what this parameter represents
            min_value: Minimum allowed value (for continuous and discrete)
            max_value: Maximum allowed value (for continuous and discrete)
            allowed_values: List of allowed values (for discrete and categorical)
            distribution: Statistical distribution for random variations
            distribution_params: Parameters for the distribution
            custom_distribution: Custom function for generating values
            metadata: Additional metadata for the parameter
        """
        self.name = name
        self.parameter_type = parameter_type
        self.units = units
        self.description = description or f"{name} parameter"
        self.metadata = metadata or {}
        
        # Validate and set initial value
        self._value = self._validate_initial_value(initial_value)
        self._history = [(datetime.now(), self._value)]
        
        # Set constraints
        self.min_value = min_value
        self.max_value = max_value
        self.allowed_values = allowed_values
        
        # Set distribution properties
        self.distribution = distribution
        self.distribution_params = distribution_params or {}
        self.custom_distribution = custom_distribution
        
        # Additional properties
        self.constraints = []
        self.rate_of_change = None
        self.pattern = None
        
    def _validate_initial_value(self, value: Any) -> Any:
        """Validate and possibly convert the initial value based on parameter type."""
        if self.parameter_type == ParameterType.CONTINUOUS:
            try:
                return float(value)
            except (ValueError, TypeError):
                raise ValueError(f"Initial value for continuous parameter {self.name} must be convertible to float")
        
        elif self.parameter_type == ParameterType.DISCRETE:
            try:
                return int(value)
            except (ValueError, TypeError):
                raise ValueError(f"Initial value for discrete parameter {self.name} must be convertible to int")
        
        elif self.parameter_type == ParameterType.BOOLEAN:
            return bool(value)
        
        # For categorical, just use the value as is
        return value
    
    @property
    def value(self) -> Any:
        """Get the current value of the parameter."""
        return self._value
    
    @value.setter
    def value(self, new_value: Any) -> None:
        """
        Set a new value for the parameter.
        
        This will validate the value against constraints and add it to the history.
        
        Args:
            new_value: New value to set
            
        Raises:
            ValueError: If the value violates any constraints
        """
        # Validate type and constraints
        if self.parameter_type == ParameterType.CONTINUOUS:
            new_value = float(new_value)
        elif self.parameter_type == ParameterType.DISCRETE:
            new_value = int(new_value)
        elif self.parameter_type == ParameterType.BOOLEAN:
            new_value = bool(new_value)
        
        # Check min/max constraints
        if self.min_value is not None and new_value < self.min_value:
            raise ValueError(f"Value {new_value} is below minimum {self.min_value} for {self.name}")
        
        if self.max_value is not None and new_value > self.max_value:
            raise ValueError(f"Value {new_value} is above maximum {self.max_value} for {self.name}")
        
        # Check allowed values
        if self.allowed_values is not None and new_value not in self.allowed_values:
            raise ValueError(f"Value {new_value} is not in allowed values {self.allowed_values} for {self.name}")
        
        # Check rate of change
        if self.rate_of_change is not None:
            old_value = self._value
            change = abs(new_value - old_value)
            if change > self.rate_of_change:
                raise ValueError(
                    f"Change {change} exceeds maximum rate of change {self.rate_of_change} for {self.name}"
                )
        
        # Check custom constraints
        for constraint_func, constraint_name in self.constraints:
            if not constraint_func(new_value, self._value):
                raise ValueError(f"Value {new_value} violates constraint {constraint_name} for {self.name}")
        
        # Set the new value and update history
        self._value = new_value
        self._history.append((datetime.now(), new_value))
    
    def add_constraint(self, constraint_func: Callable[[Any, Any], bool], name: str) -> None:
        """
        Add a custom constraint function.
        
        Args:
            constraint_func: Function that takes (new_value, old_value) and returns True if valid
            name: Name of the constraint for error reporting
        """
        self.constraints.append((constraint_func, name))
    
    def set_rate_of_change_constraint(self, max_rate: float) -> None:
        """
        Set the maximum rate of change constraint.
        
        Args:
            max_rate: Maximum allowed change between consecutive values
        """
        self.rate_of_change = max_rate
    
    def generate_next_value(self, time_delta: float = 1.0) -> Any:
        """
        Generate the next value based on distributions and constraints.
        
        Args:
            time_delta: Time step for the generation
            
        Returns:
            Next generated value
        """
        # If no distribution is set, return the current value
        if not self.distribution:
            return self._value
        
        # Generate a new value based on the distribution
        if self.distribution == Distribution.CUSTOM and self.custom_distribution:
            # Custom distribution uses a provided function
            new_value = self.custom_distribution(self._value, time_delta, self.distribution_params)
        
        elif self.distribution == Distribution.UNIFORM:
            # Uniform distribution
            min_val = self.distribution_params.get('min', self.min_value)
            max_val = self.distribution_params.get('max', self.max_value)
            
            if min_val is None or max_val is None:
                raise ValueError(f"Uniform distribution requires min and max parameters for {self.name}")
            
            new_value = np.random.uniform(min_val, max_val)
        
        elif self.distribution == Distribution.NORMAL:
            # Normal distribution
            mean = self.distribution_params.get('mean', self._value)
            std_dev = self.distribution_params.get('std_dev', 1.0)
            
            new_value = np.random.normal(mean, std_dev)
        
        elif self.distribution == Distribution.EXPONENTIAL:
            # Exponential distribution
            scale = self.distribution_params.get('scale', 1.0)
            
            # Exponential distribution generates positive values, might need offset
            new_value = np.random.exponential(scale)
            
            # If there's an offset parameter, apply it
            offset = self.distribution_params.get('offset', 0.0)
            new_value += offset
        
        elif self.distribution == Distribution.POISSON:
            # Poisson distribution (for discrete values)
            lam = self.distribution_params.get('lambda', 1.0)
            
            new_value = np.random.poisson(lam)
        
        elif self.distribution == Distribution.BINOMIAL:
            # Binomial distribution (for discrete values)
            n = self.distribution_params.get('n', 1)
            p = self.distribution_params.get('p', 0.5)
            
            new_value = np.random.binomial(n, p)
        
        else:
            raise ValueError(f"Unsupported distribution {self.distribution} for {self.name}")
        
        # Apply constraints
        if self.parameter_type == ParameterType.DISCRETE or self.parameter_type == ParameterType.CATEGORICAL:
            if self.allowed_values:
                # For discrete/categorical with allowed values, find the closest allowed value
                if new_value not in self.allowed_values:
                    # This only works for numeric types
                    if self.parameter_type == ParameterType.DISCRETE:
                        new_value = min(self.allowed_values, key=lambda x: abs(x - new_value))
                    else:
                        # For categorical, just keep the current value
                        new_value = self._value
            
            # For discrete parameters, convert to int
            if self.parameter_type == ParameterType.DISCRETE:
                new_value = int(round(new_value))
        
        # Apply min/max constraints
        if self.min_value is not None:
            new_value = max(self.min_value, new_value)
        
        if self.max_value is not None:
            new_value = min(self.max_value, new_value)
        
        # Apply rate of change constraint if specified
        if self.rate_of_change is not None:
            max_change = self.rate_of_change * time_delta
            old_value = self._value
            
            if abs(new_value - old_value) > max_change:
                # Clamp the change to the maximum allowed
                if new_value > old_value:
                    new_value = old_value + max_change
                else:
                    new_value = old_value - max_change
        
        return new_value
    
    def update(self, time_delta: float = 1.0) -> None:
        """
        Update the parameter value based on its distribution and constraints.
        
        Args:
            time_delta: Time step for the update
        """
        try:
            new_value = self.generate_next_value(time_delta)
            self.value = new_value
        except ValueError as e:
            # If there's a constraint violation, don't update the value
            print(f"Warning: Could not update {self.name}: {str(e)}")
    
    def get_history(self, limit: Optional[int] = None) -> List[Tuple[datetime, Any]]:
        """
        Get the history of values for this parameter.
        
        Args:
            limit: Maximum number of history entries to return (newest first)
            
        Returns:
            List of (timestamp, value) tuples
        """
        if limit:
            return self._history[-limit:]
        return self._history
    
    def reset(self, value: Optional[Any] = None) -> None:
        """
        Reset the parameter to a specific value or its initial value.
        
        Args:
            value: Value to reset to, or None to use the initial value
        """
        if value is None:
            value = self._history[0][1]  # Use the initial value
        
        self._value = self._validate_initial_value(value)
        self._history = [(datetime.now(), self._value)]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the parameter to a dictionary representation.
        
        Returns:
            Dictionary representation of the parameter
        """
        return {
            "name": self.name,
            "type": self.parameter_type.value,
            "current_value": self._value,
            "units": self.units,
            "description": self.description,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "allowed_values": self.allowed_values,
            "distribution": self.distribution.value if self.distribution else None,
            "distribution_params": self.distribution_params,
            "rate_of_change": self.rate_of_change,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Parameter':
        """
        Create a parameter from a dictionary representation.
        
        Args:
            data: Dictionary representation of the parameter
            
        Returns:
            New Parameter instance
        """
        # Extract required parameters
        name = data["name"]
        parameter_type = ParameterType(data["type"])
        initial_value = data["current_value"]
        
        # Create the parameter
        param = cls(
            name=name,
            parameter_type=parameter_type,
            initial_value=initial_value,
            units=data.get("units"),
            description=data.get("description"),
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            allowed_values=data.get("allowed_values"),
            distribution=Distribution(data["distribution"]) if data.get("distribution") else None,
            distribution_params=data.get("distribution_params", {}),
            metadata=data.get("metadata", {})
        )
        
        # Set rate of change constraint if specified
        if "rate_of_change" in data and data["rate_of_change"] is not None:
            param.set_rate_of_change_constraint(data["rate_of_change"])
        
        return param




class ParameterRelationship:
    """
    Defines a relationship between parameters.
    
    Relationships can be one-way (parameter A affects parameter B)
    or two-way (parameters A and B affect each other).
    """
    
    def __init__(
        self,
        source_parameter: str,
        target_parameter: str,
        relationship_function: Callable[[Any, Dict[str, Any]], Any],
        bidirectional: bool = False,
        reverse_function: Optional[Callable[[Any, Dict[str, Any]], Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ):
        """
        Initialize a parameter relationship.
        
        Args:
            source_parameter: Name of the source parameter
            target_parameter: Name of the target parameter
            relationship_function: Function that computes target value from source value
            bidirectional: Whether the relationship works in both directions
            reverse_function: Function for the reverse relationship (if bidirectional)
            params: Additional parameters for the relationship functions
            description: Description of the relationship
        """
        self.source_parameter = source_parameter
        self.target_parameter = target_parameter
        self.relationship_function = relationship_function
        self.bidirectional = bidirectional
        self.reverse_function = reverse_function
        self.params = params or {}
        self.description = description or f"Relationship from {source_parameter} to {target_parameter}"
    
    def apply(self, source_value: Any) -> Any:
        """
        Apply the relationship to compute the target value.
        
        Args:
            source_value: Value of the source parameter
            
        Returns:
            Computed value for the target parameter
        """
        return self.relationship_function(source_value, self.params)
    
    def apply_reverse(self, target_value: Any) -> Any:
        """
        Apply the reverse relationship to compute the source value.
        
        Args:
            target_value: Value of the target parameter
            
        Returns:
            Computed value for the source parameter
            
        Raises:
            ValueError: If the relationship is not bidirectional or no reverse function
        """
        if not self.bidirectional:
            raise ValueError(f"Relationship from {self.source_parameter} to {self.target_parameter} is not bidirectional")
        
        if not self.reverse_function:
            raise ValueError(f"No reverse function defined for relationship from {self.source_parameter} to {self.target_parameter}")
        
        return self.reverse_function(target_value, self.params)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the relationship to a dictionary representation.
        
        Returns:
            Dictionary representation of the relationship
        """
        return {
            "source_parameter": self.source_parameter,
            "target_parameter": self.target_parameter,
            "bidirectional": self.bidirectional,
            "params": self.params,
            "description": self.description
        }


# Example relationship functions

def linear_relationship(source_value: float, params: Dict[str, Any]) -> float:
    """
    Linear relationship between parameters.
    
    Target = slope * Source + offset
    
    Args:
        source_value: Value of the source parameter
        params: Parameters with 'slope' and 'offset'
        
    Returns:
        Computed value for the target parameter
    """
    slope = params.get("slope", 1.0)
    offset = params.get("offset", 0.0)
    return slope * source_value + offset


def exponential_relationship(source_value: float, params: Dict[str, Any]) -> float:
    """
    Exponential relationship between parameters.
    
    Target = base ^ (scale * Source) + offset
    
    Args:
        source_value: Value of the source parameter
        params: Parameters with 'base', 'scale', and 'offset'
        
    Returns:
        Computed value for the target parameter
    """
    base = params.get("base", 2.0)
    scale = params.get("scale", 1.0)
    offset = params.get("offset", 0.0)
    return base ** (scale * source_value) + offset


def threshold_relationship(source_value: float, params: Dict[str, Any]) -> float:
    """
    Threshold-based relationship between parameters.
    
    If Source >= threshold: Target = high_value
    Else: Target = low_value
    
    Args:
        source_value: Value of the source parameter
        params: Parameters with 'threshold', 'low_value', and 'high_value'
        
    Returns:
        Computed value for the target parameter
    """
    threshold = params.get("threshold", 0.0)
    low_value = params.get("low_value", 0.0)
    high_value = params.get("high_value", 1.0)
    
    if source_value >= threshold:
        return high_value
    else:
        return low_value


def logistic_relationship(source_value: float, params: Dict[str, Any]) -> float:
    """
    Logistic (sigmoid) relationship between parameters.
    
    Target = L / (1 + e^(-k * (Source - x0))) + offset
    
    Args:
        source_value: Value of the source parameter
        params: Parameters with 'L' (max), 'k' (steepness), 'x0' (midpoint), and 'offset'
        
    Returns:
        Computed value for the target parameter
    """
    L = params.get("L", 1.0)  # Maximum value
    k = params.get("k", 1.0)  # Steepness
    x0 = params.get("x0", 0.0)  # Midpoint
    offset = params.get("offset", 0.0)
    
    return L / (1 + np.exp(-k * (source_value - x0))) + offset
