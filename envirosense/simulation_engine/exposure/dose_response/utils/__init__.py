"""
Utility functions and helpers for dose-response modeling.

This module provides various supporting tools for working with
dose-response curves, such as plotting utilities, environmental
adjustments, and common curve fitting functions.
"""

from envirosense.core.exposure.dose_response.utils.plotting import (
    plot_dose_response_curve,
    plot_comparison
)
from envirosense.core.exposure.dose_response.utils.environmental import (
    EnvironmentalCompensation,
    adjust_for_temperature,
    adjust_for_humidity
)
from envirosense.core.exposure.dose_response.utils.fitting import (
    fit_curve_to_data,
    calculate_confidence_bounds
)

__all__ = [
    'plot_dose_response_curve',
    'plot_comparison',
    'EnvironmentalCompensation',
    'adjust_for_temperature',
    'adjust_for_humidity',
    'fit_curve_to_data',
    'calculate_confidence_bounds',
]
