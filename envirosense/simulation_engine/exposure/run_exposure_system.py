"""
Exposure Tracking System Runner

This script provides a comprehensive demonstration of the exposure tracking system.
It creates sample exposure data, performs assessments (both standard and personalized),
and visualizes the results.

Usage:
    python -m envirosense.core.exposure.run_exposure_system

Options:
    --sensitivity-profile PATH   Path to a sensitivity profile JSON file
    --output-dir PATH            Directory for output files
    --chemicals CHEM1,CHEM2      Specific chemicals to focus on
    --duration HOURS             Duration of simulated exposure in hours
"""

import os
import sys
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

from envirosense.core.exposure.records import ExposureRecord, ExposureHistory
from envirosense.core.exposure.assessment import (
    RiskLevel,
    ExposureAssessment,
    PersonalizedExposureAssessment
)
from envirosense.core.exposure.storage import ExposureStorage

# Import the demo functionality
from envirosense.core.exposure.profile_integrated_demo import (
    generate_sample_exposure_data,
    create_sample_exposure_history,
    compare_standard_vs_personalized_assessment,
    visualize_assessment_comparison,
    load_sensitivity_profile
)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="EnviroSense Exposure Tracking System Demo")
    
    parser.add_argument(
        "--sensitivity-profile",
        help="Path to sensitivity profile JSON file",
        default=None
    )
    
    parser.add_argument(
        "--output-dir",
        help="Directory for output files",
        default=os.path.join("envirosense", "output", "exposure_demo")
    )
    
    parser.add_argument(
        "--chemicals",
        help="Comma-separated list of chemicals to include",
        default="formaldehyde,co,no2,benzene"
    )
    
    parser.add_argument(
        "--duration",
        help="Duration of simulated exposure in hours",
        type=float,
        default=8.0
    )
    
    parser.add_argument(
        "--use-defaults",
        help="Use default profiles from example_profiles directory",
        action="store_true"
    )
    
    return parser.parse_args()


