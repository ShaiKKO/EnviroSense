"""
Tests for the Parameter module.
"""

import unittest
import numpy as np
from datetime import datetime

from envirosense.core.time_series.parameters import (
    Parameter,
    ParameterType,
    Distribution,
    Pattern,
    PatternType,
    ParameterRelationship,
    linear_relationship
)


class TestParameter(unittest.TestCase):
    """Test cases for the Parameter class."""
    
    def setUp(self):
        """Set up test cases."""
        # Create a continuous parameter
        self.temp = Parameter(
            name="temperature",
            parameter_type=ParameterType.CONTINUOUS,
            initial_value=25.0,
            units="°C",
            description="Ambient temperature",
            min_value=0.0,
            max_value=50.0
        )
        
        # Create a discrete parameter
        self.level = Parameter(
            name="level",
            parameter_type=ParameterType.DISCRETE,
            initial_value=3,
            min_value=0,
            max_value=10
        )
        
        # Create a categorical parameter
        self.status = Parameter(
            name="status",
            parameter_type=ParameterType.CATEGORICAL,
            initial_value="normal",
            allowed_values=["normal", "alert", "emergency"]
        )
        
        # Create a boolean parameter
        self.active = Parameter(
            name="active",
            parameter_type=ParameterType.BOOLEAN,
            initial_value=True
        )
    
    def test_initial_values(self):
        """Test that initial values are set correctly."""
        self.assertEqual(self.temp.value, 25.0)
        self.assertEqual(self.level.value, 3)
        self.assertEqual(self.status.value, "normal")
        self.assertEqual(self.active.value, True)
    
    def test_min_max_constraints(self):
        """Test that min/max constraints are enforced."""
        # Test setting valid values
        self.temp.value = 30.0
        self.assertEqual(self.temp.value, 30.0)
        
        # Test setting values outside the range
        with self.assertRaises(ValueError):
            self.temp.value = -10.0
        
        with self.assertRaises(ValueError):
            self.temp.value = 60.0
        
        # Value should remain unchanged after constraint violations
        self.assertEqual(self.temp.value, 30.0)
    
    def test_allowed_values_constraint(self):
        """Test that allowed values constraint is enforced."""
        # Test setting a valid value
        self.status.value = "alert"
        self.assertEqual(self.status.value, "alert")
        
        # Test setting an invalid value
        with self.assertRaises(ValueError):
            self.status.value = "warning"
        
        # Value should remain unchanged after constraint violation
        self.assertEqual(self.status.value, "alert")
    
    def test_rate_of_change_constraint(self):
        """Test that rate of change constraint is enforced."""
        # Set a rate of change constraint
        self.temp.set_rate_of_change_constraint(5.0)
        
        # Test valid change (starting value is 30.0 from test_min_max_constraints)
        self.temp.value = 25.0  # Change is 5.0, which is within limit
        self.assertEqual(self.temp.value, 25.0)
        
        # Test invalid change
        with self.assertRaises(ValueError):
            self.temp.value = 15.0  # Change of 10.0 exceeds limit
        
        # Value should remain unchanged after constraint violation
        self.assertEqual(self.temp.value, 25.0)
    
    def test_custom_constraint(self):
        """Test that custom constraints are enforced."""
        # Add a custom constraint: value must be even
        self.level.add_constraint(
            lambda new_val, old_val: new_val % 2 == 0,
            "even_only"
        )
        
        # Test valid change
        self.level.value = 4
        self.assertEqual(self.level.value, 4)
        
        # Test invalid change
        with self.assertRaises(ValueError):
            self.level.value = 5
        
        # Value should remain unchanged after constraint violation
        self.assertEqual(self.level.value, 4)
    
    def test_reset(self):
        """Test that reset works correctly."""
        # Change values
        self.temp.value = 40.0
        self.level.value = 7
        
        # Reset to initial values
        self.temp.reset()
        self.level.reset()
        
        # Check that values are reset
        self.assertEqual(self.temp.value, 25.0)
        self.assertEqual(self.level.value, 3)
        
        # Reset to specific values
        self.temp.reset(35.0)
        self.level.reset(5)
        
        # Check that values are reset to the specified values
        self.assertEqual(self.temp.value, 35.0)
        self.assertEqual(self.level.value, 5)
    
    def test_distribution(self):
        """Test that distributions work correctly."""
        # Set a normal distribution for temperature
        self.temp.distribution = Distribution.NORMAL
        self.temp.distribution_params = {
            "mean": 25.0,
            "std_dev": 2.0
        }
        
        # Set a seed for reproducibility
        np.random.seed(42)
        
        # Generate a new value
        new_value = self.temp.generate_next_value()
        
        # Check that the value is different but within constraints
        self.assertNotEqual(new_value, self.temp.value)
        self.assertGreaterEqual(new_value, self.temp.min_value)
        self.assertLessEqual(new_value, self.temp.max_value)
        
        # Update the parameter
        old_value = self.temp.value
        self.temp.update()
        
        # Check that the value has changed
        self.assertNotEqual(self.temp.value, old_value)
    
    def test_to_from_dict(self):
        """Test that to_dict and from_dict work correctly."""
        # Convert to dictionary
        temp_dict = self.temp.to_dict()
        
        # Check dictionary values
        self.assertEqual(temp_dict["name"], "temperature")
        self.assertEqual(temp_dict["type"], "continuous")
        self.assertEqual(temp_dict["units"], "°C")
        self.assertEqual(temp_dict["min_value"], 0.0)
        self.assertEqual(temp_dict["max_value"], 50.0)
        
        # Create a new parameter from the dictionary
        new_temp = Parameter.from_dict(temp_dict)
        
        # Check that the new parameter has the same properties
        self.assertEqual(new_temp.name, self.temp.name)
        self.assertEqual(new_temp.parameter_type, self.temp.parameter_type)
        self.assertEqual(new_temp.value, self.temp.value)
        self.assertEqual(new_temp.units, self.temp.units)
        self.assertEqual(new_temp.min_value, self.temp.min_value)
        self.assertEqual(new_temp.max_value, self.temp.max_value)


