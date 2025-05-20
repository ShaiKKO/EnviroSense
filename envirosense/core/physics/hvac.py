"""
EnviroSense Physics Engine - HVAC System Modeling

This module provides classes for modeling HVAC (Heating, Ventilation, and
Air Conditioning) systems in environmental simulations, including air exchange,
filtering, temperature control, and their effects on parameter distribution.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
import logging
from .space import SpatialGrid, GridCell
from .airflow import AirflowModel, VentilationSource
from .geometry import Room, GeometryObject

logger = logging.getLogger(__name__)


class AirFilter:
    """
    Represents an air filter with specific filtration properties for different parameters.
    """
    
    # Common filter types with their MERV ratings
    FILTER_TYPES = {
        "residential_basic": {"merv": 4, "description": "Basic residential filter (MERV 1-4)"},
        "residential_better": {"merv": 8, "description": "Better residential filter (MERV 5-8)"},
        "residential_best": {"merv": 11, "description": "Best residential filter (MERV 9-12)"},
        "commercial": {"merv": 13, "description": "Commercial grade filter (MERV 13-16)"},
        "hepa": {"merv": 17, "description": "HEPA filter (MERV 17+)"},
        "carbon": {"merv": None, "description": "Activated carbon filter (specialized for gases)"},
        "electrostatic": {"merv": None, "description": "Electrostatic precipitator"}
    }
    
    def __init__(self, name: str, filter_type: str, 
                efficiency: Optional[Dict[str, float]] = None):
        """
        Initialize an air filter.
        
        Args:
            name: Filter identifier
            filter_type: Type of filter, one of the FILTER_TYPES keys
            efficiency: Optional custom efficiency dict mapping parameter names to 
                        removal percentages (0-1)
        """
        self.name = name
        
        # Set filter type, defaulting to residential_basic if not recognized
        if filter_type not in self.FILTER_TYPES:
            logger.warning(f"Unknown filter type: {filter_type}. Using residential_basic.")
            filter_type = "residential_basic"
        self.filter_type = filter_type
        self.filter_info = self.FILTER_TYPES[filter_type]
        
        # Set up filter efficiency for different parameters
        self.efficiency = self._get_default_efficiency()
        if efficiency is not None:
            # Override defaults with provided values
            self.efficiency.update(efficiency)
            
        # Track filter condition (0-1, where 1 is clean and 0 is fully clogged)
        self.condition = 1.0
        
        # Filter usage hours tracking for maintenance
        self.usage_hours = 0.0
    
    def _get_default_efficiency(self) -> Dict[str, float]:
        """
        Get default filter efficiency values based on filter type.
        
        Returns:
            Dictionary mapping parameter names to removal percentages (0-1)
        """
        merv = self.filter_info.get("merv")
        
        # Default efficiencies based on MERV rating
        # These values are simplified approximations
        if merv is None:
            # Special filter types with different characteristics
            if self.filter_type == "carbon":
                return {
                    "formaldehyde": 0.9,
                    "benzene": 0.85,
                    "toluene": 0.9,
                    "xylene": 0.9,
                    "voc_total": 0.8,
                    "co": 0.05,
                    "co2": 0.0,
                    "no2": 0.5,
                    "pm10": 0.15,
                    "pm2.5": 0.1
                }
            elif self.filter_type == "electrostatic":
                return {
                    "formaldehyde": 0.1,
                    "benzene": 0.1,
                    "toluene": 0.1,
                    "xylene": 0.1,
                    "voc_total": 0.1,
                    "co": 0.0,
                    "co2": 0.0,
                    "no2": 0.05,
                    "pm10": 0.97,
                    "pm2.5": 0.95
                }
            return {}
        
        # Define efficiency based on MERV rating
        if merv <= 4:
            return {
                "pm10": 0.2,
                "pm2.5": 0.05,
                "pollen": 0.7,
                "dust_mites": 0.15,
                "voc_total": 0.0
            }
        elif merv <= 8:
            return {
                "pm10": 0.35,
                "pm2.5": 0.2,
                "pollen": 0.8,
                "dust_mites": 0.3,
                "voc_total": 0.05
            }
        elif merv <= 12:
            return {
                "pm10": 0.5,
                "pm2.5": 0.35,
                "pollen": 0.9,
                "dust_mites": 0.55,
                "voc_total": 0.1
            }
        elif merv <= 16:
            return {
                "pm10": 0.85,
                "pm2.5": 0.75,
                "pollen": 0.99,
                "dust_mites": 0.9,
                "voc_total": 0.15
            }
        else:  # HEPA (MERV 17+)
            return {
                "pm10": 0.9999,
                "pm2.5": 0.9997,
                "pollen": 0.9999,
                "dust_mites": 0.9995,
                "voc_total": 0.2
            }
    
    def get_efficiency(self, parameter: str) -> float:
        """
        Get the filter efficiency for a specific parameter.
        
        Args:
            parameter: The parameter name
            
        Returns:
            Efficiency value between 0 and 1, adjusted for filter condition
        """
        base_efficiency = self.efficiency.get(parameter, 0.0)
        # Adjust for filter condition - as filter clogs, efficiency for
        # particulates may initially increase but eventually decreases
        adjusted_efficiency = base_efficiency * self.condition
        return adjusted_efficiency
    
    def update_condition(self, hours: float, load_factor: float = 1.0) -> None:
        """
        Update filter condition based on usage time and load.
        
        Args:
            hours: Hours of operation to add
            load_factor: Factor representing pollutant load (higher = faster degradation)
        """
        self.usage_hours += hours
        
        # Simplified model for filter degradation
        # Assumes linear degradation based on usage hours and load
        degradation = hours * load_factor * 0.001  # 0.1% degradation per hour at normal load
        self.condition = max(0.0, self.condition - degradation)
    
    def replace_filter(self) -> None:
        """
        Replace the filter, resetting condition and usage hours.
        """
        self.condition = 1.0
        self.usage_hours = 0.0
    
    def filter_parameter(self, parameter: str, value: float) -> float:
        """
        Calculate new parameter value after passing through this filter.
        
        Args:
            parameter: Parameter name
            value: Current parameter value
            
        Returns:
            Filtered parameter value
        """
        efficiency = self.get_efficiency(parameter)
        return value * (1.0 - efficiency)


class HVACSystem:
    """
    Models a complete HVAC system including ventilation, heating, cooling,
    and filtration components.
    """
    
    # HVAC operating modes
    MODE_OFF = "off"
    MODE_FAN_ONLY = "fan_only"
    MODE_HEAT = "heat"
    MODE_COOL = "cool"
    MODE_AUTO = "auto"
    
    def __init__(self, name: str, grid: SpatialGrid, airflow_model: AirflowModel):
        """
        Initialize an HVAC system.
        
        Args:
            name: System identifier
            grid: The spatial grid for the environment
            airflow_model: The airflow model to use for air movement
        """
        self.name = name
        self.grid = grid
        self.airflow_model = airflow_model
        
        # HVAC components
        self.supply_vents = {}  # Dict mapping vent names to VentilationSource objects
        self.return_vents = {}  # Dict mapping vent names to VentilationSource objects
        self.filters = {}  # Dict mapping filter names to AirFilter objects
        
        # HVAC properties
        self.current_mode = self.MODE_OFF
        self.fan_speed = 0.0  # 0.0 to 1.0
        self.heating_setpoint = 21.0  # Celsius
        self.cooling_setpoint = 24.0  # Celsius
        self.outdoor_air_fraction = 0.2  # Fraction of outdoor air in supply (0-1)
        
        # Performance parameters
        self.heating_capacity = 10.0  # kW
        self.cooling_capacity = 8.0  # kW
        self.fan_max_flow_rate = 0.5  # m³/s
        self.duct_leakage = 0.1  # Fraction of air leaked from ducts (0-1)
        
        # Current state tracking
        self.is_running = False
        self.current_temperature = None
        self.target_temperature = None
        
        # Zones for zoned HVAC systems
        self.zones = {}  # Dict mapping zone names to lists of grid positions
    
    def add_supply_vent(self, vent_name: str, position: Tuple[float, float, float],
                       direction: Tuple[float, float, float],
                       radius: float = 0.15) -> None:
        """
        Add a supply vent to the HVAC system.
        
        Args:
            vent_name: Vent identifier
            position: Position of the vent in physical space (x, y, z) in meters
            direction: Direction of airflow from the vent
            radius: Radius of the vent in meters
        """
        flow_rate = self.fan_max_flow_rate / max(1, len(self.supply_vents) + 1)
        vent = VentilationSource(
            name=vent_name,
            position=position,
            direction=direction,
            flow_rate=flow_rate,
            source_type=VentilationSource.TYPE_INLET,
            radius=radius
        )
        
        self.supply_vents[vent_name] = vent
        self.airflow_model.add_source(vent)
    
    def add_return_vent(self, vent_name: str, position: Tuple[float, float, float],
                       radius: float = 0.2) -> None:
        """
        Add a return vent to the HVAC system.
        
        Args:
            vent_name: Vent identifier
            position: Position of the vent in physical space (x, y, z) in meters
            radius: Radius of the vent in meters
        """
        # Return vents flow inward (negative pressure)
        flow_rate = self.fan_max_flow_rate / max(1, len(self.return_vents) + 1)
        vent = VentilationSource(
            name=vent_name,
            position=position,
            direction=(0, 0, -1),  # Assuming downward for return, actual direction matters less
            flow_rate=flow_rate,
            source_type=VentilationSource.TYPE_OUTLET,
            radius=radius
        )
        
        self.return_vents[vent_name] = vent
        self.airflow_model.add_source(vent)
    
    def add_filter(self, filter_name: str, filter_type: str,
                  efficiency: Optional[Dict[str, float]] = None) -> None:
        """
        Add a filter to the HVAC system.
        
        Args:
            filter_name: Filter identifier
            filter_type: Type of filter (from AirFilter.FILTER_TYPES)
            efficiency: Optional custom efficiency dict
        """
        air_filter = AirFilter(filter_name, filter_type, efficiency)
        self.filters[filter_name] = air_filter
    
    def define_zone(self, zone_name: str, positions: List[Tuple[int, int, int]]) -> None:
        """
        Define a zone for the HVAC system.
        
        Args:
            zone_name: Zone identifier
            positions: List of grid positions included in this zone
        """
        self.zones[zone_name] = positions
    
    def set_mode(self, mode: str) -> None:
        """
        Set the HVAC operating mode.
        
        Args:
            mode: One of the MODE_* constants
        """
        valid_modes = [self.MODE_OFF, self.MODE_FAN_ONLY, 
                      self.MODE_HEAT, self.MODE_COOL, self.MODE_AUTO]
        
        if mode not in valid_modes:
            logger.warning(f"Invalid HVAC mode: {mode}. Using OFF.")
            mode = self.MODE_OFF
            
        self.current_mode = mode
        
        # Update system state based on mode
        if mode == self.MODE_OFF:
            self._set_fan_speed(0.0)
            self.is_running = False
        elif mode == self.MODE_FAN_ONLY:
            self._set_fan_speed(1.0)
            self.is_running = True
        else:
            # For heating, cooling, or auto modes, the system will control
            # based on temperature setpoints, but we set it running initially
            self.is_running = True
            self._set_fan_speed(1.0)
    
    def _set_fan_speed(self, speed: float) -> None:
        """
        Set the fan speed, which affects flow rates of all vents.
        
        Args:
            speed: Fan speed as fraction of maximum (0-1)
        """
        speed = max(0.0, min(1.0, speed))
        self.fan_speed = speed
        
        # Update all vent flow rates
        total_supply_vents = max(1, len(self.supply_vents))
        for vent in self.supply_vents.values():
            flow_rate = self.fan_max_flow_rate * speed / total_supply_vents
            vent.set_flow_rate(flow_rate)
            
        total_return_vents = max(1, len(self.return_vents))
        for vent in self.return_vents.values():
            flow_rate = self.fan_max_flow_rate * speed / total_return_vents
            vent.set_flow_rate(flow_rate)
    
    def set_temperature_setpoints(self, heating: float, cooling: float) -> None:
        """
        Set temperature setpoints for the system.
        
        Args:
            heating: Heating setpoint in Celsius
            cooling: Cooling setpoint in Celsius
        """
        # Ensure cooling setpoint is higher than heating setpoint
        if cooling <= heating:
            logger.warning("Cooling setpoint must be higher than heating setpoint.")
            cooling = heating + 2.0  # Default 2 degree differential
            
        self.heating_setpoint = heating
        self.cooling_setpoint = cooling
    
    def set_outdoor_air_fraction(self, fraction: float) -> None:
        """
        Set the fraction of outdoor air in the supply air.
        
        Args:
            fraction: Fraction of outdoor air (0-1)
        """
        self.outdoor_air_fraction = max(0.0, min(1.0, fraction))
    
    def get_air_exchange_rate(self) -> float:
        """
        Calculate the current air exchange rate in air changes per hour.
        
        Returns:
            Air changes per hour
        """
        if not self.is_running:
            return 0.0
        
        # Calculate total air flow in m³/s
        total_flow = sum(vent.flow_rate for vent in self.supply_vents.values())
        
        # Get room volume in m³
        width, length, height = self.grid.dimensions
        cell_size = self.grid.cell_size
        room_volume = width * length * height * (cell_size ** 3)
        
        # Calculate air changes per hour
        # 1 m³/s flowing into a room = (3600/volume) air changes per hour
        ach = total_flow * 3600 / room_volume
        
        return ach
    
    def get_zone_temperature(self, zone_name: Optional[str] = None) -> float:
        """
        Get the average temperature in a zone or the entire space.
        
        Args:
            zone_name: Optional zone name, or None for entire space
            
        Returns:
            Average temperature in Celsius
        """
        if zone_name is not None and zone_name not in self.zones:
            logger.warning(f"Zone {zone_name} not found.")
            return None
            
        # Get positions to average
        if zone_name is None:
            # Average entire grid
            positions = [pos for pos, _ in self.grid.iterate_cells()]
        else:
            # Average only zone positions
            positions = self.zones[zone_name]
            
        # Sum temperatures
        total_temp = 0.0
        count = 0
        for pos in positions:
            cell = self.grid.get_cell(pos)
            if cell:
                temp = cell.get_parameter("temperature", None)
                if temp is not None:
                    total_temp += temp
                    count += 1
                    
        if count == 0:
            return None
            
        return total_temp / count
    
    def update_temperature_control(self, time_step: float) -> None:
        """
        Update temperature control based on current conditions.
        
        Args:
            time_step: Time step in seconds
        """
        if self.current_mode in [self.MODE_OFF, self.MODE_FAN_ONLY]:
            return
            
        # Get current average temperature
        self.current_temperature = self.get_zone_temperature()
        if self.current_temperature is None:
            return
            
        # Determine if heating or cooling is needed
        if self.current_mode == self.MODE_AUTO:
            if self.current_temperature < self.heating_setpoint:
                active_mode = self.MODE_HEAT
            elif self.current_temperature > self.cooling_setpoint:
                active_mode = self.MODE_COOL
            else:
                # In deadband, so no active heating/cooling, but fan may run
                self._set_fan_speed(0.2)  # Low fan speed for circulation
                return
        else:
            active_mode = self.current_mode
            
        # Apply heating or cooling
        if active_mode == self.MODE_HEAT:
            self.target_temperature = self.heating_setpoint
            self._apply_heating(time_step)
        elif active_mode == self.MODE_COOL:
            self.target_temperature = self.cooling_setpoint
            self._apply_cooling(time_step)
    
    def _apply_heating(self, time_step: float) -> None:
        """
        Apply heating to the space.
        
        Args:
            time_step: Time step in seconds
        """
        if not self.is_running or self.current_temperature >= self.heating_setpoint:
            # No heating needed
            self._set_fan_speed(0.2)  # Low circulation
            return
            
        # Full heating mode
        self._set_fan_speed(1.0)
        
        # Calculate heating delta
        temp_diff = self.heating_setpoint - self.current_temperature
        power_factor = min(1.0, temp_diff / 2.0)  # Scale power based on how far from setpoint
        
        # Apply heating to supply vent locations
        for vent_name, vent in self.supply_vents.items():
            # Convert physical position to grid position
            vent_pos = self.grid.grid_coordinates(vent.position.to_tuple())
            
            # Get surrounding cells within influence radius
            influence_radius = int(vent.radius / self.grid.cell_size) + 1
            
            # Apply temperature increase to cells around vent
            for x in range(vent_pos[0] - influence_radius, vent_pos[0] + influence_radius + 1):
                for y in range(vent_pos[1] - influence_radius, vent_pos[1] + influence_radius + 1):
                    for z in range(vent_pos[2] - influence_radius, vent_pos[2] + influence_radius + 1):
                        pos = (x, y, z)
                        
                        # Skip if outside grid
                        if not self.grid.is_position_valid(pos):
                            continue
                            
                        # Get distance from vent
                        cell = self.grid.get_cell(pos)
                        phys_pos = self.grid.physical_coordinates(pos)
                        distance = sum((a - b) ** 2 for a, b in zip(vent.position.to_tuple(), phys_pos)) ** 0.5
                        
                        # Skip if outside influence radius
                        if distance > vent.radius * 2:
                            continue
                            
                        # Calculate heating effect based on distance and power
                        current_temp = cell.get_parameter("temperature", self.current_temperature)
                        distance_factor = max(0, 1 - (distance / (vent.radius * 2)))
                        delta_temp = (self.heating_capacity * power_factor * distance_factor * time_step) / 500.0
                        
                        # Apply temperature increase
                        new_temp = current_temp + delta_temp
                        cell.set_parameter("temperature", new_temp)
    
    def _apply_cooling(self, time_step: float) -> None:
        """
        Apply cooling to the space.
        
        Args:
            time_step: Time step in seconds
        """
        if not self.is_running or self.current_temperature <= self.cooling_setpoint:
            # No cooling needed
            self._set_fan_speed(0.2)  # Low circulation
            return
            
        # Full cooling mode
        self._set_fan_speed(1.0)
        
        # Calculate cooling delta
        temp_diff = self.current_temperature - self.cooling_setpoint
        power_factor = min(1.0, temp_diff / 2.0)  # Scale power based on how far from setpoint
        
        # Apply cooling to supply vent locations
        for vent_name, vent in self.supply_vents.items():
            # Convert physical position to grid position
            vent_pos = self.grid.grid_coordinates(vent.position.to_tuple())
            
            # Get surrounding cells within influence radius
            influence_radius = int(vent.radius / self.grid.cell_size) + 1
            
            # Apply temperature decrease to cells around vent
            for x in range(vent_pos[0] - influence_radius, vent_pos[0] + influence_radius + 1):
                for y in range(vent_pos[1] - influence_radius, vent_pos[1] + influence_radius + 1):
                    for z in range(vent_pos[2] - influence_radius, vent_pos[2] + influence_radius + 1):
                        pos = (x, y, z)
                        
                        # Skip if outside grid
                        if not self.grid.is_position_valid(pos):
                            continue
                            
                        # Get distance from vent
                        cell = self.grid.get_cell(pos)
                        phys_pos = self.grid.physical_coordinates(pos)
                        distance = sum((a - b) ** 2 for a, b in zip(vent.position.to_tuple(), phys_pos)) ** 0.5
                        
                        # Skip if outside influence radius
                        if distance > vent.radius * 2:
                            continue
                            
                        # Calculate cooling effect based on distance and power
                        current_temp = cell.get_parameter("temperature", self.current_temperature)
                        distance_factor = max(0, 1 - (distance / (vent.radius * 2)))
                        delta_temp = (self.cooling_capacity * power_factor * distance_factor * time_step) / 500.0
                        
                        # Apply temperature decrease
                        new_temp = current_temp - delta_temp
                        cell.set_parameter("temperature", new_temp)
    
    def filter_return_air(self, parameters: List[str]) -> None:
        """
        Apply filtration to return air parameters.
        
        Args:
            parameters: List of parameter names to filter
        """
        if not self.is_running or not self.filters:
            return
            
        # Apply filtering around return vents
        for vent_name, vent in self.return_vents.items():
            # Convert physical position to grid position
            vent_pos = self.grid.grid_coordinates(vent.position.to_tuple())
            
            # Get surrounding cells within influence radius
            influence_radius = int(vent.radius / self.grid.cell_size) + 1
            
            # Apply filtration to cells around vent
            for x in range(vent_pos[0] - influence_radius, vent_pos[0] + influence_radius + 1):
                for y in range(vent_pos[1] - influence_radius, vent_pos[1] + influence_radius + 1):
                    for z in range(vent_pos[2] - influence_radius, vent_pos[2] + influence_radius + 1):
                        pos = (x, y, z)
                        
                        # Skip if outside grid
                        if not self.grid.is_position_valid(pos):
                            continue
                            
                        # Get distance from vent
                        cell = self.grid.get_cell(pos)
                        phys_pos = self.grid.physical_coordinates(pos)
                        distance = sum((a - b) ** 2 for a, b in zip(vent.position.to_tuple(), phys_pos)) ** 0.5
                        
                        # Skip if outside influence radius
                        if distance > vent.radius * 2:
                            continue
                            
                        # Calculate filtration effect based on distance from vent
                        # Closer to the vent = more air passing through filter
                        distance_factor = max(0, 1 - (distance / (vent.radius * 2)))
                        filtration_factor = distance_factor * self.fan_speed
                        
                        # Apply filtration to each parameter
                        for param in parameters:
                            current_value = cell.get_parameter(param, 0.0)
                            
                            if current_value <= 0.0:
                                continue
                                
                            # Apply each filter in series
                            filtered_value = current_value
                            for air_filter in self.filters.values():
                                # Apply filter based on distance and fan speed
                                full_effect = air_filter.filter_parameter(param, filtered_value)
                                # Scale effect by distance and fan speed
                                partial_effect = filtered_value - ((filtered_value - full_effect) * filtration_factor)
                                filtered_value = partial_effect
                                
                            # Update cell parameter
                            cell.set_parameter(param, filtered_value)
    
    def update_system(self, time_step: float, parameters: List[str]) -> None:
        """
        Update the HVAC system for a time step.
        
        Args:
            time_step: Time step in seconds
            parameters: List of parameter names to process
        """
        # Skip if system is off
        if not self.is_running:
            return
            
        # Update temperature control
        self.update_temperature_control(time_step)
        
        # Filter return air
        self.filter_return_air(parameters)
        
        # Introduce outdoor air
        if self.outdoor_air_fraction > 0:
            self._apply_outdoor_air_mixing(parameters)
            
        # Update filter condition
        for air_filter in self.filters.values():
            air_filter.update_condition(time_step / 3600.0)  # Convert seconds to hours
    
    def _apply_outdoor_air_mixing(self, parameters: List[str]) -> None:
        """
        Apply mixing of outdoor air with return air.
        
        Args:
            parameters: List of parameter names to process
        """
        if self.outdoor_air_fraction <= 0:
            return
            
        # Apply outdoor air mixing at supply vents
        for vent_name, vent in self.supply_vents.items():
            # Convert physical position to grid position
            vent_pos = self.grid.grid_coordinates(vent.position.to_tuple())
            
            # Skip if position is invalid
            if not self.grid.is_position_valid(vent_pos):
                continue
                
            # Get surrounding cells within influence radius
            influence_radius = int(vent.radius / self.grid.cell_size) + 1
            
            # Use default outdoor parameter values (could be replaced with actual outdoor values)
            outdoor_values = {
                "temperature": 20.0,  # Default outdoor temperature (°C)
                "relative_humidity": 50.0,  # Default outdoor humidity (%)
                "pm2.5": 10.0,  # Default outdoor PM2.5 (μg/m³)
                "pm10": 20.0,  # Default outdoor PM10 (μg/m³)
                "co2": 400.0,  # Default outdoor CO2 (ppm)
                "co": 0.1,  # Default outdoor CO (ppm)
                "no2": 0.02,  # Default outdoor NO2 (ppm)
                "o3": 0.03,  # Default outdoor O3 (ppm)
                "formaldehyde": 0.0,  # Default outdoor formaldehyde (ppm)
                "benzene": 0.0,  # Default outdoor benzene (ppm)
                "toluene": 0.0,  # Default outdoor toluene (ppm)
                "voc_total": 0.05  # Default outdoor total VOCs (ppm)
            }
            
            # Apply mixing to cells around vent
            for x in range(vent_pos[0] - influence_radius, vent_pos[0] + influence_radius + 1):
                for y in range(vent_pos[1] - influence_radius, vent_pos[1] + influence_radius + 1):
                    for z in range(vent_pos[2] - influence_radius, vent_pos[2] + influence_radius + 1):
                        pos = (x, y, z)
                        
                        # Skip if outside grid
                        if not self.grid.is_position_valid(pos):
                            continue
                            
                        # Get distance from vent
                        cell = self.grid.get_cell(pos)
                        phys_pos = self.grid.physical_coordinates(pos)
                        distance = sum((a - b) ** 2 for a, b in zip(vent.position.to_tuple(), phys_pos)) ** 0.5
                        
                        # Skip if outside influence radius
                        if distance > vent.radius * 2:
                            continue
                            
                        # Calculate mixing effect based on distance from vent
                        distance_factor = max(0, 1 - (distance / (vent.radius * 2)))
                        mixing_factor = distance_factor * self.fan_speed * self.outdoor_air_fraction
                        
                        # Apply outdoor air mixing to each parameter
                        for param in parameters:
                            if param not in outdoor_values:
                                continue
                                
                            current_value = cell.get_parameter(param, 0.0)
                            outdoor_value = outdoor_values[param]
                            
                            # Mix indoor and outdoor air
                            mixed_value = current_value * (1.0 - mixing_factor) + outdoor_value * mixing_factor
                            
                            # Update cell parameter
                            cell.set_parameter(param, mixed_value)
