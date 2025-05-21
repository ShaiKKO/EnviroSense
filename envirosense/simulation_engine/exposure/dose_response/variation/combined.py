"""
Combined variation factors for dose-response curves.

This module provides mechanisms for applying multiple variation factors
together and integrating with sensitivity profiles from the system.

References:
- jpm-12-01706.pdf: Section 5 "Integrated Personalized Response Models"
"""

from typing import Dict, List, Optional, Union, Any, Tuple
import numpy as np
import copy
import json

from envirosense.core.exposure.dose_response.base import DoseResponseCurve
from envirosense.core.exposure.dose_response.types import LiteratureReference
from envirosense.core.exposure.dose_response.variation.base import VariationFactor


class VariationFactorSet(VariationFactor):
    """
    Variation factor that combines multiple other variation factors.
    
    This factor applies multiple variation factors in sequence, allowing
    for complex combinations of demographic, genetic, and health status
    factors to be applied together.
    
    Implementation based on research from:
    - jpm-12-01706.pdf: Section 5.1 "Combining Multiple Factors"
    """
    
    def __init__(
        self,
        factors: List[VariationFactor],
        application_order: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        """
        Initialize a combined variation factor set.
        
        Args:
            factors: List of variation factors to apply
            application_order: Optional list of factor type names to specify
                the order in which factors should be applied. If not provided,
                factors will be applied in the order they are provided.
            **kwargs: Additional arguments to pass to VariationFactor.__init__
        """
        name = kwargs.pop("name", f"Combined Variation Factors ({len(factors)})")
        description = kwargs.pop("description", 
                              f"Combines multiple variation factors into a single factor")
        
        super().__init__(name=name, description=description, **kwargs)
        
        self.factors = factors
        self.application_order = application_order
        
        # If an application order is specified, sort factors accordingly
        if application_order:
            # Create a mapping of factor types to indexes in the application order
            order_map = {factor_type: i for i, factor_type in enumerate(application_order)}
            
            # Sort factors by their type's position in the application order
            # Factors whose types are not in the application order will be applied last
            self.factors = sorted(
                self.factors,
                key=lambda f: order_map.get(type(f).__name__, len(application_order))
            )
    
    def modify_dose_response(self, dose_response: DoseResponseCurve) -> DoseResponseCurve:
        """
        Modify a dose-response curve by applying all variation factors in sequence.
        
        This method applies each variation factor in the set in order, with each
        factor modifying the result of the previous factor's application.
        
        Args:
            dose_response: Original dose-response curve
            
        Returns:
            Modified dose-response curve with all variations applied
        """
        # Start with the original curve
        modified_curve = copy.deepcopy(dose_response)
        
        # Apply each factor in sequence
        for factor in self.factors:
            modified_curve = factor.modify_dose_response(modified_curve)
        
        # Add metadata about this factor set
        if "variations" not in modified_curve.metadata:
            modified_curve.metadata["variations"] = []
            
        modified_curve.metadata["variations"].append({
            "factor_type": "VariationFactorSet",
            "factor_count": len(self.factors),
            "factor_types": [type(f).__name__ for f in self.factors]
        })
        
        return modified_curve
    
    def add_factor(self, factor: VariationFactor) -> None:
        """
        Add a new variation factor to this set.
        
        Args:
            factor: Variation factor to add
        """
        self.factors.append(factor)
        
        # If an application order is specified, re-sort factors
        if self.application_order:
            # Create a mapping of factor types to indexes in the application order
            order_map = {factor_type: i for i, factor_type in enumerate(self.application_order)}
            
            # Sort factors by their type's position in the application order
            self.factors = sorted(
                self.factors,
                key=lambda f: order_map.get(type(f).__name__, len(self.application_order))
            )
    
    def get_factor_by_type(self, factor_type: str) -> Optional[VariationFactor]:
        """
        Get the first factor of a specific type.
        
        Args:
            factor_type: Name of the factor type class
            
        Returns:
            The first factor of the specified type, or None if not found
        """
        for factor in self.factors:
            if type(factor).__name__ == factor_type:
                return factor
        return None
    
    def get_factors_by_type(self, factor_type: str) -> List[VariationFactor]:
        """
        Get all factors of a specific type.
        
        Args:
            factor_type: Name of the factor type class
            
        Returns:
            List of factors of the specified type
        """
        return [factor for factor in self.factors if type(factor).__name__ == factor_type]
    
    def get_modification_info(self) -> Dict[str, Any]:
        """
        Get information about the modifications this factor set applies.
        
        Returns:
            Dictionary containing details about the modifications
        """
        base_info = super().get_modification_info()
        
        # Add information about the contained factors
        factor_info = []
        for factor in self.factors:
            factor_info.append(factor.get_modification_info())
        
        base_info["contained_factors"] = factor_info
        
        return base_info


class ProfileBasedVariation(VariationFactor):
    """
    Variation factor that creates variation factors from a sensitivity profile.
    
    This factor extracts information from a sensitivity profile and creates
    appropriate variation factors based on the profile's demographics, health
    conditions, and other characteristics.
    
    Implementation based on research from:
    - jpm-12-01706.pdf: Section 5.2 "Profile-Based Personalization"
    """
    
    def __init__(
        self,
        profile: Dict[str, Any],
        **kwargs
    ) -> None:
        """
        Initialize a profile-based variation factor.
        
        Args:
            profile: Sensitivity profile data
            **kwargs: Additional arguments to pass to VariationFactor.__init__
        """
        # Extract profile ID for name if available
        profile_id = profile.get("profile_id", "Unknown")
        name = kwargs.pop("name", f"Profile-Based Variation ({profile_id})")
        description = kwargs.pop("description", 
                              f"Variation factor based on sensitivity profile")
        
        super().__init__(name=name, description=description, **kwargs)
        
        self.profile = profile
        self.factor_set = self._create_variation_factors()
    
    def _create_variation_factors(self) -> VariationFactorSet:
        """
        Create variation factors based on the sensitivity profile.
        
        Returns:
            VariationFactorSet containing all extracted factors
        """
        factors = []
        
        # Import factor classes here to avoid circular imports
        from envirosense.core.exposure.dose_response.variation.demographic import (
            AgeFactor, GenderFactor, BodyMassIndexFactor
        )
        from envirosense.core.exposure.dose_response.variation.genetic import (
            GeneticFactor, EnzymeExpressionFactor
        )
        from envirosense.core.exposure.dose_response.variation.health_status import (
            HealthConditionFactor, OrganFunctionFactor
        )
        
        # Extract demographic factors
        demographics = self.profile.get("demographics", {})
        
        # Age factor
        if "age" in demographics and demographics["age"] is not None:
            factors.append(AgeFactor(demographics["age"]))
        
        # Gender factor
        if "sex" in demographics and demographics["sex"] is not None:
            factors.append(GenderFactor(demographics["sex"]))
        
        # BMI factor
        if "bmi" in demographics and demographics["bmi"] is not None:
            factors.append(BodyMassIndexFactor(demographics["bmi"]))
        
        # Extract health condition factors
        conditions = self.profile.get("conditions", [])
        if conditions:
            factors.append(HealthConditionFactor(conditions))
        
        # Extract genetic factors if available
        genetic_variants = self.profile.get("genetic_variants", [])
        if genetic_variants:
            factors.append(GeneticFactor(genetic_variants))
        
        # Extract enzyme expression levels if available
        enzyme_levels = self.profile.get("enzyme_expression_levels", {})
        if enzyme_levels:
            factors.append(EnzymeExpressionFactor(enzyme_levels))
        
        # Extract organ function levels if available
        organ_function = self.profile.get("organ_function_levels", {})
        if organ_function:
            factors.append(OrganFunctionFactor(organ_function))
        
        # Extract sensitivity scores for chemicals
        sensitivity_scores = self.profile.get("sensitivity_scores", {})
        
        # Create application order based on jpm-12-01706.pdf recommendations
        application_order = [
            "AgeFactor",             # Basic demographics first
            "GenderFactor",
            "BodyMassIndexFactor",
            "GeneticFactor",         # Genetic factors affect metabolism
            "EnzymeExpressionFactor",
            "HealthConditionFactor", # Health conditions affect organ function
            "OrganFunctionFactor"    # Organ function is most specific
        ]
        
        return VariationFactorSet(factors, application_order=application_order)
    
    def modify_dose_response(self, dose_response: DoseResponseCurve) -> DoseResponseCurve:
        """
        Modify a dose-response curve based on the sensitivity profile.
        
        This method applies all the variation factors extracted from the profile
        to the dose-response curve.
        
        Args:
            dose_response: Original dose-response curve
            
        Returns:
            Modified dose-response curve with profile-based variations applied
        """
        # Use the factor set to modify the curve
        modified_curve = self.factor_set.modify_dose_response(dose_response)
        
        # Apply direct sensitivity adjustments if available
        chemical_id = dose_response.chemical_id
        sensitivity_scores = self.profile.get("sensitivity_scores", {})
        
        # If we have a direct sensitivity score for this chemical or its class
        if chemical_id in sensitivity_scores:
            # Create a deep copy if we haven't already modified the curve
            if modified_curve is dose_response:
                modified_curve = copy.deepcopy(dose_response)
            
            # Get the sensitivity score (1.0 = average, higher = more sensitive)
            sensitivity = sensitivity_scores[chemical_id]
            
            # Apply curve-type specific adjustments
            curve_type = type(dose_response).__name__
            
            if curve_type == "LinearDoseResponse":
                # For linear models, adjust slope based on sensitivity
                if "slope" in modified_curve.parameters:
                    modified_curve._parameters["slope"] *= sensitivity
                    
            elif curve_type == "SigmoidDoseResponse" or curve_type == "LogisticDoseResponse":
                # For sigmoid/logistic curves, adjust EC50 inversely with sensitivity
                if "ec50" in modified_curve.parameters:
                    modified_curve._parameters["ec50"] *= (1 / sensitivity)
        
        # Add metadata about this profile-based variation
        if "variations" not in modified_curve.metadata:
            modified_curve.metadata["variations"] = []
            
        modified_curve.metadata["variations"].append({
            "factor_type": "ProfileBasedVariation",
            "profile_id": self.profile.get("profile_id", "Unknown"),
            "profile_demographics": self.profile.get("demographics", {}),
            "factor_count": len(self.factor_set.factors)
        })
        
        return modified_curve
    
    def get_modification_info(self) -> Dict[str, Any]:
        """
        Get information about the modifications this profile applies.
        
        Returns:
            Dictionary containing details about the modifications
        """
        base_info = super().get_modification_info()
        
        # Add information about the profile
        base_info["profile_id"] = self.profile.get("profile_id", "Unknown")
        base_info["profile_demographics"] = self.profile.get("demographics", {})
        base_info["profile_conditions"] = self.profile.get("conditions", [])
        
        # Add information about the extracted factors
        base_info["extracted_factors"] = [
            type(factor).__name__ for factor in self.factor_set.factors
        ]
        
        return base_info
