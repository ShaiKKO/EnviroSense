"""
Base Biometric Signal Model

This module provides the base class for all biometric signal models in the EnviroSense
system. It defines common interfaces and functionality for generating physiological
signals that respond to environmental factors and chemical exposures.
"""

import abc
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
import uuid
import matplotlib.pyplot as plt

from envirosense.core.time_series.parameters import Parameter


class BiometricSignalModel(abc.ABC):
    """Base abstract class for all biometric signal models.
    
    This class defines the common interface for all biometric signal models, which
    simulate physiological responses to environmental conditions and exposures.
    
    Attributes:
        name (str): Name of the biometric signal model
        description (str): Description of what the model represents
        parameters (Dict[str, Parameter]): Dictionary of parameters that influence the signal
        baseline_value (float): Baseline value of the signal when no exposure occurs
        response_factors (Dict[str, float]): Dictionary of response factors for different chemicals/exposures
        uuid (str): Unique identifier for the model instance
        is_active (bool): Whether the model is currently active
        history (List[Tuple[float, float]]): History of signal values (time, value)
    """
    
    def __init__(self, 
                name: str, 
                description: str,
                baseline_value: float,
                parameters: Optional[Dict[str, Parameter]] = None,
                response_factors: Optional[Dict[str, float]] = None):
        """Initialize the biometric signal model.
        
        Args:
            name: Name of the model
            description: Description of what the model represents
            baseline_value: Baseline value when no exposure occurs
            parameters: Optional dictionary of parameters that influence the signal
            response_factors: Optional dictionary of response factors for different chemicals/exposures
        """
        self.name = name
        self.description = description
        self.baseline_value = baseline_value
        self.parameters = parameters or {}
        self.response_factors = response_factors or {}
        self.uuid = str(uuid.uuid4())
        self.is_active = True
        self.history = []
    
    @abc.abstractmethod
    def generate_signal(self, 
                       time_point: float, 
                       exposures: Optional[Dict[str, float]] = None, 
                       environmental_conditions: Optional[Dict[str, float]] = None) -> float:
        """Generate a biometric signal value for a given time point.
        
        Args:
            time_point: The time point to generate the signal for
            exposures: Optional dictionary of chemical exposures and their concentrations
            environmental_conditions: Optional dictionary of environmental conditions
            
        Returns:
            The generated signal value
        """
        pass
    
    def add_to_history(self, time_point: float, value: float) -> None:
        """Add a signal value to the history.
        
        Args:
            time_point: The time point
            value: The signal value
        """
        self.history.append((time_point, value))
    
    def get_history_array(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get the history as numpy arrays.
        
        Returns:
            Tuple of (time_points, values) as numpy arrays
        """
        if not self.history:
            return np.array([]), np.array([])
        
        time_points, values = zip(*self.history)
        return np.array(time_points), np.array(values)
    
    def reset_history(self) -> None:
        """Reset the signal history."""
        self.history = []
    
    def plot_history(self, 
                    title: Optional[str] = None, 
                    figsize: Tuple[int, int] = (10, 6),
                    ylim: Optional[Tuple[float, float]] = None) -> plt.Figure:
        """Plot the signal history.
        
        Args:
            title: Optional title for the plot
            figsize: Figure size (width, height) in inches
            ylim: Optional y-axis limits as (min, max)
            
        Returns:
            The matplotlib figure object
        """
        if not self.history:
            raise ValueError("No history to plot")
        
        fig, ax = plt.subplots(figsize=figsize)
        
        time_points, values = self.get_history_array()
        ax.plot(time_points, values, label=self.name)
        
        if title:
            ax.set_title(title)
        else:
            ax.set_title(f"{self.name} - Biometric Signal")
        
        ax.set_xlabel("Time")
        ax.set_ylabel("Signal Value")
        
        if ylim:
            ax.set_ylim(ylim)
        
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        return fig
    
    def set_parameter(self, name: str, parameter: Parameter) -> None:
        """Set a parameter for the model.
        
        Args:
            name: Parameter name
            parameter: Parameter object
        """
        self.parameters[name] = parameter
    
    def set_response_factor(self, agent: str, factor: float) -> None:
        """Set a response factor for a specific agent.
        
        Args:
            agent: Name of the chemical or environmental factor
            factor: Response factor value
        """
        self.response_factors[agent] = factor
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        return {
            "uuid": self.uuid,
            "name": self.name,
            "description": self.description,
            "baseline_value": self.baseline_value,
            "parameters": {name: param.to_dict() for name, param in self.parameters.items()},
            "response_factors": self.response_factors,
            "is_active": self.is_active,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BiometricSignalModel':
        """Create a model instance from a dictionary.
        
        This method must be implemented by subclasses to properly initialize
        model-specific attributes.
        
        Args:
            data: Dictionary containing model data
            
        Returns:
            An instance of the model
        """
        raise NotImplementedError("Subclasses must implement from_dict method")
