"""
Tests for the TimeSeriesGenerator module.
"""

import unittest
import numpy as np
import os
import tempfile
from datetime import datetime, timedelta

from envirosense.core.time_series.parameters import (
    Parameter,
    ParameterType,
    Distribution,
    Pattern,
    PatternType,
    ParameterRelationship,
    linear_relationship
)
from envirosense.core.time_series.generator import TimeSeriesGenerator


class TestTimeSeriesGenerator(unittest.TestCase):
    """Test cases for the TimeSeriesGenerator class."""
    
    def setUp(self):
        """Set up test cases."""
        # Create a generator with a fixed seed for reproducibility
        self.generator = TimeSeriesGenerator({"seed": 42})
        
        # Add some parameters
        self.generator.create_parameter(
            name="temperature",
            parameter_type=ParameterType.CONTINUOUS,
            initial_value=25.0,
            units="°C",
            description="Ambient temperature",
            min_value=0.0,
            max_value=50.0,
            distribution=Distribution.NORMAL,
            distribution_params={"mean": 25.0, "std_dev": 2.0}
        )
        
        self.generator.create_parameter(
            name="humidity",
            parameter_type=ParameterType.CONTINUOUS,
            initial_value=50.0,
            units="%",
            description="Relative humidity",
            min_value=0.0,
            max_value=100.0
        )
        
        self.generator.create_parameter(
            name="air_quality",
            parameter_type=ParameterType.DISCRETE,
            initial_value=3,
            units="AQI",
            description="Air Quality Index",
            min_value=1,
            max_value=5,
            distribution=Distribution.POISSON,
            distribution_params={"lambda": 3.0}
        )
        
        self.generator.create_parameter(
            name="alert",
            parameter_type=ParameterType.BOOLEAN,
            initial_value=False,
            description="Alert status"
        )
    
    def test_parameter_creation(self):
        """Test that parameters are created correctly."""
        # Check that all parameters exist
        self.assertIn("temperature", self.generator.parameters)
        self.assertIn("humidity", self.generator.parameters)
        self.assertIn("air_quality", self.generator.parameters)
        self.assertIn("alert", self.generator.parameters)
        
        # Check parameter values
        self.assertEqual(self.generator.get_parameter_value("temperature"), 25.0)
        self.assertEqual(self.generator.get_parameter_value("humidity"), 50.0)
        self.assertEqual(self.generator.get_parameter_value("air_quality"), 3)
        self.assertEqual(self.generator.get_parameter_value("alert"), False)
    
    def test_parameter_update(self):
        """Test that parameter values can be updated."""
        # Set parameter values
        self.generator.set_parameter_value("temperature", 30.0)
        self.generator.set_parameter_value("humidity", 60.0)
        
        # Check that values are updated
        self.assertEqual(self.generator.get_parameter_value("temperature"), 30.0)
        self.assertEqual(self.generator.get_parameter_value("humidity"), 60.0)
    
    def test_relationship(self):
        """Test that relationships between parameters work correctly."""
        # Create a relationship: humidity = 0.5 * temperature + 30
        relationship = ParameterRelationship(
            source_parameter="temperature",
            target_parameter="humidity",
            relationship_function=linear_relationship,
            params={
                "slope": 0.5,
                "offset": 30.0
            }
        )
        
        # Add the relationship
        self.generator.add_relationship(relationship)
        
        # Set temperature and check that humidity is updated
        self.generator.set_parameter_value("temperature", 40.0)
        self.assertEqual(self.generator.get_parameter_value("humidity"), 0.5 * 40.0 + 30.0)
        
        # Set temperature again and check that humidity is updated
        self.generator.set_parameter_value("temperature", 20.0)
        self.assertEqual(self.generator.get_parameter_value("humidity"), 0.5 * 20.0 + 30.0)
    
    def test_bidirectional_relationship(self):
        """Test that bidirectional relationships work correctly."""
        # Remove existing parameters
        self.generator = TimeSeriesGenerator({"seed": 42})
        
        # Manually reset random seed since we created a new generator
        np.random.seed(42)
        
        # Add Celsius temperature parameter
        self.generator.create_parameter(
            name="celsius",
            parameter_type=ParameterType.CONTINUOUS,
            initial_value=30.0,  # Changed to match updated test
            units="°C",
            min_value=-273.15,
            max_value=1000.0
        )
        
        # Add Fahrenheit temperature parameter
        self.generator.create_parameter(
            name="fahrenheit",
            parameter_type=ParameterType.CONTINUOUS,
            initial_value=86.0,  # Changed to be consistent with 30.0°C
            units="°F",
            min_value=-459.67,
            max_value=1832.0
        )
        
        # Create conversion functions
        def c_to_f(celsius, params):
            return celsius * 9/5 + 32
        
        def f_to_c(fahrenheit, params):
            return (fahrenheit - 32) * 5/9
        
        # Create a bidirectional relationship
        relationship = ParameterRelationship(
            source_parameter="celsius",
            target_parameter="fahrenheit",
            relationship_function=c_to_f,
            bidirectional=True,
            reverse_function=f_to_c
        )
        
        # Add the relationship
        self.generator.add_relationship(relationship)
        
        # Check that setting Celsius updates Fahrenheit
        self.generator.set_parameter_value("celsius", 30.0)
        self.assertAlmostEqual(self.generator.get_parameter_value("fahrenheit"), 86.0)
        
        # Check that setting Fahrenheit updates Celsius
        self.generator.set_parameter_value("fahrenheit", 50.0)
        self.assertAlmostEqual(self.generator.get_parameter_value("celsius"), 10.0)
    
    def test_step(self):
        """Test that stepping the generator updates parameter values."""
        # Get initial values
        initial_temp = self.generator.get_parameter_value("temperature")
        initial_aqi = self.generator.get_parameter_value("air_quality")
        
        # Step the generator
        self.generator.step()
        
        # Check that values have changed
        self.assertNotEqual(self.generator.get_parameter_value("temperature"), initial_temp)
        # AQI might not change due to Poisson distribution with lambda=3
        
        # Check that current time has increased
        self.assertEqual(self.generator.current_time, 1.0)
    
    def test_generate_series(self):
        """Test that generating a time series works correctly."""
        # Generate a series for 24 hours
        series = self.generator.generate_series(24.0, 1.0)
        
        # Check that the series has the correct length
        self.assertEqual(len(series["temperature"]), 24)
        self.assertEqual(len(series["humidity"]), 24)
        self.assertEqual(len(series["air_quality"]), 24)
        self.assertEqual(len(series["alert"]), 24)
        
        # Check that the series has timestamps
        self.assertEqual(len(series["timestamp"]), 24)
        
        # Check that the time step is correct
        self.assertEqual(series["timestamp"][1] - series["timestamp"][0], timedelta(hours=1))
    
    def test_reset(self):
        """Test that resetting the generator works correctly."""
        # Step the generator a few times
        for _ in range(5):
            self.generator.step()
        
        # Check that current time has increased
        self.assertEqual(self.generator.current_time, 5.0)
        
        # Reset the generator
        self.generator.reset()
        
        # Check that current time is reset
        self.assertEqual(self.generator.current_time, 0.0)
        
        # Check that parameter values are reset
        self.assertEqual(self.generator.get_parameter_value("temperature"), 25.0)
        self.assertEqual(self.generator.get_parameter_value("humidity"), 50.0)
        self.assertEqual(self.generator.get_parameter_value("air_quality"), 3)
        self.assertEqual(self.generator.get_parameter_value("alert"), False)
    
    def test_save_load(self):
        """Test that saving and loading the generator works correctly."""
        # Create a temporary file
        fd, filepath = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        
        try:
            # Save the generator
            self.generator.save(filepath)
            
            # Load the generator
            loaded_generator = TimeSeriesGenerator.load(filepath)
            
            # Check that the loaded generator has the same parameters
            self.assertEqual(
                set(loaded_generator.parameters.keys()),
                set(self.generator.parameters.keys())
            )
            
            # Check that parameter values are the same
            for name in self.generator.parameters:
                self.assertEqual(
                    loaded_generator.get_parameter_value(name),
                    self.generator.get_parameter_value(name)
                )
        finally:
            # Clean up the temporary file
            os.unlink(filepath)
    
    def test_export_csv(self):
        """Test that exporting to CSV works correctly."""
        # Create a temporary file
        fd, filepath = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        
        try:
            # Generate a series
            series = self.generator.generate_series(5.0, 1.0)
            
            # Export to CSV
            self.generator.export_to_csv(filepath, series)
            
            # Check that the file exists
            self.assertTrue(os.path.exists(filepath))
            
            # Check that the file has the correct content (just check it's not empty)
            with open(filepath, 'r') as f:
                content = f.read()
                self.assertTrue(len(content) > 0)
        finally:
            # Clean up the temporary file
            os.unlink(filepath)
    
    def test_export_json(self):
        """Test that exporting to JSON works correctly."""
        # Create a temporary file
        fd, filepath = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        
        try:
            # Generate a series
            series = self.generator.generate_series(5.0, 1.0)
            
            # Export to JSON
            self.generator.export_to_json(filepath, series)
            
            # Check that the file exists
            self.assertTrue(os.path.exists(filepath))
            
            # Check that the file has the correct content (just check it's not empty)
            with open(filepath, 'r') as f:
                content = f.read()
                self.assertTrue(len(content) > 0)
        finally:
            # Clean up the temporary file
            os.unlink(filepath)
    
    def test_config_initialization(self):
        """Test that initialization from config works correctly."""
        # Create a config - use parameter names that don't overlap with previous tests
        config = {
            "seed": 42,
            "parameters": [
                {
                    "name": "param1",
                    "type": "continuous",
                    "current_value": 10.0,
                    "min_value": 0.0,
                    "max_value": 100.0
                },
                {
                    "name": "param2",
                    "type": "discrete",
                    "current_value": 5,
                    "min_value": 0,
                    "max_value": 10
                }
            ],
            # Use relationship function that's defined in the module
            "relationships": [
                {
                    "source_parameter": "param1",
                    "target_parameter": "param2",
                    "function": "threshold_relationship",
                    "params": {
                        "thresholds": [50.0],
                        "values": [5, 10]
                    }
                }
            ]
        }
        
        # Create a generator from the config
        generator = TimeSeriesGenerator(config)
        
        # Check that parameters are created
        self.assertIn("param1", generator.parameters)
        self.assertIn("param2", generator.parameters)
        
        # Check parameter values
        self.assertEqual(generator.get_parameter_value("param1"), 10.0)
        self.assertEqual(generator.get_parameter_value("param2"), 5)


if __name__ == "__main__":
    unittest.main()
