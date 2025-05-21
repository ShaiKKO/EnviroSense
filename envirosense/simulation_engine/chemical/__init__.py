"""
EnviroSense Chemical Module

This module provides functionality for simulating various chemicals and their behaviors
in an environmental context. It includes chemical source models for different emission
patterns, a comprehensive chemical properties database, and utilities for calculating
how chemicals interact with the environment.

Components:
- Chemical Properties Database: Physical and health-related properties of chemicals
- Chemical Sources: Classes for generating chemical emissions with various patterns
- Chemical Interactions: Modeling how chemicals interact with environment and materials
"""

from envirosense.core.chemical.chemical_properties import (
    ChemicalCategory,
    CHEMICAL_PROPERTIES,
    get_chemical_property,
    get_chemicals_by_category,
    get_diffusion_coefficient
)

from envirosense.core.chemical.sources import (
    SourceStatus,
    ChemicalSource,
    ConstantSource,
    PulsedSource,
    DecayingSource,
    DiurnalSource,
    EventTriggeredSource,
    ChemicalSourceManager
)

# Version info
__version__ = '0.1.0'
