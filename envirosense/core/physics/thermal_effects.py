"""
EnviroSense Physics Engine - Thermal Effects Module

This module provides classes for modeling how temperature affects physical and chemical
processes within environmental simulations, including reaction rates, volatilization,
and other temperature-dependent phenomena.
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Optional, Union, Any
import logging
from .space import SpatialGrid, GridCell

logger = logging.getLogger(__name__)


class ThermalEffects:
    """Models how temperature affects chemical behavior and physical processes."""
    
    # Arrhenius equation constants for common reaction types
    REACTION_TYPES = {
        "voc_degradation": {"A": 1.2e6, "Ea": 42000},  # Pre-exponential factor and activation energy
        "formaldehyde_release": {"A": 2.5e5, "Ea": 38000},
        "pyrolysis_onset": {"A": 8.7e7, "Ea": 88000},
        "ozone_formation": {"A": 4.3e4, "Ea": 12000},
        "no2_formation": {"A": 3.2e5, "Ea": 25000},
    }
    
    # Physical constants
    R = 8.314  # Universal gas constant (J/mol·K)
    STANDARD_TEMP = 298.15  # Standard temperature (25°C in K)
    
    def __init__(self):
        """Initialize thermal effects model."""
        # Vapor pressure parameters for common VOCs at reference temperature (25°C)
        # Format: [vapor pressure at 25°C (Pa), enthalpy of vaporization (J/mol)]
        self.vapor_pressure_params = {
            "benzene": [12700.0, 33900],
            "toluene": [3800.0, 38000],
            "xylene": [1100.0, 42700],
            "formaldehyde": [518000.0, 25500],
            "acetaldehyde": [120000.0, 29000],
            "acetone": [30800.0, 31300],
            "methanol": [16900.0, 38000],
            "ethanol": [7900.0, 42300],
            "water": [3170.0, 44000],
        }
        
        # Temperature thresholds for phase transitions (°C)
        self.phase_transition_temps = {
            "water": {"freezing": 0.0, "boiling": 100.0},
            "benzene": {"freezing": 5.5, "boiling": 80.1},
            "toluene": {"freezing": -95.0, "boiling": 110.6},
            "xylene": {"freezing": -47.8, "boiling": 138.4},
            "formaldehyde": {"freezing": -92.0, "boiling": -19.0},
            "acetaldehyde": {"freezing": -123.0, "boiling": 20.2},
        }
    
    def calculate_reaction_rate_adjustment(self, base_rate: float, temperature: float, 
                                           reaction_type: str = "voc_degradation") -> float:
        """
        Adjust chemical reaction rate based on temperature using the Arrhenius equation.
        
        Args:
            base_rate: Base reaction rate at standard temperature (25°C)
            temperature: Current temperature in Celsius
            reaction_type: Type of reaction (from REACTION_TYPES)
            
        Returns:
            Adjusted reaction rate
        """
        # Convert temperature to Kelvin
        temp_kelvin = temperature + 273.15
        std_temp_kelvin = self.STANDARD_TEMP
        
        # Get Arrhenius parameters
        if reaction_type not in self.REACTION_TYPES:
            logger.warning(f"Unknown reaction type: {reaction_type}. Using voc_degradation.")
            reaction_type = "voc_degradation"
            
        params = self.REACTION_TYPES[reaction_type]
        A = params["A"]
        Ea = params["Ea"]
        
        # Calculate rate constant ratio using Arrhenius equation
        # k = A * exp(-Ea/RT)
        k_current = A * math.exp(-Ea / (self.R * temp_kelvin))
        k_standard = A * math.exp(-Ea / (self.R * std_temp_kelvin))
        
        # Adjust base rate by ratio of rate constants
        adjustment_factor = k_current / k_standard
        adjusted_rate = base_rate * adjustment_factor
        
        return adjusted_rate
    
    def calculate_vapor_pressure(self, chemical: str, temperature: float) -> float:
        """
        Calculate vapor pressure of a chemical at a given temperature using the
        Clausius-Clapeyron equation.
        
        Args:
            chemical: Chemical name
            temperature: Temperature in Celsius
            
        Returns:
            Vapor pressure in Pascals
        """
        if chemical not in self.vapor_pressure_params:
            logger.warning(f"No vapor pressure data for {chemical}. Returning estimate.")
            return 1000.0  # Default estimate
            
        # Get reference data
        ref_pressure, delta_h_vap = self.vapor_pressure_params[chemical]
        
        # Convert temperatures to Kelvin
        temp_kelvin = temperature + 273.15
        ref_temp_kelvin = self.STANDARD_TEMP
        
        # Clausius-Clapeyron equation
        # ln(P2/P1) = (ΔHvap/R) * (1/T1 - 1/T2)
        exponent = (delta_h_vap / self.R) * ((1 / ref_temp_kelvin) - (1 / temp_kelvin))
        new_pressure = ref_pressure * math.exp(exponent)
        
        return new_pressure
    
    def calculate_volatilization_rate(self, chemical: str, temperature: float, 
                                     base_rate: float, surface_area: float = 1.0) -> float:
        """
        Calculate volatilization rate for a chemical at a given temperature.
        
        Args:
            chemical: Chemical name
            temperature: Temperature in Celsius
            base_rate: Base volatilization rate at standard conditions
            surface_area: Surface area factor (default 1.0)
            
        Returns:
            Adjusted volatilization rate
        """
        # Get vapor pressures
        current_vp = self.calculate_vapor_pressure(chemical, temperature)
        standard_vp = self.calculate_vapor_pressure(chemical, 25.0)  # 25°C reference
        
        # Volatilization rate is proportional to vapor pressure
        vp_ratio = current_vp / standard_vp
        
        # Adjust for temperature effect on diffusion (approximation)
        # Diffusion coefficient ~ T^1.75 (theoretical)
        temp_ratio = ((temperature + 273.15) / self.STANDARD_TEMP) ** 1.75
        
        # Combined adjustment
        adjusted_rate = base_rate * vp_ratio * temp_ratio * surface_area
        
        return adjusted_rate
    
    def calculate_phase_transition(self, chemical: str, temperature: float) -> str:
        """
        Determine the phase of a chemical at a given temperature.
        
        Args:
            chemical: Chemical name
            temperature: Temperature in Celsius
            
        Returns:
            Phase state: "solid", "liquid", or "gas"
        """
        if chemical not in self.phase_transition_temps:
            # Default to liquid for unknown chemicals in normal temperature range
            if temperature < 0:
                return "solid"
            elif temperature > 100:
                return "gas"
            else:
                return "liquid"
                
        transitions = self.phase_transition_temps[chemical]
        freezing = transitions["freezing"]
        boiling = transitions["boiling"]
        
        if temperature <= freezing:
            return "solid"
        elif temperature >= boiling:
            return "gas"
        else:
            return "liquid"
    
    def apply_temperature_effects(self, grid: SpatialGrid, time_step: float,
                                 chemical_params: List[str] = None) -> None:
        """
        Apply temperature effects to chemical parameters across the entire grid.
        
        Args:
            grid: The spatial grid to process
            time_step: Time step in seconds
            chemical_params: List of chemical parameters to process
        """
        # Default to common VOCs if no parameters specified
        if chemical_params is None:
            chemical_params = ["formaldehyde", "benzene", "toluene", "xylene", "voc_total"]
            
        # Process each cell
        for position, cell in grid.iterate_cells():
            temperature = cell.get_parameter("temperature", 25.0)  # Default to 25°C
            
            # Skip if temperature is at standard temp (25°C)
            if abs(temperature - 25.0) < 0.1:
                continue
                
            # Apply temperature effects to each chemical parameter
            for param in chemical_params:
                current_value = cell.get_parameter(param, 0.0)
                
                # Skip if no chemical present
                if current_value <= 0.0:
                    continue
                    
                # Determine chemical name (strip suffixes like _ppb if present)
                chemical = param.split('_')[0]
                
                # Reaction rate adjustment
                reaction_rate = 0.0001 * time_step  # Base degradation rate per second
                adjusted_rate = self.calculate_reaction_rate_adjustment(
                    reaction_rate, temperature)
                
                # Calculate degradation
                degradation = current_value * adjusted_rate
                
                # Volatilization adjustment for emission sources
                if cell.get_parameter(f"{param}_source", 0.0) > 0:
                    base_emission = cell.get_parameter(f"{param}_emission_rate", 0.0)
                    if base_emission > 0:
                        adjusted_emission = self.calculate_volatilization_rate(
                            chemical, temperature, base_emission)
                        # Update emission rate
                        cell.set_parameter(f"{param}_emission_rate", adjusted_emission)
                
                # Apply combined effects
                new_value = max(0.0, current_value - degradation)
                cell.set_parameter(param, new_value)
    
    def apply_temperature_gradient(self, grid: SpatialGrid,
                                  source_positions: List[Tuple[int, int, int]],
                                  source_temperatures: List[float],
                                  ambient_temperature: float = 22.0,
                                  diffusivity: float = 0.1) -> None:
        """
        Apply temperature gradient across the grid based on heat sources.
        
        Args:
            grid: The spatial grid to process
            source_positions: List of heat source positions in grid coordinates
            source_temperatures: List of heat source temperatures (must match source_positions)
            ambient_temperature: Background temperature
            diffusivity: Thermal diffusivity factor (0-1)
        """
        if len(source_positions) != len(source_temperatures):
            raise ValueError("source_positions and source_temperatures must have the same length")
            
        # Create a new grid to store updated temperatures
        new_temps = {}
        
        # Initialize all cells with ambient temperature if they don't have a temperature
        for position, cell in grid.iterate_cells():
            if not cell.has_parameter("temperature"):
                cell.set_parameter("temperature", ambient_temperature)
                
        # Apply heat diffusion
        for position, cell in grid.iterate_cells():
            current_temp = cell.get_parameter("temperature", ambient_temperature)
            
            # Calculate temperature from nearby sources
            source_contribution = 0.0
            for src_pos, src_temp in zip(source_positions, source_temperatures):
                # Calculate distance to source
                distance = sum((a - b) ** 2 for a, b in zip(position, src_pos)) ** 0.5
                
                # Skip if too far away
                if distance > 10:  # Limit calculation radius for efficiency
                    continue
                    
                # Heat falls off with square of distance
                if distance < 0.1:  # Avoid division by zero
                    strength = 1.0
                else:
                    strength = 1.0 / (1.0 + distance ** 2)
                    
                # Add weighted contribution
                temp_diff = src_temp - ambient_temperature
                source_contribution += temp_diff * strength
            
            # Get neighbor temperatures for diffusion
            neighbors = cell.get_all_neighbors()
            neighbor_temp_sum = 0.0
            neighbor_count = 0
            
            for direction, neighbor in neighbors.items():
                if neighbor:
                    neighbor_temp = neighbor.get_parameter("temperature", ambient_temperature)
                    neighbor_temp_sum += neighbor_temp
                    neighbor_count += 1
            
            # Calculate diffusion effect
            if neighbor_count > 0:
                avg_neighbor_temp = neighbor_temp_sum / neighbor_count
                diffusion_effect = (avg_neighbor_temp - current_temp) * diffusivity
            else:
                diffusion_effect = 0.0
            
            # Calculate new temperature
            new_temp = current_temp + diffusion_effect + source_contribution * diffusivity
            
            # Store new temperature
            new_temps[position] = new_temp
        
        # Update all cells with new temperatures
        for position, temp in new_temps.items():
            cell = grid.get_cell(position)
            if cell:
                cell.set_parameter("temperature", temp)


class ThermalSource:
    """Represents a heat source in the environment."""
    
    TYPE_HEATER = "heater"
    TYPE_COOLER = "cooler"
    TYPE_ELECTRONIC = "electronic"
    TYPE_CHEMICAL = "chemical"
    TYPE_FIRE = "fire"
    
    def __init__(self, name: str, position: Tuple[float, float, float], 
                source_type: str, temperature: float, radius: float = 0.5,
                power: float = 1000.0):
        """
        Initialize a thermal source.
        
        Args:
            name: Source identifier
            position: Position in physical space (x, y, z) in meters
            source_type: Type of thermal source
            temperature: Source temperature in Celsius
            radius: Influence radius in meters
            power: Thermal power in watts
        """
        self.name = name
        self.position = position
        self.source_type = source_type
        self.temperature = temperature
        self.radius = radius
        self.power = power
        self.is_active = True
    
    def set_temperature(self, temperature: float) -> None:
        """
        Set the source temperature.
        
        Args:
            temperature: New temperature in Celsius
        """
        self.temperature = temperature
    
    def set_power(self, power: float) -> None:
        """
        Set the source power.
        
        Args:
            power: Thermal power in watts
        """
        self.power = power
    
    def set_active(self, is_active: bool) -> None:
        """
        Set whether the source is active.
        
        Args:
            is_active: True if active, False otherwise
        """
        self.is_active = is_active
    
    def apply_to_grid(self, grid: SpatialGrid) -> None:
        """
        Apply thermal effects to the grid.
        
        Args:
            grid: The spatial grid to apply effects to
        """
        if not self.is_active:
            return
            
        # Convert physical position to grid position
        grid_pos = grid.grid_coordinates(self.position)
        
        # Calculate influence radius in grid cells
        cell_radius = int(self.radius / grid.cell_size) + 1
        
        # Apply temperature to cells within radius
        for x in range(grid_pos[0] - cell_radius, grid_pos[0] + cell_radius + 1):
            for y in range(grid_pos[1] - cell_radius, grid_pos[1] + cell_radius + 1):
                for z in range(grid_pos[2] - cell_radius, grid_pos[2] + cell_radius + 1):
                    pos = (x, y, z)
                    
                    # Skip if outside grid
                    if not grid.is_position_valid(pos):
                        continue
                        
                    # Get distance from source
                    cell = grid.get_cell(pos)
                    phys_pos = grid.physical_coordinates(pos)
                    distance = sum((a - b) ** 2 for a, b in zip(self.position, phys_pos)) ** 0.5
                    
                    # Skip if outside influence radius
                    if distance > self.radius:
                        continue
                        
                    # Calculate temperature effect based on distance
                    current_temp = cell.get_parameter("temperature", 22.0)
                    
                    # Temperature effect decreases with square of distance
                    distance_factor = 1.0 - min(1.0, (distance / self.radius) ** 2)
                    
                    # Calculate weighted average with current temperature
                    # Closer to source = more weight to source temperature
                    weight = distance_factor * (self.power / 1000.0)  # Normalize power
                    new_temp = current_temp * (1.0 - weight) + self.temperature * weight
                    
                    # Update cell temperature
                    cell.set_parameter("temperature", new_temp)


class ThermalManager:
    """Manages thermal sources and effects in the environment."""
    
    def __init__(self, grid: SpatialGrid):
        """
        Initialize the thermal manager.
        
        Args:
            grid: The spatial grid to manage thermal effects for
        """
        self.grid = grid
        self.thermal_effects = ThermalEffects()
        self.thermal_sources = {}  # Dict mapping source names to ThermalSource objects
        
        # Environment settings
        self.ambient_temperature = 22.0  # Default ambient temperature in Celsius
        self.enable_chemical_effects = True  # Whether to apply thermal effects to chemicals
        self.enable_sources = True  # Whether to apply thermal sources
    
    def add_source(self, source: ThermalSource) -> None:
        """
        Add a thermal source to the manager.
        
        Args:
            source: The thermal source to add
        """
        self.thermal_sources[source.name] = source
    
    def remove_source(self, source_name: str) -> None:
        """
        Remove a thermal source from the manager.
        
        Args:
            source_name: Name of the source to remove
        """
        if source_name in self.thermal_sources:
            del self.thermal_sources[source_name]
    
    def set_ambient_temperature(self, temperature: float) -> None:
        """
        Set the ambient temperature.
        
        Args:
            temperature: Ambient temperature in Celsius
        """
        self.ambient_temperature = temperature
    
    def initialize_temperatures(self) -> None:
        """
        Initialize temperatures across the grid with ambient temperature.
        """
        for position, cell in self.grid.iterate_cells():
            # Only set if not already set
            if not cell.has_parameter("temperature"):
                cell.set_parameter("temperature", self.ambient_temperature)
    
    def update_sources(self) -> None:
        """
        Apply all thermal sources to the grid.
        """
        if not self.enable_sources:
            return
            
        for source in self.thermal_sources.values():
            if source.is_active:
                source.apply_to_grid(self.grid)
    
    def update_temperature_diffusion(self, diffusivity: float = 0.1) -> None:
        """
        Update temperature diffusion across the grid.
        
        Args:
            diffusivity: Thermal diffusivity factor (0-1)
        """
        # Collect source positions and temperatures
        source_positions = []
        source_temperatures = []
        
        for source in self.thermal_sources.values():
            if source.is_active:
                grid_pos = self.grid.grid_coordinates(source.position)
                source_positions.append(grid_pos)
                source_temperatures.append(source.temperature)
                
        # Apply temperature gradient
        self.thermal_effects.apply_temperature_gradient(
            self.grid, source_positions, source_temperatures,
            self.ambient_temperature, diffusivity)
    
    def update_chemical_effects(self, time_step: float, 
                              chemical_params: List[str] = None) -> None:
        """
        Update thermal effects on chemical parameters.
        
        Args:
            time_step: Time step in seconds
            chemical_params: List of chemical parameters to process
        """
        if not self.enable_chemical_effects:
            return
            
        self.thermal_effects.apply_temperature_effects(
            self.grid, time_step, chemical_params)
    
    def update(self, time_step: float, chemical_params: List[str] = None) -> None:
        """
        Update all thermal effects for a time step.
        
        Args:
            time_step: Time step in seconds
            chemical_params: List of chemical parameters to process
        """
        # Apply sources first
        self.update_sources()
        
        # Then diffuse temperature
        self.update_temperature_diffusion()
        
        # Finally apply effects to chemicals
        self.update_chemical_effects(time_step, chemical_params)
