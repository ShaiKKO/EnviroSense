"""
Tests for the advanced pattern generation capabilities.

This module tests the enhanced pattern functionality including different waveforms,
noise, interruptions, and correlation matrices.
"""

import unittest
import numpy as np
from envirosense.core.time_series.patterns import (
    Pattern,
    PatternType,
    WaveformType,
    CompositePattern
)
from envirosense.core.time_series.correlation import (
    CorrelationMatrix,
    StochasticElementGenerator,
    generate_correlated_variables,
    correlation_to_covariance
)


class TestAdvancedWaveforms(unittest.TestCase):
    """Test cases for the advanced waveform functionality."""
    
    def setUp(self):
        """Set up test parameters."""
        self.base_value = 20.0
        self.amplitude = 5.0
        self.period = 24.0
        self.phase_shift = 14.0
        self.test_hours = [0.0, 6.0, 12.0, 18.0, 24.0]
    
    def test_sine_waveform(self):
        """Test sine waveform pattern."""
        pattern = Pattern.create_diurnal(
            base_value=self.base_value,
            amplitude=self.amplitude,
            phase_shift=self.phase_shift,
            waveform=WaveformType.SINE
        )
        
        # For sine with phase_shift=14, expect min around 2AM and max around 2PM + 6h = 8PM
        # This is different from cosine whose max is at phase_shift
        values = [pattern.get_value(h) for h in self.test_hours]
        
        # Due to phase shift, we expect values to follow specific pattern
        # At hour 0 (midnight), we should be between min and max
        self.assertTrue(self.base_value - self.amplitude < values[0] < self.base_value + self.amplitude)
        
        # At hour 6 (around 6AM), we should be near a minimum
        self.assertAlmostEqual(values[1], self.base_value - self.amplitude, delta=1.0)
        
        # At hour 18 (around 6PM), we should be near a maximum
        self.assertAlmostEqual(values[3], self.base_value + self.amplitude, delta=1.0)
    
    def test_square_wave(self):
        """Test square wave pattern."""
        pattern = Pattern.create_square_wave(
            base_value=self.base_value,
            amplitude=self.amplitude,
            period=self.period,
            duty_cycle=0.5  # 50% high, 50% low
        )
        
        # Check values at specific times
        # At 25% of period, should be high
        self.assertEqual(pattern.get_value(self.period * 0.25), self.base_value + self.amplitude)
        
        # At 75% of period, should be low
        self.assertEqual(pattern.get_value(self.period * 0.75), self.base_value - self.amplitude)
        
        # With a different duty cycle
        pattern_75 = Pattern.create_square_wave(
            base_value=self.base_value,
            amplitude=self.amplitude,
            period=self.period,
            duty_cycle=0.75  # 75% high, 25% low
        )
        
        # At 60% of period, should still be high
        self.assertEqual(pattern_75.get_value(self.period * 0.6), self.base_value + self.amplitude)
        
        # At 80% of period, should be low
        self.assertEqual(pattern_75.get_value(self.period * 0.8), self.base_value - self.amplitude)
    
    def test_triangle_wave(self):
        """Test triangle wave pattern."""
        pattern = Pattern.create_triangle_wave(
            base_value=self.base_value,
            amplitude=self.amplitude,
            period=self.period,
            duty_cycle=0.5  # Symmetric rise and fall
        )
        
        # At start of period, should be at minimum
        self.assertAlmostEqual(pattern.get_value(0), self.base_value - self.amplitude, delta=0.01)
        
        # At 50% of period, should be at maximum
        self.assertAlmostEqual(pattern.get_value(self.period * 0.5), self.base_value + self.amplitude, delta=0.01)
        
        # At end of period, should be back to minimum
        self.assertAlmostEqual(pattern.get_value(self.period), self.base_value - self.amplitude, delta=0.01)
        
        # With asymmetric rise/fall (70% rise, 30% fall)
        pattern_asym = Pattern.create_triangle_wave(
            base_value=self.base_value,
            amplitude=self.amplitude,
            period=self.period,
            duty_cycle=0.7
        )
        
        # At 70% of period, should be at maximum
        self.assertAlmostEqual(pattern_asym.get_value(self.period * 0.7), self.base_value + self.amplitude, delta=0.01)
    
    def test_sawtooth_wave(self):
        """Test sawtooth wave pattern."""
        pattern = Pattern.create_sawtooth_wave(
            base_value=self.base_value,
            amplitude=self.amplitude,
            period=self.period
        )
        
        # At start of period, should be at minimum
        self.assertAlmostEqual(pattern.get_value(0), self.base_value - self.amplitude, delta=0.01)
        
        # At 50% of period, should be at mid-point
        self.assertAlmostEqual(pattern.get_value(self.period * 0.5), self.base_value, delta=0.01)
        
        # At end of period, should be at maximum (just before reset)
        self.assertAlmostEqual(pattern.get_value(self.period - 0.01), self.base_value + self.amplitude - 0.01, delta=0.1)
    
    def test_waveform_noise(self):
        """Test addition of noise to waveforms."""
        # Create patterns with different noise levels
        pattern_no_noise = Pattern.create_diurnal(
            base_value=self.base_value,
            amplitude=self.amplitude,
            noise_level=0.0
        )
        
        pattern_with_noise = Pattern.create_diurnal(
            base_value=self.base_value,
            amplitude=self.amplitude,
            noise_level=0.5  # 50% noise level (large for testing)
        )
        
        # For no noise, values at same time point should be identical
        time = 12.0
        self.assertEqual(pattern_no_noise.get_value(time), pattern_no_noise.get_value(time))
        
        # For high noise, values at same time point should likely be different
        # This is probabilistic, but with high noise level it's very likely
        values = [pattern_with_noise.get_value(time) for _ in range(10)]
        self.assertTrue(any(abs(values[0] - v) > 0.1 for v in values[1:]))
        
        # The mean of many noisy samples should be close to the true value
        # Again probabilistic, but should be true with enough samples
        true_value = pattern_no_noise.get_value(time)
        noisy_values = [pattern_with_noise.get_value(time) for _ in range(1000)]
        mean_noisy = np.mean(noisy_values)
        
        # Mean should be within 10% of true value with high probability
        self.assertAlmostEqual(mean_noisy, true_value, delta=abs(0.1 * true_value))


