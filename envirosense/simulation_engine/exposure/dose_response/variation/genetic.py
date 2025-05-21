"""
Genetic variation factors for dose-response curves.

This module implements variation factors based on genetic characteristics
that affect how individuals respond to chemical exposures, such as enzyme
expression levels and receptor variations.

References:
- jpm-12-01706.pdf: Section 4.2 "Genetic Determinants of Toxicokinetic Variability"
"""

from typing import Dict, List, Optional, Union, Any, Tuple
import numpy as np
import copy
import math

from envirosense.core.exposure.dose_response.base import DoseResponseCurve
from envirosense.core.exposure.dose_response.types import LiteratureReference
from envirosense.core.exposure.dose_response.variation.base import VariationFactor


class GeneticFactor(VariationFactor):
    """
    Variation factor that adjusts dose-response based on genetic polymorphisms.
    
    This factor models how specific genetic variations affect the metabolism
    and excretion of chemicals, based on research from pharmacogenomics.
    
    Implementation based on research from:
    - jpm-12-01706.pdf: Section 4.2.1 "Genetic Polymorphisms in Metabolism"
    """
    
    # Genetic variants and their effects on metabolism and excretion
    # Values derived from research literature in jpm-12-01706.pdf
    GENETIC_VARIANTS = {
        "CYP2D6_poor_metabolizer": {
            "description": "Poor metabolizer phenotype for CYP2D6 enzyme",
            "metabolism_rate": 0.3,     # Significantly reduced metabolism
            "affected_chemicals": ["antidepressants", "antipsychotics", "opioids", "beta_blockers"]
        },
        "CYP2D6_intermediate_metabolizer": {
            "description": "Intermediate metabolizer phenotype for CYP2D6 enzyme",
            "metabolism_rate": 0.7,     # Moderately reduced metabolism
            "affected_chemicals": ["antidepressants", "antipsychotics", "opioids", "beta_blockers"]
        },
        "CYP2D6_normal_metabolizer": {
            "description": "Normal (extensive) metabolizer phenotype for CYP2D6 enzyme",
            "metabolism_rate": 1.0,     # Reference baseline
            "affected_chemicals": ["antidepressants", "antipsychotics", "opioids", "beta_blockers"]
        },
        "CYP2D6_ultra_metabolizer": {
            "description": "Ultra-rapid metabolizer phenotype for CYP2D6 enzyme",
            "metabolism_rate": 1.7,     # Significantly increased metabolism
            "affected_chemicals": ["antidepressants", "antipsychotics", "opioids", "beta_blockers"]
        },
        "CYP2C19_poor_metabolizer": {
            "description": "Poor metabolizer phenotype for CYP2C19 enzyme",
            "metabolism_rate": 0.3,
            "affected_chemicals": ["proton_pump_inhibitors", "anticonvulsants", "antimalarials"]
        },
        "CYP2C9_decreased_function": {
            "description": "Decreased function variant for CYP2C9 enzyme",
            "metabolism_rate": 0.5,
            "affected_chemicals": ["nsaids", "anticoagulants", "oral_hypoglycemics"]
        },
        "GSTM1_null": {
            "description": "Null genotype for Glutathione S-transferase M1",
            "detoxification_rate": 0.6, # Reduced ability to detoxify
            "affected_chemicals": ["benzene", "polycyclic_aromatic_hydrocarbons", "aflatoxin"]
        },
        "NAT2_slow_acetylator": {
            "description": "Slow acetylator phenotype for N-acetyltransferase 2",
            "metabolism_rate": 0.4,
            "affected_chemicals": ["isoniazid", "hydralazine", "aromatic_amines"]
        }
    }
    
    # Chemical class mapping (simplified for common exposure categories)
    CHEMICAL_CLASS_MAPPING = {
        "benzene": ["benzene", "aromatic_hydrocarbons"],
        "toluene": ["aromatic_hydrocarbons"],
        "formaldehyde": ["aldehydes"],
        "pesticides": ["organophosphates"],
        "mercury": ["heavy_metals"],
        "lead": ["heavy_metals"],
        "carbon_monoxide": ["gases"],
        "polycyclic_aromatic_hydrocarbons": ["polycyclic_aromatic_hydrocarbons", "combustion_products"],
        "arsenic": ["heavy_metals", "metalloids"],
        "cadmium": ["heavy_metals"],
        "dioxins": ["persistent_organic_pollutants"],
        "pcbs": ["persistent_organic_pollutants"],
        "bpa": ["endocrine_disruptors"],
        "phthalates": ["endocrine_disruptors"]
    }
    
    def __init__(
        self,
        genetic_variants: List[str],
        chemical_specific_adjustments: Optional[Dict[str, Dict[str, float]]] = None,
        **kwargs
    ) -> None:
        """
        Initialize a genetic variation factor.
        
        Args:
            genetic_variants: List of genetic variant identifiers
            chemical_specific_adjustments: Optional dictionary mapping chemical IDs to
                parameter adjustment dictionaries (overrides default adjustments)
            **kwargs: Additional arguments to pass to VariationFactor.__init__
        """
        variant_str = ", ".join(genetic_variants[:2])
        if len(genetic_variants) > 2:
            variant_str += f" and {len(genetic_variants) - 2} more"
            
        name = kwargs.pop("name", f"Genetic Factor ({variant_str})")
        description = kwargs.pop("description", 
                               f"Adjusts dose-response parameters based on genetic variants")
        
        super().__init__(name=name, description=description, **kwargs)
        
        self.genetic_variants = genetic_variants
        self.variant_effects = self._get_variant_effects(genetic_variants)
        self.chemical_specific_adjustments = chemical_specific_adjustments or {}
    
    def _get_variant_effects(self, variants: List[str]) -> Dict[str, Any]:
        """
        Get the combined effects of multiple genetic variants.
        
        This method aggregates the effects of multiple genetic variants,
        considering potential interactions and overlapping effects.
        
        Args:
            variants: List of genetic variant identifiers
            
        Returns:
            Dictionary of combined effects
        """
        # Start with default values
        combined_effects = {
            "metabolism_rate": 1.0,
            "detoxification_rate": 1.0,
            "excretion_rate": 1.0,
            "affected_chemicals": set()
        }
        
        # Add effects from each variant
        for variant in variants:
            if variant in self.GENETIC_VARIANTS:
                variant_data = self.GENETIC_VARIANTS[variant]
                
                # Update metabolism rate (multiplicative effect for multiple variants)
                if "metabolism_rate" in variant_data:
                    combined_effects["metabolism_rate"] *= variant_data["metabolism_rate"]
                
                # Update detoxification rate
                if "detoxification_rate" in variant_data:
                    combined_effects["detoxification_rate"] *= variant_data["detoxification_rate"]
                
                # Update excretion rate
                if "excretion_rate" in variant_data:
                    combined_effects["excretion_rate"] *= variant_data["excretion_rate"]
                
                # Add affected chemicals
                if "affected_chemicals" in variant_data:
                    combined_effects["affected_chemicals"].update(variant_data["affected_chemicals"])
        
        # Convert affected_chemicals from set to list for easier JSON serialization
        combined_effects["affected_chemicals"] = list(combined_effects["affected_chemicals"])
        
        return combined_effects
    
    def _chemical_is_affected(self, chemical_id: str) -> bool:
        """
        Determine if a chemical is affected by the genetic variants.
        
        Args:
            chemical_id: Chemical identifier
            
        Returns:
            True if the chemical is affected, False otherwise
        """
        # Get the classes this chemical belongs to
        chemical_classes = self.CHEMICAL_CLASS_MAPPING.get(chemical_id.lower(), [])
        
        # Add the chemical itself as a class
        chemical_classes.append(chemical_id.lower())
        
        # Check if any of the affected chemicals match any of the chemical classes
        for affected_chemical in self.variant_effects["affected_chemicals"]:
            if affected_chemical in chemical_classes:
                return True
            
            # Also check if the chemical ID contains the affected chemical as a substring
            # (e.g., "benzene_exposure" contains "benzene")
            for chem_class in chemical_classes:
                if affected_chemical in chem_class or chem_class in affected_chemical:
                    return True
        
        return False
    
    def modify_dose_response(self, dose_response: DoseResponseCurve) -> DoseResponseCurve:
        """
        Modify a dose-response curve based on genetic factors.
        
        This method applies genetic-specific adjustments to the curve's parameters,
        primarily affecting metabolism, which impacts how quickly chemicals are
        processed and eliminated from the body.
        
        Args:
            dose_response: Original dose-response curve
            
        Returns:
            Modified dose-response curve with genetic-adjusted parameters
        """
        # Create a deep copy to avoid modifying the original
        modified_curve = copy.deepcopy(dose_response)
        
        # Get chemical-specific adjustments if available, otherwise use defaults
        chemical_id = dose_response.chemical_id
        
        # If this chemical isn't affected by these genetic variants, return unmodified
        if not self._chemical_is_affected(chemical_id) and chemical_id not in self.chemical_specific_adjustments:
            return modified_curve
        
        # Get adjustments - prefer specific ones provided, otherwise use calculated effects
        adjustment_factors = self.chemical_specific_adjustments.get(chemical_id, self.variant_effects)
        
        # Apply modifications to parameters based on curve type
        curve_type = type(dose_response).__name__
        
        # Calculate the effective adjustment factor, primarily based on metabolism
        effective_adjustment = (
            (adjustment_factors.get("metabolism_rate", 1.0) * 0.6) +
            (adjustment_factors.get("detoxification_rate", 1.0) * 0.3) +
            (adjustment_factors.get("excretion_rate", 1.0) * 0.1)
        )
        
        # Parameter modifications vary by curve type
        if curve_type == "LinearDoseResponse":
            # For linear models, adjust slope and possibly intercept
            if "slope" in modified_curve.parameters:
                # Inverse relationship: slower metabolism = higher effective dose = steeper slope
                modified_curve._parameters["slope"] *= (1 / effective_adjustment)
                
        elif curve_type == "SigmoidDoseResponse" or curve_type == "LogisticDoseResponse":
            # For sigmoid/logistic curves, mainly modify EC50
            if "ec50" in modified_curve.parameters:
                # Direct relationship: slower metabolism = higher blood levels = lower EC50 needed
                modified_curve._parameters["ec50"] *= effective_adjustment
                
            # May also affect the Hill slope in some cases
            if "hill_slope" in modified_curve.parameters:
                # Slower metabolism often means more gradual response onset
                slope_factor = math.sqrt(effective_adjustment)  # Less dramatic than the EC50 effect
                modified_curve._parameters["hill_slope"] *= slope_factor
        
        # Add metadata about the modification
        if "variations" not in modified_curve.metadata:
            modified_curve.metadata["variations"] = []
            
        modified_curve.metadata["variations"].append({
            "factor_type": "GeneticFactor",
            "genetic_variants": self.genetic_variants,
            "effective_adjustment": effective_adjustment,
            "affected_chemicals": self.variant_effects["affected_chemicals"]
        })
        
        return modified_curve


