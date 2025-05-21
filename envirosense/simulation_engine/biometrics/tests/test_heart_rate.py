"""
Tests for the Heart Rate Model

This module contains unit tests for the heart rate biometric signal model.
"""

import unittest
import numpy as np

from envirosense.core.biometrics.heart_rate import HeartRateModel


class TestHeartRateModel(unittest.TestCase):
    """Test case for the HeartRateModel class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.model = HeartRateModel(
            baseline_heart_rate=70.0,
            variability=2.0,
            recovery_rate=0.1,
            max_heart_rate=180.0,
            stress_factor=1.2
        )
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.model = None
    
    def test_initialization(self):
        """Test initialization of the heart rate model."""
        self.assertEqual(self.model.baseline_heart_rate, 70.0)
        self.assertEqual(self.model.variability, 2.0)
        self.assertEqual(self.model.recovery_rate, 0.1)
        self.assertEqual(self.model.max_heart_rate, 180.0)
        self.assertEqual(self.model.stress_factor, 1.2)
        self.assertTrue(self.model.is_active)
        self.assertEqual(len(self.model.history), 0)
    
    def test_baseline_signal(self):
        """Test generation of baseline heart rate signal."""
        # Generate signal with no exposures or environmental conditions
        hr = self.model.generate_signal(0.0)
        
        # Should be close to baseline but with some variability
        self.assertTrue(60.0 <= hr <= 80.0)  # Allow for variability
        
        # Should have added to history
        self.assertEqual(len(self.model.history), 1)
        
        # Generate a few more points
        for t in range(1, 10):
            self.model.generate_signal(float(t))
        
        # Should have 10 points in history
        self.assertEqual(len(self.model.history), 10)
    
    def test_co_exposure_response(self):
        """Test heart rate response to carbon monoxide exposure."""
        # Get baseline heart rate
        baseline_hr = self.model.generate_signal(0.0)
        
        # Reset model
        self.model.reset()
        
        # Generate signal with CO exposure
        exposures = {"carbon_monoxide": 10.0}  # High CO concentration
        hr_with_co = self.model.generate_signal(0.0, exposures=exposures)
        
        # Heart rate should increase with CO exposure
        self.assertTrue(hr_with_co > baseline_hr)
    
    def test_environmental_response(self):
        """Test heart rate response to environmental conditions."""
        # Get baseline heart rate
        baseline_hr = self.model.generate_signal(0.0)
        
        # Reset model
        self.model.reset()
        
        # Generate signal with high temperature and humidity
        env_conditions = {
            "temperature": 35.0,  # High temperature
            "humidity": 90.0,     # High humidity
            "noise": 90.0         # High noise level
        }
        hr_with_env = self.model.generate_signal(0.0, environmental_conditions=env_conditions)
        
        # Heart rate should increase with environmental stress
        self.assertTrue(hr_with_env > baseline_hr)
    
    def test_recovery(self):
        """Test heart rate recovery after exposure."""
        # First generate high heart rate with exposure
        exposures = {"carbon_monoxide": 10.0}
        hr_exposed = self.model.generate_signal(0.0, exposures=exposures)
        
        # Then generate a sequence with no exposures and check for recovery
        hrs = []
        for t in range(1, 20):
            hr = self.model.generate_signal(float(t))  # No exposures
            hrs.append(hr)
        
        # Heart rate should trend back toward baseline
        # Check if the last few heart rates are closer to baseline than the exposed heart rate
        avg_final_hrs = np.mean(hrs[-5:])
        self.assertTrue(abs(avg_final_hrs - self.model.baseline_heart_rate) < 
                       abs(hr_exposed - self.model.baseline_heart_rate))
    
    def test_physiological_limits(self):
        """Test that heart rate stays within physiological limits."""
        # Test with very high exposure to ensure heart rate doesn't exceed max
        exposures = {"carbon_monoxide": 100.0}  # Unrealistically high
        hr = self.model.generate_signal(0.0, exposures=exposures)
        
        # Heart rate should not exceed maximum
        self.assertTrue(hr <= self.model.max_heart_rate)
        
        # Reset model
        self.model.reset()
        
        # Test with conditions that would cause very low heart rate
        # Set last_value artificially low to simulate recovery to baseline
        self.model.last_value = 30.0
        hr = self.model.generate_signal(0.0)
        
        # Heart rate should not go below 40 BPM (physiological minimum)
        self.assertTrue(hr >= 40.0)
    
    def test_hrv_calculation(self):
        """Test heart rate variability calculation."""
        # Generate a sequence of heart rates
        for t in range(30):
            self.model.generate_signal(float(t))
        
        # Calculate HRV
        hrv = self.model.calculate_hrv(window_size=20)
        
        # HRV should be a positive number
        self.assertTrue(hrv > 0)
        
        # Test with insufficient history
        self.model.reset()
        self.assertIsNone(self.model.calculate_hrv(window_size=20))
    
    def test_serialization(self):
        """Test serialization to and from dictionary."""
        # Generate some heart rate data
        for t in range(10):
            self.model.generate_signal(float(t))
        
        # Convert to dictionary
        model_dict = self.model.to_dict()
        
        # Check dictionary contents
        self.assertEqual(model_dict["baseline_heart_rate"], 70.0)
        self.assertEqual(model_dict["variability"], 2.0)
        self.assertEqual(model_dict["is_active"], True)
        
        # Create new model from dictionary
        new_model = HeartRateModel.from_dict(model_dict)
        
        # Check new model attributes
        self.assertEqual(new_model.baseline_heart_rate, 70.0)
        self.assertEqual(new_model.variability, 2.0)
        self.assertEqual(new_model.recovery_rate, 0.1)
        self.assertEqual(new_model.is_active, True)


if __name__ == "__main__":
    unittest.main()
