"""
Environment-focused data generators for EnviroSense testing.

This package provides generators for environmental parameters, conditions and scenarios
for use in EnviroSense testing. These generators create realistic simulations of
environmental data patterns and variations.
"""

from envirosense.testing.generators.environmental.parameter_generator import (
    EnvironmentalParameterGenerator,
    PARAMETER_DEFINITIONS,
    LOCATION_CHARACTERISTICS,
    SEASONAL_PATTERNS
)

__all__ = [
    'EnvironmentalParameterGenerator',
    'PARAMETER_DEFINITIONS',
    'LOCATION_CHARACTERISTICS',
    'SEASONAL_PATTERNS'
]
