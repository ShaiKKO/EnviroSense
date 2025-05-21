"""
Time Series Alignment Components for the EnviroSense Core Platform.

This module provides the algorithms and tools for aligning time series data
from different sources, sampling rates, and with various noise characteristics.
"""

import numpy as np
from typing import List, Tuple, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass


class TimeSeriesAligner:
    """Base class for time series alignment algorithms.
    
    The TimeSeriesAligner provides common functionality for aligning temporal data
    from different sources, with methods to handle timestamp misalignment, 
    different sampling rates, and varying data formats.
    """
    
    def __init__(self, 
                 reference_series: Optional[np.ndarray] = None,
                 target_series: Optional[np.ndarray] = None,
                 reference_timestamps: Optional[np.ndarray] = None,
                 target_timestamps: Optional[np.ndarray] = None):
        """Initialize the TimeSeriesAligner.
        
        Args:
            reference_series: The reference time series data to align to
            target_series: The target time series data to be aligned
            reference_timestamps: Timestamp array for reference series
            target_timestamps: Timestamp array for target series
        """
        self.reference_series = reference_series
        self.target_series = target_series
        self.reference_timestamps = reference_timestamps
        self.target_timestamps = target_timestamps
        self._aligned_data = None
        self._alignment_report = None
    
    def align(self) -> Tuple[np.ndarray, np.ndarray]:
        """Align the target series to the reference series.
        
        Returns:
            Tuple containing (aligned_reference, aligned_target)
        """
        raise NotImplementedError("Subclasses must implement align()")
    
    def get_alignment_report(self) -> Dict[str, Any]:
        """Get detailed information about the alignment process.
        
        Returns:
            Dictionary with alignment metrics and diagnostics
        """
        if self._alignment_report is None:
            raise ValueError("No alignment has been performed yet")
        return self._alignment_report


class DynamicTimeWarping(TimeSeriesAligner):
    """Align time series using Dynamic Time Warping algorithm.
    
    Dynamic Time Warping (DTW) finds an optimal alignment between two time series by
    warping the time dimension to minimize the distance between corresponding points.
    This is particularly useful for environmental data where events may occur at
    different rates or with temporal shifts.
    """
    
    def __init__(self, 
                 reference_series: np.ndarray,
                 target_series: np.ndarray,
                 reference_timestamps: Optional[np.ndarray] = None,
                 target_timestamps: Optional[np.ndarray] = None,
                 window_size: Optional[int] = None,
                 distance_metric: str = 'euclidean'):
        """Initialize the DTW aligner.
        
        Args:
            reference_series: The reference time series data
            target_series: The target time series data
            reference_timestamps: Timestamp array for reference series
            target_timestamps: Timestamp array for target series
            window_size: Sakoe-Chiba band width for constraining the warping path
            distance_metric: Distance metric to use ('euclidean', 'manhattan', etc.)
        """
        super().__init__(reference_series, target_series, 
                        reference_timestamps, target_timestamps)
        self.window_size = window_size
        self.distance_metric = distance_metric
        self.warping_path = None
        self.dtw_matrix = None
        
    def align(self) -> Tuple[np.ndarray, np.ndarray]:
        """Align the target series to the reference series using DTW.
        
        Returns:
            Tuple containing (aligned_reference, aligned_target)
        """
        # Compute DTW matrix and warping path
        self._compute_dtw_matrix()
        self._compute_warping_path()
        
        # Use warping path to create aligned sequences
        aligned_reference = np.zeros(len(self.warping_path))
        aligned_target = np.zeros(len(self.warping_path))
        
        for i, (ref_idx, tar_idx) in enumerate(self.warping_path):
            aligned_reference[i] = self.reference_series[ref_idx]
            aligned_target[i] = self.target_series[tar_idx]
        
        # Prepare alignment report
        self._alignment_report = {
            'dtw_distance': self.dtw_matrix[-1, -1],
            'warping_path_length': len(self.warping_path),
            'compression_ratio': len(self.warping_path) / 
                               (len(self.reference_series) + len(self.target_series)),
            'warping_path': self.warping_path
        }
        
        self._aligned_data = (aligned_reference, aligned_target)
        return self._aligned_data
    
    def _compute_dtw_matrix(self):
        """Compute the DTW cost matrix."""
        n, m = len(self.reference_series), len(self.target_series)
        self.dtw_matrix = np.full((n+1, m+1), np.inf)
        self.dtw_matrix[0, 0] = 0
        
        for i in range(1, n+1):
            for j in range(1, m+1):
                if self.window_size is None or abs(i-j) <= self.window_size:
                    cost = self._distance(self.reference_series[i-1], 
                                        self.target_series[j-1])
                    self.dtw_matrix[i, j] = cost + min(
                        self.dtw_matrix[i-1, j],    # insertion
                        self.dtw_matrix[i, j-1],    # deletion
                        self.dtw_matrix[i-1, j-1]   # match
                    )
    
    def _compute_warping_path(self):
        """Extract the optimal warping path from the DTW matrix."""
        n, m = self.dtw_matrix.shape
        i, j = n-1, m-1
        
        path = []
        while i > 0 or j > 0:
            path.append((i-1, j-1))
            
            if i == 0:
                j -= 1
            elif j == 0:
                i -= 1
            else:
                min_idx = np.argmin([
                    self.dtw_matrix[i-1, j-1],  # match
                    self.dtw_matrix[i-1, j],    # insertion
                    self.dtw_matrix[i, j-1]     # deletion
                ])
                
                if min_idx == 0:
                    i -= 1
                    j -= 1
                elif min_idx == 1:
                    i -= 1
                else:
                    j -= 1
        
        self.warping_path = path[::-1]  # Reverse to get correct order
    
    def _distance(self, a, b):
        """Compute distance between two points based on the selected metric."""
        if self.distance_metric == 'euclidean':
            return (a - b) ** 2
        elif self.distance_metric == 'manhattan':
            return abs(a - b)
        else:
            raise ValueError(f"Unsupported distance metric: {self.distance_metric}")


