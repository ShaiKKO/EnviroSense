"""
Variation factors for dose-response curves.

This package contains modules for adjusting dose-response curves
based on individual characteristics, such as demographic factors,
genetic factors, health conditions, and combined variation models.

Each module provides specific variation factor classes that can
be applied to dose-response curves to model personalized responses
to chemical exposures.
"""

from envirosense.core.exposure.dose_response.variation.base import VariationFactor, VariationAwareDoseResponse
