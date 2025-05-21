"""
Unit tests for the Integrated Biometric Profile
"""

import unittest
import numpy as np
import json
from typing import Dict, List, Any

from envirosense.core.biometrics.heart_rate import HeartRateModel
from envirosense.core.biometrics.skin_conductance import SkinConductanceModel
from envirosense.core.biometrics.respiratory import RespiratoryModel
from envirosense.core.biometrics.biometric_profile import BiometricProfile


class TestBiometricProfile(unittest.TestCase):
    """Test cases for the BiometricProfile class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a profile with default parameters
        self.profile = BiometricProfile(
            name="Test Profile",
            description="Profile for testing purposes"
        )
        
        # Create a profile with custom component models
        self.heart_rate = HeartRateModel(
            baseline_heart_rate=65.0,
            max_heart_rate=180.0,
            rate_variability=0.4,
            recovery_rate=0.12
        )
        
        self.skin_conductance = SkinConductanceModel(
            baseline_conductance=3.0,
            max_conductance=18.0,
            conductance_variability=0.1,
            recovery_rate=0.08
        )
        
        self.respiratory = RespiratoryModel(
            baseline_rate=12.0,
            baseline_volume=0.6,
            rate_variability=0.3,
            volume_variability=0.02,
            recovery_rate=0.1
        )
        
        self.custom_profile = BiometricProfile(
            name="Custom Profile",
            description="Profile with custom component models",
            heart_rate=self.heart_rate,
            skin_conductance=self.skin_conductance,
            respiratory=self.respiratory,
            sensitivity_factors={
                "stress": 1.2,
                "chemical": 0.8,
                "environmental": 1.1
            }
        )
    
    def test_initialization(self):
        """Test that the profile initializes correctly."""
        # Test default profile
        self.assertEqual(self.profile.name, "Test Profile")
        self.assertEqual(self.profile.description, "Profile for testing purposes")
        self.assertTrue(hasattr(self.profile, "uuid"))
        self.assertIsInstance(self.profile.heart_rate, HeartRateModel)
        self.assertIsInstance(self.profile.skin_conductance, SkinConductanceModel)
        self.assertIsInstance(self.profile.respiratory, RespiratoryModel)
        self.assertDictEqual(self.profile.sensitivity_factors, {
            "stress": 1.0,
            "chemical": 1.0,
            "environmental": 1.0,
            "cardio_stress": 1.0,
            "respiratory_stress": 1.0,
            "dermal_stress": 1.0,
            "exercise": 1.0
        })
        self.assertEqual(len(self.profile.history), 0)
        
        # Test custom profile
        self.assertEqual(self.custom_profile.name, "Custom Profile")
        self.assertEqual(self.custom_profile.heart_rate, self.heart_rate)
        self.assertEqual(self.custom_profile.skin_conductance, self.skin_conductance)
        self.assertEqual(self.custom_profile.respiratory, self.respiratory)
        self.assertEqual(self.custom_profile.sensitivity_factors["stress"], 1.2)
        self.assertEqual(self.custom_profile.sensitivity_factors["chemical"], 0.8)
    
    def test_generate_signals_basic(self):
        """Test generating signals with no special conditions."""
        # Generate a signal point
        signals = self.profile.generate_signals(0.0)
        
        # Should contain all three signal types
        self.assertIn("heart_rate", signals)
        self.assertIn("skin_conductance", signals)
        self.assertIn("respiratory", signals)
        
        # Heart rate should have a heart_rate field
        self.assertIn("heart_rate", signals["heart_rate"])
        
        # Respiratory should have rate and volume fields
        self.assertIn("rate", signals["respiratory"])
        self.assertIn("volume", signals["respiratory"])
        
        # History should have one entry
        self.assertEqual(len(self.profile.history), 1)
        
        # Generate another point
        signals2 = self.profile.generate_signals(1.0)
        
        # History should have two entries
        self.assertEqual(len(self.profile.history), 2)
        self.assertEqual(self.profile.history[0][0], 0.0)
        self.assertEqual(self.profile.history[1][0], 1.0)
    
    def test_exercise_response(self):
        """Test the response to exercise."""
        # Generate baseline signals
        self.profile.reset()
        baseline = self.profile.generate_signals(0.0)
        self.profile.reset()
        
        # Generate signals with exercise
        exercise = self.profile.generate_signals(0.0, exercise_level=0.7)
        
        # Exercise should increase heart rate, respiratory rate and volume
        self.assertGreater(
            exercise["heart_rate"]["heart_rate"],
            baseline["heart_rate"]["heart_rate"]
        )
        self.assertGreater(
            exercise["respiratory"]["rate"],
            baseline["respiratory"]["rate"]
        )
        self.assertGreater(
            exercise["respiratory"]["volume"],
            baseline["respiratory"]["volume"]
        )
        
        # Test with custom profile and sensitivity adjusted
        self.custom_profile.reset()
        baseline = self.custom_profile.generate_signals(0.0)
        self.custom_profile.reset()
        
        # Set exercise sensitivity high
        self.custom_profile.sensitivity_factors["exercise"] = 1.5
        exercise = self.custom_profile.generate_signals(0.0, exercise_level=0.7)
        
        # Response should be stronger with higher sensitivity
        self.assertGreater(
            exercise["heart_rate"]["heart_rate"],
            baseline["heart_rate"]["heart_rate"] * 1.3
        )
    
    def test_chemical_exposure_response(self):
        """Test the response to chemical exposure."""
        # Generate baseline signals
        self.profile.reset()
        baseline = self.profile.generate_signals(0.0)
        self.profile.reset()
        
        # Generate signals with chemical exposure
        exposure = self.profile.generate_signals(
            0.0, 
            exposures={"carbon_monoxide": 8.0}
        )
        
        # CO exposure should affect respiratory and heart rate
        self.assertNotEqual(
            exposure["respiratory"]["pattern"],
            baseline["respiratory"]["pattern"]
        )
        self.assertGreater(
            exposure["heart_rate"]["heart_rate"],
            baseline["heart_rate"]["heart_rate"]
        )
        
        # Test with custom profile and reduced sensitivity
        self.custom_profile.reset()
        baseline = self.custom_profile.generate_signals(0.0)
        self.custom_profile.reset()
        
        # Set chemical sensitivity low
        self.custom_profile.sensitivity_factors["chemical"] = 0.5
        exposure = self.custom_profile.generate_signals(
            0.0, 
            exposures={"carbon_monoxide": 8.0}
        )
        
        # Response should be weaker with lower sensitivity
        heart_rate_increase_default = (
            exposure["heart_rate"]["heart_rate"] - 
            baseline["heart_rate"]["heart_rate"]
        )
        
        # Generate with standard profile for comparison
        self.profile.reset()
        baseline_std = self.profile.generate_signals(0.0)
        self.profile.reset()
        exposure_std = self.profile.generate_signals(
            0.0, 
            exposures={"carbon_monoxide": 8.0}
        )
        
        heart_rate_increase_std = (
            exposure_std["heart_rate"]["heart_rate"] - 
            baseline_std["heart_rate"]["heart_rate"]
        )
        
        # The custom profile with lower sensitivity should have less change
        self.assertLess(heart_rate_increase_default, heart_rate_increase_std)
    
    def test_stress_response(self):
        """Test the response to stress."""
        # Generate baseline signals
        self.profile.reset()
        baseline = self.profile.generate_signals(0.0)
        self.profile.reset()
        
        # Generate signals with stress
        stress = self.profile.generate_signals(0.0, stress_level=0.8)
        
        # Stress should increase heart rate and skin conductance
        self.assertGreater(
            stress["heart_rate"]["heart_rate"],
            baseline["heart_rate"]["heart_rate"]
        )
        self.assertGreater(
            stress["skin_conductance"],
            baseline["skin_conductance"]
        )
        
        # Test with custom profile and increased sensitivity
        self.custom_profile.reset()
        baseline = self.custom_profile.generate_signals(0.0)
        self.custom_profile.reset()
        
        # Set stress sensitivity high
        self.custom_profile.sensitivity_factors["stress"] = 1.8
        stress = self.custom_profile.generate_signals(0.0, stress_level=0.8)
        
        # Response should be stronger with higher sensitivity
        heart_rate_increase_default = (
            stress["heart_rate"]["heart_rate"] - 
            baseline["heart_rate"]["heart_rate"]
        )
        
        # Generate with standard profile for comparison
        self.profile.reset()
        baseline_std = self.profile.generate_signals(0.0)
        self.profile.reset()
        stress_std = self.profile.generate_signals(0.0, stress_level=0.8)
        
        heart_rate_increase_std = (
            stress_std["heart_rate"]["heart_rate"] - 
            baseline_std["heart_rate"]["heart_rate"]
        )
        
        # The custom profile with higher sensitivity should have more change
        self.assertGreater(heart_rate_increase_default, heart_rate_increase_std)
    
    def test_coordinated_response(self):
        """Test that the biometric signals coordinate with each other."""
        # Generate a sequence with respiratory distress
        self.profile.reset()
        
        # First normal signal
        normal = self.profile.generate_signals(0.0)
        
        # Then introduce respiratory distress
        distress = self.profile.generate_signals(1.0, distress_level=0.7)
        
        # Respiratory distress should cause increased heart rate
        self.assertGreater(
            distress["heart_rate"]["heart_rate"],
            normal["heart_rate"]["heart_rate"]
        )
        
        # Should also affect skin conductance
        self.assertGreater(
            distress["skin_conductance"],
            normal["skin_conductance"]
        )
        
        # Now test the reverse - cause stress and see if it affects respiratory
        self.profile.reset()
        normal = self.profile.generate_signals(0.0)
        stress = self.profile.generate_signals(1.0, stress_level=0.8)
        
        # Stress should affect respiratory rate
        self.assertGreater(
            stress["respiratory"]["rate"],
            normal["respiratory"]["rate"]
        )
    
    def test_environmental_response(self):
        """Test response to environmental conditions."""
        # Generate baseline signals
        self.profile.reset()
        baseline = self.profile.generate_signals(0.0)
        self.profile.reset()
        
        # Generate signals with environmental stress (high temp)
        env_stress = self.profile.generate_signals(
            0.0, 
            environmental_conditions={"temperature": 38.0, "humidity": 80.0}
        )
        
        # High temperature and humidity should affect respiratory and heart rate
        self.assertGreater(
            env_stress["respiratory"]["rate"],
            baseline["respiratory"]["rate"]
        )
        self.assertGreater(
            env_stress["heart_rate"]["heart_rate"],
            baseline["heart_rate"]["heart_rate"]
        )
    
    def test_combined_stressors(self):
        """Test response to multiple stressors at once."""
        # Generate baseline signals
        self.profile.reset()
        baseline = self.profile.generate_signals(0.0)
        self.profile.reset()
        
        # Generate signals with combined stressors
        combined = self.profile.generate_signals(
            0.0, 
            exposures={"formaldehyde": 3.0},
            environmental_conditions={"temperature": 35.0},
            exercise_level=0.3,
            stress_level=0.4
        )
        
        # Should show significant changes in all metrics
        self.assertGreater(
            combined["respiratory"]["rate"],
            baseline["respiratory"]["rate"] * 1.4
        )
        self.assertGreater(
            combined["heart_rate"]["heart_rate"],
            baseline["heart_rate"]["heart_rate"] * 1.5
        )
        self.assertGreater(
            combined["skin_conductance"],
            baseline["skin_conductance"] * 1.4
        )
    
    def test_calculate_stress_index(self):
        """Test the stress index calculation."""
        # Generate baseline with no stress
        self.profile.reset()
        self.profile.generate_signals(0.0)
        baseline_stress = self.profile.calculate_stress_index()
        
        # Should be low
        self.assertLess(baseline_stress, 0.2)
        
        # Generate with moderate stress
        self.profile.reset()
        self.profile.generate_signals(0.0, stress_level=0.5)
        moderate_stress = self.profile.calculate_stress_index()
        
        # Should be higher
        self.assertGreater(moderate_stress, baseline_stress)
        
        # Generate with high stress
        self.profile.reset()
        self.profile.generate_signals(0.0, stress_level=0.9)
        high_stress = self.profile.calculate_stress_index()
        
        # Should be highest
        self.assertGreater(high_stress, moderate_stress)
    
    def test_calculate_energy_expenditure(self):
        """Test the energy expenditure calculation."""
        # Calculate MET at rest
        self.profile.reset()
        self.profile.generate_signals(0.0)
        rest_met = self.profile.calculate_energy_expenditure()
        
        # Should be close to 1.0
        self.assertAlmostEqual(rest_met, 1.0, delta=0.2)
        
        # Calculate with moderate exercise
        self.profile.reset()
        self.profile.generate_signals(0.0, exercise_level=0.4)
        moderate_met = self.profile.calculate_energy_expenditure()
        
        # Should be higher
        self.assertGreater(moderate_met, rest_met)
        
        # Calculate with vigorous exercise
        self.profile.reset()
        self.profile.generate_signals(0.0, exercise_level=0.9)
        high_met = self.profile.calculate_energy_expenditure()
        
        # Should be highest
        self.assertGreater(high_met, moderate_met)
    
    def test_detect_biometric_pattern(self):
        """Test the pattern detection functionality."""
        # Not enough data initially
        self.profile.reset()
        result = self.profile.detect_biometric_pattern()
        self.assertTrue(result.get("insufficient_data", False))
        
        # Create some exercise data
        self.profile.reset()
        for t in range(10):
            self.profile.generate_signals(float(t), exercise_level=0.7)
        
        # Should detect physical exertion
        result = self.profile.detect_biometric_pattern()
        self.assertFalse(result.get("insufficient_data", False))
        self.assertEqual(result["primary_factor"], "physical_exertion")
        self.assertTrue(result["physical_exertion"])
        
        # Create some chemical exposure data
        self.profile.reset()
        for t in range(10):
            self.profile.generate_signals(
                float(t), 
                exposures={"formaldehyde": 4.0}
            )
        
        # Should detect chemical exposure
        result = self.profile.detect_biometric_pattern()
        self.assertEqual(result["primary_factor"], "chemical_exposure")
        self.assertTrue(result["chemical_exposure"])
    
    def test_serialization(self):
        """Test serialization and deserialization."""
        # Generate some history
        self.profile.reset()
        for t in range(5):
            self.profile.generate_signals(float(t))
        
        # Convert to dictionary and JSON
        data = self.profile.to_dict()
        json_str = self.profile.to_json()
        
        # Required fields should be present
        self.assertIn("name", data)
        self.assertIn("description", data)
        self.assertIn("uuid", data)
        self.assertIn("sensitivity_factors", data)
        self.assertIn("heart_rate", data)
        self.assertIn("skin_conductance", data)
        self.assertIn("respiratory", data)
        
        # Deserialize
        profile2 = BiometricProfile.from_dict(data)
        profile3 = BiometricProfile.from_json(json_str)
        
        # Check restored properties
        self.assertEqual(profile2.name, self.profile.name)
        self.assertEqual(profile2.uuid, self.profile.uuid)
        self.assertEqual(
            profile2.sensitivity_factors["stress"], 
            self.profile.sensitivity_factors["stress"]
        )
        
        # JSON version should also match
        self.assertEqual(profile3.name, self.profile.name)
        self.assertEqual(profile3.uuid, self.profile.uuid)
    
    def test_create_demographic_variant(self):
        """Test creating demographic variants."""
        # Create an athletic young adult
        young_athletic = self.profile.create_demographic_variant(
            age=22, 
            fitness_level=0.9,
            name="Athletic Young Adult"
        )
        
        # Create an older adult
        older_adult = self.profile.create_demographic_variant(
            age=70, 
            fitness_level=0.3,
            chemical_sensitivity=1.4,
            name="Older Adult"
        )
        
        # Young athletic should have:
        # - Higher max heart rate
        # - Lower resting heart rate
        # - Higher recovery rate
        self.assertGreater(
            young_athletic.heart_rate.max_heart_rate,
            older_adult.heart_rate.max_heart_rate
        )
        self.assertLess(
            young_athletic.heart_rate.baseline_heart_rate,
            older_adult.heart_rate.baseline_heart_rate
        )
        self.assertGreater(
            young_athletic.heart_rate.recovery_rate,
            older_adult.heart_rate.recovery_rate
        )
        
        # Older adult should have:
        # - Higher chemical sensitivity
        self.assertGreater(
            older_adult.sensitivity_factors["chemical"],
            young_athletic.sensitivity_factors["chemical"]
        )
        
        # Generate exercise response and compare
        young_athletic.reset()
        older_adult.reset()
        
        young_athletic.generate_signals(0.0, exercise_level=0.7)
        older_adult.generate_signals(0.0, exercise_level=0.7)
        
        # Calculate energy expenditure - should be more efficient for athletic
        young_met = young_athletic.calculate_energy_expenditure()
        older_met = older_adult.calculate_energy_expenditure()
        
        # Same exercise should be harder (higher MET) for less fit person
        self.assertGreater(older_met, young_met)


if __name__ == "__main__":
    unittest.main()