class TestInterruptedPatterns(unittest.TestCase):
    """Test cases for patterns with interruptions."""
    
    def setUp(self):
        """Set up test patterns and interruptions."""
        self.base_value = 25.0
        self.amplitude = 10.0
        
        # Define the base pattern
        self.base_pattern = {
            "pattern_type": PatternType.DIURNAL,
            "base_value": self.base_value,
            "amplitude": self.amplitude,
            "period": 24.0,
            "phase_shift": 14.0
        }
        
        # Create a non-interrupted pattern for comparison
        self.normal_pattern = Pattern(**self.base_pattern)
    
    def test_flat_interruption(self):
        """Test a pattern with a flat-line interruption."""
        # Define interruptions
        interruptions = [
            {
                "start_time": 24.0,  # Start at hour 24
                "end_time": 36.0,    # End at hour 36
                "value": self.base_value  # Flat at the base value
            }
        ]
        
        # Create the interrupted pattern
        interrupted_pattern = Pattern.create_interrupted_pattern(
            base_pattern=self.base_pattern,
            interruptions=interruptions
        )
        
        # Check values before interruption
        self.assertEqual(interrupted_pattern.get_value(12.0), self.normal_pattern.get_value(12.0))
        
        # Check values during interruption
        self.assertEqual(interrupted_pattern.get_value(30.0), self.base_value)
        
        # Check values after interruption
        self.assertEqual(interrupted_pattern.get_value(48.0), self.normal_pattern.get_value(48.0))
    
    def test_pattern_interruption(self):
        """Test a pattern interrupted by another pattern."""
        # Define interruptions with explicit square wave pattern
        square_pattern = Pattern.create_square_wave(
            base_value=self.base_value,
            amplitude=self.amplitude * 0.5,
            period=4.0,
            duty_cycle=0.5
        )
        
        # Get the dictionary representation
        square_pattern_dict = square_pattern.to_dict()
        
        # Define the interruptions using the pattern from above
        interruptions = [
            {
                "start_time": 24.0,
                "end_time": 36.0,
                "pattern": square_pattern_dict
            }
        ]
        
        # Create the interrupted pattern
        interrupted_pattern = Pattern.create_interrupted_pattern(
            base_pattern=self.base_pattern,
            interruptions=interruptions
        )
        
        # For debugging: Print detailed information
        test_time_high = 25.0  # This is clearly in the high phase
        actual_value_high = interrupted_pattern.get_value(test_time_high)
        expected_value_high = self.base_value + self.amplitude * 0.5
        print(f"Value at {test_time_high}: {actual_value_high}, Expected: {expected_value_high}")
        
        # Verify the square wave pattern directly for high phase
        time_since_start_high = test_time_high - 24.0  # 1 hour since interruption start
        cycle_position_high = time_since_start_high % 4.0  # Position in 4-hour cycle
        phase_high = cycle_position_high / 4.0  # Phase in cycle (0-1)
        print(f"Time since start: {time_since_start_high}, Cycle position: {cycle_position_high}, Phase: {phase_high}")
        print(f"Expected high? {phase_high < 0.5}")
        
        # Direct test of square wave pattern to verify it works
        direct_value_high = square_pattern.get_value(cycle_position_high)
        print(f"Direct square pattern value at {cycle_position_high}: {direct_value_high}")
        
        # Test a time for low phase
        test_time_low = 27.0  # This is clearly in the low phase
        actual_value_low = interrupted_pattern.get_value(test_time_low)
        expected_value_low = self.base_value - self.amplitude * 0.5
        print(f"Value at {test_time_low}: {actual_value_low}, Expected: {expected_value_low}")
        
        # Check values during interruption
        # Should follow square wave pattern
        self.assertEqual(interrupted_pattern.get_value(25.0), self.base_value + self.amplitude * 0.5)  # High phase
        self.assertEqual(interrupted_pattern.get_value(27.0), self.base_value - self.amplitude * 0.5)  # Low phase
    
    def test_multiple_interruptions(self):
        """Test a pattern with multiple interruptions."""
        # Define interruptions
        interruptions = [
            {
                "start_time": 24.0,
                "end_time": 36.0,
                "value": self.base_value
            },
            {
                "start_time": 48.0,
                "end_time": 60.0,
                "pattern": {
                    "pattern_type": PatternType.TRIANGLE_WAVE,
                    "base_value": self.base_value,
                    "amplitude": self.amplitude * 0.75,
                    "period": 6.0
                }
            }
        ]
        
        # Create the interrupted pattern
        interrupted_pattern = Pattern.create_interrupted_pattern(
            base_pattern=self.base_pattern,
            interruptions=interruptions
        )
        
        # Check first interruption
        self.assertEqual(interrupted_pattern.get_value(30.0), self.base_value)
        
        # Check second interruption
        # Should follow triangle wave pattern
        self.assertNotEqual(interrupted_pattern.get_value(54.0), self.normal_pattern.get_value(54.0))
        
        # Check between interruptions
        self.assertEqual(interrupted_pattern.get_value(42.0), self.normal_pattern.get_value(42.0))


