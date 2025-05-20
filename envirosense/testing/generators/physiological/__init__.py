"""
Physiological data generators for EnviroSense testing.

This package provides generators for physiological data including sensitivity profiles,
biometric responses, and human factors for use in EnviroSense testing scenarios.
"""

from envirosense.testing.generators.physiological.sensitivity_profiles import (
    SensitivityProfile,
    SensitivityProfileGenerator
)

__all__ = [
    'SensitivityProfile',
    'SensitivityProfileGenerator'
]
