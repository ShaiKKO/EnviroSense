"""
EnviroSense Time Series Generator Module

This module provides tools for generating time series data for
environmental and physiological parameters.
"""

from envirosense.core.time_series.parameters import (
    Parameter,
    ParameterType,
    Distribution,
    ConstraintType,
    Pattern,
    PatternType,
    ParameterRelationship,
    linear_relationship,
    exponential_relationship,
    threshold_relationship,
    logistic_relationship
)

from envirosense.core.time_series.generator import TimeSeriesGenerator

__all__ = [
    'Parameter',
    'ParameterType',
    'Distribution',
    'ConstraintType',
    'Pattern',
    'PatternType',
    'ParameterRelationship',
    'linear_relationship',
    'exponential_relationship',
    'threshold_relationship',
    'logistic_relationship',
    'TimeSeriesGenerator'
]