class TestCorrelationMatrix(unittest.TestCase):
    """Test cases for the correlation matrix functionality."""
    
    def setUp(self):
        """Set up test correlation matrices."""
        self.matrix = CorrelationMatrix()
        
        # Add some correlations
        self.matrix.add_correlation("A", "B", 0.8)
        self.matrix.add_correlation("A", "C", -0.5)
        self.matrix.add_correlation("B", "C", -0.3)
    
    def test_correlation_values(self):
        """Test that correlation values are stored correctly."""
        self.assertEqual(self.matrix.get_correlation("A", "B"), 0.8)
        self.assertEqual(self.matrix.get_correlation("B", "A"), 0.8)  # Symmetric
        self.assertEqual(self.matrix.get_correlation("A", "C"), -0.5)
        self.assertEqual(self.matrix.get_correlation("B", "C"), -0.3)
        
        # Non-existent correlation should be 0.0
        self.assertEqual(self.matrix.get_correlation("A", "D"), 0.0)
    
    def test_generate_relationships(self):
        """Test generation of relationships from correlations."""
        # Generate with threshold 0.4
        relationships = self.matrix.generate_relationships(threshold=0.4)
        
        # Should only include A-B and A-C relationships
        self.assertEqual(len(relationships), 4)  # 2 pairs, bidirectional
        
        # With higher threshold, only A-B should be included
        high_threshold = self.matrix.generate_relationships(threshold=0.7)
        self.assertEqual(len(high_threshold), 2)  # 1 pair, bidirectional
        
        # Check relationship parameters
        for source, target, params in relationships:
            if source == "A" and target == "B":
                self.assertEqual(params["slope"], 0.8)
            elif source == "A" and target == "C":
                self.assertEqual(params["slope"], -0.5)
    
    def test_detect_cycles(self):
        """Test detection of cycles in relationships."""
        # Create relationships with a cycle
        cyclic_rels = [
            ("A", "B", {"slope": 0.8}),
            ("B", "C", {"slope": -0.3}),
            ("C", "A", {"slope": 0.4})
        ]
        
        cycles = self.matrix.detect_cycles(cyclic_rels)
        self.assertEqual(len(cycles), 1)
        
        # Create relationships without a cycle
        acyclic_rels = [
            ("A", "B", {"slope": 0.8}),
            ("B", "C", {"slope": -0.3})
        ]
        
        cycles = self.matrix.detect_cycles(acyclic_rels)
        self.assertEqual(len(cycles), 0)
    
    def test_serialization(self):
        """Test serialization to and from dictionary."""
        # Convert to dictionary
        matrix_dict = self.matrix.to_dict()
        
        # Check dictionary structure
        self.assertIn("parameters", matrix_dict)
        self.assertIn("correlations", matrix_dict)
        self.assertEqual(len(matrix_dict["parameters"]), 3)  # A, B, C
        
        # Recreate from dictionary
        new_matrix = CorrelationMatrix.from_dict(matrix_dict)
        
        # Check recreated correlations
        self.assertEqual(new_matrix.get_correlation("A", "B"), 0.8)
        self.assertEqual(new_matrix.get_correlation("A", "C"), -0.5)
        self.assertEqual(new_matrix.get_correlation("B", "C"), -0.3)