class EnzymeExpressionFactor(VariationFactor):
    """
    Variation factor that adjusts dose-response based on enzyme expression levels.
    
    This factor models how variations in enzyme expression affect the metabolism
    and excretion of chemicals, which can vary based on both genetic and 
    environmental factors.
    
    Implementation based on research from:
    - jpm-12-01706.pdf: Section 4.2.2 "Enzyme Expression and Activity"
    """
    
    # Enzyme systems and their effects on chemical processing
    # Values derived from research literature in jpm-12-01706.pdf
    ENZYME_SYSTEMS = {
        "cytochrome_p450": {
            "description": "Cytochrome P450 enzyme family (primary Phase I metabolism)",
            "affected_chemicals": ["organic_compounds", "drugs", "pesticides", "aromatic_hydrocarbons"],
            "parameter_effects": {
                "metabolism_rate": 1.0  # Baseline
            }
        },
        "glutathione_s_transferase": {
            "description": "Glutathione S-transferase (key Phase II metabolism)",
            "affected_chemicals": ["electrophilic_compounds", "epoxides", "aldehydes"],
            "parameter_effects": {
                "detoxification_rate": 1.0  # Baseline
            }
        },
        "udp_glucuronosyltransferase": {
            "description": "UDP-glucuronosyltransferase (UGT) enzyme family",
            "affected_chemicals": ["phenols", "amines", "carboxylic_acids", "alcohols"],
            "parameter_effects": {
                "conjugation_rate": 1.0  # Baseline
            }
        },
        "n_acetyltransferase": {
            "description": "N-acetyltransferase enzymes",
            "affected_chemicals": ["aromatic_amines", "hydrazines"],
            "parameter_effects": {
                "acetylation_rate": 1.0  # Baseline
            }
        },
        "sulfotransferase": {
            "description": "Sulfotransferase enzymes",
            "affected_chemicals": ["phenols", "alcohols", "amines"],
            "parameter_effects": {
                "sulfonation_rate": 1.0  # Baseline
            }
        }
    }
    
    def __init__(
        self,
        enzyme_expression_levels: Dict[str, float],
        chemical_specific_adjustments: Optional[Dict[str, Dict[str, float]]] = None,
        **kwargs
    ) -> None:
        """
        Initialize an enzyme expression variation factor.
        
        Args:
            enzyme_expression_levels: Dictionary mapping enzyme system names to expression
                level multipliers (1.0 = normal expression, 0.5 = half expression, etc.)
            chemical_specific_adjustments: Optional dictionary mapping chemical IDs to
                parameter adjustment dictionaries (overrides default adjustments)
            **kwargs: Additional arguments to pass to VariationFactor.__init__
        """
        name = kwargs.pop("name", f"Enzyme Expression Factor")
        description = kwargs.pop("description", 
                               f"Adjusts dose-response parameters based on enzyme expression levels")
        
        super().__init__(name=name, description=description, **kwargs)
        
        self.enzyme_expression_levels = enzyme_expression_levels
        self.enzyme_effects = self._get_enzyme_effects(enzyme_expression_levels)
        self.chemical_specific_adjustments = chemical_specific_adjustments or {}
    
    def _get_enzyme_effects(self, expression_levels: Dict[str, float]) -> Dict[str, Any]:
        """
        Calculate the combined effects of enzyme expression levels.
        
        Args:
            expression_levels: Dictionary mapping enzyme system names to expression levels
            
        Returns:
            Dictionary of combined effects
        """
        # Start with default values
        combined_effects = {
            "metabolism_rate": 1.0,
            "detoxification_rate": 1.0,
            "conjugation_rate": 1.0,
            "acetylation_rate": 1.0,
            "sulfonation_rate": 1.0,
            "affected_chemicals": set()
        }
        
        # Process each enzyme system
        for enzyme, level in expression_levels.items():
            if enzyme in self.ENZYME_SYSTEMS:
                enzyme_data = self.ENZYME_SYSTEMS[enzyme]
                
                # Apply expression level to each parameter effect
                for param, baseline in enzyme_data["parameter_effects"].items():
                    if param in combined_effects:
                        # Weight the effect by the relative importance of this enzyme for this parameter
                        weight = 0.7  # Default weight factor
                        
                        # Enzyme contributes 70% to parameter, current value retains 30% influence
                        combined_effects[param] = (combined_effects[param] * 0.3) + (baseline * level * weight)
                
                # Add affected chemicals
                if "affected_chemicals" in enzyme_data:
                    combined_effects["affected_chemicals"].update(enzyme_data["affected_chemicals"])
        
        # Convert affected_chemicals from set to list for easier JSON serialization
        combined_effects["affected_chemicals"] = list(combined_effects["affected_chemicals"])
        
        return combined_effects
    
    def _chemical_is_affected(self, chemical_id: str) -> bool:
        """
        Determine if a chemical is affected by enzyme expression levels.
        
        Args:
            chemical_id: Chemical identifier
            
        Returns:
            True if the chemical is affected, False otherwise
        """
        # Get the classes this chemical belongs to
        chemical_classes = GeneticFactor.CHEMICAL_CLASS_MAPPING.get(chemical_id.lower(), [])
        
        # Add the chemical itself as a class
        chemical_classes.append(chemical_id.lower())
        
        # Check if any of the affected chemicals match any of the chemical classes
        for affected_chemical in self.enzyme_effects["affected_chemicals"]:
            if affected_chemical in chemical_classes:
                return True
            
            # Also check if the chemical ID contains the affected chemical as a substring
            for chem_class in chemical_classes:
                if affected_chemical in chem_class or chem_class in affected_chemical:
                    return True
        
        return False
    
    def modify_dose_response(self, dose_response: DoseResponseCurve) -> DoseResponseCurve:
        """
        Modify a dose-response curve based on enzyme expression levels.
        
        This method applies enzyme-specific adjustments to the curve's parameters,
        affecting how quickly chemicals are metabolized and eliminated.
        
        Args:
            dose_response: Original dose-response curve
            
        Returns:
            Modified dose-response curve with enzyme-adjusted parameters
        """
        # Create a deep copy to avoid modifying the original
        modified_curve = copy.deepcopy(dose_response)
        
        # Get chemical-specific adjustments if available, otherwise use defaults
        chemical_id = dose_response.chemical_id
        
        # If this chemical isn't affected by these enzymes, return unmodified
        if not self._chemical_is_affected(chemical_id) and chemical_id not in self.chemical_specific_adjustments:
            return modified_curve
        
        # Get adjustments - prefer specific ones provided, otherwise use calculated effects
        adjustment_factors = self.chemical_specific_adjustments.get(chemical_id, self.enzyme_effects)
        
        # Apply modifications to parameters based on curve type
        curve_type = type(dose_response).__name__
        
        # Calculate effective metabolism adjustment based on all relevant enzyme activities
        effective_metabolism = (
            (adjustment_factors.get("metabolism_rate", 1.0) * 0.4) +
            (adjustment_factors.get("detoxification_rate", 1.0) * 0.2) +
            (adjustment_factors.get("conjugation_rate", 1.0) * 0.2) +
            (adjustment_factors.get("acetylation_rate", 1.0) * 0.1) +
            (adjustment_factors.get("sulfonation_rate", 1.0) * 0.1)
        )
        
        # Parameter modifications vary by curve type
        if curve_type == "LinearDoseResponse":
            # For linear models, adjust slope
            if "slope" in modified_curve.parameters:
                # Inverse relationship: slower metabolism = higher effective dose = steeper slope
                modified_curve._parameters["slope"] *= (1 / effective_metabolism)
                
        elif curve_type == "SigmoidDoseResponse" or curve_type == "LogisticDoseResponse":
            # For sigmoid/logistic curves, adjust EC50
            if "ec50" in modified_curve.parameters:
                # Direct relationship: slower metabolism = higher blood levels = lower EC50 needed
                modified_curve._parameters["ec50"] *= effective_metabolism
        
        # Add metadata about the modification
        if "variations" not in modified_curve.metadata:
            modified_curve.metadata["variations"] = []
            
        modified_curve.metadata["variations"].append({
            "factor_type": "EnzymeExpressionFactor",
            "enzyme_expression_levels": self.enzyme_expression_levels,
            "effective_metabolism": effective_metabolism
        })
        
        return modified_curve
