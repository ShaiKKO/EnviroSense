"""
Demonstration of the ProfileManager in the EnviroSense system.

This script demonstrates how to use the ProfileManager for working with 
sensitivity profiles, including creating, loading, searching, and modifying profiles.
"""

import os
import json
import datetime
from pathlib import Path

from envirosense.testing.generators.physiological.profile_manager import (
    ProfileManager,
    ValidationError
)


def create_output_dir(base_path):
    """Create output directory if it doesn't exist."""
    output_dir = Path(base_path)
    output_dir.mkdir(exist_ok=True, parents=True)
    return output_dir


def main():
    """Demonstrate ProfileManager capabilities."""
    # Setup profile storage directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    profiles_dir = os.path.join(base_dir, "../../../output/sensitivity_profiles/managed_profiles")
    create_output_dir(profiles_dir)
    
    # Initialize the ProfileManager
    manager = ProfileManager(profiles_dir)
    print(f"Initialized ProfileManager with storage at: {profiles_dir}")
    
    # Create some example profiles
    print("\n=== Creating Sample Profiles ===")
    
    # Create a healthy adult profile
    healthy_adult = manager.create_profile({
        "demographics": {
            "age": 35,
            "age_group": "young_adult",
            "sex": "female",
            "height": 170,  # cm
            "weight": 65,   # kg
            "bmi": 22.5
        },
        "conditions": [],
        "sensitivity_scores": {
            "respiratory": 1.0,  # average
            "ocular": 1.0,       # average
            "dermal": 1.0,       # average
            "immune": 1.0        # average
        }
    })
    manager.save_profile(healthy_adult)
    print(f"Created healthy adult profile: {healthy_adult.profile_id}")
    
    # Create an elderly person with COPD
    elderly_with_copd = manager.create_profile({
        "demographics": {
            "age": 72,
            "age_group": "older_adult",
            "sex": "male",
            "height": 175,  # cm
            "weight": 70,   # kg
            "bmi": 22.9
        },
        "conditions": ["chronic_obstructive_pulmonary_disease", "hypertension"],
        "sensitivity_scores": {
            "respiratory": 1.8,  # high sensitivity
            "ocular": 1.2,       # above average
            "dermal": 1.3,       # above average
            "immune": 1.4        # above average
        }
    })
    manager.save_profile(elderly_with_copd)
    print(f"Created elderly with COPD profile: {elderly_with_copd.profile_id}")
    
    # Create a child with asthma
    child_with_asthma = manager.create_profile({
        "demographics": {
            "age": 10,
            "age_group": "child",
            "sex": "male",
            "height": 140,  # cm
            "weight": 35,   # kg
            "bmi": 17.9
        },
        "conditions": ["asthma", "eczema"],
        "sensitivity_scores": {
            "respiratory": 1.7,  # high sensitivity
            "ocular": 1.1,       # slightly above average
            "dermal": 1.5,       # above average
            "immune": 1.4        # above average
        }
    })
    manager.save_profile(child_with_asthma)
    print(f"Created child with asthma profile: {child_with_asthma.profile_id}")
    
    # Create a chemically sensitive adult
    chemically_sensitive = manager.create_profile({
        "demographics": {
            "age": 42,
            "age_group": "middle_aged",
            "sex": "female",
            "height": 165,  # cm
            "weight": 60,   # kg
            "bmi": 22.0
        },
        "conditions": ["multiple_chemical_sensitivity", "migraine"],
        "sensitivity_scores": {
            "respiratory": 1.8,  # high sensitivity
            "ocular": 1.9,       # high sensitivity
            "dermal": 1.8,       # high sensitivity
            "immune": 1.7        # high sensitivity
        },
        "symptom_thresholds": {
            "headache": 0.3,     # low threshold (sensitive)
            "nausea": 0.4,
            "dizziness": 0.3,
            "throat_irritation": 0.5
        }
    })
    manager.save_profile(chemically_sensitive)
    print(f"Created chemically sensitive adult profile: {chemically_sensitive.profile_id}")
    
    # Demonstrate profile retrieval
    print("\n=== Profile Retrieval ===")
    retrieved_profile = manager.get_profile(child_with_asthma.profile_id)
    print(f"Retrieved child profile with ID: {retrieved_profile.profile_id}")
    print(f"  Age: {retrieved_profile.demographics['age']}")
    print(f"  Conditions: {', '.join(retrieved_profile.conditions)}")
    print(f"  Respiratory sensitivity: {retrieved_profile.sensitivity_scores['respiratory']}")
    
    # Demonstrate profile modification
    print("\n=== Profile Modification ===")
    # Add a new medical condition to the child profile
    retrieved_profile.conditions.append("seasonal_allergies")
    manager.save_profile(retrieved_profile)
    print(f"Added 'seasonal_allergies' to child profile")
    
    # Update sensitivity score for the elderly profile
    elderly_profile = manager.get_profile(elderly_with_copd.profile_id)
    elderly_profile.sensitivity_scores["respiratory"] = 2.0  # maximum sensitivity
    manager.save_profile(elderly_profile)
    print(f"Updated respiratory sensitivity for elderly profile to 2.0")
    
    # Demonstrate profile cloning
    print("\n=== Profile Cloning ===")
    # Clone the elderly profile and modify it
    elderly_clone = manager.clone_profile(elderly_with_copd.profile_id)
    elderly_clone.demographics["age"] = 75
    elderly_clone.conditions.append("diabetes")
    manager.save_profile(elderly_clone)
    print(f"Created clone of elderly profile with ID: {elderly_clone.profile_id}")
    print(f"  Modified age to 75 and added 'diabetes' condition")
    
    # Demonstrate profile searching
    print("\n=== Profile Searching ===")
    
    # Search for all child profiles
    child_profiles = manager.search_profiles({
        "demographics": {
            "age_group": "child"
        }
    })
    print(f"Found {len(child_profiles)} child profiles")
    
    # Search for profiles with respiratory sensitivity above 1.5
    sensitive_profiles = manager.search_profiles({
        "sensitivity_scores": {
            "respiratory": 1.5  # minimum threshold
        }
    })
    print(f"Found {len(sensitive_profiles)} profiles with high respiratory sensitivity:")
    for profile in sensitive_profiles:
        print(f"  - {profile.profile_id}: {profile.sensitivity_scores['respiratory']}")
    
    # Search for profiles with specific conditions
    asthma_profiles = manager.search_profiles({
        "conditions": "asthma"
    })
    print(f"Found {len(asthma_profiles)} profiles with asthma")
    
    # Demonstrate validation
    print("\n=== Profile Validation ===")
    
    # Validate a correct profile
    valid_result = manager.validate_profile(healthy_adult.profile_id)
    print(f"Healthy adult profile valid: {valid_result.is_valid}")
    
    # Create an invalid profile with an impossible age
    try:
        invalid_profile = manager.create_profile({
            "demographics": {
                "age": 150,  # impossible age
                "sex": "male"
            },
            "sensitivity_scores": {
                "respiratory": 1.0
            }
        })
        manager.save_profile(invalid_profile)
    except ValidationError as e:
        print(f"Validation caught invalid profile: {str(e)}")
    
    # Demonstrate documentation generation
    print("\n=== Documentation Generation ===")
    
    # Generate Markdown documentation for the chemically sensitive profile
    doc_path = os.path.join(profiles_dir, f"{chemically_sensitive.profile_id}_doc.md")
    markdown_doc = manager.generate_documentation(chemically_sensitive.profile_id, format="markdown")
    
    with open(doc_path, "w") as f:
        f.write(markdown_doc)
    
    print(f"Generated Markdown documentation: {doc_path}")
    
    # Demonstrate bulk operations
    print("\n=== Bulk Operations ===")
    
    # Export all profiles
    all_profiles = manager.search_profiles({})
    profile_ids = [p.profile_id for p in all_profiles]
    export_path = os.path.join(profiles_dir, "all_profiles_export.json")
    
    result = manager.bulk_export(profile_ids, export_path)
    print(f"Exported {result['exported']} profiles to {export_path}")
    
    # Print summary
    print("\n=== Summary ===")
    print(f"Total profiles: {manager.get_profile_count()}")
    print("Profile manager demonstration completed successfully")


if __name__ == "__main__":
    main()
