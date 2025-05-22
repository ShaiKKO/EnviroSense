"""
EnviroSense Temporal Correlation System.

This package provides components for analyzing temporal relationships between 
different data sources, enabling detection of patterns, correlations, and causal
relationships across time series data from multiple environmental sensors and systems.
"""

# Import directly from local modules instead of via core_platform
from .alignment import (
    TimeSeriesAligner,
    DynamicTimeWarping,
    SampleRateSynchronizer,
    NoiseResistantAligner
)

from .window_analysis import (
    MovingWindowAnalyzer,
    AdaptiveWindowSizer,
    WindowOverlapManager,
    SignificanceTester
)

from .delayed_response import (
    DelayedResponseModel,
    TemporalPattern,
    DelayParameters,
    CompoundDelayProfile,
    PathwayResponseTiming
)

from .cumulative_effect import (
    CumulativeEffectModel,
    AccumulationModelType,
    AccumulationProfile,
    CumulativeThresholdSystem,
    CumulativeEffectVisualizer
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
    'PathwayResponseTiming',
    
    # Cumulative effect components
    'CumulativeEffectModel',
    'AccumulationModelType',
    'AccumulationProfile',
    'CumulativeThresholdSystem',
    'CumulativeEffectVisualizer'
]

# Version information
__version__ = '0.1.0'
