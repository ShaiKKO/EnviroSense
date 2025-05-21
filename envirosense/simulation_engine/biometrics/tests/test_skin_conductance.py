"""
Unit tests for the Skin Conductance Biometric Signal Model
"""

import unittest
import numpy as np
import uuid
import json
from typing import Dict, Any

from envirosense.core.biometrics.skin_conductance import SkinConductanceModel
from envirosense.core.time_series.parameters import Parameter


class TestSkinConductanceModel(unittest.TestCase):
    """Test cases for the SkinConductanceModel class."""

    def setUp(self):
        """Set up test fixtures."""
        self.model = SkinConductanceModel(
            baseline_conductance=3.0,
            variability=0.2,
            recovery_rate=0.05,
            max_conductance=20.0,
            stress_sensitivity=1.5
        )
    
    def test_initialization(self):
        """Test that the model initializes with the correct parameters."""
        self.assertEqual(self.model.baseline_conductance, 3.0)
        self.assertEqual(self.model.variability, 0.2)
        self.assertEqual(self.model.recovery_rate, 0.05)
        self.assertEqual(self.model.max_conductance, 20.0)
        self.assertEqual(self.model.stress_sensitivity, 1.5)
        self.assertEqual(self.model.tonic_level, 3.0)
        self.assertFalse(self.model.scr_in_progress)
        self.assertEqual(len(self.model.history), 0)
        self.assertTrue(self.model.is_active)
        self.assertTrue(isinstance(self.model.uuid, str))
    
    def test_generate_signal_normal(self):
        """Test generating a signal under normal conditions."""
        # Generate a signal with no exposures or environmental stress
        sc = self.model.generate_signal(0.0)
        
        # Signal should be close to baseline with some variability
        self.assertAlmostEqual(sc, self.model.baseline_conductance, delta=0.5)
        
        # History should have one entry
        self.assertEqual(len(self.model.history), 1)
        self.assertEqual(self.model.history[0][0], 0.0)
        self.assertEqual(self.model.history[0][1], sc)
    
    def test_generate_signal_sequence(self):
        """Test generating a sequence of signals."""
        # Generate signals at different time points
        times = [0.0, 1.0, 2.0, 3.0, 4.0]
        signals = [self.model.generate_signal(t) for t in times]
        
        # All signals should be within a reasonable range of baseline
        for sc in signals:
            self.assertGreaterEqual(sc, 0.5)  # Minimum value
            self.assertLessEqual(sc, self.model.max_conductance)
        
        # History should have entries for all signals
        self.assertEqual(len(self.model.history), len(times))
    
    def test_exposure_response(self):
        """Test that the model responds to chemical exposures."""
        # Generate signal with no exposure
        baseline_sc = self.model.generate_signal(0.0)
        self.model.reset()
        
        # Generate signal with carbon monoxide exposure
        exposures = {"carbon_monoxide": 10.0}
        exposure_sc = self.model.generate_signal(0.0, exposures=exposures)
        
        # Exposure should increase skin conductance
        self.assertGreater(exposure_sc, baseline_sc)
    
    def test_environmental_response(self):
        """Test that the model responds to environmental conditions."""
        # Generate signal with normal conditions
        self.model.reset()
        baseline_sc = self.model.generate_signal(0.0)
        self.model.reset()
        
        # Generate signal with high temperature and humidity
        env_conditions = {"temperature": 35.0, "humidity": 85.0}
        env_sc = self.model.generate_signal(0.0, environmental_conditions=env_conditions)
        
        # High temperature and humidity should increase skin conductance
        self.assertGreater(env_sc, baseline_sc)
    
    def test_stress_response(self):
        """Test that the model responds to stress levels."""
        # Generate signal with no stress
        self.model.reset()
        baseline_sc = self.model.generate_signal(0.0)
        self.model.reset()
        
        # Generate signal with high stress
        stress_sc = self.model.generate_signal(0.0, stress_level=0.8)
        
        # Stress should increase skin conductance
        self.assertGreater(stress_sc, baseline_sc)
    
    def test_scr_generation(self):
        """Test that the model can generate specific SCR responses."""
        # Generate signal with no SCR
        self.model.reset()
        baseline_sc = self.model.generate_signal(0.0)
        self.model.reset()
        
        # Generate an SCR
        scr_sc = self.model.generate_scr_response(0.0, intensity=1.0)
        
        # SCR should increase skin conductance
        self.assertGreater(scr_sc, baseline_sc)
        self.assertTrue(self.model.scr_in_progress)
    
    def test_tonic_level_recovery(self):
        """Test that tonic level recovers toward baseline over time."""
        # Increase tonic level with stress
        self.model.reset()
        self.model.generate_signal(0.0, stress_level=0.9)  # Initial high stress
        initial_tonic = self.model.tonic_level
        
        # Generate more signals with no stress - should see recovery
        for t in range(1, 20):
            self.model.generate_signal(float(t))
        
        # Tonic level should be closer to baseline after time has passed
        final_tonic = self.model.tonic_level
        self.assertLess(abs(final_tonic - self.model.baseline_conductance), 
                        abs(initial_tonic - self.model.baseline_conductance))
    
    def test_scr_frequency_calculation(self):
        """Test calculation of SCR frequency from history."""
        # Generate multiple SCRs
        self.model.reset()
        
        # Create 5 SCRs over 60 seconds
        for t in [10, 20, 30, 40, 50]:
            self.model.generate_scr_response(float(t))
            
            # Generate some regular points in between
            if t < 50:
                for i in range(1, 10):
                    self.model.generate_signal(float(t) + i * 0.1)
        
        # Calculate SCR frequency
        freq = self.model.calculate_scr_frequency(window_size=60)
        
        # Should detect approximately 5 SCRs per minute
        self.assertAlmostEqual(freq, 5.0, delta=1.0)
    
    def test_physiological_limits(self):
        """Test that the model maintains physiological limits."""
        # Try to generate extremely high skin conductance
        self.model.reset()
        
        # Combine multiple factors to try to push conductance very high
        sc = self.model.generate_signal(
            0.0, 
            exposures={"carbon_monoxide": 50.0},
            environmental_conditions={"temperature": 45.0, "humidity": 95.0},
            stress_level=1.0
        )
        
        # Value should be capped at max_conductance
        self.assertLessEqual(sc, self.model.max_conductance)
        
        # Try to generate extremely low skin conductance
        self.model.tonic_level = 0.1  # Artificially set very low
        
        # Add huge negative variability (this is a hack to test the lower bound)
        self.model.variability = 10.0
        original_random = np.random.normal
        try:
            # Mock random.gauss to always return a large negative number
            import random
            random.gauss = lambda mu, sigma: -10.0
            
            sc = self.model.generate_signal(1.0)
            
            # Value should be capped at minimum physiological value
            self.assertGreaterEqual(sc, 0.5)
        finally:
            # Restore the original random function
            random.gauss = original_random
    
    def test_serialization(self):
        """Test serialization and deserialization."""
        # Generate some history
        self.model.reset()
        for t in range(10):
            self.model.generate_signal(float(t))
        
        # Convert to dictionary
        data = self.model.to_dict()
        
        # Check that all expected fields are present
        expected_fields = [
            "name", "description", "baseline_conductance", "variability",
            "recovery_rate", "max_conductance", "stress_sensitivity",
            "uuid", "is_active", "response_factors"
        ]
        for field in expected_fields:
            self.assertIn(field, data)
        
        # Convert to JSON and back
        json_str = json.dumps(data)
        loaded_data = json.loads(json_str)
        
        # Create a new model from the data
        new_model = SkinConductanceModel.from_dict(loaded_data)
        
        # Check that properties were preserved
        self.assertEqual(new_model.baseline_conductance, self.model.baseline_conductance)
        self.assertEqual(new_model.variability, self.model.variability)
        self.assertEqual(new_model.recovery_rate, self.model.recovery_rate)
        self.assertEqual(new_model.max_conductance, self.model.max_conductance)
        self.assertEqual(new_model.stress_sensitivity, self.model.stress_sensitivity)
        self.assertEqual(new_model.uuid, self.model.uuid)


if __name__ == '__main__':
    unittest.main()
