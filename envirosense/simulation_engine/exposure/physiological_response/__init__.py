"""
Physiological response modeling for environmental exposures.

This package provides the foundation for modeling physiological responses
to environmental exposures, including both immediate and temporal (delayed,
chronic, and cascading) effects.
"""

# Base components
from envirosense.core.exposure.physiological_response.base import (
    PhysiologicalResponseSystem,
    SystemOutput,
    ResponseSeverityLevel,
    PhysiologicalSystemSet
)

from envirosense.core.exposure.physiological_response.thresholds import (
    ThresholdRegistry,
    load_default_thresholds
)

# Standard physiological systems
from envirosense.core.exposure.physiological_response.respiratory import (
    RespiratoryResponseSystem
)

from envirosense.core.exposure.physiological_response.neurological import (
    NeurologicalResponseSystem
)

# Temporal response framework
from envirosense.core.exposure.physiological_response.temporal_response import (
    TemporalResponseMixin,
    TemporalParameters,
    TemporalPattern,
    PhysiologicalEffectGraph,
    TemporalSystemSet
)

# Enhanced temporal physiological systems
from envirosense.core.exposure.physiological_response.temporal_respiratory import (
    TemporalRespiratorySystem
)

from envirosense.core.exposure.physiological_response.temporal_neurological import (
    TemporalNeurologicalSystem
)

# Ensure the default thresholds are loaded
load_default_thresholds()
