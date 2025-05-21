"""
Base class for dose-response models.

This module defines the abstract base class that all dose-response curve models
must implement, ensuring a consistent interface and behavior.
"""

import abc
from typing import Dict, List, Optional, Union, Any, Tuple
import numpy as np
import json

from envirosense.core.exposure.dose_response.types import (
    ResponseType, DoseUnit, ResponseUnit, ReliabilityRating,
    LiteratureReference, DoseValue, ResponseValue
)


class DoseResponseCurve(abc.ABC):
    """
    Abstract base class for all dose-response curve models.
    
    This class defines the common interface that all dose-response models
    must implement, ensuring consistent behavior across different model types.
    
    Attributes:
        chemical_id (str): Identifier for the chemical substance
        response_type (ResponseType): Type of biological response being modeled
        dose_unit (DoseUnit): Unit of measurement for dose values
        response_unit (ResponseUnit): Unit of measurement for response values
        reliability (ReliabilityRating): Rating of data reliability
        references (List[LiteratureReference]): Scientific references supporting this model
        description (str): Human-readable description of this curve
        metadata (Dict[str, Any]): Additional metadata about this curve
    """
    
    def __init__(
        self,
        chemical_id: str,
        response_type: Union[ResponseType, str],
        dose_unit: Union[DoseUnit, str],
        response_unit: Union[ResponseUnit, str],
        reliability: Optional[Union[ReliabilityRating, str]] = None,
        references: Optional[List[LiteratureReference]] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize the dose-response curve.
        
        Args:
            chemical_id: Identifier for the chemical substance
            response_type: Type of biological response this curve models
            dose_unit: Unit of measurement for the dose (e.g., 'mg/kg', 'ppm')
            response_unit: Unit of measurement for the response (e.g., '%', 'probability')
            reliability: Rating of the data reliability
            references: Scientific references supporting this model
            description: Human-readable description of this curve
            metadata: Additional metadata about this curve
        """
        # Store basic identification information
        self.chemical_id = chemical_id
        self.description = description or f"Dose-response curve for {chemical_id}"
        
        # Convert string enums to proper enum values if needed
        if isinstance(response_type, str):
            self.response_type = ResponseType(response_type)
        else:
            self.response_type = response_type
            
        if isinstance(dose_unit, str):
            self.dose_unit = DoseUnit(dose_unit)
        else:
            self.dose_unit = dose_unit
            
        if isinstance(response_unit, str):
            self.response_unit = ResponseUnit(response_unit)
        else:
            self.response_unit = response_unit
            
        if reliability is not None:
            if isinstance(reliability, str):
                self.reliability = ReliabilityRating(reliability)
            else:
                self.reliability = reliability
        else:
            self.reliability = ReliabilityRating.UNKNOWN
        
        # References and metadata
        self.references = references or []
        self.metadata = metadata or {}
        
        # Initialize internal parameter and uncertainty storage
        self._parameters = {}
        self._uncertainty = {}
        self._parameter_info = {}
    
    @abc.abstractmethod
    def predict(
        self, 
        doses: Union[DoseValue, List[DoseValue], np.ndarray], 
        include_uncertainty: bool = False,
        confidence_level: float = 0.95,
        **kwargs
    ) -> Union[ResponseValue, Tuple]:
        """
        Predict response values for given dose values.
        
        Args:
            doses: Single dose value or array of dose values
            include_uncertainty: Whether to include uncertainty estimates
            confidence_level: Confidence level for uncertainty bounds (0-1)
            **kwargs: Additional prediction options
            
        Returns:
            If include_uncertainty is False:
                Single response value or array of response values
            If include_uncertainty is True:
                Tuple of (responses, lower_bound, upper_bound)
        """
        pass
    
    @abc.abstractmethod
    def fit(
        self, 
        doses: Union[List[DoseValue], np.ndarray], 
        responses: Union[List[ResponseValue], np.ndarray],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fit the model parameters to observed dose-response data.
        
        Args:
            doses: Array of dose values
            responses: Array of response values
            **kwargs: Additional fitting options
            
        Returns:
            Dictionary of fitting results and diagnostics
        """
        pass
    
    @property
    def parameters(self) -> Dict[str, float]:
        """Get all model parameters as a dictionary."""
        return self._parameters.copy()
    
    @property
    def uncertainty(self) -> Dict[str, float]:
        """Get uncertainty estimates for all parameters."""
        return self._uncertainty.copy()
    
    @property
    def parameter_info(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed information about each parameter."""
        return self._parameter_info.copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the model to a dictionary representation suitable for serialization.
        
        Returns:
            Dictionary representation of the model.
        """
        # Collect basic model information
        result = {
            'model_type': self.__class__.__name__,
            'chemical_id': self.chemical_id,
            'response_type': self.response_type.value,
            'dose_unit': self.dose_unit.value,
            'response_unit': self.response_unit.value,
            'reliability': self.reliability.value,
            'description': self.description,
            'parameters': self.parameters,
            'uncertainty': self.uncertainty,
            'metadata': self.metadata
        }
        
        # Convert references to dictionaries
        if self.references:
            result['references'] = [ref.to_dict() for ref in self.references]
        else:
            result['references'] = []
            
        return result
    
    def to_json(self, indent: int = 2) -> str:
        """
        Convert the model to a JSON string representation.
        
        Args:
            indent: Number of spaces for indentation in the JSON string
            
        Returns:
            JSON string representation of the model.
        """
        model_dict = self.to_dict()
        return json.dumps(model_dict, indent=indent)
    
    def save(self, file_path: str) -> None:
        """
        Save the model to a JSON file.
        
        Args:
            file_path: Path to save the model JSON file
        """
        with open(file_path, 'w') as f:
            f.write(self.to_json())
            
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DoseResponseCurve':
        """
        Create a model instance from a dictionary representation.
        
        This is a placeholder method that derived classes should override
        to implement proper deserialization logic specific to each model type.
        
        Args:
            data: Dictionary containing model parameters and metadata
            
        Returns:
            Instance of a dose-response model
            
        Raises:
            NotImplementedError: This base method is not implemented
        """
        raise NotImplementedError(
            "from_dict() is not implemented in the base class. "
            "Each derived class must implement its own version."
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DoseResponseCurve':
        """
        Create a model instance from a JSON string representation.
        
        Args:
            json_str: JSON string representation of the model
            
        Returns:
            Instance of a dose-response model
        """
        data = json.loads(json_str)
        model_type = data.get('model_type')
        
        # This would need to be expanded as more model types are added
        if model_type == 'LinearDoseResponse':
            # Import here to avoid circular import
            from envirosense.core.exposure.dose_response.models import LinearDoseResponse
            return LinearDoseResponse.from_dict(data)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    @classmethod
    def load(cls, file_path: str) -> 'DoseResponseCurve':
        """
        Load a model from a JSON file.
        
        Args:
            file_path: Path to the model JSON file
            
        Returns:
            Instance of a dose-response model
        """
        with open(file_path, 'r') as f:
            json_str = f.read()
        return cls.from_json(json_str)
    
    def __str__(self) -> str:
        """String representation of the model."""
        return (
            f"{self.__class__.__name__}(chemical_id='{self.chemical_id}', "
            f"response_type={self.response_type}, "
            f"parameters={self.parameters})"
        )
    
    def __repr__(self) -> str:
        """Detailed string representation of the model."""
        return str(self)
