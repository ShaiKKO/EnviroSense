"""
Moving Window Analysis Components for the EnviroSense Core Platform.

This module provides tools for analyzing time series data using sliding windows,
enabling detection of temporal patterns and correlations that vary over time.
"""

import numpy as np
from typing import List, Tuple, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass
from scipy import stats


class MovingWindowAnalyzer:
    """Base class for moving window time series analysis.
    
    This class implements sliding window analysis methods for time series data,
    enabling detection of changing correlations and patterns over time.
    """
    
    def __init__(self, 
                 window_size: int,
                 step_size: int = 1,
                 center_window: bool = True):
        """Initialize the moving window analyzer.
        
        Args:
            window_size: Size of the sliding window (number of samples)
            step_size: How many samples to move the window in each step
            center_window: If True, results are aligned to window center rather than start
        """
        self.window_size = window_size
        self.step_size = step_size
        self.center_window = center_window
        self._analysis_results = None
        
    def apply(self, 
             time_series: np.ndarray, 
             timestamps: Optional[np.ndarray] = None) -> np.ndarray:
        """Apply moving window analysis to a single time series.
        
        Args:
            time_series: The time series data to analyze
            timestamps: Optional timestamps for the time series data
            
        Returns:
            Array of analysis results, one per window position
        """
        raise NotImplementedError("Subclasses must implement apply()")
        
    def apply_dual(self,
                  series_a: np.ndarray,
                  series_b: np.ndarray,
                  timestamps_a: Optional[np.ndarray] = None,
                  timestamps_b: Optional[np.ndarray] = None) -> np.ndarray:
        """Apply moving window analysis to two time series.
        
        Args:
            series_a: First time series data
            series_b: Second time series data
            timestamps_a: Optional timestamps for first series
            timestamps_b: Optional timestamps for second series
            
        Returns:
            Array of analysis results, one per window position
        """
        raise NotImplementedError("Subclasses must implement apply_dual()")
    
    def get_window_positions(self, 
                           series_length: int) -> List[Tuple[int, int]]:
        """Get the start and end indices for each window position.
        
        Args:
            series_length: Length of the time series
            
        Returns:
            List of (start_idx, end_idx) tuples for each window
        """
        positions = []
        start = 0
        
        while start + self.window_size <= series_length:
            end = start + self.window_size
            positions.append((start, end))
            start += self.step_size
            
        return positions
    
    def get_result_timestamps(self, 
                             timestamps: np.ndarray) -> np.ndarray:
        """Get timestamps corresponding to analysis results.
        
        Args:
            timestamps: The original timestamps
            
        Returns:
            Timestamps aligned with analysis results
        """
        positions = self.get_window_positions(len(timestamps))
        
        if not positions:
            return np.array([])
            
        result_timestamps = []
        
        for start, end in positions:
            if self.center_window:
                # Align to window center
                center_idx = start + (end - start) // 2
                result_timestamps.append(timestamps[center_idx])
            else:
                # Align to window start
                result_timestamps.append(timestamps[start])
                
        return np.array(result_timestamps)


