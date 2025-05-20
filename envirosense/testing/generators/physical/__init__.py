"""
Physical environment simulation generators for EnviroSense testing.

This package provides generators for physical simulations including spatial distribution
of environmental parameters, diffusion models, fluid dynamics, and other physics-based
simulations for use in EnviroSense testing.
"""

from envirosense.testing.generators.physical.spatial_environment import (
    SpatialEnvironmentGenerator
)

__all__ = [
    'SpatialEnvironmentGenerator'
]
