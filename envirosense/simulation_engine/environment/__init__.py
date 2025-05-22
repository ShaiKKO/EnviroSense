# This file makes the 'environment' directory a Python package.
# It will contain classes related to managing and representing the 3D simulated environment.

from .state import Environment3DState # Example, if state.py is created

__all__ = [
    "Environment3DState"
]