class TestPattern(unittest.TestCase):
    """Test cases for the Pattern class."""
    
    def setUp(self):
        """Set up test cases."""
        # Create a diurnal pattern
        self.diurnal = Pattern(
            pattern_type=PatternType.DIURNAL,
            base_value=25.0,
            amplitude=5.0,
            period=24.0,
            phase_shift=6.0  # Peak at noon
        )
        
        # Create a seasonal pattern
        self.seasonal = Pattern(
            pattern_type=PatternType.SEASONAL,
            base_value=15.0,
            amplitude=10.0,
            period=365.0,  # 365 days
            phase_shift=172.0  # Peak in summer
        )
    
    def test_diurnal_pattern(self):
        """Test that diurnal pattern works correctly."""
        # Check base value
        self.assertEqual(self.diurnal.base_value, 25.0)
        
        # For a diurnal pattern with phase_shift=6.0, the peak will be at 6.0
        # Peak: cos(0) = 1, so value = base + amplitude
        # Trough: cos(π) = -1, so value = base - amplitude
        
        # At phase_shift (6:00), cos(0) = 1, value should be base_value + amplitude
        self.assertAlmostEqual(self.diurnal.get_value(6.0), 30.0, places=5)
        
        # At phase_shift + period/4 (12:00), cos(π/2) = 0, value should be base_value
        self.assertAlmostEqual(self.diurnal.get_value(12.0), 25.0, places=5)
        
        # At phase_shift + period/2 (18:00), cos(π) = -1, value should be base_value - amplitude
        self.assertAlmostEqual(self.diurnal.get_value(18.0), 20.0, places=5)
        
        # At phase_shift + 3*period/4 (0:00), cos(3π/2) = 0, value should be base_value
        self.assertAlmostEqual(self.diurnal.get_value(0.0), 25.0, places=5)
    
    def test_seasonal_pattern(self):
        """Test that seasonal pattern works correctly."""
        # Check base value
        self.assertEqual(self.seasonal.base_value, 15.0)
        
        # Check values at different times
        # Note: seasonal pattern uses days, so time is in hours
        
        # Middle of winter (day 355, hour 0)
        winter_value = self.seasonal.get_value(355 * 24)
        self.assertLess(winter_value, 15.0)  # Should be below base value
        
        # Middle of summer (day 172, hour 0)
        summer_value = self.seasonal.get_value(172 * 24)
        self.assertAlmostEqual(summer_value, 25.0, places=5)  # Should be at peak


class TestParameterRelationship(unittest.TestCase):
    """Test cases for the ParameterRelationship class."""
    
    def setUp(self):
        """Set up test cases."""
        # Create a relationship: humidity = 0.5 * temperature + 30
        self.relationship = ParameterRelationship(
            source_parameter="temperature",
            target_parameter="humidity",
            relationship_function=linear_relationship,
            params={
                "slope": 0.5,
                "offset": 30.0
            },
            description="Temperature affects humidity"
        )
    
    def test_apply(self):
        """Test that apply works correctly."""
        # Apply the relationship to a temperature value
        humidity = self.relationship.apply(25.0)
        
        # Check the result
        self.assertEqual(humidity, 0.5 * 25.0 + 30.0)
    
    def test_to_dict(self):
        """Test that to_dict works correctly."""
        # Convert to dictionary
        rel_dict = self.relationship.to_dict()
        
        # Check dictionary values
        self.assertEqual(rel_dict["source_parameter"], "temperature")
        self.assertEqual(rel_dict["target_parameter"], "humidity")
        self.assertEqual(rel_dict["bidirectional"], False)
        self.assertEqual(rel_dict["params"]["slope"], 0.5)
        self.assertEqual(rel_dict["params"]["offset"], 30.0)


if __name__ == "__main__":
    unittest.main()
