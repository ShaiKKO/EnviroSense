"""
Vibration Physics Module

This package provides tools for modeling, propagation, and visualization of vibrations
in physical environments. It includes classes for various vibration sources, vibration
propagation through materials, and analysis/visualization tools.
"""

# Import base classes
from envirosense.core.physics.vibration.base import Vector3D, VibrationSource

# Import all sources
from envirosense.core.physics.vibration.sources import (
    TransformerVibration,
    MotorVibration,
    GeneratorVibration,
    CompressorVibration
)

# Import propagation and analysis tools
from envirosense.core.physics.vibration.propagation import VibrationPropagation
from envirosense.core.physics.vibration.profile import VibrationProfile
from envirosense.core.physics.vibration.visualizer import VibrationVisualizer

# Define package exports
__all__ = [
    'Vector3D',
    'VibrationSource',
    'TransformerVibration',
    'MotorVibration',
    'GeneratorVibration',
    'CompressorVibration',
    'VibrationPropagation',
    'VibrationProfile',
    'VibrationVisualizer'
]