class AdaptiveWindowSizer:
    """Dynamically adjust window size based on data characteristics.
    
    This utility class provides methods to automatically determine optimal window 
    sizes for time series analysis based on data properties such as frequency content,
    stationarity, and information density.
    """
    
    def __init__(self, 
                 min_window_size: int = 10,
                 max_window_size: int = 1000,
                 target_stationarity: float = 0.05):
        """Initialize the adaptive window sizer.
        
        Args:
            min_window_size: Minimum allowable window size
            max_window_size: Maximum allowable window size
            target_stationarity: Target p-value for stationarity tests
        """
        self.min_window_size = min_window_size
        self.max_window_size = max_window_size
        self.target_stationarity = target_stationarity
        
    def get_optimal_window_size(self, 
                              time_series: np.ndarray,
                              sampling_rate: Optional[float] = None) -> int:
        """Determine optimal window size for given time series.
        
        Args:
            time_series: The time series data
            sampling_rate: Optional sampling rate (samples per second)
            
        Returns:
            Optimal window size (number of samples)
        """
        # Default method combines multiple approaches
        candidates = []
        
        # Frequency-based window size (if sampling rate provided)
        if sampling_rate is not None:
            freq_size = self._frequency_based_size(time_series, sampling_rate)
            candidates.append(freq_size)
            
        # Stationarity-based window size
        stat_size = self._stationarity_based_size(time_series)
        candidates.append(stat_size)
        
        # Information-based window size
        info_size = self._information_based_size(time_series)
        candidates.append(info_size)
        
        # Filter valid candidates
        valid_candidates = [
            size for size in candidates 
            if self.min_window_size <= size <= self.max_window_size
        ]
        
        if not valid_candidates:
            # If no valid candidates, use reasonable default
            return min(max(len(time_series) // 10, self.min_window_size), 
                      self.max_window_size)
        
        # Return median of valid candidates
        return int(np.median(valid_candidates))
    
    def _frequency_based_size(self, 
                            time_series: np.ndarray,
                            sampling_rate: float) -> int:
        """Determine window size based on frequency content.
        
        Uses FFT to identify dominant frequencies and sets window size to
        capture at least 2-3 cycles of the lowest significant frequency.
        """
        from scipy import signal
        
        # Get power spectrum
        freqs, psd = signal.welch(time_series, fs=sampling_rate, 
                                 nperseg=min(len(time_series), 1024))
        
        # Find peaks in power spectrum
        peaks, _ = signal.find_peaks(psd)
        
        if not peaks.size:
            # No clear peaks, use default
            return min(sampling_rate * 10, self.max_window_size)
        
        # Get frequencies of peaks
        peak_freqs = freqs[peaks]
        peak_powers = psd[peaks]
        
        # Sort peaks by power
        sorted_idx = np.argsort(peak_powers)[::-1]
        
        # Get lowest frequency among top 3 peaks
        top_peak_freqs = peak_freqs[sorted_idx[:3]]
        lowest_freq = np.min(top_peak_freqs)
        
        # Window should contain 3 cycles of lowest frequency
        window_seconds = 3.0 / lowest_freq
        window_samples = int(window_seconds * sampling_rate)
        
        return window_samples
    
    def _stationarity_based_size(self, time_series: np.ndarray) -> int:
        """Determine window size based on stationarity.
        
        Find largest window where data remains approximately stationary.
        """
        from statsmodels.tsa.stattools import adfuller
        
        # Try different window sizes
        for size in range(self.min_window_size, 
                         min(len(time_series) // 2, self.max_window_size), 
                         max(5, (self.max_window_size - self.min_window_size) // 20)):
            
            # Test stationarity in several parts of the series
            stationary_windows = 0
            non_stationary_windows = 0
            
            # Test 5 different segments
            for start in np.linspace(0, len(time_series) - size, 5).astype(int):
                segment = time_series[start:start+size]
                try:
                    # Augmented Dickey-Fuller test
                    result = adfuller(segment)
                    p_value = result[1]
                    
                    if p_value < self.target_stationarity:
                        stationary_windows += 1
                    else:
                        non_stationary_windows += 1
                except:
                    # Statistical test failed, continue to next window
                    continue
            
            # If most windows are stationary, return this size
            if stationary_windows > non_stationary_windows:
                return size
        
        # If no suitable size found, return minimum
        return self.min_window_size
    
    def _information_based_size(self, time_series: np.ndarray) -> int:
        """Determine window size based on information content.
        
        Uses entropy and dimensionality measures to find appropriate window size.
        """
        # Simple approximation using signal variance as complexity measure
        n = len(time_series)
        variances = []
        
        # Calculate variance for different window sizes
        for size in np.linspace(self.min_window_size, min(n // 2, self.max_window_size), 20).astype(int):
            var_sum = 0
            count = 0
            
            for i in range(0, n - size, size // 2):
                segment = time_series[i:i+size]
                var_sum += np.var(segment)
                count += 1
                
            if count > 0:
                variances.append((size, var_sum / count))
        
        if not variances:
            return self.min_window_size
        
        # Find point where variance stabilizes (diminishing returns)
        sizes, vars = zip(*variances)
        diffs = np.diff(vars) / np.array(vars[:-1])
        
        # Find where variance change drops below threshold
        stable_idx = np.where(np.abs(diffs) < 0.05)[0]
        
        if len(stable_idx) > 0:
            return sizes[stable_idx[0]]
        else:
            # No clear stabilization point
            return sizes[len(sizes) // 2]  # Middle option


class WindowOverlapManager:
    """Manage overlapping windows for time series analysis.
    
    This class handles the combination of results from overlapping windows,
    providing methods for weighted aggregation and smoothing of analysis results.
    """
    
    def __init__(self,
                overlap_fraction: float = 0.5,
                edge_weighting: str = 'triangular'):
        """Initialize the window overlap manager.
        
        Args:
            overlap_fraction: Fraction of window that overlaps with neighbors
            edge_weighting: Method for weighting edge effects ('none', 'triangular', 
                          'gaussian', 'cosine')
        """
        self.overlap_fraction = max(0.0, min(0.9, overlap_fraction))
        self.edge_weighting = edge_weighting
        
    def get_step_size(self, window_size: int) -> int:
        """Get step size for given window size and overlap fraction.
        
        Args:
            window_size: Size of the analysis window
            
        Returns:
            Appropriate step size for desired overlap
        """
        step_size = max(1, int(window_size * (1.0 - self.overlap_fraction)))
        return step_size
    
    def get_weights(self, window_size: int) -> np.ndarray:
        """Get window weights based on selected weighting function.
        
        Args:
            window_size: Size of the analysis window
            
        Returns:
            Array of weights for samples within window
        """
        if self.edge_weighting == 'none':
            return np.ones(window_size)
        
        elif self.edge_weighting == 'triangular':
            # Triangular window (maximum weight in center)
            center = (window_size - 1) / 2
            return 1.0 - np.abs(np.arange(window_size) - center) / center
        
        elif self.edge_weighting == 'gaussian':
            # Gaussian window
            center = (window_size - 1) / 2
            sigma = window_size / 6  # 3*sigma covers half the window
            x = np.arange(window_size)
            return np.exp(-0.5 * ((x - center) / sigma) ** 2)
        
        elif self.edge_weighting == 'cosine':
            # Cosine window (Hann window)
            return 0.5 * (1 - np.cos(2 * np.pi * np.arange(window_size) / (window_size - 1)))
        
        else:
            # Default to uniform weighting
            return np.ones(window_size)
    
    def combine_overlapping_results(self, 
                                  results: List[np.ndarray],
                                  window_positions: List[Tuple[int, int]],
                                  series_length: int) -> np.ndarray:
        """Combine results from overlapping windows.
        
        Args:
            results: List of results from each window position
            window_positions: List of (start, end) indices for each window
            series_length: Total length of the original time series
            
        Returns:
            Combined results array aligned with original time series
        """
        # Initialize combined results and weights arrays
        combined = np.zeros(series_length)
        weights = np.zeros(series_length)
        
        # Get window weights
        window_weights = self.get_weights(window_positions[0][1] - window_positions[0][0])
        
        # For each window position and corresponding result
        for (start, end), result in zip(window_positions, results):
            # Weight result values by window weights
            weighted_result = result * window_weights
            
            # Add to combined results
            for i, val in enumerate(weighted_result):
                if start + i < series_length:
                    combined[start + i] += val
                    weights[start + i] += window_weights[i]
        
        # Normalize by weights (avoiding division by zero)
        positive_weights = weights > 0
        combined[positive_weights] /= weights[positive_weights]
        
        return combined


class SignificanceTester:
    """Statistical tests for significance of window analysis results.
    
    This class provides methods to determine whether patterns and correlations
    detected in time series windows are statistically significant or could have
    occurred by chance.
    """
    
    def __init__(self, alpha: float = 0.05, n_surrogate: int = 100):
        """Initialize the significance tester.
        
        Args:
            alpha: Significance level (e.g., 0.05 for 95% confidence)
            n_surrogate: Number of surrogate data sets for Monte Carlo testing
        """
        self.alpha = alpha
        self.n_surrogate = n_surrogate
        
    def test_correlation_significance(self, 
                                    series_a: np.ndarray,
                                    series_b: np.ndarray,
                                    correlation: float,
                                    method: str = 't-test') -> bool:
        """Test if a correlation is statistically significant.
        
        Args:
            series_a: First time series
            series_b: Second time series
            correlation: Observed correlation coefficient
            method: Testing method ('t-test', 'permutation', 'bootstrap')
            
        Returns:
            True if correlation is significant, False otherwise
        """
        if method == 't-test':
            # Use parametric t-test (assumes normality)
            n = len(series_a)
            t_stat = correlation * np.sqrt((n - 2) / (1 - correlation**2))
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))
            return p_value < self.alpha
            
        elif method == 'permutation':
            # Permutation test
            n_greater = 0
            
            for _ in range(self.n_surrogate):
                # Shuffle one series to break any correlation
                shuffled = np.random.permutation(series_b)
                surr_corr = np.corrcoef(series_a, shuffled)[0, 1]
                
                if abs(surr_corr) >= abs(correlation):
                    n_greater += 1
                    
            p_value = n_greater / self.n_surrogate
            return p_value < self.alpha
            
        elif method == 'bootstrap':
            # Bootstrap confidence interval
            n = len(series_a)
            bootstrap_corrs = []
            
            for _ in range(self.n_surrogate):
                # Sample with replacement
                indices = np.random.choice(n, size=n, replace=True)
                a_sample = series_a[indices]
                b_sample = series_b[indices]
                
                bootstrap_corrs.append(np.corrcoef(a_sample, b_sample)[0, 1])
                
            # Compute confidence interval
            bootstrap_corrs = np.array(bootstrap_corrs)
            lower = np.percentile(bootstrap_corrs, self.alpha/2 * 100)
            upper = np.percentile(bootstrap_corrs, (1 - self.alpha/2) * 100)
            
            # Check if zero is in the confidence interval
            return not (lower <= 0 <= upper)
            
        else:
            raise ValueError(f"Unsupported method: {method}")
    
    def test_pattern_significance(self, 
                               observed_pattern: np.ndarray,
                               null_hypothesis: str = 'white_noise') -> bool:
        """Test if an observed pattern is statistically significant.
        
        Args:
            observed_pattern: The pattern detected in the data
            null_hypothesis: Type of null model ('white_noise', 'red_noise', 
                           'shuffled')
            
        Returns:
            True if pattern is significant, False otherwise
        """
        # Extract test statistic from pattern (e.g., mean, variance, max)
        test_statistic = np.max(np.abs(observed_pattern))
        
        # Generate surrogate data under null hypothesis
        surrogate_stats = []
        
        for _ in range(self.n_surrogate):
            if null_hypothesis == 'white_noise':
                # Generate white noise with same mean and variance
                surrogate = np.random.normal(
                    np.mean(observed_pattern),
                    np.std(observed_pattern),
                    size=len(observed_pattern)
                )
                
            elif null_hypothesis == 'red_noise':
                # Generate autocorrelated noise (AR(1) process)
                from statsmodels.tsa.ar_model import AutoReg
                
                # Fit AR(1) model to observed pattern
                try:
                    model = AutoReg(observed_pattern, lags=1).fit()
                    phi = model.params[1]  # AR coefficient
                except:
                    # Fall back to white noise if fitting fails
                    phi = 0
                
                # Generate AR(1) process
                surrogate = np.zeros_like(observed_pattern)
                surrogate[0] = observed_pattern[0]
                
                for i in range(1, len(surrogate)):
                    surrogate[i] = phi * surrogate[i-1] + np.random.normal(
                        0, np.std(observed_pattern) * np.sqrt(1 - phi**2)
                    )
                    
            elif null_hypothesis == 'shuffled':
                # Shuffled version of original data
                surrogate = np.random.permutation(observed_pattern)
                
            else:
                raise ValueError(f"Unsupported null hypothesis: {null_hypothesis}")
            
            # Calculate test statistic for surrogate
            surrogate_stats.append(np.max(np.abs(surrogate)))
        
        # Calculate p-value
        p_value = np.mean(np.array(surrogate_stats) >= test_statistic)
        
        return p_value < self.alpha
