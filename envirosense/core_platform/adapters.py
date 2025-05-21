"""
EnviroSense Core Platform Integration Adapters.

This module provides adapters that integrate components from the Simulation Engine
into the Core Platform, following the three-tier architecture defined in the master plan.
"""

import importlib
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


class SimulationEngineAdapter:
    """
    Adapter for integrating with the EnviroSense Simulation Engine.
    
    This adapter provides a unified interface for accessing simulation engine components
    and ensures version compatibility between the Core Platform and Simulation Engine.
    """

    def __init__(self):
        """Initialize the simulation engine adapter."""
        self._engine_modules = {}
        self._version_compatibility = {
            # Define compatible simulation engine versions
            "0.1.0": ["0.1.0", "0.1.1"],
            "0.2.0": ["0.2.0"],
        }
        
    def get_module(self, module_path: str) -> Any:
        """
        Get a module from the simulation engine.
        
        Args:
            module_path: The module path relative to simulation_engine package.
                         Example: "time_series.generator" for the module at
                         envirosense.simulation_engine.time_series.generator
                         
        Returns:
            The imported module
            
        Raises:
            ImportError: If the module cannot be found or imported.
            VersionError: If the module version is not compatible with the core platform.
        """
        if module_path in self._engine_modules:
            return self._engine_modules[module_path]
        
        try:
            full_path = f"envirosense.simulation_engine.{module_path}"
            module = importlib.import_module(full_path)
            self._engine_modules[module_path] = module
            
            # Verify version compatibility if module has version info
            if hasattr(module, "__version__"):
                self._check_version_compatibility(module_path, module.__version__)
                
            return module
        except ImportError as e:
            raise ImportError(f"Could not import simulation engine module '{module_path}': {e}")
    
    def _check_version_compatibility(self, module_path: str, version: str) -> None:
        """Check if the module version is compatible with the core platform."""
        from envirosense.core_platform import __version__ as platform_version
        
        if platform_version not in self._version_compatibility:
            # If we don't have explicit compatibility info, allow for now
            return
            
        compatible_versions = self._version_compatibility[platform_version]
        if version not in compatible_versions:
            raise VersionError(
                f"Module '{module_path}' version '{version}' is not compatible with "
                f"core platform version '{platform_version}'. Compatible versions: {compatible_versions}"
            )


class VersionError(Exception):
    """Exception raised when there is a version compatibility issue."""
    pass


# Create a singleton instance for use throughout the core platform
simulation_engine = SimulationEngineAdapter()
