"""
Grid Guardian specific data generators

This module provides data generators for Grid Guardian devices, focusing on
fire precursor detection, electrical anomalies, and wildlife fire risk conditions.
These generators produce realistic test data based on the Grid Guardian specifications.
"""

# Import generator classes from their respective modules
from envirosense.testing.generators.fire_precursor import (
    FirePrecursorGenerator,
    THRESHOLD_FORMALDEHYDE,
    THRESHOLD_ACETALDEHYDE,
    THRESHOLD_ACROLEIN,
    THRESHOLD_PHENOL,
    THRESHOLD_CRESOL,
    THRESHOLD_GUAIACOL,
    THRESHOLD_CO,
    THRESHOLD_NO2
)

from envirosense.testing.generators.arcing_detection import ArcingDetectionGenerator
from envirosense.testing.generators.wildland_fire_risk import WildlandFireRiskGenerator

# Export all generators
__all__ = [
    'FirePrecursorGenerator',
    'ArcingDetectionGenerator',
    'WildlandFireRiskGenerator'
]
