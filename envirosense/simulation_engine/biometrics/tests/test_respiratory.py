"""
Unit tests for the Respiratory Biometric Signal Model
"""

import unittest
import numpy as np
import json
from typing import Dict, Any

from envirosense.core.biometrics.respiratory import RespiratoryModel
from envirosense.core.time_series.parameters import Parameter


class TestRespiratoryModel(unittest.TestCase):
    """Test cases for the RespiratoryModel class."""

    def setUp(self):
        """Set up test fixtures."""
        self.model = RespiratoryModel(
            baseline_rate=14.0,
            baseline_volume=0.5,
            rate_variability=0.5,
            volume_variability=0.02,
            recovery_rate=0.1,
            max_rate=35.0,
            min_rate=8.0,
            max_volume=1.2,
            min_volume=0.2,
            chemical_sensitivity=1.2
        )
    
    def test_initialization(self):
        """Test that the model initializes with the correct parameters."""
        self.assertEqual(self.model.baseline_rate, 14.0)
        self.assertEqual(self.model.baseline_volume, 0.5)
        self.assertEqual(self.model.rate_variability, 0.5)
        self.assertEqual(self.model.volume_variability, 0.02)
        self.assertEqual(self.model.recovery_rate, 0.1)
        self.assertEqual(self.model.max_rate, 35.0)
        self.assertEqual(self.model.min_rate, 8.0)
        self.assertEqual(self.model.max_volume, 1.2)
        self.assertEqual(self.model.min_volume, 0.2)
        self.assertEqual(self.model.chemical_sensitivity, 1.2)
        self.assertEqual(self.model.current_rate, 14.0)
        self.assertEqual(self.model.current_volume, 0.5)
        self.assertEqual(self.model.breathing_pattern, "normal")
        self.assertEqual(self.model.distress_level, 0.0)
        self.assertFalse(self.model.breath_hold)
        self.assertEqual(len(self.model.history), 0)
        self.assertTrue(self.model.is_active)
        self.assertTrue(isinstance(self.model.uuid, str))
    
    def test_generate_signal_normal(self):
        """Test generating a signal under normal conditions."""
        # Generate a signal with no exposures or environmental stress
        resp = self.model.generate_signal(0.0)
        
        # Check that required keys are present
        expected_keys = ["rate", "volume", "minute_volume", "phase", "pattern", "distress"]
        for key in expected_keys:
            self.assertIn(key, resp)
        
        # Signal should be close to baseline with some variability
        self.assertAlmostEqual(resp["rate"], self.model.baseline_rate, delta=1.0)
        self.assertAlmostEqual(resp["volume"], self.model.baseline_volume, delta=0.1)
        
        # Minute volume should equal rate * volume
        self.assertAlmostEqual(resp["minute_volume"], resp["rate"] * resp["volume"], delta=0.001)
        
        # Pattern should be normal
        self.assertEqual(resp["pattern"], "normal")
        
        # Distress should be zero
        self.assertEqual(resp["distress"], 0.0)
        
        # History should have one entry
        self.assertEqual(len(self.model.history), 1)
        self.assertEqual(self.model.history[0][0], 0.0)
        self.assertEqual(self.model.history[0][1], resp)
    
    def test_generate_signal_sequence(self):
        """Test generating a sequence of signals."""
        # Generate signals at different time points
        times = [0.0, 1.0, 2.0, 3.0, 4.0]
        values = [self.model.generate_signal(t) for t in times]
        
        # All rates should be within a reasonable range
        for resp in values:
            self.assertGreaterEqual(resp["rate"], self.model.min_rate)
            self.assertLessEqual(resp["rate"], self.model.max_rate)
            self.assertGreaterEqual(resp["volume"], self.model.min_volume)
            self.assertLessEqual(resp["volume"], self.model.max_volume)
        
        # History should have entries for all signals
        self.assertEqual(len(self.model.history), len(times))
    
    def test_chemical_exposure_response(self):
        """Test that the model responds to chemical exposures."""
        # Generate signal with no exposure
        self.model.reset()
        baseline_resp = self.model.generate_signal(0.0)
        self.model.reset()
        
        # Generate signal with carbon monoxide exposure
        exposures = {"carbon_monoxide": 10.0}
        exposure_resp = self.model.generate_signal(0.0, exposures=exposures)
        
        # Carbon monoxide should increase breathing rate
        self.assertGreater(exposure_resp["rate"], baseline_resp["rate"])
        
        # Test formaldehyde exposure (causes rapid, shallow breathing)
        self.model.reset()
        formaldehyde_exposures = {"formaldehyde": 5.0}
        formaldehyde_resp = self.model.generate_signal(0.0, exposures=formaldehyde_exposures)
        
        # Formaldehyde should increase rate but potentially decrease volume
        self.assertGreater(formaldehyde_resp["rate"], baseline_resp["rate"])
    
    def test_environmental_response(self):
        """Test that the model responds to environmental conditions."""
        # Generate signal with normal conditions
        self.model.reset()
        baseline_resp = self.model.generate_signal(0.0)
        self.model.reset()
        
        # Generate signal with high temperature
        env_conditions = {"temperature": 35.0}
        temp_resp = self.model.generate_signal(0.0, environmental_conditions=env_conditions)
        
        # High temperature should increase breathing rate
        self.assertGreater(temp_resp["rate"], baseline_resp["rate"])
        
        # Test high altitude
        self.model.reset()
        altitude_conditions = {"altitude": 3000}
        altitude_resp = self.model.generate_signal(0.0, environmental_conditions=altitude_conditions)
        
        # High altitude should increase rate and potentially decrease volume
        self.assertGreater(altitude_resp["rate"], baseline_resp["rate"])
    
    def test_exercise_response(self):
        """Test that the model responds to exercise levels."""
        # Generate signal with no exercise
        self.model.reset()
        baseline_resp = self.model.generate_signal(0.0)
        self.model.reset()
        
        # Generate signal with moderate exercise
        exercise_resp = self.model.generate_signal(0.0, exercise_level=0.5)
        
        # Exercise should increase both rate and volume
        self.assertGreater(exercise_resp["rate"], baseline_resp["rate"])
        self.assertGreater(exercise_resp["volume"], baseline_resp["volume"])
        
        # Minute ventilation should increase significantly
        self.assertGreater(exercise_resp["minute_volume"], baseline_resp["minute_volume"] * 1.5)
    
    def test_distress_response(self):
        """Test that the model responds to respiratory distress."""
        # Generate signal with no distress
        self.model.reset()
        baseline_resp = self.model.generate_signal(0.0)
        self.model.reset()
        
        # Generate signal with mild distress
        mild_distress_resp = self.model.generate_signal(0.0, distress_level=0.2)
        
        # Mild distress should increase rate
        self.assertGreater(mild_distress_resp["rate"], baseline_resp["rate"])
        
        # Generate signal with severe distress
        self.model.reset()
        severe_distress_resp = self.model.generate_signal(0.0, distress_level=0.8)
        
        # Severe distress should increase rate more and potentially decrease volume
        self.assertGreater(severe_distress_resp["rate"], mild_distress_resp["rate"])
        self.assertEqual(severe_distress_resp["pattern"], "labored")
    
    def test_breath_hold(self):
        """Test the breath hold functionality."""
        # Start with normal breathing
        self.model.reset()
        self.model.generate_signal(0.0)
        initial_phase = self.model.breathing_phase
        
        # Start breath hold
        self.model.start_breath_hold(1.0, 10.0)
        self.assertTrue(self.model.breath_hold)
        self.assertEqual(self.model.breath_hold_start_time, 1.0)
        self.assertEqual(self.model.breath_hold_duration, 10.0)
        
        # Generate signal during breath hold
        hold_resp = self.model.generate_signal(5.0)
        
        # Phase should not change during breath hold
        self.assertEqual(self.model.breathing_phase, initial_phase)
        
        # Generate signal after breath hold ends
        after_resp = self.model.generate_signal(12.0)
        
        # Breath hold should have ended
        self.assertFalse(self.model.breath_hold)
        
        # Phase should have changed after breath hold
        self.assertNotEqual(self.model.breathing_phase, initial_phase)
    
    def test_recovery(self):
        """Test that rate and volume recover toward baseline over time."""
        # Increase rate and volume with exercise
        self.model.reset()
        self.model.generate_signal(0.0, exercise_level=0.8)
        elevated_rate = self.model.current_rate
        elevated_volume = self.model.current_volume
        
        # Generate more signals with no exercise - should see recovery
        for t in range(1, 30):
            self.model.generate_signal(float(t))
        
        # Rate and volume should be closer to baseline after time has passed
        self.assertLess(abs(self.model.current_rate - self.model.baseline_rate), 
                        abs(elevated_rate - self.model.baseline_rate))
        self.assertLess(abs(self.model.current_volume - self.model.baseline_volume), 
                        abs(elevated_volume - self.model.baseline_volume))
    
    def test_breathing_pattern_classification(self):
        """Test that breathing patterns are correctly classified."""
        # Normal pattern
        self.model.reset()
        self.model.generate_signal(0.0)
        self.assertEqual(self.model.breathing_pattern, "normal")
        
        # Rapid pattern (high rate)
        self.model.reset()
        self.model.generate_signal(0.0, exercise_level=0.9)  # Exercise to increase rate
        if self.model.current_rate > 25.0:
            self.assertEqual(self.model.breathing_pattern, "rapid")
        
        # Slow pattern (low rate)
        self.model.reset()
        self.model.current_rate = 9.0  # Directly set low rate
        self.model.generate_signal(0.0)
        self.assertEqual(self.model.breathing_pattern, "slow")
        
        # Labored pattern (high distress)
        self.model.reset()
        self.model.generate_signal(0.0, distress_level=0.8)
        self.assertEqual(self.model.breathing_pattern, "labored")
    
    def test_lung_capacity_calculation(self):
        """Test calculation of lung capacity used."""
        # Set a specific volume
        self.model.reset()
        self.model.current_volume = 0.6  # 0.6 L tidal volume
        
        # Calculate capacity (assuming 6L total capacity)
        capacity = self.model.calculate_lung_capacity_used()
        
        # Should be 0.6/6.0 = 0.1 (10%)
        self.assertAlmostEqual(capacity, 0.1, delta=0.001)
    
    def test_respiratory_efficiency_calculation(self):
        """Test calculation of respiratory efficiency."""
        # Optimal breathing (rate around 14, good volume)
        self.model.reset()
        self.model.current_rate = 14.0
        self.model.current_volume = 0.75  # 75% of max volume
        self.model.distress_level = 0.0
        efficiency1 = self.model.calculate_respiratory_efficiency()
        
        # Suboptimal breathing (rate too high)
        self.model.current_rate = 30.0
        efficiency2 = self.model.calculate_respiratory_efficiency()
        
        # Distressed breathing
        self.model.current_rate = 14.0
        self.model.distress_level = 0.5
        efficiency3 = self.model.calculate_respiratory_efficiency()
        
        # First should be most efficient, then third, then second
        self.assertGreater(efficiency1, efficiency2)
        self.assertGreater(efficiency1, efficiency3)
    
    def test_get_history_methods(self):
        """Test the methods that extract history in different formats."""
        # Generate some history
        self.model.reset()
        for t in range(5):
            self.model.generate_signal(float(t))
        
        # Get rate history
        rate_history = self.model.get_rate_history()
        self.assertEqual(len(rate_history), 5)
        for i, (t, rate) in enumerate(rate_history):
            self.assertEqual(t, float(i))
            self.assertEqual(rate, self.model.history[i][1]["rate"])
        
        # Get volume history
        volume_history = self.model.get_volume_history()
        self.assertEqual(len(volume_history), 5)
        for i, (t, volume) in enumerate(volume_history):
            self.assertEqual(t, float(i))
            self.assertEqual(volume, self.model.history[i][1]["volume"])
        
        # Get minute volume history
        mv_history = self.model.get_minute_volume_history()
        self.assertEqual(len(mv_history), 5)
        for i, (t, mv) in enumerate(mv_history):
            self.assertEqual(t, float(i))
            self.assertEqual(mv, self.model.history[i][1]["minute_volume"])
    
    def test_physiological_limits(self):
        """Test that the model maintains physiological limits."""
        # Try to generate extremely high rate and volume
        self.model.reset()
        
        # Combine multiple factors to try to push values very high
        resp = self.model.generate_signal(
            0.0, 
            exposures={"carbon_monoxide": 50.0, "smoke": 20.0},
            environmental_conditions={"temperature": 45.0, "altitude": 5000},
            exercise_level=1.0,
            distress_level=1.0
        )
        
        # Values should be capped at max
        self.assertLessEqual(resp["rate"], self.model.max_rate)
        self.assertLessEqual(resp["volume"], self.model.max_volume)
        
        # Try to generate extremely low values
        self.model.reset()
        
        # Artificially set current values very low and use huge variability to try to go below min
        self.model.current_rate = self.model.min_rate
        self.model.current_volume = self.model.min_volume
        original_rate_var = self.model.rate_variability
        original_vol_var = self.model.volume_variability
        
        # Try with very high negative variability
        self.model.rate_variability = 10.0
        self.model.volume_variability = 1.0
        
        try:
            # Mock random.gauss to always return a large negative number
            import random
            original_gauss = random.gauss
            random.gauss = lambda mu, sigma: -10.0
            
            resp = self.model.generate_signal(1.0)
            
            # Values should be capped at minimum
            self.assertGreaterEqual(resp["rate"], self.model.min_rate)
            self.assertGreaterEqual(resp["volume"], self.model.min_volume)
        finally:
            # Restore the original random function and variability
            random.gauss = original_gauss
            self.model.rate_variability = original_rate_var
            self.model.volume_variability = original_vol_var
    
    def test_serialization(self):
        """Test serialization and deserialization."""
        # Generate some history
        self.model.reset()
        for t in range(10):
            self.model.generate_signal(float(t))
        
        # Set some distinctive pattern and distress
        self.model.breathing_pattern = "rapid-shallow"
        self.model.distress_level = 0.35
        
        # Convert to dictionary
        data = self.model.to_dict()
        
        # Check that all expected fields are present
        expected_fields = [
            "name", "description", "baseline_rate", "baseline_volume", 
            "rate_variability", "volume_variability", "recovery_rate",
            "max_rate", "min_rate", "max_volume", "min_volume",
            "chemical_sensitivity", "breathing_pattern", "distress_level",
            "uuid", "is_active", "response_factors"
        ]
        for field in expected_fields:
            self.assertIn(field, data)
        
        # Convert to JSON and back
        json_str = json.dumps(data)
        loaded_data = json.loads(json_str)
        
        # Create a new model from the data
        new_model = RespiratoryModel.from_dict(loaded_data)
        
        # Check that properties were preserved
        self.assertEqual(new_model.baseline_rate, self.model.baseline_rate)
        self.assertEqual(new_model.baseline_volume, self.model.baseline_volume)
        self.assertEqual(new_model.rate_variability, self.model.rate_variability)
        self.assertEqual(new_model.volume_variability, self.model.volume_variability)
        self.assertEqual(new_model.recovery_rate, self.model.recovery_rate)
        self.assertEqual(new_model.max_rate, self.model.max_rate)
        self.assertEqual(new_model.min_rate, self.model.min_rate)
        self.assertEqual(new_model.max_volume, self.model.max_volume)
        self.assertEqual(new_model.min_volume, self.model.min_volume)
        self.assertEqual(new_model.chemical_sensitivity, self.model.chemical_sensitivity)
        self.assertEqual(new_model.breathing_pattern, self.model.breathing_pattern)
        self.assertEqual(new_model.distress_level, self.model.distress_level)
        self.assertEqual(new_model.uuid, self.model.uuid)


if __name__ == '__main__':
    unittest.main()
