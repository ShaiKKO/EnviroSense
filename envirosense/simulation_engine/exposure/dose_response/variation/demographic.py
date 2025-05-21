"""
Demographic variation factors for dose-response curves.

This module implements variation factors based on demographic characteristics
such as age, gender, and body mass index, which can significantly affect
an individual's response to chemical exposures.

References:
- Dose_response_Curve_measurements.pdf: "Age-Dependent Pharmacokinetics"
- jpm-12-01706.pdf: Section 4.1 "Demographic Factors in Toxicokinetics"
"""

from typing import Dict, List, Optional, Union, Any, Tuple
import numpy as np
import copy

from envirosense.core.exposure.dose_response.base import DoseResponseCurve
from envirosense.core.exposure.dose_response.types import LiteratureReference
from envirosense.core.exposure.dose_response.variation.base import VariationFactor


class AgeFactor(VariationFactor):
    """
    Variation factor that adjusts dose-response based on age.
    
    This factor models how age affects pharmacokinetics and pharmacodynamics,
    typically by modifying clearance rates, absorption, and sensitivity
    parameters in dose-response curves.
    
    Implementation based on age-based adjustment factors from:
    - Dose_response_Curve_measurements.pdf: Table 4 "Age-Based Pharmacokinetic Adjustment Factors"
    """
    
    # Age group definitions and parameter adjustment factors
    # Values based on research findings in Dose_response_Curve_measurements.pdf
    AGE_GROUPS = {
        "infant": (0, 2, {
            "clearance_rate": 0.5,      # Reduced clearance in infants
            "absorption_rate": 1.2,     # Increased absorption
            "slope": 1.5,               # Steeper dose-response curve
            "threshold": 0.7            # Lower threshold (more sensitive)
        }),
        "child": (3, 12, {
            "clearance_rate": 0.7,
            "absorption_rate": 1.1,
            "slope": 1.3,
            "threshold": 0.8
        }),
        "adolescent": (13, 19, {
            "clearance_rate": 0.9,
            "absorption_rate": 1.0,
            "slope": 1.1,
            "threshold": 0.9
        }),
        "adult": (20, 64, {
            "clearance_rate": 1.0,      # Reference group (baseline)
            "absorption_rate": 1.0,
            "slope": 1.0,
            "threshold": 1.0
        }),
        "elderly": (65, 120, {
            "clearance_rate": 0.8,      # Reduced clearance in elderly
            "absorption_rate": 0.9,
            "slope": 1.2,
            "threshold": 0.8
        })
    }
    
    def __init__(
        self,
        age: int,
        chemical_specific_adjustments: Optional[Dict[str, Dict[str, float]]] = None,
        **kwargs
    ) -> None:
        """
        Initialize an age-based variation factor.
        
        Args:
            age: Age in years
            chemical_specific_adjustments: Optional dictionary mapping chemical IDs to
                parameter adjustment dictionaries (overrides default adjustments)
            **kwargs: Additional arguments to pass to VariationFactor.__init__
        """
        name = kwargs.pop("name", f"Age Factor ({age} years)")
        description = kwargs.pop("description", 
                               f"Adjusts dose-response parameters based on age ({age} years)")
        
        super().__init__(name=name, description=description, **kwargs)
        
        self.age = age
        self.age_group = self._determine_age_group(age)
        self.adjustment_factors = self._get_adjustment_factors(self.age_group)
        self.chemical_specific_adjustments = chemical_specific_adjustments or {}
        
    def _determine_age_group(self, age: int) -> str:
        """
        Determine the age group for a given age.
        
        Args:
            age: Age in years
            
        Returns:
            Age group name
        """
        for group_name, (min_age, max_age, _) in self.AGE_GROUPS.items():
            if min_age <= age <= max_age:
                return group_name
        
        # Default to adult if age is outside all ranges
        return "adult"
    
    def _get_adjustment_factors(self, age_group: str) -> Dict[str, float]:
        """
        Get the adjustment factors for a given age group.
        
        Args:
            age_group: Age group name
            
        Returns:
            Dictionary of adjustment factors
        """
        _, _, factors = self.AGE_GROUPS.get(age_group, self.AGE_GROUPS["adult"])
        return factors
    
    def modify_dose_response(self, dose_response: DoseResponseCurve) -> DoseResponseCurve:
        """
        Modify a dose-response curve based on age-related factors.
        
        This method applies age-specific adjustments to the curve's parameters,
        typically affecting the clearance rate (which impacts effective dose),
        the slope of the curve, and the threshold at which effects begin.
        
        Args:
            dose_response: Original dose-response curve
            
        Returns:
            Modified dose-response curve with age-adjusted parameters
        """
        # Create a deep copy to avoid modifying the original
        modified_curve = copy.deepcopy(dose_response)
        
        # Get chemical-specific adjustments if available, otherwise use defaults
        chemical_id = dose_response.chemical_id
        adjustment_factors = (
            self.chemical_specific_adjustments.get(chemical_id, self.adjustment_factors)
        )
        
        # Apply modifications to parameters based on curve type
        curve_type = type(dose_response).__name__
        
        # Parameter modifications vary by curve type
        if curve_type == "LinearDoseResponse":
            # For linear models, modify slope and intercept
            if "slope" in modified_curve.parameters and "slope" in adjustment_factors:
                modified_curve._parameters["slope"] *= adjustment_factors["slope"]
                
            if "intercept" in modified_curve.parameters and "threshold" in adjustment_factors:
                # Adjust intercept based on threshold factor (inverse relationship)
                threshold_factor = adjustment_factors["threshold"]
                modified_curve._parameters["intercept"] *= (2 - threshold_factor)
                
        elif curve_type == "SigmoidDoseResponse" or curve_type == "LogisticDoseResponse":
            # For sigmoid/logistic curves, modify EC50 (median effective concentration) and Hill slope
            if "ec50" in modified_curve.parameters and "threshold" in adjustment_factors:
                # Lower threshold (more sensitive) means lower EC50
                modified_curve._parameters["ec50"] *= adjustment_factors["threshold"]
                
            if "hill_slope" in modified_curve.parameters and "slope" in adjustment_factors:
                modified_curve._parameters["hill_slope"] *= adjustment_factors["slope"]
        
        # Add metadata about the modification
        if "variations" not in modified_curve.metadata:
            modified_curve.metadata["variations"] = []
            
        modified_curve.metadata["variations"].append({
            "factor_type": "AgeFactor",
            "age": self.age,
            "age_group": self.age_group,
            "adjustment_factors": adjustment_factors
        })
        
        return modified_curve


