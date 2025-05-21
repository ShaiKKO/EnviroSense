"""
EnviroSense Temporal Correlation System.

This package provides components for analyzing temporal relationships between 
different data sources, enabling detection of patterns, correlations, and causal
relationships across time series data from multiple environmental sensors and systems.
"""

from envirosense.core_platform.temporal_correlation.alignment import (
    TimeSeriesAligner,
    DynamicTimeWarping,
    SampleRateSynchronizer,
    NoiseResistantAligner
)

from envirosense.core_platform.temporal_correlation.window_analysis import (
    MovingWindowAnalyzer,
    AdaptiveWindowSizer,
    WindowOverlapManager,
    SignificanceTester
)

from envirosense.core_platform.temporal_correlation.delayed_response import (
    DelayedResponseModel,
    TemporalPattern,
    DelayParameters,
    CompoundDelayProfile,
    PathwayResponseTiming
)

__all__ = [
    # Alignment components
    'TimeSeriesAligner',
    'DynamicTimeWarping',
    'SampleRateSynchronizer',
    'NoiseResistantAligner',
    
    # Window analysis components
    'MovingWindowAnalyzer',
    'AdaptiveWindowSizer',
    'WindowOverlapManager',
    'SignificanceTester',
    
    # Delayed response components
    'DelayedResponseModel',
    'TemporalPattern',
    'DelayParameters',
    'CompoundDelayProfile',
    'PathwayResponseTiming'
]

# Version information
__version__ = '0.1.0'