class SampleRateSynchronizer(TimeSeriesAligner):
    """Align time series with different sampling rates.
    
    This class resamples time series to a common sampling rate, making them 
    directly comparable for analysis and visualization.
    """
    
    def __init__(self, 
                 reference_series: np.ndarray,
                 target_series: np.ndarray,
                 reference_timestamps: np.ndarray,
                 target_timestamps: np.ndarray,
                 target_sampling_rate: Optional[float] = None,
                 interpolation_method: str = 'linear'):
        """Initialize the sample rate synchronizer.
        
        Args:
            reference_series: The reference time series data
            target_series: The target time series data
            reference_timestamps: Timestamp array for reference series
            target_timestamps: Timestamp array for target series
            target_sampling_rate: Desired sampling rate (samples per second)
                                 If None, use the higher rate of the two series
            interpolation_method: Method for interpolation ('linear', 'cubic', etc.)
        """
        super().__init__(reference_series, target_series, 
                        reference_timestamps, target_timestamps)
        
        self.interpolation_method = interpolation_method
        
        # Calculate original sampling rates
        self.reference_rate = 1.0 / np.mean(np.diff(reference_timestamps))
        self.target_rate = 1.0 / np.mean(np.diff(target_timestamps))
        
        # Determine target sampling rate
        if target_sampling_rate is None:
            self.target_sampling_rate = max(self.reference_rate, self.target_rate)
        else:
            self.target_sampling_rate = target_sampling_rate
            
    def align(self) -> Tuple[np.ndarray, np.ndarray]:
        """Resample both series to the target sampling rate.
        
        Returns:
            Tuple containing (resampled_reference, resampled_target)
        """
        from scipy import interpolate
        
        # Create common time grid at the target sampling rate
        t_min = max(self.reference_timestamps[0], self.target_timestamps[0])
        t_max = min(self.reference_timestamps[-1], self.target_timestamps[-1])
        
        # Generate new time points
        num_points = int((t_max - t_min) * self.target_sampling_rate) + 1
        new_timestamps = np.linspace(t_min, t_max, num_points)
        
        # Create interpolators
        ref_interp = interpolate.interp1d(
            self.reference_timestamps, 
            self.reference_series,
            kind=self.interpolation_method,
            bounds_error=False,
            fill_value="extrapolate"
        )
        
        tar_interp = interpolate.interp1d(
            self.target_timestamps, 
            self.target_series,
            kind=self.interpolation_method,
            bounds_error=False,
            fill_value="extrapolate"
        )
        
        # Resample both series
        resampled_reference = ref_interp(new_timestamps)
        resampled_target = tar_interp(new_timestamps)
        
        # Prepare alignment report
        self._alignment_report = {
            'original_ref_rate': self.reference_rate,
            'original_target_rate': self.target_rate,
            'common_sampling_rate': self.target_sampling_rate,
            'common_timestamps': new_timestamps,
            'aligned_duration': t_max - t_min,
            'num_aligned_points': num_points
        }
        
        self._aligned_data = (resampled_reference, resampled_target)
        return self._aligned_data