class GenderFactor(VariationFactor):
    """
    Variation factor that adjusts dose-response based on gender.
    
    This factor models how gender affects pharmacokinetics and pharmacodynamics,
    such as differences in body composition, enzyme expression, and hormonal
    influences on metabolism.
    
    Implementation based on gender-specific adjustment factors from:
    - jpm-12-01706.pdf: Section 4.1.2 "Gender-Related Differences in Toxicokinetics"
    """
    
    # Gender-specific parameter adjustment factors
    # Values based on research findings in jpm-12-01706.pdf
    GENDER_ADJUSTMENTS = {
        "male": {
            "clearance_rate": 1.0,      # Reference group (baseline)
            "absorption_rate": 1.0,
            "distribution_volume": 1.0,
            "metabolic_rate": 1.0
        },
        "female": {
            "clearance_rate": 0.9,      # Typically lower clearance rates
            "absorption_rate": 1.1,     # Often higher absorption
            "distribution_volume": 0.8,  # Lower average body water content
            "metabolic_rate": 0.9       # Different enzyme expression levels
        },
        # Could include other categories based on available research
    }
    
    def __init__(
        self,
        gender: str,
        chemical_specific_adjustments: Optional[Dict[str, Dict[str, float]]] = None,
        **kwargs
    ) -> None:
        """
        Initialize a gender-based variation factor.
        
        Args:
            gender: Gender identifier (e.g., "male", "female")
            chemical_specific_adjustments: Optional dictionary mapping chemical IDs to
                parameter adjustment dictionaries (overrides default adjustments)
            **kwargs: Additional arguments to pass to VariationFactor.__init__
        """
        name = kwargs.pop("name", f"Gender Factor ({gender})")
        description = kwargs.pop("description", 
                               f"Adjusts dose-response parameters based on gender ({gender})")
        
        super().__init__(name=name, description=description, **kwargs)
        
        self.gender = gender.lower()
        self.adjustment_factors = self._get_adjustment_factors(self.gender)
        self.chemical_specific_adjustments = chemical_specific_adjustments or {}
        
    def _get_adjustment_factors(self, gender: str) -> Dict[str, float]:
        """
        Get the adjustment factors for a given gender.
        
        Args:
            gender: Gender identifier
            
        Returns:
            Dictionary of adjustment factors
        """
        return self.GENDER_ADJUSTMENTS.get(gender, self.GENDER_ADJUSTMENTS["male"])
    
    def modify_dose_response(self, dose_response: DoseResponseCurve) -> DoseResponseCurve:
        """
        Modify a dose-response curve based on gender-related factors.
        
        This method applies gender-specific adjustments to the curve's parameters,
        affecting aspects like clearance rate, metabolic processing, and
        distribution volume which impact the effective dose.
        
        Args:
            dose_response: Original dose-response curve
            
        Returns:
            Modified dose-response curve with gender-adjusted parameters
        """
        # Create a deep copy to avoid modifying the original
        modified_curve = copy.deepcopy(dose_response)
        
        # Get chemical-specific adjustments if available, otherwise use defaults
        chemical_id = dose_response.chemical_id
        adjustment_factors = (
            self.chemical_specific_adjustments.get(chemical_id, self.adjustment_factors)
        )
        
        # Apply modifications to parameters based on curve type
        curve_type = type(dose_response).__name__
        
        # Parameter modifications vary by curve type and are affected by the 
        # chemical's processing in the body
        if curve_type == "LinearDoseResponse":
            # For linear models, primarily adjust slope which represents sensitivity
            if "slope" in modified_curve.parameters:
                # Calculate effective adjustment based on multiple physiological factors
                effective_adjustment = (
                    (adjustment_factors.get("clearance_rate", 1.0) * 0.4) +
                    (adjustment_factors.get("metabolic_rate", 1.0) * 0.4) +
                    (adjustment_factors.get("distribution_volume", 1.0) * 0.2)
                )
                
                # Inverse relationship: lower clearance = higher effective dose = steeper slope
                modified_curve._parameters["slope"] *= (2 - effective_adjustment)
                
        elif curve_type == "SigmoidDoseResponse" or curve_type == "LogisticDoseResponse":
            # For sigmoid/logistic curves, mainly modify EC50
            if "ec50" in modified_curve.parameters:
                # Calculate effective adjustment
                effective_adjustment = (
                    (adjustment_factors.get("clearance_rate", 1.0) * 0.3) +
                    (adjustment_factors.get("metabolic_rate", 1.0) * 0.3) +
                    (adjustment_factors.get("absorption_rate", 1.0) * 0.2) +
                    (adjustment_factors.get("distribution_volume", 1.0) * 0.2)
                )
                
                # Direct relationship: lower clearance = higher blood levels = lower EC50 needed
                modified_curve._parameters["ec50"] *= effective_adjustment
        
        # Add metadata about the modification
        if "variations" not in modified_curve.metadata:
            modified_curve.metadata["variations"] = []
            
        modified_curve.metadata["variations"].append({
            "factor_type": "GenderFactor",
            "gender": self.gender,
            "adjustment_factors": adjustment_factors
        })
        
        return modified_curve


