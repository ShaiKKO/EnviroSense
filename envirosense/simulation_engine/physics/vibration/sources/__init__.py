"""
Vibration Sources

This subpackage provides classes for different types of vibration sources
commonly found in industrial and infrastructure environments.
"""

from envirosense.core.physics.vibration.sources.transformer import TransformerVibration
from envirosense.core.physics.vibration.sources.motor import MotorVibration
from envirosense.core.physics.vibration.sources.generator import GeneratorVibration
from envirosense.core.physics.vibration.sources.compressor import CompressorVibration

__all__ = [
    'TransformerVibration',
    'MotorVibration',
    'GeneratorVibration',
    'CompressorVibration'
]
