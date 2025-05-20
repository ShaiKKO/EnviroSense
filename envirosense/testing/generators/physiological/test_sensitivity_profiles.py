"""
Tests for the sensitivity profile generation system.

This module contains tests to verify the functionality of the sensitivity profile generation
system, ensuring that it creates valid profiles with appropriate demographic distributions 
and sensitivity characteristics.
"""

import os
import json
import unittest
import numpy as np
import datetime
from pathlib import Path

from envirosense.testing.generators.physiological.sensitivity_profiles import (
    SensitivityProfile,
    SensitivityProfileGenerator,
    SENSITIVITY_TYPES,
    AGE_DISTRIBUTIONS
)
from envirosense.testing.framework import TestScenario


class TestSensitivityProfile(unittest.TestCase):
    """Tests for the SensitivityProfile class."""
    
    def setUp(self):
        """Set up a profile for testing."""
        self.profile = SensitivityProfile()
        self.profile_id = self.profile.profile_id
        
        # Add some test data
        self.profile.demographics = {
            "age": 35,
            "age_group": "young_adult",
            "sex": "female",
            "height": 165.5,
            "weight": 60.2,
            "bmi": 22.0,
            "ethnicity": "asian",
            "geographic_region": "northeast"
        }
        
        self.profile.conditions = ["asthma", "allergic_rhinitis"]
        
        self.profile.sensitivity_scores = {
            "respiratory": 1.8,
            "dermal": 1.2,
            "ocular": 1.5
        }
        
        self.profile.subtype_modifiers = {
            "respiratory": {
                "upper_respiratory": 1.1,
                "lower_respiratory": 1.2
            }
        }
        
        self.profile.parameter_modifiers = {
            "pm2_5": 1.5,
            "ozone": 1.3,
            "formaldehyde": 1.2
        }
        
        self.profile.response_curves = {
            "respiratory": {
                "threshold": 0.2,
                "slope": 2.0,
                "max_response": 1.0
            }
        }
        
        self.profile.symptom_thresholds = {
            "coughing": 0.3,
            "wheezing": 0.5,
            "shortness_of_breath": 0.7
        }
    
    def test_profile_creation(self):
        """Test that a profile can be created with a unique ID."""
        self.assertIsNotNone(self.profile_id)
        self.assertTrue(isinstance(self.profile_id, str))
        
        # Create a second profile and ensure IDs are different
        profile2 = SensitivityProfile()
        self.assertNotEqual(self.profile_id, profile2.profile_id)
    
    def test_to_dict(self):
        """Test conversion of profile to dictionary."""
        profile_dict = self.profile.to_dict()
        
        # Check all expected fields are present
        self.assertEqual(profile_dict["profile_id"], self.profile_id)
        self.assertEqual(profile_dict["demographics"]["age"], 35)
        self.assertEqual(profile_dict["demographics"]["sex"], "female")
        self.assertEqual(profile_dict["conditions"], ["asthma", "allergic_rhinitis"])
        self.assertEqual(profile_dict["sensitivity_scores"]["respiratory"], 1.8)
        self.assertEqual(profile_dict["subtype_modifiers"]["respiratory"]["upper_respiratory"], 1.1)
        self.assertEqual(profile_dict["parameter_modifiers"]["pm2_5"], 1.5)
        self.assertEqual(profile_dict["response_curves"]["respiratory"]["threshold"], 0.2)
        self.assertEqual(profile_dict["symptom_thresholds"]["coughing"], 0.3)
    
    def test_from_dict(self):
        """Test loading profile data from a dictionary."""
        # Create a new profile
        new_profile = SensitivityProfile()
        
        # Get dictionary from original profile
        profile_dict = self.profile.to_dict()
        
        # Load into new profile
        new_profile.from_dict(profile_dict)
        
        # Verify data was loaded correctly
        self.assertEqual(new_profile.profile_id, self.profile_id)
        self.assertEqual(new_profile.demographics, self.profile.demographics)
        self.assertEqual(new_profile.conditions, self.profile.conditions)
        self.assertEqual(new_profile.sensitivity_scores, self.profile.sensitivity_scores)
        self.assertEqual(new_profile.subtype_modifiers, self.profile.subtype_modifiers)
        self.assertEqual(new_profile.parameter_modifiers, self.profile.parameter_modifiers)
        self.assertEqual(new_profile.response_curves, self.profile.response_curves)
        self.assertEqual(new_profile.symptom_thresholds, self.profile.symptom_thresholds)
    
    def test_serialization(self):
        """Test JSON serialization and deserialization of profiles."""
        # Convert to JSON
        profile_json = json.dumps(self.profile.to_dict())
        
        # Create a new profile from JSON
        new_profile = SensitivityProfile()
        new_profile.from_dict(json.loads(profile_json))
        
        # Verify data matches
        self.assertEqual(new_profile.profile_id, self.profile_id)
        self.assertEqual(new_profile.demographics["age"], 35)
        self.assertEqual(new_profile.sensitivity_scores["respiratory"], 1.8)
    
    def test_file_storage(self):
        """Test saving and loading profiles to/from files."""
        # Create a temporary file path
        temp_dir = Path("temp_test_profiles")
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / f"{self.profile_id}.json"
        
        try:
            # Save profile to file
            with open(temp_file, 'w') as f:
                json.dump(self.profile.to_dict(), f, indent=2)
            
            # Load profile from file
            new_profile = SensitivityProfile()
            with open(temp_file, 'r') as f:
                new_profile.from_dict(json.load(f))
            
            # Verify data matches
            self.assertEqual(new_profile.profile_id, self.profile_id)
            self.assertEqual(new_profile.demographics["age"], 35)
            self.assertEqual(new_profile.sensitivity_scores["respiratory"], 1.8)
            
        finally:
            # Clean up
            if temp_file.exists():
                temp_file.unlink()
            if temp_dir.exists():
                temp_dir.rmdir()