class BodyMassIndexFactor(VariationFactor):
    """
    Variation factor that adjusts dose-response based on Body Mass Index (BMI).
    
    This factor models how BMI affects pharmacokinetics, particularly through
    differences in distribution volume, fat solubility of chemicals, and
    clearance rates.
    
    Implementation based on BMI-related research from:
    - jpm-12-01706.pdf: Section 4.1.3 "Body Composition and Toxicokinetics"
    """
    
    # BMI category definitions and parameter adjustment factors
    BMI_CATEGORIES = {
        "underweight": (0, 18.5, {
            "distribution_volume": 0.8,  # Lower body volume
            "clearance_rate": 1.1,       # Often faster clearance (per kg)
            "lipophilic_distribution": 0.7,  # Less fat tissue for lipophilic compounds
            "hydrophilic_distribution": 1.1   # Relatively more water content
        }),
        "normal": (18.5, 25, {
            "distribution_volume": 1.0,  # Reference (baseline)
            "clearance_rate": 1.0,
            "lipophilic_distribution": 1.0,
            "hydrophilic_distribution": 1.0
        }),
        "overweight": (25, 30, {
            "distribution_volume": 1.1,  # Higher body volume
            "clearance_rate": 0.9,       # Often slower clearance
            "lipophilic_distribution": 1.2,  # More fat tissue for lipophilic compounds
            "hydrophilic_distribution": 0.9   # Relatively less water content
        }),
        "obese": (30, 100, {
            "distribution_volume": 1.3,  # Much higher body volume
            "clearance_rate": 0.8,       # Typically slower clearance
            "lipophilic_distribution": 1.5,  # Substantially more fat tissue
            "hydrophilic_distribution": 0.8   # Relatively much less water content
        })
    }
    
    # Chemical properties (simplified for common toxins)
    CHEMICAL_PROPERTIES = {
        "formaldehyde": {"lipophilicity": 0.2},  # Hydrophilic
        "benzene": {"lipophilicity": 0.7},       # Moderately lipophilic
        "toluene": {"lipophilicity": 0.8},       # Lipophilic
        "carbon_monoxide": {"lipophilicity": 0.1},  # Gas, less affected by fat
        "lead": {"lipophilicity": 0.3},          # Mostly hydrophilic
        "mercury": {"lipophilicity": 0.5},       # Both hydro and lipophilic forms
        "pcbs": {"lipophilicity": 0.9},          # Highly lipophilic
        "dioxins": {"lipophilicity": 0.95}       # Extremely lipophilic
    }
    
    def __init__(
        self,
        bmi: float,
        chemical_specific_adjustments: Optional[Dict[str, Dict[str, float]]] = None,
        **kwargs
    ) -> None:
        """
        Initialize a BMI-based variation factor.
        
        Args:
            bmi: Body Mass Index value
            chemical_specific_adjustments: Optional dictionary mapping chemical IDs to
                parameter adjustment dictionaries (overrides default adjustments)
            **kwargs: Additional arguments to pass to VariationFactor.__init__
        """
        name = kwargs.pop("name", f"BMI Factor ({bmi})")
        description = kwargs.pop("description", 
                               f"Adjusts dose-response parameters based on BMI ({bmi})")
        
        super().__init__(name=name, description=description, **kwargs)
        
        self.bmi = bmi
        self.bmi_category = self._determine_bmi_category(bmi)
        self.adjustment_factors = self._get_adjustment_factors(self.bmi_category)
        self.chemical_specific_adjustments = chemical_specific_adjustments or {}
        
    def _determine_bmi_category(self, bmi: float) -> str:
        """
        Determine the BMI category for a given BMI value.
        
        Args:
            bmi: Body Mass Index value
            
        Returns:
            BMI category name
        """
        for category, (min_bmi, max_bmi, _) in self.BMI_CATEGORIES.items():
            if min_bmi <= bmi < max_bmi:
                return category
        
        # Default to "normal" if outside all ranges
        return "normal"
    
    def _get_adjustment_factors(self, bmi_category: str) -> Dict[str, float]:
        """
        Get the adjustment factors for a given BMI category.
        
        Args:
            bmi_category: BMI category name
            
        Returns:
            Dictionary of adjustment factors
        """
        _, _, factors = self.BMI_CATEGORIES.get(bmi_category, self.BMI_CATEGORIES["normal"])
        return factors
    
    def _get_chemical_property(self, chemical_id: str, property_name: str, default: float) -> float:
        """
        Get a chemical property for a given chemical ID.
        
        Args:
            chemical_id: Chemical identifier
            property_name: Property name
            default: Default value if property is not found
            
        Returns:
            Property value
        """
        # Try to find the chemical by exact ID
        chemical_props = self.CHEMICAL_PROPERTIES.get(chemical_id.lower(), {})
        
        # If not found, try to match with a substring (e.g., "benzene" in "benzene_exposure")
        if not chemical_props:
            for chem_id, props in self.CHEMICAL_PROPERTIES.items():
                if chem_id in chemical_id.lower():
                    chemical_props = props
                    break
        
        return chemical_props.get(property_name, default)
    
    def modify_dose_response(self, dose_response: DoseResponseCurve) -> DoseResponseCurve:
        """
        Modify a dose-response curve based on BMI-related factors.
        
        This method applies BMI-specific adjustments to the curve's parameters,
        with effects varying based on the chemical's lipophilicity (fat solubility).
        BMI primarily affects distribution volume and clearance, which impact
        the effective internal dose for a given external exposure.
        
        Args:
            dose_response: Original dose-response curve
            
        Returns:
            Modified dose-response curve with BMI-adjusted parameters
        """
        # Create a deep copy to avoid modifying the original
        modified_curve = copy.deepcopy(dose_response)
        
        # Get chemical-specific adjustments if available, otherwise use defaults
        chemical_id = dose_response.chemical_id
        adjustment_factors = (
            self.chemical_specific_adjustments.get(chemical_id, self.adjustment_factors)
        )
        
        # Get the chemical's lipophilicity
        lipophilicity = self._get_chemical_property(chemical_id, "lipophilicity", 0.5)
        
        # Calculate the effect of lipophilicity
        # For lipophilic compounds (high lipophilicity), distribution in fat tissue is more important
        # For hydrophilic compounds (low lipophilicity), water distribution is more important
        lipophilic_weight = lipophilicity
        hydrophilic_weight = 1 - lipophilicity
        
        # Calculate the overall distribution factor
        distribution_factor = (
            (adjustment_factors.get("lipophilic_distribution", 1.0) * lipophilic_weight) +
            (adjustment_factors.get("hydrophilic_distribution", 1.0) * hydrophilic_weight)
        )
        
        # Apply modifications to parameters based on curve type
        curve_type = type(dose_response).__name__
        
        # Parameter modifications vary by curve type
        if curve_type == "LinearDoseResponse":
            # For linear models, modify intercept and slope
            if "slope" in modified_curve.parameters:
                # Calculate effective adjustment based on both distribution and clearance
                effective_adjustment = (
                    (distribution_factor * 0.7) +
                    (adjustment_factors.get("clearance_rate", 1.0) * 0.3)
                )
                
                # For highly lipophilic compounds in obese individuals:
                # - Higher distribution volume = lower blood concentration = lower slope
                # - Lower clearance rate = higher blood concentration = higher slope
                # These effects partially counteract, but distribution typically dominates
                modified_curve._parameters["slope"] *= (1 / effective_adjustment)
                
        elif curve_type == "SigmoidDoseResponse" or curve_type == "LogisticDoseResponse":
            # For sigmoid/logistic curves, mainly modify EC50
            if "ec50" in modified_curve.parameters:
                # Calculate effective adjustment
                effective_adjustment = (
                    (distribution_factor * 0.6) +
                    (adjustment_factors.get("clearance_rate", 1.0) * 0.4)
                )
                
                # Higher distribution volume = higher EC50 needed
                modified_curve._parameters["ec50"] *= effective_adjustment
        
        # Add metadata about the modification
        if "variations" not in modified_curve.metadata:
            modified_curve.metadata["variations"] = []
            
        modified_curve.metadata["variations"].append({
            "factor_type": "BodyMassIndexFactor",
            "bmi": self.bmi,
            "bmi_category": self.bmi_category,
            "lipophilicity": lipophilicity,
            "distribution_factor": distribution_factor,
            "adjustment_factors": adjustment_factors
        })
        
        return modified_curve