def select_sensitivity_profile():
    """Allow user to select a sensitivity profile from available options."""
    profiles_dir = os.path.join("envirosense", "output", "sensitivity_profiles", "example_profiles")
    
    if not os.path.exists(profiles_dir):
        print(f"Profile directory not found: {profiles_dir}")
        return None
    
    # Find all JSON profiles
    profiles = []
    for filename in os.listdir(profiles_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(profiles_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    name = data.get("name", filename)
                    profiles.append((name, filepath))
            except:
                # Skip files that can't be parsed
                continue
    
    if not profiles:
        print("No sensitivity profiles found.")
        return None
    
    # Display options
    print("\nAvailable sensitivity profiles:")
    for i, (name, _) in enumerate(profiles):
        print(f"{i+1}. {name}")
    
    # Get user selection
    while True:
        try:
            choice = input("\nSelect a profile number (or 0 to cancel): ")
            choice = int(choice.strip())
            
            if choice == 0:
                return None
            
            if 1 <= choice <= len(profiles):
                _, filepath = profiles[choice - 1]
                return filepath
            
            print(f"Please enter a number between 1 and {len(profiles)}")
        except ValueError:
            print("Please enter a valid number")


def run_demo():
    """Run the exposure tracking system demonstration."""
    args = parse_arguments()
    
    # Allow interactive profile selection if not specified and not using defaults
    if args.sensitivity_profile is None and not args.use_defaults:
        profile_path = select_sensitivity_profile()
        if profile_path:
            args.sensitivity_profile = profile_path
    
    # Set up output directory
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    
    # Set up storage
    storage = ExposureStorage(base_dir=output_dir)
    
    # Generate sample exposure data
    print("\nGenerating exposure data...")
    chemicals = [c.strip() for c in args.chemicals.split(",")]
    
    # Create exposure history
    history = ExposureHistory()
    
    # Generate data for each chemical
    for i, chemical in enumerate(chemicals):
        # Use different patterns for each chemical to make the demo interesting
        pattern = ["increasing", "peak", "steady", "decreasing"][i % 4]
        
        # Base concentration varies by chemical
        if chemical == "co":
            base = 5.0  # CO typically measured in higher ppm 
        elif chemical == "no2":
            base = 0.03  # NO2 typically lower
        elif chemical == "formaldehyde":
            base = 0.05  # Formaldehyde also lower
        else:
            base = 0.1  # Default
            
        records = generate_sample_exposure_data(
            chemical_id=chemical,
            duration_hours=args.duration,
            base_concentration=base,
            trend=pattern
        )
        
        print(f"  Generated {len(records)} records for {chemical} ({pattern} pattern)")
        history.add_records(records)
    
    # Save history
    history_path = storage.save_history(history)
    print(f"\nSaved exposure history to: {history_path}")
    
    # Create visualization of raw exposure data
    viz_path = storage.save_history_visualization(history)
    print(f"Saved exposure visualization to: {viz_path}")
    
    # Perform standard assessment for all chemicals
    print("\nPerforming standard assessment...")
    assessment = ExposureAssessment(history)
    standard_results = assessment.assess_all_chemicals()
    
    # Display standard results
    print("\nStandard Assessment Results:")
    for chemical, result in standard_results.items():
        print(f"  {chemical}: Risk Level = {result['risk_level']}")
        if 'metrics' in result:
            print(f"    8hr TWA: {result['metrics'].get('8hr_twa', 'N/A'):.4f} ppm")
            print(f"    Peak: {result['metrics'].get('peak_concentration', 'N/A'):.4f} ppm")
    
    # Save standard results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    standard_path = os.path.join(output_dir, f"standard_assessment_{timestamp}.json")
    with open(standard_path, 'w') as f:
        json.dump(standard_results, f, indent=2)
    
    print(f"\nSaved standard assessment to: {standard_path}")
    
    # Process profiles for personalized assessment
    profiles_to_process = []
    
    if args.sensitivity_profile:
        # Use specific profile
        profiles_to_process.append(args.sensitivity_profile)
    elif args.use_defaults:
        # Use all default profiles
        profiles_dir = os.path.join("envirosense", "output", "sensitivity_profiles", "example_profiles")
        if os.path.exists(profiles_dir):
            for filename in os.listdir(profiles_dir):
                if filename.endswith(".json"):
                    profiles_to_process.append(os.path.join(profiles_dir, filename))
    
    # Process each profile
    for profile_path in profiles_to_process:
        try:
            profile = load_sensitivity_profile(profile_path)
            profile_id = profile.get("profile_id", "unknown")
            profile_name = profile.get("name", os.path.basename(profile_path))
            
            print(f"\nProcessing profile: {profile_name}")
            print(f"  Profile ID: {profile_id}")
            
            # Create personalized assessment for all chemicals
            personalized_assessment = PersonalizedExposureAssessment(history, profile)
            all_results = personalized_assessment.assess_all_chemicals()
            
            # Save assessment results
            results_file = os.path.join(output_dir, f"assessment_{profile_id}_{timestamp}.json")
            with open(results_file, 'w') as f:
                json.dump(all_results, f, indent=2)
            print(f"  Saved assessment results to: {results_file}")
            
            # Display personalized results
            print(f"\n  Personalized Assessment Results for {profile_name}:")
            for chemical, result in all_results.items():
                sensitivity = result.get("sensitivity_factor", 1.0)
                print(f"    {chemical}: Risk Level = {result['risk_level']} " +
                      f"(Sensitivity: {sensitivity:.2f}x)")
                if 'metrics' in result:
                    print(f"      Adjusted 8hr TWA: " +
                          f"{result['metrics'].get('adjusted_8hr_twa', 'N/A'):.4f} ppm")
            
            # Generate comparison for each chemical
            for chemical_id in all_results.keys():
                comparison = compare_standard_vs_personalized_assessment(
                    history, profile_path, chemical_id
                )
                
                # Visualize comparison
                fig = visualize_assessment_comparison(comparison)
                
                # Save visualization
                viz_file = os.path.join(output_dir, 
                                      f"comparison_{profile_id}_{chemical_id}_{timestamp}.png")
                fig.savefig(viz_file, dpi=300, bbox_inches='tight')
                plt.close(fig)
                
                print(f"  Saved comparison for {chemical_id} to: {viz_file}")
            
        except Exception as e:
            print(f"Error processing profile {profile_path}: {e}")
    
    print("\nDemonstration completed successfully!")
    print(f"Output files have been saved to: {output_dir}")


if __name__ == "__main__":
    run_demo()
