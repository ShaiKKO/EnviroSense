"""
Health status variation factors for dose-response curves.

This module implements variation factors based on health conditions and organ
function status that affect how individuals respond to chemical exposures.

References:
- jpm-12-01706.pdf: Section 4.3 "Health Status and Disease States"
"""

from typing import Dict, List, Optional, Union, Any, Tuple
import numpy as np
import copy

from envirosense.core.exposure.dose_response.base import DoseResponseCurve
from envirosense.core.exposure.dose_response.types import LiteratureReference
from envirosense.core.exposure.dose_response.variation.base import VariationFactor


class HealthConditionFactor(VariationFactor):
    """
    Variation factor that adjusts dose-response based on health conditions.
    
    This factor models how specific health conditions affect the metabolism,
    distribution, and excretion of chemicals, as well as target organ sensitivity.
    
    Implementation based on research from:
    - jpm-12-01706.pdf: Section 4.3.1 "Impact of Disease States on Toxicokinetics"
    """
    
    # Health conditions and their effects on chemical processing
    # Values derived from research literature in jpm-12-01706.pdf
    HEALTH_CONDITIONS = {
        "liver_disease": {
            "description": "Liver disease affecting hepatic function",
            "metabolism_rate": 0.4,        # Significantly reduced metabolism
            "clearance_rate": 0.5,         # Reduced clearance
            "organ_sensitivity": {
                "liver": 2.0,              # Increased liver sensitivity
                "kidney": 1.3,             # Secondary effect on kidneys
                "central_nervous_system": 1.5  # Neurotoxicity concern
            },
            "affected_chemicals": ["xenobiotics", "pharmaceuticals", "organic_solvents"]
        },
        "kidney_disease": {
            "description": "Kidney disease affecting renal function",
            "excretion_rate": 0.4,         # Significantly reduced excretion
            "clearance_rate": 0.6,         # Reduced clearance
            "organ_sensitivity": {
                "kidney": 2.0,             # Increased kidney sensitivity
                "liver": 1.2               # Secondary effect on liver
            },
            "affected_chemicals": ["water_soluble_compounds", "heavy_metals", "nephrotoxins"]
        },
        "respiratory_disease": {
            "description": "Respiratory conditions like asthma, COPD",
            "absorption_rate": 1.3,        # Increased absorption for inhaled compounds
            "organ_sensitivity": {
                "respiratory_system": 2.0,  # Increased respiratory sensitivity
                "cardiovascular": 1.3       # Secondary cardiovascular effects
            },
            "affected_chemicals": ["airborne_particles", "gases", "volatile_organic_compounds"]
        },
        "cardiovascular_disease": {
            "description": "Cardiovascular conditions like hypertension, heart disease",
            "distribution_rate": 0.8,       # Altered distribution due to circulation changes
            "organ_sensitivity": {
                "cardiovascular": 1.8,      # Increased cardiovascular sensitivity
                "respiratory_system": 1.3   # Secondary respiratory effects
            },
            "affected_chemicals": ["carbon_monoxide", "particulate_matter", "cardiotoxins"]
        },
        "diabetes": {
            "description": "Diabetes mellitus (Type 1 or 2)",
            "metabolism_rate": 0.8,         # Altered metabolism
            "organ_sensitivity": {
                "kidney": 1.5,              # Increased kidney sensitivity
                "cardiovascular": 1.5,      # Increased cardiovascular sensitivity
                "nervous_system": 1.4       # Increased nervous system sensitivity
            },
            "affected_chemicals": ["nephrotoxins", "neurotoxins", "cardiotoxins"]
        },
        "immune_disorder": {
            "description": "Autoimmune or immunodeficiency disorders",
            "immune_response": 1.8,         # Increased immune reactivity (autoimmune) or decreased (immunodeficiency)
            "organ_sensitivity": {
                "immune_system": 2.0,       # Increased immune system sensitivity
                "skin": 1.5,                # Increased skin sensitivity
                "respiratory_system": 1.4   # Increased respiratory sensitivity
            },
            "affected_chemicals": ["allergens", "sensitizers", "immune_modulators"]
        }
    }
    
    # Chemical categories and typical organ impacts
    # Based on toxicological literature
    CHEMICAL_ORGAN_IMPACTS = {
        "benzene": {
            "primary_targets": ["bone_marrow", "immune_system"],
            "secondary_targets": ["liver", "central_nervous_system"]
        },
        "formaldehyde": {
            "primary_targets": ["respiratory_system", "skin", "eyes"],
            "secondary_targets": ["immune_system"]
        },
        "lead": {
            "primary_targets": ["central_nervous_system", "bone_marrow", "kidney"],
            "secondary_targets": ["cardiovascular", "reproductive_system"]
        },
        "mercury": {
            "primary_targets": ["central_nervous_system", "kidney"],
            "secondary_targets": ["immune_system", "cardiovascular"]
        },
        "carbon_monoxide": {
            "primary_targets": ["cardiovascular", "central_nervous_system"],
            "secondary_targets": ["respiratory_system"]
        },
        "pesticides": {
            "primary_targets": ["nervous_system", "liver"],
            "secondary_targets": ["kidney", "immune_system", "endocrine_system"]
        },
        "solvents": {
            "primary_targets": ["liver", "central_nervous_system", "respiratory_system"],
            "secondary_targets": ["kidney", "skin"]
        }
    }
    
    def __init__(
        self,
        health_conditions: List[str],
        chemical_specific_adjustments: Optional[Dict[str, Dict[str, float]]] = None,
        **kwargs
    ) -> None:
        """
        Initialize a health condition variation factor.
        
        Args:
            health_conditions: List of health condition identifiers
            chemical_specific_adjustments: Optional dictionary mapping chemical IDs to
                parameter adjustment dictionaries (overrides default adjustments)
            **kwargs: Additional arguments to pass to VariationFactor.__init__
        """
        conditions_str = ", ".join(health_conditions[:2])
        if len(health_conditions) > 2:
            conditions_str += f" and {len(health_conditions) - 2} more"
            
        name = kwargs.pop("name", f"Health Condition Factor ({conditions_str})")
        description = kwargs.pop("description", 
                              f"Adjusts dose-response parameters based on health conditions")
        
        super().__init__(name=name, description=description, **kwargs)
        
        self.health_conditions = health_conditions
        self.condition_effects = self._get_condition_effects(health_conditions)
        self.chemical_specific_adjustments = chemical_specific_adjustments or {}
    
    def _get_condition_effects(self, conditions: List[str]) -> Dict[str, Any]:
        """
        Get the combined effects of multiple health conditions.
        
        This method aggregates the effects of multiple health conditions,
        considering potential interactions and overlapping effects.
        
        Args:
            conditions: List of health condition identifiers
            
        Returns:
            Dictionary of combined effects
        """
        # Start with default values
        combined_effects = {
            "metabolism_rate": 1.0,
            "excretion_rate": 1.0,
            "clearance_rate": 1.0,
            "absorption_rate": 1.0,
            "distribution_rate": 1.0,
            "immune_response": 1.0,
            "organ_sensitivity": {},
            "affected_chemicals": set()
        }
        
        # Add effects from each condition
        for condition in conditions:
            if condition in self.HEALTH_CONDITIONS:
                condition_data = self.HEALTH_CONDITIONS[condition]
                
                # Update rates with multiplicative effects
                for rate_key in ["metabolism_rate", "excretion_rate", "clearance_rate", 
                               "absorption_rate", "distribution_rate", "immune_response"]:
                    if rate_key in condition_data:
                        combined_effects[rate_key] *= condition_data[rate_key]
                
                # Update organ sensitivities (take max value for each organ)
                if "organ_sensitivity" in condition_data:
                    for organ, sensitivity in condition_data["organ_sensitivity"].items():
                        current = combined_effects["organ_sensitivity"].get(organ, 1.0)
                        # Use the more severe sensitivity (higher value)
                        combined_effects["organ_sensitivity"][organ] = max(current, sensitivity)
                
                # Add affected chemicals
                if "affected_chemicals" in condition_data:
                    combined_effects["affected_chemicals"].update(condition_data["affected_chemicals"])
        
        # Convert affected_chemicals from set to list for easier JSON serialization
        combined_effects["affected_chemicals"] = list(combined_effects["affected_chemicals"])
        
        return combined_effects
    
    def _get_chemical_target_organs(self, chemical_id: str) -> Dict[str, List[str]]:
        """
        Get the target organs for a chemical.
        
        Args:
            chemical_id: Chemical identifier
            
        Returns:
            Dictionary mapping "primary_targets" and "secondary_targets" to lists of organs
        """
        # Try exact match
        if chemical_id.lower() in self.CHEMICAL_ORGAN_IMPACTS:
            return self.CHEMICAL_ORGAN_IMPACTS[chemical_id.lower()]
        
        # Try partial match
        for chem_id, impacts in self.CHEMICAL_ORGAN_IMPACTS.items():
            if chem_id in chemical_id.lower() or chemical_id.lower() in chem_id:
                return impacts
        
        # Default targets if not found
        return {
            "primary_targets": ["liver", "kidney"],  # Most common default targets
            "secondary_targets": ["central_nervous_system"]
        }
    
    def _calculate_organ_sensitivity_factor(self, chemical_id: str) -> float:
        """
        Calculate an overall sensitivity factor based on affected target organs.
        
        Args:
            chemical_id: Chemical identifier
            
        Returns:
            Overall sensitivity factor
        """
        # Get target organs for this chemical
        targets = self._get_chemical_target_organs(chemical_id)
        
        # Calculate weighted sensitivity factor
        primary_weight = 0.7
        secondary_weight = 0.3
        
        primary_sum = 0
        primary_count = len(targets["primary_targets"]) or 1  # Avoid division by zero
        
        secondary_sum = 0
        secondary_count = len(targets["secondary_targets"]) or 1  # Avoid division by zero
        
        # Calculate average sensitivity for primary targets
        for organ in targets["primary_targets"]:
            primary_sum += self.condition_effects["organ_sensitivity"].get(organ, 1.0)
        
        # Calculate average sensitivity for secondary targets
        for organ in targets["secondary_targets"]:
            secondary_sum += self.condition_effects["organ_sensitivity"].get(organ, 1.0)
        
        # Weighted average of primary and secondary sensitivities
        primary_avg = primary_sum / primary_count
        secondary_avg = secondary_sum / secondary_count
        
        return (primary_avg * primary_weight) + (secondary_avg * secondary_weight)
    
    def modify_dose_response(self, dose_response: DoseResponseCurve) -> DoseResponseCurve:
        """
        Modify a dose-response curve based on health condition factors.
        
        This method applies condition-specific adjustments to the curve's parameters,
        considering both pharmacokinetic effects (metabolism, excretion) and
        pharmacodynamic effects (target organ sensitivity).
        
        Args:
            dose_response: Original dose-response curve
            
        Returns:
            Modified dose-response curve with health-adjusted parameters
        """
        # Create a deep copy to avoid modifying the original
        modified_curve = copy.deepcopy(dose_response)
        
        # Get chemical-specific adjustments if available, otherwise use defaults
        chemical_id = dose_response.chemical_id
        adjustment_factors = self.chemical_specific_adjustments.get(chemical_id, {})
        
        # Calculate pharmacokinetic adjustment (affects internal dose)
        pk_adjustment = (
            (adjustment_factors.get("metabolism_rate", self.condition_effects["metabolism_rate"]) * 0.3) +
            (adjustment_factors.get("clearance_rate", self.condition_effects["clearance_rate"]) * 0.3) +
            (adjustment_factors.get("excretion_rate", self.condition_effects["excretion_rate"]) * 0.2) +
            (adjustment_factors.get("absorption_rate", self.condition_effects["absorption_rate"]) * 0.1) +
            (adjustment_factors.get("distribution_rate", self.condition_effects["distribution_rate"]) * 0.1)
        )
        
        # Calculate pharmacodynamic adjustment (affects response to a given dose)
        pd_adjustment = adjustment_factors.get(
            "organ_sensitivity_factor", 
            self._calculate_organ_sensitivity_factor(chemical_id)
        )
        
        # Apply modifications to parameters based on curve type
        curve_type = type(dose_response).__name__
        
        # Parameter modifications vary by curve type
        if curve_type == "LinearDoseResponse":
            # For linear models, adjust slope based on both PK and PD factors
            if "slope" in modified_curve.parameters:
                # PK effect: Inverse relationship with clearance
                # PD effect: Direct relationship with organ sensitivity
                modified_curve._parameters["slope"] *= ((1 / pk_adjustment) * pd_adjustment)
                
        elif curve_type == "SigmoidDoseResponse" or curve_type == "LogisticDoseResponse":
            # For sigmoid/logistic curves, adjust EC50 (PK) and hill slope (PD)
            if "ec50" in modified_curve.parameters:
                # Lower clearance = lower EC50 needed
                modified_curve._parameters["ec50"] *= pk_adjustment
                
            if "hill_slope" in modified_curve.parameters:
                # Higher organ sensitivity = steeper dose-response curve
                modified_curve._parameters["hill_slope"] *= pd_adjustment
        
        # Add metadata about the modification
        if "variations" not in modified_curve.metadata:
            modified_curve.metadata["variations"] = []
            
        modified_curve.metadata["variations"].append({
            "factor_type": "HealthConditionFactor",
            "health_conditions": self.health_conditions,
            "pharmacokinetic_adjustment": pk_adjustment,
            "pharmacodynamic_adjustment": pd_adjustment,
            "organ_sensitivity": dict(self.condition_effects["organ_sensitivity"])
        })
        
        return modified_curve