class NoiseResistantAligner(TimeSeriesAligner):
    """Align time series with significant noise or outliers.
    
    This class implements robust alignment techniques that are less sensitive to 
    noise and outliers in the data, making it suitable for real-world sensor data
    with artifacts or interference.
    """
    
    def __init__(self, 
                 reference_series: np.ndarray,
                 target_series: np.ndarray,
                 reference_timestamps: Optional[np.ndarray] = None,
                 target_timestamps: Optional[np.ndarray] = None,
                 window_size: int = 10,
                 outlier_threshold: float = 3.0,
                 smoothing_factor: float = 0.5):
        """Initialize the noise-resistant aligner.
        
        Args:
            reference_series: The reference time series data
            target_series: The target time series data
            reference_timestamps: Timestamp array for reference series
            target_timestamps: Timestamp array for target series
            window_size: Size of the moving window for feature extraction
            outlier_threshold: Z-score threshold for outlier detection
            smoothing_factor: Strength of smoothing (0-1) before alignment
        """
        super().__init__(reference_series, target_series, 
                        reference_timestamps, target_timestamps)
        
        self.window_size = window_size
        self.outlier_threshold = outlier_threshold
        self.smoothing_factor = smoothing_factor
        
    def align(self) -> Tuple[np.ndarray, np.ndarray]:
        """Align time series while handling noise and outliers.
        
        Returns:
            Tuple containing (aligned_reference, aligned_target)
        """
        # Preprocess series to remove outliers and reduce noise
        clean_reference = self._preprocess(self.reference_series)
        clean_target = self._preprocess(self.target_series)
        
        # Extract robust features (e.g., moving averages, zero crossings)
        ref_features = self._extract_features(clean_reference)
        tar_features = self._extract_features(clean_target)
        
        # Use DTW on features for initial alignment
        dtw_aligner = DynamicTimeWarping(
            ref_features, tar_features,
            self.reference_timestamps, self.target_timestamps
        )
        _, _ = dtw_aligner.align()
        warping_path = dtw_aligner.warping_path
        
        # Apply alignment to original series
        aligned_reference = np.zeros(len(warping_path))
        aligned_target = np.zeros(len(warping_path))
        
        for i, (ref_idx, tar_idx) in enumerate(warping_path):
            if ref_idx < len(self.reference_series) and tar_idx < len(self.target_series):
                aligned_reference[i] = self.reference_series[ref_idx]
                aligned_target[i] = self.target_series[tar_idx]
        
        # Prepare alignment report
        self._alignment_report = {
            'detected_outliers_reference': sum(self._detect_outliers(self.reference_series)),
            'detected_outliers_target': sum(self._detect_outliers(self.target_series)),
            'warping_path': warping_path,
            'alignment_quality': self._calculate_alignment_quality(
                aligned_reference, aligned_target)
        }
        
        self._aligned_data = (aligned_reference, aligned_target)
        return self._aligned_data
    
    def _preprocess(self, series: np.ndarray) -> np.ndarray:
        """Clean and preprocess a time series."""
        # Detect and replace outliers
        outlier_mask = self._detect_outliers(series)
        clean_series = series.copy()
        
        if np.any(outlier_mask):
            # Replace outliers with local median
            for i in np.where(outlier_mask)[0]:
                start = max(0, i - self.window_size // 2)
                end = min(len(series), i + self.window_size // 2 + 1)
                neighborhood = series[start:end]
                clean_series[i] = np.median(neighborhood[~self._detect_outliers(neighborhood)])
        
        # Apply smoothing if needed
        if self.smoothing_factor > 0:
            clean_series = self._smooth_series(clean_series)
            
        return clean_series
    
    def _detect_outliers(self, series: np.ndarray) -> np.ndarray:
        """Detect outliers using z-score."""
        from scipy import stats
        z_scores = np.abs(stats.zscore(series, nan_policy='omit'))
        return z_scores > self.outlier_threshold
    
    def _smooth_series(self, series: np.ndarray) -> np.ndarray:
        """Apply Savitzky-Golay smoothing to the series."""
        from scipy.signal import savgol_filter
        
        # Calculate window size (must be odd)
        window_length = max(3, 2 * int(len(series) * self.smoothing_factor * 0.05) + 1)
        # Polynomial order
        poly_order = min(3, window_length - 1)
        
        return savgol_filter(series, window_length, poly_order)
    
    def _extract_features(self, series: np.ndarray) -> np.ndarray:
        """Extract robust features from time series."""
        from scipy import signal
        
        # Calculate multiple features and combine into feature vector
        features = []
        
        # Moving average (robust to noise)
        window = np.ones(self.window_size) / self.window_size
        moving_avg = np.convolve(series, window, mode='valid')
        features.append(moving_avg)
        
        # Trend (first derivative, smoothed)
        trend = np.gradient(moving_avg)
        features.append(trend)
        
        # Zero-crossing rate (robust feature for alignment)
        zero_crossings = np.where(np.diff(np.signbit(series)))[0]
        zc_signal = np.zeros_like(series)
        zc_signal[zero_crossings] = 1
        zc_density = np.convolve(zc_signal, window, mode='valid')
        features.append(zc_density)
        
        # Combine features (trim to same length)
        min_length = min(len(f) for f in features)
        features = [f[:min_length] for f in features]
        
        return np.column_stack(features) if len(features) > 1 else features[0]
        
    def _calculate_alignment_quality(self, aligned_ref: np.ndarray, 
                                   aligned_tar: np.ndarray) -> float:
        """Calculate a quality score for the alignment."""
        # Calculate correlation coefficient as a quality measure
        valid_indices = ~(np.isnan(aligned_ref) | np.isnan(aligned_tar))
        if not np.any(valid_indices):
            return 0.0
        
        valid_ref = aligned_ref[valid_indices]
        valid_tar = aligned_tar[valid_indices]
        
        correlation = np.corrcoef(valid_ref, valid_tar)[0, 1]
        return max(0, correlation)  # Ensure non-negative quality score