class TestStochasticElements(unittest.TestCase):
    """Test cases for stochastic element generation."""
    
    def setUp(self):
        """Set up stochastic generator."""
        self.stochastic_gen = StochasticElementGenerator()
        self.size = 1000
    
    def test_white_noise(self):
        """Test white noise generation."""
        noise = self.stochastic_gen.white_noise(self.size, scale=1.0)
        
        # Check size
        self.assertEqual(len(noise), self.size)
        
        # Check statistical properties
        self.assertAlmostEqual(np.mean(noise), 0.0, delta=0.1)
        self.assertAlmostEqual(np.std(noise), 1.0, delta=0.1)
        
        # Autocorrelation should be low
        auto_corr = np.corrcoef(noise[:-1], noise[1:])[0, 1]
        self.assertLess(abs(auto_corr), 0.1)
    
    def test_autocorrelated_noise(self):
        """Test autocorrelated noise generation."""
        noise = self.stochastic_gen.autocorrelated_noise(self.size, phi=0.9, scale=1.0)
        
        # Check size
        self.assertEqual(len(noise), self.size)
        
        # Autocorrelation should be high
        auto_corr = np.corrcoef(noise[:-1], noise[1:])[0, 1]
        self.assertGreater(auto_corr, 0.8)
    
    def test_random_events(self):
        """Test random events generation."""
        events = self.stochastic_gen.generate_random_events(
            self.size,
            event_probability=0.05,
            event_magnitude=(1.0, 3.0),
            event_duration=(10, 20)
        )
        
        # Check size
        self.assertEqual(len(events), self.size)
        
        # Most values should be 0
        zero_count = np.sum(events == 0)
        self.assertGreater(zero_count, self.size * 0.7)  # At least 70% zeros
        
        # Non-zero values should form clusters
        non_zero = events != 0
        transitions = np.sum(np.abs(np.diff(non_zero)))
        self.assertLess(transitions, self.size * 0.1)  # Fewer than 10% transitions
    
    def test_add_anomalies(self):
        """Test adding anomalies to data."""
        # Create a smooth sine wave
        x = np.linspace(0, 4 * np.pi, self.size)
        data = np.sin(x)
        
        # Add anomalies
        anomalous = self.stochastic_gen.add_anomalies(
            data,
            anomaly_probability=0.02,
            anomaly_scale=(3.0, 5.0)
        )
        
        # Check size
        self.assertEqual(len(anomalous), self.size)
        
        # Some values should be outside the [-1, 1] range of sine
        outside_range = np.sum((anomalous < -1.5) | (anomalous > 1.5))
        self.assertGreater(outside_range, 0)
        
        # But most values should still be similar to original
        similar = np.sum(np.abs(anomalous - data) < 0.1)
        self.assertGreater(similar, self.size * 0.9)  # At least 90% similar


