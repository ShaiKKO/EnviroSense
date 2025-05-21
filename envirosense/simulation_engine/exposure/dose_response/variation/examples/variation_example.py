"""
Examples of using variation factors with dose-response curves.

This module demonstrates how to use the variation factors to modify
dose-response curves for different individuals based on their characteristics.
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Optional

# Import base classes
from envirosense.core.exposure.dose_response.base import DoseResponseCurve
from envirosense.core.exposure.dose_response.variation.base import VariationFactor

# Import models
from envirosense.core.exposure.dose_response.models.linear import LinearDoseResponse
from envirosense.core.exposure.dose_response.models.logistic import LogisticDoseResponse

# Import variation factors
from envirosense.core.exposure.dose_response.variation.demographic import (
    AgeFactor, GenderFactor, BodyMassIndexFactor
)
from envirosense.core.exposure.dose_response.variation.genetic import (
    GeneticFactor, EnzymeExpressionFactor
)
from envirosense.core.exposure.dose_response.variation.health_status import (
    HealthConditionFactor, OrganFunctionFactor
)
from envirosense.core.exposure.dose_response.variation.combined import (
    VariationFactorSet, ProfileBasedVariation
)


def plot_dose_response_curves(curves: List[DoseResponseCurve], title: str, 
                            dose_range: List[float] = None, 
                            legends: List[str] = None) -> None:
    """
    Plot multiple dose-response curves for comparison.
    
    Args:
        curves: List of dose-response curves to plot
        title: Plot title
        dose_range: Optional dose range to use (if None, will be calculated)
        legends: Optional list of legend labels for each curve
    """
    plt.figure(figsize=(10, 6))
    
    # Calculate dose range if not provided
    if dose_range is None:
        min_dose = 0
        max_dose = 100
        dose_range = np.linspace(min_dose, max_dose, 100)
    
    # Set default legends if not provided
    if legends is None:
        legends = [f"Curve {i+1}" for i in range(len(curves))]
    
    # Plot each curve
    for i, curve in enumerate(curves):
        response = [curve.calculate_response(dose) for dose in dose_range]
        plt.plot(dose_range, response, linewidth=2, label=legends[i])
    
    plt.title(title)
    plt.xlabel("Dose")
    plt.ylabel("Response")
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    # Add a small note about variations if available
    for i, curve in enumerate(curves):
        if curve.metadata.get("variations"):
            var_count = len(curve.metadata["variations"])
            if var_count > 0:
                note = f"Note: Curve {i+1} has {var_count} variations applied"
                plt.figtext(0.5, 0.01, note, ha='center', fontsize=8)
    
    plt.tight_layout()
    plt.show()


def example_individual_factors():
    """
    Demonstrate how individual variation factors affect dose-response curves.
    """
    print("\n=== Example: Individual Variation Factors ===")
    
    # Create a base dose-response curve for formaldehyde (simplified for example)
    formaldehyde_curve = LinearDoseResponse(
        chemical_id="formaldehyde",
        parameters={"slope": 0.05, "intercept": 0.0},
        metadata={
            "description": "Base formaldehyde dose-response curve",
            "units": {"dose": "ppm", "response": "hazard_index"}
        }
    )
    
    print(f"Base curve parameters: {formaldehyde_curve.parameters}")
    
    # Create individual variation factors
    age_factor = AgeFactor(age=75)  # Elderly individual
    gender_factor = GenderFactor(gender="female")
    bmi_factor = BodyMassIndexFactor(bmi=32)  # Obese individual
    health_factor = HealthConditionFactor(health_conditions=["respiratory_disease"])
    
    # Apply each variation factor individually
    curves = [
        formaldehyde_curve,  # Original
        age_factor.modify_dose_response(formaldehyde_curve),
        gender_factor.modify_dose_response(formaldehyde_curve),
        bmi_factor.modify_dose_response(formaldehyde_curve),
        health_factor.modify_dose_response(formaldehyde_curve)
    ]
    
    # Print out parameter changes
    for i, curve in enumerate(curves):
        if i == 0:
            print(f"Original curve parameters: {curve.parameters}")
        else:
            print(f"After applying {type(curves[i].metadata['variations'][-1]['factor_type']).__name__}:")
            print(f"  Parameters: {curve.parameters}")
    
    # Plot the curves for comparison
    legends = [
        "Original Curve",
        "Age Factor (75 years)",
        "Gender Factor (female)",
        "BMI Factor (32)",
        "Health Factor (respiratory disease)"
    ]
    
    dose_range = np.linspace(0, 50, 100)
    plot_dose_response_curves(curves, "Individual Variation Factors - Formaldehyde", 
                            dose_range, legends)


def example_combined_factors():
    """
    Demonstrate how combined variation factors affect dose-response curves.
    """
    print("\n=== Example: Combined Variation Factors ===")
    
    # Create a base dose-response curve for benzene (simplified for example)
    benzene_curve = LogisticDoseResponse(
        chemical_id="benzene",
        parameters={"ec50": 10.0, "hill_slope": 1.2, "max_response": 1.0, "min_response": 0.0},
        metadata={
            "description": "Base benzene dose-response curve",
            "units": {"dose": "ppb", "response": "risk_factor"}
        }
    )
    
    print(f"Base curve parameters: {benzene_curve.parameters}")
    
    # Create individual variation factors
    age_factor = AgeFactor(age=5)  # Young child
    genetic_factor = GeneticFactor(genetic_variants=["GSTM1_null"])
    health_factor = HealthConditionFactor(health_conditions=["liver_disease"])
    
    # Create a variation factor set
    factor_set = VariationFactorSet(
        factors=[age_factor, genetic_factor, health_factor],
        application_order=["AgeFactor", "GeneticFactor", "HealthConditionFactor"]
    )
    
    # Apply the combined factors
    modified_curve = factor_set.modify_dose_response(benzene_curve)
    
    # Print out parameter changes
    print(f"Original curve parameters: {benzene_curve.parameters}")
    print(f"After applying combined factors:")
    print(f"  Parameters: {modified_curve.parameters}")
    
    # Apply factors individually for comparison
    age_modified = age_factor.modify_dose_response(benzene_curve)
    genetic_modified = genetic_factor.modify_dose_response(benzene_curve)
    health_modified = health_factor.modify_dose_response(benzene_curve)
    
    # Plot the curves for comparison
    curves = [
        benzene_curve,
        age_modified,
        genetic_modified, 
        health_modified,
        modified_curve
    ]
    
    legends = [
        "Original Curve",
        "Age Factor Only (5 years)",
        "Genetic Factor Only (GSTM1_null)",
        "Health Factor Only (liver_disease)",
        "All Factors Combined"
    ]
    
    dose_range = np.linspace(0, 30, 100)
    plot_dose_response_curves(curves, "Combined Variation Factors - Benzene", 
                            dose_range, legends)


def example_profile_based_variation():
    """
    Demonstrate how to use profile-based variation.
    """
    print("\n=== Example: Profile-Based Variation ===")
    
    # Create a sample sensitivity profile
    sample_profile = {
        "profile_id": "sample_individual_001",
        "demographics": {
            "age": 65,
            "sex": "male",
            "bmi": 28.5
        },
        "conditions": ["cardiovascular_disease", "diabetes"],
        "genetic_variants": ["CYP2D6_poor_metabolizer"],
        "enzyme_expression_levels": {
            "cytochrome_p450": 0.7,
            "glutathione_s_transferase": 0.6
        },
        "organ_function_levels": {
            "liver": 0.8,
            "kidney": 0.9
        },
        "sensitivity_scores": {
            "formaldehyde": 1.3,
            "benzene": 1.5,
            "carbon_monoxide": 2.0
        }
    }
    
    # Create a base dose-response curve for carbon monoxide
    co_curve = LogisticDoseResponse(
        chemical_id="carbon_monoxide",
        parameters={"ec50": 50.0, "hill_slope": 1.5, "max_response": 1.0, "min_response": 0.0},
        metadata={
            "description": "Base carbon monoxide dose-response curve",
            "units": {"dose": "ppm", "response": "severity_index"}
        }
    )
    
    # Create a profile-based variation factor
    profile_variation = ProfileBasedVariation(sample_profile)
    
    # Apply the profile-based variation
    modified_curve = profile_variation.modify_dose_response(co_curve)
    
    # Print out parameter changes
    print(f"Original curve parameters: {co_curve.parameters}")
    print(f"After applying profile-based variation:")
    print(f"  Parameters: {modified_curve.parameters}")
    
    # Print out which factors were extracted from the profile
    factor_types = [type(f).__name__ for f in profile_variation.factor_set.factors]
    print(f"Factors extracted from profile: {factor_types}")
    
    # Plot the curves for comparison
    dose_range = np.linspace(0, 100, 100)
    plot_dose_response_curves(
        [co_curve, modified_curve],
        "Profile-Based Variation - Carbon Monoxide",
        dose_range,
        ["Original Curve", "Profile-Adjusted Curve"]
    )


def main():
    """
    Run all examples.
    """
    # Display available examples
    print("Dose-Response Variation Factor Examples")
    print("---------------------------------------")
    print("1. Individual Variation Factors")
    print("2. Combined Variation Factors")
    print("3. Profile-Based Variation")
    print("4. Run All Examples")
    
    choice = input("Enter example number to run (1-4): ")
    
    if choice == "1":
        example_individual_factors()
    elif choice == "2":
        example_combined_factors()
    elif choice == "3":
        example_profile_based_variation()
    elif choice == "4":
        example_individual_factors()
        example_combined_factors()
        example_profile_based_variation()
    else:
        print("Invalid choice. Please enter a number between 1 and 4.")


if __name__ == "__main__":
    main()
