"""
EnviroSense Core Exposure Module

This module provides comprehensive tools for tracking, analyzing, and assessing
chemical exposures, including integration with sensitivity profiles for personalized
health risk assessment.
"""

# Import key classes for easier access
from envirosense.core.exposure.records import (
    ExposureRecord,
    ExposureHistory
)

from envirosense.core.exposure.assessment import (
    RiskLevel,
    ExposureAssessment,
    PersonalizedExposureAssessment
)

from envirosense.core.exposure.storage import (
    ExposureStorage
)

# Version information
__version__ = "1.0.0"
__author__ = "EnviroSense Team"

# Define public API
__all__ = [
    'ExposureRecord',
    'ExposureHistory',
    'RiskLevel',
    'ExposureAssessment',
    'PersonalizedExposureAssessment',
    'ExposureStorage',
]
