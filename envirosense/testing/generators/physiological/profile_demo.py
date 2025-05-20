"""
Demonstration of the Sensitivity Profile System

This script demonstrates how to use the sensitivity profile generation system
to create, manipulate, and analyze physiological sensitivity profiles.
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Any

from envirosense.testing.generators.physiological.sensitivity_profiles import (
    SensitivityProfile,
    SensitivityProfileGenerator,
    SENSITIVITY_TYPES,
    AGE_DISTRIBUTIONS,
    CONDITION_SENSITIVITY_MODIFIERS
)
from envirosense.testing.framework import TestScenario


def create_demo_profiles(count: int = 5, seed: int = 42) -> List[SensitivityProfile]:
    """Create a set of demonstration profiles with different characteristics."""
    # Create generator with fixed seed for reproducibility
    generator = SensitivityProfileGenerator()
    
    # Create a test scenario
    scenario = TestScenario(
        name="Demo Profile Generation",
        description="A demonstration of sensitivity profile generation"
    )
    scenario.parameters = {
        "profile_count": count,
        "random_seed": seed,
        "include_conditions": True
    }
    
    # Generate profiles
    result = generator.generate(scenario)
    
    # Convert from dictionaries to SensitivityProfile objects
    profiles = []
    for profile_dict in result["profiles"]:
        profile = SensitivityProfile()
        profile.from_dict(profile_dict)
        profiles.append(profile)
    
    return profiles


def create_specialized_profiles() -> Dict[str, SensitivityProfile]:
    """Create a set of specialized profiles for different demographics and conditions."""
    profiles = {}
    
    # Child with asthma
    child_profile = SensitivityProfile()
    child_profile.set_demographics(
        age=8,
        sex="male",
        height=130,
        weight=30
    )
    child_profile.add_condition("asthma")
    child_profile.set_sensitivity("respiratory", 1.8)
    profiles["child_with_asthma"] = child_profile
    
    # Elderly with COPD
    elderly_profile = SensitivityProfile()
    elderly_profile.set_demographics(
        age=72,
        sex="female",
        height=160,
        weight=65
    )
    elderly_profile.add_condition("copd")
    profiles["elderly_with_copd"] = elderly_profile
    
    # Adult with chemical sensitivity
    adult_profile = SensitivityProfile()
    adult_profile.set_demographics(
        age=45,
        sex="female",
        height=167,
        weight=62
    )
    adult_profile.set_sensitivity("dermal", 1.7)
    adult_profile.set_sensitivity("ocular", 1.6)
    adult_profile.set_sensitivity("respiratory", 1.5)
    profiles["chemical_sensitive_adult"] = adult_profile
    
    # Healthy adult (baseline reference)
    healthy_profile = SensitivityProfile()
    healthy_profile.set_demographics(
        age=30,
        sex="male",
        height=178,
        weight=75
    )
    profiles["healthy_adult"] = healthy_profile
    
    return profiles


def simulate_exposure_response(
    profiles: Dict[str, SensitivityProfile], 
    exposure_level: float = 0.7
) -> Dict[str, Dict[str, float]]:
    """
    Simulate response to exposure for different profiles.
    
    This simulates how individuals with different sensitivities would respond
    to the same level of environmental exposure.
    
    Args:
        profiles: Dictionary of profiles to test
        exposure_level: Normalized exposure level (0-1)
        
    Returns:
        Dictionary of response levels by profile and sensitivity type
    """
    responses = {}
    
    for name, profile in profiles.items():
        responses[name] = {}
        
        for sens_type, base_score in profile.sensitivity_scores.items():
            # Get response curve parameters if available, otherwise use defaults
            if sens_type in profile.response_curves:
                curve = profile.response_curves[sens_type]
            else:
                # Default response curve
                curve = {
                    "threshold": 0.3,
                    "slope": 1.5,
                    "max_response": 1.0
                }
            
            # Calculate response using sigmoid function
            if exposure_level < curve["threshold"]:
                # Below threshold, minimal response
                response = 0.05
            else:
                # Apply sigmoid function for response curve
                normalized_exposure = (exposure_level - curve["threshold"]) / (1 - curve["threshold"])
                response = curve["max_response"] / (1 + np.exp(-curve["slope"] * (normalized_exposure - 0.5)))
            
            # Scale by sensitivity
            response *= base_score
            
            # Cap at maximum
            response = min(1.0, response)
            
            responses[name][sens_type] = response
    
    return responses


def plot_sensitivity_distribution(profiles: List[SensitivityProfile], save_path: str = None):
    """Plot the distribution of sensitivities across profiles."""
    # Extract sensitivity scores
    sensitivity_data = {}
    for profile in profiles:
        for sens_type, score in profile.sensitivity_scores.items():
            if sens_type not in sensitivity_data:
                sensitivity_data[sens_type] = []
            sensitivity_data[sens_type].append(score)
    
    # Create box plot
    plt.figure(figsize=(10, 6))
    box_data = []
    labels = []
    
    for sens_type, scores in sensitivity_data.items():
        if len(scores) > 0:
            box_data.append(scores)
            labels.append(sens_type)
    
    plt.boxplot(box_data, labels=labels)
    plt.title("Distribution of Sensitivity Scores by Type")
    plt.ylabel("Sensitivity Score (1.0 = Average)")
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Add reference line for average sensitivity
    plt.axhline(y=1.0, color='r', linestyle='-', alpha=0.5)
    
    # Save or display
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()


def plot_response_comparison(responses: Dict[str, Dict[str, float]], save_path: str = None):
    """Plot comparison of responses between different profiles."""
    # Organize data for plotting
    profile_names = list(responses.keys())
    sensitivity_types = set()
    for profile_data in responses.values():
        sensitivity_types.update(profile_data.keys())
    sensitivity_types = sorted(sensitivity_types)
    
    # Create grouped bar chart
    fig, ax = plt.subplots(figsize=(12, 7))
    bar_width = 0.15
    index = np.arange(len(sensitivity_types))
    
    for i, profile_name in enumerate(profile_names):
        response_values = [responses[profile_name].get(sens_type, 0) for sens_type in sensitivity_types]
        offset = bar_width * (i - len(profile_names) / 2 + 0.5)
        ax.bar(index + offset, response_values, bar_width, label=profile_name)
    
    ax.set_xlabel('Sensitivity Type')
    ax.set_ylabel('Response Level (0-1)')
    ax.set_title('Response to Exposure by Profile and Sensitivity Type')
    ax.set_xticks(index)
    ax.set_xticklabels(sensitivity_types)
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.3)
    
    # Save or display
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()


def save_profiles_to_file(profiles: Dict[str, SensitivityProfile], directory: str):
    """Save profiles to JSON files."""
    save_dir = Path(directory)
    save_dir.mkdir(exist_ok=True, parents=True)
    
    for name, profile in profiles.items():
        file_path = save_dir / f"{name}.json"
        with open(file_path, 'w') as f:
            json.dump(profile.to_dict(), f, indent=2)
    
    print(f"Saved {len(profiles)} profiles to {save_dir}")


def main():
    """Run the demonstration."""
    print("Sensitivity Profile System Demonstration")
    print("=======================================")
    
    # Create output directory
    output_dir = Path("output/sensitivity_profiles")
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # 1. Generate a set of random profiles
    print("\n1. Generating random profiles...")
    random_profiles = create_demo_profiles(count=50)
    print(f"   Created {len(random_profiles)} random profiles")
    
    # Plot the distribution of sensitivities
    print("   Plotting sensitivity distributions...")
    plot_sensitivity_distribution(
        random_profiles, 
        save_path=str(output_dir / "sensitivity_distribution.png")
    )
    
    # 2. Create specialized profiles
    print("\n2. Creating specialized profiles...")
    specialized_profiles = create_specialized_profiles()
    print(f"   Created {len(specialized_profiles)} specialized profiles:")
    for name in specialized_profiles:
        print(f"   - {name}")
    
    # Save profiles to file
    print("   Saving profiles to files...")
    save_profiles_to_file(
        specialized_profiles, 
        str(output_dir / "example_profiles")
    )
    
    # 3. Simulate exposure response
    print("\n3. Simulating exposure responses...")
    responses = simulate_exposure_response(specialized_profiles)
    
    # Print responses
    print("   Response levels by profile:")
    for name, response_data in responses.items():
        print(f"   - {name}:")
        for sens_type, level in response_data.items():
            print(f"     {sens_type}: {level:.2f}")
    
    # Plot response comparison
    print("   Plotting response comparison...")
    plot_response_comparison(
        responses, 
        save_path=str(output_dir / "response_comparison.png")
    )
    
    print("\nDemonstration complete. Output saved to:", output_dir)


if __name__ == "__main__":
    main()