class TestCorrelatedVariables(unittest.TestCase):
    """Test utility functions for generating correlated variables."""
    
    def test_correlation_to_covariance(self):
        """Test conversion from correlation to covariance matrix."""
        # Define a correlation matrix
        correlation = np.array([
            [1.0, 0.5, -0.3],
            [0.5, 1.0, 0.2],
            [-0.3, 0.2, 1.0]
        ])
        
        # Define standard deviations
        std = np.array([2.0, 1.0, 3.0])
        
        # Convert to covariance
        cov = correlation_to_covariance(correlation, std)
        
        # Check dimensions
        self.assertEqual(cov.shape, correlation.shape)
        
        # Check diagonal elements (should be variances)
        self.assertAlmostEqual(cov[0, 0], std[0] * std[0])
        self.assertAlmostEqual(cov[1, 1], std[1] * std[1])
        self.assertAlmostEqual(cov[2, 2], std[2] * std[2])
        
        # Check off-diagonal elements
        self.assertAlmostEqual(cov[0, 1], correlation[0, 1] * std[0] * std[1])
        self.assertAlmostEqual(cov[0, 2], correlation[0, 2] * std[0] * std[2])
        self.assertAlmostEqual(cov[1, 2], correlation[1, 2] * std[1] * std[2])
    
    def test_generate_correlated_variables(self):
        """Test generation of correlated random variables."""
        # Define mean and covariance
        mean = [10.0, 5.0, 15.0]
        
        # Create a correlation matrix
        correlation = np.array([
            [1.0, 0.8, -0.6],
            [0.8, 1.0, -0.4],
            [-0.6, -0.4, 1.0]
        ])
        
        # Define standard deviations
        std = [2.0, 1.0, 3.0]
        
        # Calculate covariance
        cov = correlation_to_covariance(correlation, std)
        
        # Generate correlated variables
        size = 1000
        variables = generate_correlated_variables(mean, cov, size)
        
        # Check dimensions
        self.assertEqual(variables.shape, (size, len(mean)))
        
        # Check means
        means = np.mean(variables, axis=0)
        for i, m in enumerate(mean):
            self.assertAlmostEqual(means[i], m, delta=0.2)
        
        # Check correlation
        generated_corr = np.corrcoef(variables.T)
        for i in range(len(mean)):
            for j in range(i+1, len(mean)):
                # Check that correlation is close to specified
                self.assertAlmostEqual(generated_corr[i, j], correlation[i, j], delta=0.1)


if __name__ == "__main__":
    unittest.main()