class OrganFunctionFactor(VariationFactor):
    """
    Variation factor that adjusts dose-response based on organ function.
    
    This factor models how varying levels of organ function affect the
    pharmacokinetics and pharmacodynamics of chemicals in the body.
    
    Implementation based on research from:
    - jpm-12-01706.pdf: Section 4.3.2 "Quantifying Organ Function in Toxicokinetic Models"
    """
    
    # Organ function scales (0.0 = no function, 1.0 = normal function)
    ORGAN_EFFECTS = {
        "liver": {
            "description": "Liver function affecting metabolism and detoxification",
            "affected_parameters": {
                "metabolism_rate": 1.0,       # Direct relationship
                "detoxification_rate": 1.0,   # Direct relationship
                "biotransformation": 1.0      # Direct relationship
            },
            "elimination_pathways": ["hepatic_metabolism", "biliary_excretion"],
            "affected_chemicals": ["xenobiotics", "pharmaceuticals", "organic_compounds"]
        },
        "kidney": {
            "description": "Kidney function affecting excretion and clearance",
            "affected_parameters": {
                "excretion_rate": 1.0,        # Direct relationship
                "clearance_rate": 1.0,        # Direct relationship
                "filtration_rate": 1.0        # Direct relationship
            },
            "elimination_pathways": ["renal_excretion", "urinary_elimination"],
            "affected_chemicals": ["water_soluble_compounds", "heavy_metals", "small_molecules"]
        },
        "respiratory_system": {
            "description": "Respiratory function affecting absorption and elimination of gases",
            "affected_parameters": {
                "absorption_rate": 1.0,       # Direct relationship for inhaled compounds
                "elimination_rate": 1.0,      # Direct relationship for volatile compounds
                "distribution_rate": 0.8      # Some impact on distribution
            },
            "elimination_pathways": ["pulmonary_excretion", "exhalation"],
            "affected_chemicals": ["gases", "volatile_compounds", "particulate_matter"]
        },
        "gastrointestinal": {
            "description": "GI function affecting absorption and first-pass metabolism",
            "affected_parameters": {
                "absorption_rate": 1.0,       # Direct relationship for ingested compounds
                "first_pass_metabolism": 1.0, # Direct relationship
                "bioavailability": 1.0        # Direct relationship
            },
            "elimination_pathways": ["fecal_excretion", "enterohepatic_circulation"],
            "affected_chemicals": ["oral_pharmaceuticals", "food_contaminants", "pesticides"]
        },
        "cardiovascular": {
            "description": "Cardiovascular function affecting distribution and perfusion",
            "affected_parameters": {
                "distribution_rate": 1.0,     # Direct relationship
                "tissue_perfusion": 1.0,      # Direct relationship
                "plasma_protein_binding": 0.7 # Some impact
            },
            "elimination_pathways": [],       # Primarily affects distribution, not elimination
            "affected_chemicals": ["all"]     # Affects all chemicals to some degree
        }
    }
    
    # Chemical clearance pathways - dominant pathways for elimination
    CHEMICAL_CLEARANCE = {
        "benzene": ["hepatic_metabolism", "pulmonary_excretion"],
        "formaldehyde": ["hepatic_metabolism", "tissue_binding"],
        "carbon_monoxide": ["pulmonary_excretion"],
        "lead": ["renal_excretion", "bone_deposition"],
        "mercury": ["renal_excretion", "biliary_excretion"],
        "toluene": ["hepatic_metabolism", "pulmonary_excretion"],
        "ethanol": ["hepatic_metabolism", "pulmonary_excretion"],
        "pesticides": ["hepatic_metabolism", "renal_excretion"],
        "pcbs": ["hepatic_metabolism", "fecal_excretion"],
        "heavy_metals": ["renal_excretion", "biliary_excretion"]
    }
    
    def __init__(
        self,
        organ_function_levels: Dict[str, float],
        chemical_specific_adjustments: Optional[Dict[str, Dict[str, float]]] = None,
        **kwargs
    ) -> None:
        """
        Initialize an organ function variation factor.
        
        Args:
            organ_function_levels: Dictionary mapping organ names to function levels
                (0.0 = no function, 1.0 = normal function, values above 1.0 not recommended)
            chemical_specific_adjustments: Optional dictionary mapping chemical IDs to
                parameter adjustment dictionaries (overrides default adjustments)
            **kwargs: Additional arguments to pass to VariationFactor.__init__
        """
        name = kwargs.pop("name", f"Organ Function Factor")
        description = kwargs.pop("description", 
                              f"Adjusts dose-response parameters based on organ function levels")
        
        super().__init__(name=name, description=description, **kwargs)
        
        self.organ_function_levels = organ_function_levels
        self.function_effects = self._get_function_effects(organ_function_levels)
        self.chemical_specific_adjustments = chemical_specific_adjustments or {}
    
    def _get_function_effects(self, function_levels: Dict[str, float]) -> Dict[str, Any]:
        """
        Calculate the combined effects of organ function levels.
        
        Args:
            function_levels: Dictionary mapping organ names to function levels
            
        Returns:
            Dictionary of combined effects
        """
        # Start with default values for all parameters
        combined_effects = {
            "metabolism_rate": 1.0,
            "detoxification_rate": 1.0,
            "biotransformation": 1.0,
            "excretion_rate": 1.0,
            "clearance_rate": 1.0,
            "filtration_rate": 1.0,
            "absorption_rate": 1.0,
            "elimination_rate": 1.0,
            "distribution_rate": 1.0,
            "first_pass_metabolism": 1.0,
            "bioavailability": 1.0,
            "tissue_perfusion": 1.0,
            "plasma_protein_binding": 1.0,
            "affected_pathways": set(),
            "organ_status": function_levels.copy()
        }
        
        # Process each organ function level
        for organ, level in function_levels.items():
            if organ in self.ORGAN_EFFECTS:
                organ_data = self.ORGAN_EFFECTS[organ]
                
                # Apply organ function level to affected parameters
                if "affected_parameters" in organ_data:
                    for param, baseline in organ_data["affected_parameters"].items():
                        if param in combined_effects:
                            # Direct relationship: parameter scales with organ function
                            # Weight is 0.8 for primary organ, preserving 0.2 for other influences
                            weight = 0.8
                            combined_effects[param] = (combined_effects[param] * (1 - weight)) + (level * weight)
                
                # Add affected elimination pathways
                if "elimination_pathways" in organ_data:
                    combined_effects["affected_pathways"].update(organ_data["elimination_pathways"])
        
        # Convert affected_pathways from set to list for easier JSON serialization
        combined_effects["affected_pathways"] = list(combined_effects["affected_pathways"])
        
        return combined_effects
    
    def _get_chemical_clearance(self, chemical_id: str) -> List[str]:
        """
        Get the clearance pathways for a chemical.
        
        Args:
            chemical_id: Chemical identifier
            
        Returns:
            List of clearance pathways
        """
        # Try exact match
        if chemical_id.lower() in self.CHEMICAL_CLEARANCE:
            return self.CHEMICAL_CLEARANCE[chemical_id.lower()]
        
        # Try partial match
        for chem_id, pathways in self.CHEMICAL_CLEARANCE.items():
            if chem_id in chemical_id.lower() or chemical_id.lower() in chem_id:
                return pathways
        
        # Default clearance pathways if not found
        return ["hepatic_metabolism", "renal_excretion"]  # Most common default pathways
    
    def _calculate_clearance_factor(self, chemical_id: str) -> float:
        """
        Calculate the overall effect on clearance for a specific chemical.
        
        Args:
            chemical_id: Chemical identifier
            
        Returns:
            Clearance adjustment factor
        """
        # Get clearance pathways for this chemical
        pathways = self._get_chemical_clearance(chemical_id)
        
        # If no relevant pathways, return neutral factor
        if not pathways:
            return 1.0
            
        # Calculate overall effect based on affected pathways
        pathway_weights = {
            # Assign relative importance to each pathway
            "hepatic_metabolism": 0.5,
            "renal_excretion": 0.4,
            "pulmonary_excretion": 0.3,
            "biliary_excretion": 0.2,
            "fecal_excretion": 0.2,
            "tissue_binding": 0.1,
            "bone_deposition": 0.1,
            "enterohepatic_circulation": 0.1,
            "urinary_elimination": 0.4,  # Same as renal excretion
            "exhalation": 0.3           # Same as pulmonary excretion
        }
        
        # Calculate weighted average effect on clearance
        total_weight = sum(pathway_weights.get(pathway, 0.1) for pathway in pathways)
        if total_weight == 0:
            return 1.0  # Avoid division by zero
            
        weighted_sum = 0
        for pathway in pathways:
            weight = pathway_weights.get(pathway, 0.1)
            
            # Determine which parameter most affects this pathway
            if pathway in ["hepatic_metabolism", "biotransformation"]:
                param = "metabolism_rate"
            elif pathway in ["renal_excretion", "urinary_elimination"]:
                param = "excretion_rate"
            elif pathway in ["pulmonary_excretion", "exhalation"]:
                param = "elimination_rate"
            elif pathway in ["biliary_excretion", "fecal_excretion", "enterohepatic_circulation"]:
                param = "clearance_rate"
            else:
                param = "clearance_rate"  # Default
                
            # Get the parameter value from effects
            param_value = self.function_effects.get(param, 1.0)
            
            # Add weighted contribution
            weighted_sum += param_value * weight
            
        return weighted_sum / total_weight
    
    def modify_dose_response(self, dose_response: DoseResponseCurve) -> DoseResponseCurve:
        """
        Modify a dose-response curve based on organ function levels.
        
        This method applies organ-specific adjustments to the curve's parameters,
        primarily affecting the pharmacokinetics of the chemical.
        
        Args:
            dose_response: Original dose-response curve
            
        Returns:
            Modified dose-response curve with organ function-adjusted parameters
        """
        # Create a deep copy to avoid modifying the original
        modified_curve = copy.deepcopy(dose_response)
        
        # Get chemical-specific adjustments if available, otherwise calculate
        chemical_id = dose_response.chemical_id
        
        # Calculate clearance adjustment factor for this chemical
        clearance_factor = self.chemical_specific_adjustments.get(
            chemical_id, 
            {"clearance_factor": self._calculate_clearance_factor(chemical_id)}
        ).get("clearance_factor", 1.0)
        
        # Apply modifications to parameters based on curve type
        curve_type = type(dose_response).__name__
        
        # Parameter modifications vary by curve type
        if curve_type == "LinearDoseResponse":
            # For linear models, adjust slope
            if "slope" in modified_curve.parameters:
                # Inverse relationship: lower clearance = higher effective dose = steeper slope
                modified_curve._parameters["slope"] *= (1 / clearance_factor)
                
        elif curve_type == "SigmoidDoseResponse" or curve_type == "LogisticDoseResponse":
            # For sigmoid/logistic curves, adjust EC50
            if "ec50" in modified_curve.parameters:
                # Direct relationship: lower clearance = higher blood levels = lower EC50 needed
                modified_curve._parameters["ec50"] *= clearance_factor
        
        # Add metadata about the modification
        if "variations" not in modified_curve.metadata:
            modified_curve.metadata["variations"] = []
            
        modified_curve.metadata["variations"].append({
            "factor_type": "OrganFunctionFactor",
            "organ_function_levels": self.organ_function_levels,
            "clearance_factor": clearance_factor,
            "chemical_pathways": self._get_chemical_clearance(chemical_id)
        })
        
        return modified_curve
