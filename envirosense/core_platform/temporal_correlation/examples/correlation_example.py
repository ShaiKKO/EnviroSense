"""
Temporal Correlation System Example.

This example demonstrates how to use the EnviroSense temporal correlation
components to align and analyze time series data from different sources.
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple
import datetime

from envirosense.core_platform.temporal_correlation import (
    DynamicTimeWarping,
    SampleRateSynchronizer,
    NoiseResistantAligner,
    AdaptiveWindowSizer,
    WindowOverlapManager,
    SignificanceTester
)


def generate_example_data() -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generate synthetic time series data for demonstration.
    
    Returns:
        Tuple containing:
        - reference_series: Reference data values
        - reference_timestamps: Timestamps for reference data
        - target_series: Target data values (with time shifts, noise, etc.)
        - target_timestamps: Timestamps for target data (different sampling rate)
    """
    # Generate reference time series: sine wave + noise
    n_reference = 500
    reference_timestamps = np.linspace(0, 10, n_reference)
    reference_signal = np.sin(2 * np.pi * 0.5 * reference_timestamps)
    reference_noise = np.random.normal(0, 0.1, n_reference)
    reference_series = reference_signal + reference_noise
    
    # Generate target time series: similar pattern but with:
    # - Different sampling rate
    # - Time shift/warping
    # - Amplitude differences
    # - Different noise characteristics
    
    # Different sampling rate
    n_target = 400
    target_timestamps = np.linspace(0.5, 9.5, n_target)  # Offset and different range
    
    # Create non-linear warping function for time
    warping = 0.1 * np.sin(2 * np.pi * 0.1 * target_timestamps)
    warped_time = target_timestamps + warping
    
    # Generate signal with warped time
    target_signal = 1.2 * np.sin(2 * np.pi * 0.5 * warped_time)
    
    # Add both Gaussian and impulsive noise
    target_gaussian_noise = np.random.normal(0, 0.15, n_target)
    
    # Add some outliers (impulsive noise)
    outlier_indices = np.random.choice(n_target, size=10, replace=False)
    outlier_values = np.random.normal(0, 1.0, size=10)
    
    target_noise = target_gaussian_noise.copy()
    target_noise[outlier_indices] += outlier_values
    
    target_series = target_signal + target_noise
    
    return reference_series, reference_timestamps, target_series, target_timestamps


