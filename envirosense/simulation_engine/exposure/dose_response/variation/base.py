"""
Base classes for dose-response curve variation factors.

This module provides the foundational classes for creating and applying
variation factors to dose-response curves, allowing for personalized
adjustments based on individual characteristics.

References:
- jpm-12-01706.pdf: Section 4 "Toxicokinetic Variability Factors"
"""

from typing import Dict, Any, Optional
import copy
from abc import ABC, abstractmethod

from envirosense.core.exposure.dose_response.base import DoseResponseCurve


class VariationFactor(ABC):
    """
    Base class for factors that adjust dose-response curves.
    
    Variation factors modify dose-response curves based on specific
    characteristics, such as demographic factors, genetic factors,
    or health conditions.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize a variation factor.
        
        Args:
            name: Name of the variation factor
            description: Description of the variation factor
            metadata: Optional additional metadata for the variation factor
        """
        self.name = name
        self.description = description
        self.metadata = metadata or {}
    
    @abstractmethod
    def modify_dose_response(self, dose_response: DoseResponseCurve) -> DoseResponseCurve:
        """
        Modify a dose-response curve based on this variation factor.
        
        This method should be implemented by concrete subclasses to apply
        specific adjustments to the dose-response curve.
        
        Args:
            dose_response: Original dose-response curve
            
        Returns:
            Modified dose-response curve
        """
        pass
    
    def get_modification_info(self) -> Dict[str, Any]:
        """
        Get information about the modifications this factor applies.
        
        Returns:
            Dictionary containing details about the modifications
        """
        return {
            "name": self.name,
            "description": self.description,
            "type": type(self).__name__,
            "metadata": self.metadata
        }


class VariationAwareDoseResponse(DoseResponseCurve):
    """
    A dose-response curve that has built-in support for variation factors.
    
    This class extends the base DoseResponseCurve to include a list of
    variation factors that are applied when calculating responses.
    """
    
    def __init__(
        self,
        base_curve: DoseResponseCurve,
        variation_factors: Optional[list[VariationFactor]] = None
    ) -> None:
        """
        Initialize a variation-aware dose-response curve.
        
        Args:
            base_curve: Base dose-response curve to use
            variation_factors: Optional list of variation factors to apply
        """
        # Copy the base curve's attributes
        super().__init__(
            chemical_id=base_curve.chemical_id,
            parameters=copy.deepcopy(base_curve.parameters),
            metadata=copy.deepcopy(base_curve.metadata)
        )
        
        self.base_curve = base_curve
        self.variation_factors = variation_factors or []
        
        # Add information about the variation factors to the metadata
        if "variations" not in self.metadata:
            self.metadata["variations"] = []
            
        for factor in self.variation_factors:
            self.metadata["variations"].append({
                "name": factor.name,
                "description": factor.description,
                "factor_type": type(factor).__name__
            })
    
    def calculate_response(self, dose: float) -> float:
        """
        Calculate the response for a given dose, applying all variation factors.
        
        Args:
            dose: Dose value
            
        Returns:
            Response value
        """
        # Make a copy of the base curve
        modified_curve = copy.deepcopy(self.base_curve)
        
        # Apply each variation factor in sequence
        for factor in self.variation_factors:
            modified_curve = factor.modify_dose_response(modified_curve)
        
        # Calculate the response using the modified curve
        return modified_curve.calculate_response(dose)
    
    def add_variation_factor(self, factor: VariationFactor) -> None:
        """
        Add a new variation factor to this curve.
        
        Args:
            factor: Variation factor to add
        """
        self.variation_factors.append(factor)
        
        # Add information about the factor to the metadata
        if "variations" not in self.metadata:
            self.metadata["variations"] = []
            
        self.metadata["variations"].append({
            "name": factor.name,
            "description": factor.description,
            "factor_type": type(factor).__name__
        })
    
    def remove_variation_factor(self, factor_index: int) -> None:
        """
        Remove a variation factor by index.
        
        Args:
            factor_index: Index of the factor to remove
        """
        if 0 <= factor_index < len(self.variation_factors):
            # Remove the factor
            self.variation_factors.pop(factor_index)
            
            # Remove the metadata entry
            if "variations" in self.metadata and factor_index < len(self.metadata["variations"]):
                self.metadata["variations"].pop(factor_index)