class TestSensitivityProfileGenerator(unittest.TestCase):
    """Tests for the SensitivityProfileGenerator class."""
    
    def setUp(self):
        """Set up a generator and test scenario for testing."""
        self.generator = SensitivityProfileGenerator()
        self.scenario = TestScenario(
            name="Test Sensitivity Profile Generation",
            description="A test scenario for generating sensitivity profiles"
        )
        # Set parameters directly
        self.scenario.parameters = {
            "profile_count": 10,
            "random_seed": 42  # Use fixed seed for reproducibility
        }
    
    def test_generator_initialization(self):
        """Test that the generator initializes with default parameters."""
        self.assertIsInstance(self.generator, SensitivityProfileGenerator)
        self.assertIn('profile_count', self.generator.parameters)
        self.assertIn('age_distribution', self.generator.parameters)
        self.assertIn('condition_prevalence', self.generator.parameters)
    
    def test_profile_generation(self):
        """Test generation of profiles."""
        # Generate profiles
        result = self.generator.generate(self.scenario)
        
        # Check structure of result
        self.assertIn('profiles', result)
        self.assertIn('metadata', result)
        self.assertEqual(len(result['profiles']), 10)  # Should match profile_count
        
        # Check profile content
        profile = result['profiles'][0]
        self.assertIn('profile_id', profile)
        self.assertIn('demographics', profile)
        self.assertIn('sensitivity_scores', profile)
        
        # Verify demographics
        demographics = profile['demographics']
        self.assertIn('age', demographics)
        self.assertIn('sex', demographics)
        self.assertIn('height', demographics)
        self.assertIn('weight', demographics)
        
        # Verify sensitivity scores are in reasonable range
        for score in profile['sensitivity_scores'].values():
            self.assertGreaterEqual(score, 0.2)
            self.assertLessEqual(score, 2.0)
    
    def test_reproducibility(self):
        """Test that the generator produces the same results with the same seed."""
        # Generate first set
        result1 = self.generator.generate(self.scenario)
        
        # Generate second set with the same seed
        result2 = self.generator.generate(self.scenario)
        
        # Extract profile IDs (should be different) but demographics should match
        profile1 = result1['profiles'][0]
        profile2 = result2['profiles'][0]
        
        self.assertNotEqual(profile1['profile_id'], profile2['profile_id'])
        self.assertEqual(profile1['demographics']['age'], profile2['demographics']['age'])
        self.assertEqual(profile1['demographics']['sex'], profile2['demographics']['sex'])
        self.assertEqual(profile1['demographics']['height'], profile2['demographics']['height'])
    
    def test_age_distribution(self):
        """Test that age distribution follows expected patterns."""
        # Set a high profile count to test distribution
        self.scenario.parameters['profile_count'] = 1000
        
        # Generate profiles
        result = self.generator.generate(self.scenario)
        
        # Count profiles in each age group
        age_counts = {}
        for profile in result['profiles']:
            age = profile['demographics']['age']
            
            # Determine age group
            age_group = None
            for group, (min_age, max_age, _) in AGE_DISTRIBUTIONS['global'].items():
                if min_age <= age <= max_age:
                    age_group = group
                    break
            
            if age_group not in age_counts:
                age_counts[age_group] = 0
            age_counts[age_group] += 1
        
        # Verify all age groups are represented
        for group in AGE_DISTRIBUTIONS['global']:
            self.assertIn(group, age_counts)
            
        # Check approximate distributions (with some tolerance)
        expected_counts = {
            group: int(percentage * 1000) 
            for group, (_, _, percentage) in AGE_DISTRIBUTIONS['global'].items()
        }
        
        # Allow 25% tolerance due to randomness
        for group, expected in expected_counts.items():
            actual = age_counts[group]
            self.assertGreaterEqual(actual, expected * 0.75, f"Age group {group} has too few profiles")
            self.assertLessEqual(actual, expected * 1.25, f"Age group {group} has too many profiles")
    
    def test_condition_prevalence(self):
        """Test that condition prevalence follows expected rates."""
        # Set a high profile count to test distribution
        self.scenario.parameters['profile_count'] = 1000
        
        # Generate profiles
        result = self.generator.generate(self.scenario)
        
        # Count profiles with each condition
        condition_counts = {}
        for profile in result['profiles']:
            for condition in profile['conditions']:
                if condition not in condition_counts:
                    condition_counts[condition] = 0
                condition_counts[condition] += 1
        
        # Check approximate prevalence rates (with tolerance)
        for condition, expected_rate in self.generator.parameters['condition_prevalence'].items():
            if condition in condition_counts:
                actual_rate = condition_counts[condition] / 1000
                # Allow 30% tolerance due to randomness
                self.assertGreaterEqual(actual_rate, expected_rate * 0.7, 
                                       f"Condition {condition} has too low prevalence")
                self.assertLessEqual(actual_rate, expected_rate * 1.3, 
                                    f"Condition {condition} has too high prevalence")


if __name__ == '__main__':
    unittest.main()
