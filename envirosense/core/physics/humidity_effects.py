"""
EnviroSense Physics Engine - Humidity Effects Module

This module provides classes for modeling how humidity affects physical and chemical
processes in environmental simulations, including particulate behavior, chemical reactions,
and material interactions.
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Optional, Union, Any
import logging
from .space import SpatialGrid, GridCell

logger = logging.getLogger(__name__)


class HumidityEffects:
    """Models how humidity affects physical and chemical processes in the environment."""
    
    # Standard atmospheric conditions
    STANDARD_TEMP = 25.0  # Standard temperature (°C)
    STANDARD_RH = 50.0  # Standard relative humidity (%)
    
    # Hygroscopic growth factors for common particulate types
    # Format: {RH: growth_factor} where RH is in percent
    HYGROSCOPIC_GROWTH = {
        "pm2.5_urban": {
            30: 1.0,
            50: 1.1,
            70: 1.25,
            80: 1.4,
            90: 1.65,
            95: 2.0,
            99: 2.5
        },
        "pm2.5_rural": {
            30: 1.0,
            50: 1.05,
            70: 1.15,
            80: 1.3,
            90: 1.5,
            95: 1.8,
            99: 2.2
        },
        "pm10_urban": {
            30: 1.0,
            50: 1.08,
            70: 1.2,
            80: 1.3,
            90: 1.5,
            95: 1.8,
            99: 2.2
        },
        "dust": {
            30: 1.0,
            50: 1.03,
            70: 1.08,
            80: 1.12,
            90: 1.2,
            95: 1.3,
            99: 1.5
        },
        "pollen": {
            30: 1.0,
            50: 1.02,
            70: 1.05,
            80: 1.1,
            90: 1.18,
            95: 1.25,
            99: 1.4
        }
    }
    
    # Chemical reaction adjustment factors based on humidity
    # Format: {RH: adjustment_factor} where RH is in percent
    REACTION_RH_ADJUSTMENTS = {
        "voc_degradation": {
            0: 0.8,
            30: 0.9,
            50: 1.0,
            70: 1.1,
            90: 1.3,
            99: 1.5
        },
        "formaldehyde_emission": {
            0: 0.5,
            30: 0.8,
            50: 1.0,
            70: 1.2,
            90: 1.4,
            99: 1.6
        },
        "ozone_formation": {
            0: 0.7,
            30: 0.9,
            50: 1.0,
            70: 0.9,
            90: 0.7,
            99: 0.5
        },
        "no2_formation": {
            0: 0.8,
            30: 0.9,
            50: 1.0,
            70: 1.1,
            90: 1.2,
            99: 1.3
        }
    }
    
    def __init__(self):
        """Initialize humidity effects model."""
        # Material moisture absorption parameters
        # Format: [max water content (%), absorption rate]
        self.material_moisture_params = {
            "drywall": [30.0, 0.05],
            "wood": [40.0, 0.03],
            "concrete": [15.0, 0.02],
            "brick": [20.0, 0.01],
            "carpet": [60.0, 0.08],
            "foam_insulation": [10.0, 0.01],
            "fabric": [70.0, 0.1]
        }
    
    def calculate_absolute_humidity(self, temperature: float, relative_humidity: float) -> float:
        """
        Calculate absolute humidity from temperature and relative humidity.
        
        Args:
            temperature: Temperature in Celsius
            relative_humidity: Relative humidity percentage (0-100)
            
        Returns:
            Absolute humidity in g/m³
        """
        # Saturation vapor pressure using Magnus formula
        svp = 6.1078 * 10**((7.5 * temperature) / (237.3 + temperature))
        
        # Actual vapor pressure
        vp = svp * (relative_humidity / 100.0)
        
        # Absolute humidity formula
        abs_humidity = (217.0 * vp) / (temperature + 273.15)
        
        return abs_humidity
    
    def calculate_relative_humidity(self, temperature: float, absolute_humidity: float) -> float:
        """
        Calculate relative humidity from temperature and absolute humidity.
        
        Args:
            temperature: Temperature in Celsius
            absolute_humidity: Absolute humidity in g/m³
            
        Returns:
            Relative humidity percentage (0-100)
        """
        # Saturation vapor pressure using Magnus formula
        svp = 6.1078 * 10**((7.5 * temperature) / (237.3 + temperature))
        
        # Actual vapor pressure from absolute humidity
        vp = (absolute_humidity * (temperature + 273.15)) / 217.0
        
        # Relative humidity
        rh = (vp / svp) * 100.0
        
        return min(100.0, max(0.0, rh))
    
    def calculate_dew_point(self, temperature: float, relative_humidity: float) -> float:
        """
        Calculate dew point from temperature and relative humidity.
        
        Args:
            temperature: Temperature in Celsius
            relative_humidity: Relative humidity percentage (0-100)
            
        Returns:
            Dew point temperature in Celsius
        """
        # Parameters for Magnus formula
        a = 17.27
        b = 237.7
        
        # Intermediate term
        gamma = ((a * temperature) / (b + temperature)) + math.log(relative_humidity / 100.0)
        
        # Dew point formula
        dew_point = (b * gamma) / (a - gamma)
        
        return dew_point
    
    def calculate_hygroscopic_growth(self, particle_type: str, initial_size: float,
                                   relative_humidity: float) -> float:
        """
        Calculate hygroscopic particle growth due to humidity.
        
        Args:
            particle_type: Type of particle (from HYGROSCOPIC_GROWTH)
            initial_size: Initial particle diameter in micrometers
            relative_humidity: Relative humidity percentage (0-100)
            
        Returns:
            New particle diameter in micrometers
        """
        # Default to urban PM2.5 if particle type not recognized
        if particle_type not in self.HYGROSCOPIC_GROWTH:
            logger.warning(f"Unknown particle type: {particle_type}. Using pm2.5_urban.")
            particle_type = "pm2.5_urban"
            
        growth_data = self.HYGROSCOPIC_GROWTH[particle_type]
        
        # Find growth factor by interpolating between known RH points
        rh_points = sorted(growth_data.keys())
        
        # Clamp RH to valid range
        rh = min(max(rh_points), max(0.0, relative_humidity))
        
        # Find bracketing points
        if rh <= min(rh_points):
            growth_factor = growth_data[min(rh_points)]
        elif rh >= max(rh_points):
            growth_factor = growth_data[max(rh_points)]
        else:
            # Find two closest RH points
            lower_rh = max(point for point in rh_points if point <= rh)
            upper_rh = min(point for point in rh_points if point >= rh)
            
            # Interpolate
            if upper_rh == lower_rh:
                growth_factor = growth_data[lower_rh]
            else:
                lower_gf = growth_data[lower_rh]
                upper_gf = growth_data[upper_rh]
                t = (rh - lower_rh) / (upper_rh - lower_rh)
                growth_factor = lower_gf + t * (upper_gf - lower_gf)
        
        # Apply growth factor to initial size
        new_size = initial_size * growth_factor
        
        return new_size
    
    def calculate_humidity_dependent_settling(self, particle_type: str, particle_size: float,
                                            density: float, relative_humidity: float,
                                            temperature: float = 25.0) -> float:
        """
        Calculate settling velocity of particles accounting for humidity effects.
        
        Args:
            particle_type: Type of particle (from HYGROSCOPIC_GROWTH)
            particle_size: Particle diameter in micrometers
            density: Particle density in kg/m³
            relative_humidity: Relative humidity percentage (0-100)
            temperature: Temperature in Celsius
            
        Returns:
            Settling velocity in m/s
        """
        # Apply hygroscopic growth
        adjusted_size = self.calculate_hygroscopic_growth(
            particle_type, particle_size, relative_humidity)
        
        # Stokes' Law for settling velocity
        # v = (rho * d^2 * g) / (18 * mu)
        # where:
        # - rho is particle density (kg/m³)
        # - d is particle diameter (m)
        # - g is gravitational acceleration (9.81 m/s²)
        # - mu is dynamic viscosity of air (kg/m·s)
        
        # Convert diameter to meters
        diameter_m = adjusted_size * 1e-6
        
        # Calculate air viscosity, which varies with temperature
        # Sutherland's formula for air viscosity
        mu_ref = 1.827e-5  # Reference viscosity at 18°C
        T_ref = 291.15  # Reference temperature (18°C in K)
        S = 120  # Sutherland's constant for air
        T = temperature + 273.15  # Convert to K
        
        # Calculate viscosity
        mu = mu_ref * (T / T_ref)**(3/2) * (T_ref + S) / (T + S)
        
        # Calculate settling velocity
        g = 9.81  # m/s²
        settling_velocity = (density * (diameter_m**2) * g) / (18 * mu)
        
        return settling_velocity
    
    def calculate_reaction_adjustment(self, reaction_type: str, relative_humidity: float) -> float:
        """
        Calculate adjustment factor for chemical reactions based on humidity.
        
        Args:
            reaction_type: Type of reaction (from REACTION_RH_ADJUSTMENTS)
            relative_humidity: Relative humidity percentage (0-100)
            
        Returns:
            Adjustment factor for reaction rate
        """
        # Default to VOC degradation if reaction type not recognized
        if reaction_type not in self.REACTION_RH_ADJUSTMENTS:
            logger.warning(f"Unknown reaction type: {reaction_type}. Using voc_degradation.")
            reaction_type = "voc_degradation"
            
        adjustment_data = self.REACTION_RH_ADJUSTMENTS[reaction_type]
        
        # Find adjustment by interpolating between known RH points
        rh_points = sorted(adjustment_data.keys())
        
        # Clamp RH to valid range
        rh = min(100.0, max(0.0, relative_humidity))
        
        # Find bracketing points
        if rh <= min(rh_points):
            adjustment = adjustment_data[min(rh_points)]
        elif rh >= max(rh_points):
            adjustment = adjustment_data[max(rh_points)]
        else:
            # Find two closest RH points
            lower_rh = max(point for point in rh_points if point <= rh)
            upper_rh = min(point for point in rh_points if point >= rh)
            
            # Interpolate
            if upper_rh == lower_rh:
                adjustment = adjustment_data[lower_rh]
            else:
                lower_adj = adjustment_data[lower_rh]
                upper_adj = adjustment_data[upper_rh]
                t = (rh - lower_rh) / (upper_rh - lower_rh)
                adjustment = lower_adj + t * (upper_adj - lower_adj)
        
        return adjustment
    
    def calculate_material_moisture(self, material: str, ambient_rh: float, 
                                   exposure_time: float) -> float:
        """
        Calculate moisture content in materials based on ambient humidity.
        
        Args:
            material: Material type (from material_moisture_params)
            ambient_rh: Ambient relative humidity percentage (0-100)
            exposure_time: Exposure time in hours
            
        Returns:
            Material moisture content percentage
        """
        if material not in self.material_moisture_params:
            logger.warning(f"Unknown material: {material}. Using drywall.")
            material = "drywall"
            
        max_content, absorption_rate = self.material_moisture_params[material]
        
        # Equilibrium moisture content (EMC) based on RH
        # This is a simplified model; actual EMC curves are more complex
        if ambient_rh < 30:
            equilibrium = max_content * 0.2
        elif ambient_rh < 60:
            equilibrium = max_content * 0.4
        elif ambient_rh < 80:
            equilibrium = max_content * 0.7
        else:
            equilibrium = max_content
            
        # Approach equilibrium exponentially
        # M(t) = Meq * (1 - e^(-k*t))
        moisture_content = equilibrium * (1 - math.exp(-absorption_rate * exposure_time))
        
        return moisture_content
    
    def calculate_condensation(self, temperature: float, relative_humidity: float,
                             surface_temp: float) -> float:
        """
        Calculate condensation rate on a surface.
        
        Args:
            temperature: Air temperature in Celsius
            relative_humidity: Relative humidity percentage (0-100)
            surface_temp: Surface temperature in Celsius
            
        Returns:
            Condensation rate in g/m²/hour (0 if no condensation)
        """
        # Calculate dew point
        dew_point = self.calculate_dew_point(temperature, relative_humidity)
        
        # Check if surface temperature is below dew point
        if surface_temp >= dew_point:
            return 0.0  # No condensation
        
        # Calculate water vapor pressure
        svp_air = 6.1078 * 10**((7.5 * temperature) / (237.3 + temperature))
        actual_vp = svp_air * (relative_humidity / 100.0)
        
        # Calculate saturation vapor pressure at surface temperature
        svp_surface = 6.1078 * 10**((7.5 * surface_temp) / (237.3 + surface_temp))
        
        # Vapor pressure difference drives condensation
        vp_difference = actual_vp - svp_surface
        
        # Simplified condensation model
        # Actual mass transfer would depend on air flow and other factors
        condensation_rate = max(0.0, vp_difference * 0.1 * (dew_point - surface_temp))
        
        return condensation_rate * 3600  # Convert to g/m²/hour
    
    def apply_humidity_effects(self, grid: SpatialGrid, time_step: float,
                             particulate_params: List[str] = None,
                             chemical_params: List[str] = None) -> None:
        """
        Apply humidity effects to parameters across the entire grid.
        
        Args:
            grid: The spatial grid to process
            time_step: Time step in seconds
            particulate_params: List of particulate parameters to process
            chemical_params: List of chemical parameters to process
        """
        # Default to common parameters if none specified
        if particulate_params is None:
            particulate_params = ["pm2.5", "pm10", "dust", "pollen"]
            
        if chemical_params is None:
            chemical_params = ["formaldehyde", "voc_total", "ozone", "no2"]
            
        # Process each cell
        for position, cell in grid.iterate_cells():
            # Get cell humidity and temperature
            rh = cell.get_parameter("relative_humidity", 50.0)  # Default to 50%
            temperature = cell.get_parameter("temperature", 25.0)  # Default to 25°C
            
            # Skip if at standard conditions
            if abs(rh - 50.0) < 1.0 and abs(temperature - 25.0) < 0.1:
                continue
                
            # 1. Process particulate parameters
            for param in particulate_params:
                current_value = cell.get_parameter(param, 0.0)
                
                # Skip if no particulates present
                if current_value <= 0.0:
                    continue
                    
                # Determine particle type (map parameter to types in HYGROSCOPIC_GROWTH)
                if param == "pm2.5":
                    particle_type = "pm2.5_urban"
                elif param == "pm10":
                    particle_type = "pm10_urban"
                else:
                    particle_type = param
                    
                # Particles can grow due to humidity
                # This affects concentration (µg/m³) because we're counting the water
                if rh > 50.0:  # Only apply growth above standard RH
                    growth_factor = self.calculate_hygroscopic_growth(
                        particle_type, 1.0, rh) / self.calculate_hygroscopic_growth(
                            particle_type, 1.0, 50.0)
                            
                    # Apply growth to concentration
                    adjusted_value = current_value * growth_factor
                    cell.set_parameter(param, adjusted_value)
                
                # Humidity affects settling rate, which alters vertical distribution
                # This is a complex effect better handled in a separate method for
                # vertical transport, but we use a simplified approach here
                if "settling_velocity" in cell.get_parameter_names():
                    base_settling = cell.get_parameter(f"{param}_settling_velocity", 0.0)
                    if base_settling > 0:
                        # Assume standard particle density
                        density = 1000.0  # kg/m³, a simplification
                        
                        # Assume standard particle size
                        if param == "pm2.5":
                            size = 2.5
                        elif param == "pm10":
                            size = 10.0
                        elif param == "dust":
                            size = 15.0
                        elif param == "pollen":
                            size = 30.0
                        else:
                            size = 5.0  # Default
                            
                        # Calculate humidity-adjusted settling velocity
                        adjusted_settling = self.calculate_humidity_dependent_settling(
                            particle_type, size, density, rh, temperature)
                            
                        # Update settling velocity
                        cell.set_parameter(f"{param}_settling_velocity", adjusted_settling)
            
            # 2. Process chemical parameters
            for param in chemical_params:
                current_value = cell.get_parameter(param, 0.0)
                
                # Skip if no chemical present
                if current_value <= 0.0:
                    continue
                    
                # Determine reaction type
                if param == "formaldehyde":
                    reaction_type = "formaldehyde_emission"
                elif param == "ozone":
                    reaction_type = "ozone_formation"
                elif param == "no2":
                    reaction_type = "no2_formation"
                else:
                    reaction_type = "voc_degradation"
                    
                # Apply humidity adjustment to reaction rates
                base_rate = 0.0001 * time_step  # Base reaction rate per second
                rh_factor = self.calculate_reaction_adjustment(reaction_type, rh)
                
                # Calculate change in concentration
                if reaction_type.endswith("_emission"):
                    # For emission processes, higher rate means more chemical produced
                    if cell.get_parameter(f"{param}_source", 0.0) > 0:
                        base_emission = cell.get_parameter(f"{param}_emission_rate", 0.0)
                        adjusted_emission = base_emission * rh_factor
                        cell.set_parameter(f"{param}_emission_rate", adjusted_emission)
                else:
                    # For degradation processes, higher rate means more chemical consumed
                    degradation = current_value * base_rate * rh_factor
                    new_value = max(0.0, current_value - degradation)
                    cell.set_parameter(param, new_value)
            
            # 3. Calculate and update absolute humidity
            abs_humidity = self.calculate_absolute_humidity(temperature, rh)
            cell.set_parameter("absolute_humidity", abs_humidity)
            
            # 4. Calculate and update dew point
            dew_point = self.calculate_dew_point(temperature, rh)
            cell.set_parameter("dew_point", dew_point)
    
    def apply_material_moisture_effects(self, grid: SpatialGrid, 
                                      materials_map: Dict[Tuple[int, int, int], str],
                                      time_step: float) -> None:
        """
        Apply material moisture effects based on ambient humidity.
        
        Args:
            grid: The spatial grid to process
            materials_map: Dictionary mapping grid positions to material types
            time_step: Time step in seconds
        """
        # Convert time step to hours
        time_hours = time_step / 3600.0
        
        # Process materials
        for position, material in materials_map.items():
            cell = grid.get_cell(position)
            if not cell:
                continue
                
            # Get current moisture content or initialize it
            current_moisture = cell.get_parameter(f"{material}_moisture", 0.0)
            
            # Get ambient humidity
            rh = cell.get_parameter("relative_humidity", 50.0)
            
            # Calculate new moisture content
            target_moisture = self.calculate_material_moisture(material, rh, 100.0)  # Equilibrium
            
            # Approach target moisture content gradually
            moisture_change_rate = 0.01  # Rate of approach per hour
            moisture_change = (target_moisture - current_moisture) * moisture_change_rate * time_hours
            new_moisture = current_moisture + moisture_change
            
            # Update moisture content
            cell.set_parameter(f"{material}_moisture", new_moisture)
            
            # Special effects for high moisture
            if new_moisture > 25.0:  # Arbitrary threshold for high moisture
                # Increased formaldehyde emission from materials like particle board
                if material in ["plywood", "particle_board", "mdf"]:
                    base_emission = cell.get_parameter("formaldehyde_emission_rate", 0.0)
                    moisture_factor = 1.0 + ((new_moisture - 25.0) / 25.0)  # 1.0 - 2.0 factor
                    cell.set_parameter("formaldehyde_emission_rate", base_emission * moisture_factor)
                    
                # Increased mold risk
                mold_risk = max(0.0, min(1.0, (new_moisture - 25.0) / 25.0))
                cell.set_parameter("mold_risk", mold_risk)
    
    def apply_condensation_effects(self, grid: SpatialGrid, 
                                 surface_positions: Dict[Tuple[int, int, int], str],
                                 time_step: float) -> None:
        """
        Apply condensation effects on surfaces.
        
        Args:
            grid: The spatial grid to process
            surface_positions: Dictionary mapping grid positions to surface types
            time_step: Time step in seconds
        """
        # Convert time step to hours
        time_hours = time_step / 3600.0
        
        # Process surfaces
        for position, surface_type in surface_positions.items():
            cell = grid.get_cell(position)
            if not cell:
                continue
                
            # Get ambient conditions
            temperature = cell.get_parameter("temperature", 25.0)
            rh = cell.get_parameter("relative_humidity", 50.0)
            
            # Get surface temperature (usually different from air temperature)
            # This could be calculated based on thermal properties, but we use a simple approximation
            if "surface_temperature" in cell.get_parameter_names():
                surface_temp = cell.get_parameter("surface_temperature", temperature)
            else:
                # Approximation: surfaces are slightly cooler than air
                surface_temp = temperature - 1.0
                
            # Calculate condensation rate
            condensation_rate = self.calculate_condensation(temperature, rh, surface_temp)
            
            # Skip if no condensation
            if condensation_rate <= 0.0:
                continue
                
            # Update condensation amount
            current_condensation = cell.get_parameter(f"{surface_type}_condensation", 0.0)
            new_condensation = current_condensation + (condensation_rate * time_hours)
            cell.set_parameter(f"{surface_type}_condensation", new_condensation)
            
            # Secondary effects of condensation
            
            # 1. Increase local humidity near the surface
            # When water evaporates from condensation, it increases local humidity
            evaporation_rate = min(new_condensation, 0.1 * time_hours)  # g/h
            if evaporation_rate > 0:
                # Remove evaporated water from condensation
                cell.set_parameter(f"{surface_type}_condensation", new_condensation - evaporation_rate)
                
                # Increase local humidity
                volume = 0.125  # m³ (estimate of local volume)
                humidity_increase = evaporation_rate / volume  # g/m³
                
                abs_humidity = cell.get_parameter("absolute_humidity", 0.0)
                new_abs_humidity = abs_humidity + humidity_increase
                cell.set_parameter("absolute_humidity", new_abs_humidity)
                
                # Update relative humidity based on new absolute humidity
                new_rh = self.calculate_relative_humidity(temperature, new_abs_humidity)
                cell.set_parameter("relative_humidity", new_rh)
                
            # 2. Condensation can facilitate chemical reactions
            if new_condensation > 1.0:  # Threshold for sufficient condensation
                # Enhance certain chemical reactions on wet surfaces
                for param in ["formaldehyde", "no2", "so2"]:
                    if cell.has_parameter(param):
                        current_value = cell.get_parameter(param, 0.0)
                        if current_value > 0:
                            # Wet deposition factor
                            deposition_rate = 0.05 * time_hours  # 5% per hour
                            reduction = current_value * deposition_rate
                            cell.set_parameter(param, current_value - reduction)


class HumidityManager:
    """Manages humidity conditions and effects in the environment."""
    
    def __init__(self, grid: SpatialGrid):
        """
        Initialize the humidity manager.
        
        Args:
            grid: The spatial grid to manage humidity effects for
        """
        self.grid = grid
        self.humidity_effects = HumidityEffects()
        
        # Environment settings
        self.ambient_relative_humidity = 50.0  # Default ambient RH in percent
        self.enable_particulate_effects = True
        self.enable_chemical_effects = True
        self.enable_material_effects = True
        
        # Tracking for materials and surfaces
        self.materials_map = {}  # Dict mapping positions to materials
        self.surface_positions = {}  # Dict mapping positions to surface types
    
    def set_ambient_humidity(self, relative_humidity: float) -> None:
        """
        Set the ambient relative humidity.
        
        Args:
            relative_humidity: Relative humidity percentage (0-100)
        """
        self.ambient_relative_humidity = max(0.0, min(100.0, relative_humidity))
    
    def register_material(self, position: Tuple[int, int, int], material: str) -> None:
        """
        Register a material at a grid position.
        
        Args:
            position: Grid position (x, y, z)
            material: Material type
        """
        self.materials_map[position] = material
    
    def register_surface(self, position: Tuple[int, int, int], surface_type: str) -> None:
        """
        Register a surface at a grid position.
        
        Args:
            position: Grid position (x, y, z)
            surface_type: Surface type
        """
        self.surface_positions[position] = surface_type
    
    def initialize_humidity(self) -> None:
        """
        Initialize humidity across the grid with ambient humidity.
        """
        for position, cell in self.grid.iterate_cells():
            # Only set if not already set
            if not cell.has_parameter("relative_humidity"):
                cell.set_parameter("relative_humidity", self.ambient_relative_humidity)
                
                # Also initialize absolute humidity based on temperature
                temperature = cell.get_parameter("temperature", 25.0)
                abs_humidity = self.humidity_effects.calculate_absolute_humidity(
                    temperature, self.ambient_relative_humidity)
                cell.set_parameter("absolute_humidity", abs_humidity)
                
                # Initialize dew point
                dew_point = self.humidity_effects.calculate_dew_point(
                    temperature, self.ambient_relative_humidity)
                cell.set_parameter("dew_point", dew_point)
    
    def update_humidity_distributions(self, sources: List[Tuple[Tuple[int, int, int], float]],
                                    diffusivity: float = 0.1) -> None:
        """
        Update humidity distribution across the grid.
        
        Args:
            sources: List of (position, emission_rate) tuples for humidity sources
            diffusivity: Humidity diffusion factor (0-1)
        """
        # Create temporary storage for new values
        new_values = {}
        
        # Process each cell
        for position, cell in self.grid.iterate_cells():
            current_abs_humidity = cell.get_parameter("absolute_humidity", 0.0)
            
            # Calculate source contributions
            source_contribution = 0.0
            for src_pos, emission in sources:
                # Calculate distance to source
                distance = sum((a - b) ** 2 for a, b in zip(position, src_pos)) ** 0.5
                
                # Skip if too far away
                if distance > 10:  # Limit calculation radius for efficiency
                    continue
                    
                # Effect decreases with square of distance
                if distance < 0.1:  # Avoid division by zero
                    strength = 1.0
                else:
                    strength = 1.0 / (1.0 + distance ** 2)
                    
                # Add weighted contribution
                source_contribution += emission * strength
            
            # Get neighbor humidities for diffusion
            neighbors = cell.get_all_neighbors()
            neighbor_humidity_sum = 0.0
            neighbor_count = 0
            
            for direction, neighbor in neighbors.items():
                if neighbor:
                    neighbor_humidity = neighbor.get_parameter("absolute_humidity", 0.0)
                    neighbor_humidity_sum += neighbor_humidity
                    neighbor_count += 1
            
            # Calculate diffusion effect
            if neighbor_count > 0:
                avg_neighbor_humidity = neighbor_humidity_sum / neighbor_count
                diffusion_effect = (avg_neighbor_humidity - current_abs_humidity) * diffusivity
            else:
                diffusion_effect = 0.0
            
            # Calculate new absolute humidity
            new_abs_humidity = current_abs_humidity + diffusion_effect + source_contribution * diffusivity
            
            # Store new humidity
            new_values[position] = new_abs_humidity
        
        # Update all cells with new absolute humidity values
        for position, abs_humidity in new_values.items():
            cell = self.grid.get_cell(position)
            if cell:
                cell.set_parameter("absolute_humidity", abs_humidity)
                
                # Update relative humidity based on temperature and new absolute humidity
                temperature = cell.get_parameter("temperature", 25.0)
                new_rh = self.humidity_effects.calculate_relative_humidity(temperature, abs_humidity)
                cell.set_parameter("relative_humidity", new_rh)
                
                # Update dew point
                dew_point = self.humidity_effects.calculate_dew_point(temperature, new_rh)
                cell.set_parameter("dew_point", dew_point)
    
    def update_humidity_effects(self, time_step: float) -> None:
        """
        Update humidity effects for a time step.
        
        Args:
            time_step: Time step in seconds
        """
        # Skip if effects are disabled
        if not (self.enable_particulate_effects or self.enable_chemical_effects):
            return
            
        # Determine which parameters to process
        particulate_params = ["pm2.5", "pm10", "dust", "pollen"] if self.enable_particulate_effects else []
        chemical_params = ["formaldehyde", "voc_total", "ozone", "no2"] if self.enable_chemical_effects else []
        
        # Apply humidity effects
        self.humidity_effects.apply_humidity_effects(
            self.grid, time_step, particulate_params, chemical_params)
    
    def update_material_effects(self, time_step: float) -> None:
        """
        Update material moisture effects for a time step.
        
        Args:
            time_step: Time step in seconds
        """
        if not self.enable_material_effects or not self.materials_map:
            return
            
        # Apply material moisture effects
        self.humidity_effects.apply_material_moisture_effects(
            self.grid, self.materials_map, time_step)
    
    def update_condensation_effects(self, time_step: float) -> None:
        """
        Update condensation effects for a time step.
        
        Args:
            time_step: Time step in seconds
        """
        if not self.enable_material_effects or not self.surface_positions:
            return
            
        # Apply condensation effects
        self.humidity_effects.apply_condensation_effects(
            self.grid, self.surface_positions, time_step)
    
    def update(self, time_step: float, humidity_sources: List[Tuple[Tuple[int, int, int], float]] = None) -> None:
        """
        Update all humidity effects for a time step.
        
        Args:
            time_step: Time step in seconds
            humidity_sources: Optional list of (position, emission_rate) tuples for humidity sources
        """
        # Update humidity distribution first
        if humidity_sources:
            self.update_humidity_distributions(humidity_sources)
            
        # Then update effects based on current humidity
        self.update_humidity_effects(time_step)
        self.update_material_effects(time_step)
        self.update_condensation_effects(time_step)
