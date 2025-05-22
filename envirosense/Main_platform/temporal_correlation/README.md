# EnviroSense Temporal Correlation System

This module provides robust tools for analyzing temporal relationships between different data sources, enabling detection of patterns, correlations, and causal relationships across time series data.

## Overview

The Temporal Correlation System is designed to handle the complex challenges of real-world environmental sensor data, including:

- Different sampling rates across data sources
- Time shifts and misalignments
- Noise and outliers
- Complex temporal patterns

## Components

### Time Series Alignment

Tools for synchronizing and aligning time series data from different sources:

- `TimeSeriesAligner`: Base class for alignment algorithms
- `DynamicTimeWarping`: Aligns series with non-linear time warping
- `SampleRateSynchronizer`: Handles data with different sampling rates
- `NoiseResistantAligner`: Robust alignment for noisy data with outliers

### Window Analysis

Tools for analyzing data in sliding time windows to detect changes over time:

- `MovingWindowAnalyzer`: Base class for window-based analysis
- `AdaptiveWindowSizer`: Determines optimal window sizes for analysis
- `WindowOverlapManager`: Handles overlapping windows
- `SignificanceTester`: Statistical significance tests for correlations

## Usage Examples

The `examples` directory contains practical demonstrations:

- `correlation_example.py`: Demonstrates the main features

Example usage:

```python
from envirosense.core_platform.temporal_correlation import DynamicTimeWarping

# Create DTW aligner with a constraint window
dtw_aligner = DynamicTimeWarping(
    reference_series=reference_data,
    target_series=target_data,
    reference_timestamps=reference_times,
    target_timestamps=target_times,
    window_size=50  # Constrain warping to reduce computational cost
)

# Perform alignment
aligned_ref, aligned_target = dtw_aligner.align()

# Get alignment report
report = dtw_aligner.get_alignment_report()
print(f"DTW Distance: {report['dtw_distance']:.4f}")
```

## Integration

This system integrates with other EnviroSense components:

- **Time Series Core**: Uses patterns and generation capabilities
- **Physics Models**: Aligns data from physical simulations
- **Biometrics**: Correlates physiological responses with environmental factors

## Extension

The system is designed for extensibility. To add new alignment algorithms:

1. Subclass `TimeSeriesAligner`
2. Implement the `align()` method
3. Add the new class to the imports in `__init__.py`

## Dependencies

- NumPy: For numerical operations
- SciPy: For signal processing and statistics
- Matplotlib: For visualization (examples only)