def plot_alignment_results(reference: np.ndarray, target: np.ndarray, 
                          aligned_ref: np.ndarray, aligned_target: np.ndarray,
                          title: str) -> None:
    """Plot original and aligned time series for visual comparison.
    
    Args:
        reference: Original reference series
        target: Original target series
        aligned_ref: Aligned reference series
        aligned_target: Aligned target series
        title: Plot title
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Plot original series
    ax1.plot(np.arange(len(reference)), reference, 'b-', label='Reference Series')
    ax1.plot(np.arange(len(target)), target, 'r-', label='Target Series')
    ax1.set_title(f'Original Series - {title}')
    ax1.legend()
    ax1.grid(True)
    
    # Plot aligned series
    ax2.plot(np.arange(len(aligned_ref)), aligned_ref, 'b-', label='Aligned Reference')
    ax2.plot(np.arange(len(aligned_target)), aligned_target, 'r-', label='Aligned Target')
    ax2.set_title(f'Aligned Series - {title}')
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    
    # Save to file with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    plt.savefig(f"envirosense/output/correlation_example_{title.replace(' ', '_').lower()}_{timestamp}.png")
    plt.close()


def demonstrate_dynamic_time_warping():
    """Demonstrate Dynamic Time Warping alignment."""
    print("Demonstrating Dynamic Time Warping alignment...")
    
    # Generate example data
    ref_series, ref_time, target_series, target_time = generate_example_data()
    
    # Create DTW aligner with a constraint window
    dtw_aligner = DynamicTimeWarping(
        reference_series=ref_series,
        target_series=target_series,
        reference_timestamps=ref_time,
        target_timestamps=target_time,
        window_size=50  # Constrain warping to reduce computational cost
    )
    
    # Perform alignment
    aligned_ref, aligned_target = dtw_aligner.align()
    
    # Get alignment report
    report = dtw_aligner.get_alignment_report()
    print(f"DTW Distance: {report['dtw_distance']:.4f}")
    print(f"Warping Path Length: {report['warping_path_length']}")
    print(f"Compression Ratio: {report['compression_ratio']:.4f}")
    
    # Plot results
    plot_alignment_results(
        ref_series, target_series, aligned_ref, aligned_target,
        "Dynamic Time Warping"
    )


def demonstrate_sample_rate_synchronization():
    """Demonstrate sample rate synchronization."""
    print("\nDemonstrating Sample Rate Synchronization...")
    
    # Generate example data
    ref_series, ref_time, target_series, target_time = generate_example_data()
    
    # Create sample rate synchronizer
    synchronizer = SampleRateSynchronizer(
        reference_series=ref_series,
        target_series=target_series,
        reference_timestamps=ref_time,
        target_timestamps=target_time,
        interpolation_method='cubic'  # Use cubic interpolation for smoothness
    )
    
    # Perform alignment
    resampled_ref, resampled_target = synchronizer.align()
    
    # Get alignment report
    report = synchronizer.get_alignment_report()
    print(f"Original Reference Sampling Rate: {report['original_ref_rate']:.4f} Hz")
    print(f"Original Target Sampling Rate: {report['original_target_rate']:.4f} Hz")
    print(f"Common Sampling Rate: {report['common_sampling_rate']:.4f} Hz")
    print(f"Aligned Duration: {report['aligned_duration']:.4f} seconds")
    print(f"Number of Aligned Points: {report['num_aligned_points']}")
    
    # Plot results
    plot_alignment_results(
        ref_series, target_series, resampled_ref, resampled_target,
        "Sample Rate Synchronization"
    )


def demonstrate_noise_resistant_alignment():
    """Demonstrate noise-resistant alignment."""
    print("\nDemonstrating Noise Resistant Alignment...")
    
    # Generate example data
    ref_series, ref_time, target_series, target_time = generate_example_data()
    
    # Create noise-resistant aligner
    robust_aligner = NoiseResistantAligner(
        reference_series=ref_series,
        target_series=target_series,
        reference_timestamps=ref_time,
        target_timestamps=target_time,
        window_size=15,        # Window for local feature extraction
        outlier_threshold=2.5, # Z-score threshold for outlier detection
        smoothing_factor=0.3   # Moderate smoothing (0-1 scale)
    )
    
    # Perform alignment
    aligned_ref, aligned_target = robust_aligner.align()
    
    # Get alignment report
    report = robust_aligner.get_alignment_report()
    print(f"Detected Outliers in Reference: {report['detected_outliers_reference']}")
    print(f"Detected Outliers in Target: {report['detected_outliers_target']}")
    print(f"Alignment Quality Score: {report['alignment_quality']:.4f}")
    
    # Plot results
    plot_alignment_results(
        ref_series, target_series, aligned_ref, aligned_target,
        "Noise Resistant Alignment"
    )


def demonstrate_adaptive_window_sizing():
    """Demonstrate adaptive window sizing."""
    print("\nDemonstrating Adaptive Window Sizing...")
    
    # Generate example data with multiple frequency components
    t = np.linspace(0, 20, 1000)
    
    # Multiple frequency components + trend + noise
    series = (np.sin(2 * np.pi * 0.5 * t) +    # Low frequency
             0.5 * np.sin(2 * np.pi * 2.0 * t) + # Medium frequency
             0.2 * np.sin(2 * np.pi * 5.0 * t) + # High frequency
             0.05 * t +                        # Linear trend
             0.1 * np.random.randn(len(t)))     # Noise
    
    # Create adaptive window sizer
    window_sizer = AdaptiveWindowSizer(
        min_window_size=10,
        max_window_size=500,
        target_stationarity=0.05
    )
    
    # Get optimal window size for this time series
    sampling_rate = 1000 / 20  # 1000 samples over 20 seconds = 50 Hz
    optimal_size = window_sizer.get_optimal_window_size(
        series, sampling_rate=sampling_rate
    )
    
    print(f"Time Series Length: {len(series)} samples")
    print(f"Sampling Rate: {sampling_rate:.1f} Hz")
    print(f"Optimal Window Size: {optimal_size} samples")
    print(f"Optimal Window Duration: {optimal_size / sampling_rate:.2f} seconds")
    
    # Plot the series with optimal window highlighted
    plt.figure(figsize=(12, 6))
    plt.plot(t, series, 'b-', label='Time Series')
    
    # Highlight a window of optimal size in the middle
    mid_point = len(series) // 2
    window_start = mid_point - optimal_size // 2
    window_end = window_start + optimal_size
    
    plt.axvspan(t[window_start], t[window_end], color='r', alpha=0.2, 
               label=f'Optimal Window ({optimal_size} samples)')
    
    plt.title('Adaptive Window Size Determination')
    plt.xlabel('Time (s)')
    plt.ylabel('Value')
    plt.legend()
    plt.grid(True)
    
    # Save to file with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    plt.savefig(f"envirosense/output/adaptive_window_size_{timestamp}.png")
    plt.close()


def demonstrate_significance_testing():
    """Demonstrate significance testing for correlations."""
    print("\nDemonstrating Significance Testing...")
    
    # Generate data with known correlation
    n_samples = 100
    x = np.random.randn(n_samples)
    
    # Create related series with different correlation strengths
    y_strong = 0.8 * x + 0.2 * np.random.randn(n_samples)  # Strong correlation
    y_weak = 0.3 * x + 0.7 * np.random.randn(n_samples)    # Weak correlation
    y_none = np.random.randn(n_samples)                   # No correlation
    
    # Calculate actual correlations
    corr_strong = np.corrcoef(x, y_strong)[0, 1]
    corr_weak = np.corrcoef(x, y_weak)[0, 1]
    corr_none = np.corrcoef(x, y_none)[0, 1]
    
    print(f"Strong Correlation: {corr_strong:.4f}")
    print(f"Weak Correlation: {corr_weak:.4f}")
    print(f"No Correlation: {corr_none:.4f}")
    
    # Create significance tester
    tester = SignificanceTester(alpha=0.05, n_surrogate=1000)
    
    # Test significance with different methods
    methods = ['t-test', 'permutation', 'bootstrap']
    
    for method in methods:
        print(f"\nMethod: {method}")
        
        # Test strong correlation
        is_significant = tester.test_correlation_significance(
            x, y_strong, corr_strong, method=method
        )
        print(f"Strong correlation significant: {is_significant}")
        
        # Test weak correlation
        is_significant = tester.test_correlation_significance(
            x, y_weak, corr_weak, method=method
        )
        print(f"Weak correlation significant: {is_significant}")
        
        # Test no correlation
        is_significant = tester.test_correlation_significance(
            x, y_none, corr_none, method=method
        )
        print(f"No correlation significant: {is_significant}")
    
    # Plot the data
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
    
    ax1.scatter(x, y_strong, alpha=0.7)
    ax1.set_title(f'Strong Correlation (r={corr_strong:.2f})')
    ax1.grid(True)
    
    ax2.scatter(x, y_weak, alpha=0.7)
    ax2.set_title(f'Weak Correlation (r={corr_weak:.2f})')
    ax2.grid(True)
    
    ax3.scatter(x, y_none, alpha=0.7)
    ax3.set_title(f'No Correlation (r={corr_none:.2f})')
    ax3.grid(True)
    
    plt.tight_layout()
    
    # Save to file with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    plt.savefig(f"envirosense/output/correlation_significance_{timestamp}.png")
    plt.close()


def main():
    """Run all demonstrations."""
    # Create output directory if it doesn't exist
    import os
    os.makedirs("envirosense/output", exist_ok=True)
    
    # Run demonstrations
    demonstrate_dynamic_time_warping()
    demonstrate_sample_rate_synchronization()
    demonstrate_noise_resistant_alignment()
    demonstrate_adaptive_window_sizing()
    demonstrate_significance_testing()
    
    print("\nAll demonstrations completed. Results saved to envirosense/output/")


if __name__ == "__main__":
    main()
