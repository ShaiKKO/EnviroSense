"""
Environmental parameter generators for EnviroSense testing.

This module provides data generators for realistic environmental parameters such as
temperature, humidity, air quality, atmospheric pressure, and other environmental
conditions. These generators can be used to simulate real-world environments with
realistic patterns, trends, and variations.
"""

import datetime
import math
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Union

from envirosense.testing.framework import DataGenerator, TestScenario


# Define environmental parameter defaults and ranges
PARAMETER_DEFINITIONS = {
    "temperature": {
        "unit": "°C",
        "default_range": (-10, 40),
        "typical_indoor_range": (18, 25),
        "typical_outdoor_range": (-5, 35),
        "seasonal_variation": True,
        "diurnal_variation": True,
        "indoor_outdoor_difference": True,
        "typical_rate_of_change": 0.5,  # °C per hour under normal conditions
        "noise_level": 0.2,  # Standard deviation
    },
    "humidity": {
        "unit": "%",
        "default_range": (0, 100),
        "typical_indoor_range": (30, 60),
        "typical_outdoor_range": (20, 90),
        "seasonal_variation": True,
        "diurnal_variation": True,
        "indoor_outdoor_difference": True,
        "typical_rate_of_change": 2.0,  # % per hour under normal conditions
        "noise_level": 1.0,  # Standard deviation
    },
    "atmospheric_pressure": {
        "unit": "hPa",
        "default_range": (970, 1030),
        "typical_range": (990, 1020),
        "seasonal_variation": True,
        "diurnal_variation": False,
        "indoor_outdoor_difference": False,
        "typical_rate_of_change": 0.5,  # hPa per hour during weather changes
        "noise_level": 0.1,  # Standard deviation
    },
    "co2": {
        "unit": "ppm",
        "default_range": (300, 5000),
        "typical_outdoor_range": (350, 450),
        "typical_indoor_range": (400, 1500),
        "seasonal_variation": False,
        "diurnal_variation": True,
        "indoor_outdoor_difference": True,
        "typical_rate_of_change": 20,  # ppm per hour with occupancy changes
        "noise_level": 10,  # Standard deviation
    },
    "tvoc": {
        "unit": "ppb",
        "default_range": (0, 10000),
        "typical_range": (50, 1000),
        "seasonal_variation": False,
        "diurnal_variation": True,
        "indoor_outdoor_difference": True,
        "typical_rate_of_change": 50,  # ppb per hour with activity changes
        "noise_level": 20,  # Standard deviation
    },
    "pm2_5": {
        "unit": "μg/m³",
        "default_range": (0, 500),
        "typical_outdoor_clean_range": (0, 12),
        "typical_outdoor_polluted_range": (12, 100),
        "typical_indoor_range": (0, 50),
        "seasonal_variation": True,
        "diurnal_variation": True,
        "indoor_outdoor_difference": True,
        "typical_rate_of_change": 2.0,  # μg/m³ per hour
        "noise_level": 1.0,  # Standard deviation
    },
    "pm10": {
        "unit": "μg/m³",
        "default_range": (0, 1000),
        "typical_outdoor_clean_range": (0, 20),
        "typical_outdoor_polluted_range": (20, 150),
        "typical_indoor_range": (0, 75),
        "seasonal_variation": True,
        "diurnal_variation": True,
        "indoor_outdoor_difference": True,
        "typical_rate_of_change": 3.0,  # μg/m³ per hour
        "noise_level": 1.5,  # Standard deviation
    },
    "ozone": {
        "unit": "ppb",
        "default_range": (0, 200),
        "typical_range": (20, 100),
        "seasonal_variation": True,
        "diurnal_variation": True,
        "indoor_outdoor_difference": True,
        "typical_rate_of_change": 1.0,  # ppb per hour
        "noise_level": 0.5,  # Standard deviation
    },
    "no2": {
        "unit": "ppb",
        "default_range": (0, 200),
        "typical_range": (5, 60),
        "seasonal_variation": True,
        "diurnal_variation": True,
        "indoor_outdoor_difference": True,
        "typical_rate_of_change": 1.0,  # ppb per hour
        "noise_level": 0.5,  # Standard deviation
    },
    "light_level": {
        "unit": "lux",
        "default_range": (0, 100000),
        "typical_indoor_range": (100, 1000),
        "typical_outdoor_range": (1000, 50000),
        "seasonal_variation": True,
        "diurnal_variation": True,
        "indoor_outdoor_difference": True,
        "typical_rate_of_change": 1000,  # lux per hour with cloud coverage changes
        "noise_level": 50,  # Standard deviation
    },
    "noise_level": {
        "unit": "dB",
        "default_range": (0, 120),
        "typical_indoor_quiet_range": (30, 50),
        "typical_indoor_active_range": (50, 75),
        "typical_outdoor_urban_range": (60, 90),
        "seasonal_variation": False,
        "diurnal_variation": True,
        "indoor_outdoor_difference": True,
        "typical_rate_of_change": 5.0,  # dB per hour with activity changes
        "noise_level": 2.0,  # Standard deviation
    },
    "wind_speed": {
        "unit": "m/s",
        "default_range": (0, 30),
        "typical_range": (0, 10),
        "seasonal_variation": True,
        "diurnal_variation": True,
        "indoor_outdoor_difference": False,
        "typical_rate_of_change": 0.5,  # m/s per hour
        "noise_level": 0.2,  # Standard deviation
    },
    "wind_direction": {
        "unit": "degrees",
        "default_range": (0, 359),
        "seasonal_variation": False,
        "diurnal_variation": False,
        "indoor_outdoor_difference": False,
        "typical_rate_of_change": 10,  # degrees per hour
        "noise_level": 5,  # Standard deviation
    },
    "solar_radiation": {
        "unit": "W/m²",
        "default_range": (0, 1200),
        "typical_range": (0, 1000),
        "seasonal_variation": True,
        "diurnal_variation": True,
        "indoor_outdoor_difference": False,
        "typical_rate_of_change": 100,  # W/m² per hour with cloud coverage changes
        "noise_level": 20,  # Standard deviation
    },
    "uv_index": {
        "unit": "index",
        "default_range": (0, 12),
        "typical_range": (0, 10),
        "seasonal_variation": True,
        "diurnal_variation": True,
        "indoor_outdoor_difference": False,
        "typical_rate_of_change": 0.5,  # index value per hour
        "noise_level": 0.1,  # Standard deviation
    },
    "soil_moisture": {
        "unit": "%",
        "default_range": (0, 100),
        "typical_range": (10, 80),
        "seasonal_variation": True,
        "diurnal_variation": False,
        "indoor_outdoor_difference": False,
        "typical_rate_of_change": 1.0,  # % per hour during precipitation
        "noise_level": 0.5,  # Standard deviation
    },
    "soil_temperature": {
        "unit": "°C",
        "default_range": (-10, 40),
        "typical_range": (5, 30),
        "seasonal_variation": True,
        "diurnal_variation": True,
        "indoor_outdoor_difference": False,
        "typical_rate_of_change": 0.2,  # °C per hour
        "noise_level": 0.1,  # Standard deviation
    }
}


# Default location characteristics
LOCATION_CHARACTERISTICS = {
    "urban": {
        "temperature_modifier": 2.0,  # Urban heat island effect
        "humidity_modifier": -5.0,  # Generally drier in urban areas
        "pm2_5_modifier": 1.5,  # Higher particulate matter
        "pm10_modifier": 1.5,  # Higher particulate matter
        "co2_modifier": 1.3,  # Higher CO2 levels
        "no2_modifier": 2.0,  # Higher NO2 from traffic
        "ozone_modifier": 1.2,  # Can be higher in urban areas
        "light_pollution": True,
        "noise_modifier": 1.5  # Higher noise levels
    },
    "suburban": {
        "temperature_modifier": 1.0,  # Baseline
        "humidity_modifier": 0.0,  # Baseline
        "pm2_5_modifier": 1.0,  # Baseline
        "pm10_modifier": 1.0,  # Baseline
        "co2_modifier": 1.0,  # Baseline
        "no2_modifier": 1.0,  # Baseline
        "ozone_modifier": 1.0,  # Baseline
        "light_pollution": True,
        "noise_modifier": 1.0  # Baseline
    },
    "rural": {
        "temperature_modifier": 0.0,  # No urban heat island
        "humidity_modifier": 5.0,  # Often more humid
        "pm2_5_modifier": 0.7,  # Lower particulate matter
        "pm10_modifier": 0.7,  # Lower particulate matter
        "co2_modifier": 0.8,  # Lower CO2 levels
        "no2_modifier": 0.5,  # Lower NO2 levels
        "ozone_modifier": 0.9,  # Can be lower in rural areas
        "light_pollution": False,
        "noise_modifier": 0.6  # Lower noise levels
    },
    "coastal": {
        "temperature_modifier": -1.0,  # Cooler near water
        "humidity_modifier": 15.0,  # Much higher humidity
        "pm2_5_modifier": 0.8,  # Sea spray but less industrial
        "pm10_modifier": 0.9,  # Sea spray but less industrial
        "co2_modifier": 0.9,  # Generally lower
        "no2_modifier": 0.8,  # Generally lower
        "ozone_modifier": 1.1,  # Can be higher in sunny coastal areas
        "light_pollution": False,
        "noise_modifier": 1.2  # Wave noise
    },
    "desert": {
        "temperature_modifier": 5.0,  # Much hotter
        "humidity_modifier": -20.0,  # Much drier
        "pm2_5_modifier": 1.2,  # Dust can increase particulates
        "pm10_modifier": 1.5,  # Dust can increase particulates
        "co2_modifier": 0.9,  # Generally lower
        "no2_modifier": 0.7,  # Generally lower
        "ozone_modifier": 1.3,  # Higher due to strong sunlight
        "light_pollution": False,
        "noise_modifier": 0.5  # Very quiet
    },
    "mountain": {
        "temperature_modifier": -3.0,  # Cooler at altitude
        "humidity_modifier": -10.0,  # Drier at altitude
        "pm2_5_modifier": 0.6,  # Cleaner air
        "pm10_modifier": 0.6,  # Cleaner air
        "co2_modifier": 0.9,  # Generally lower
        "no2_modifier": 0.6,  # Generally lower
        "ozone_modifier": 1.2,  # Can be higher at altitude
        "light_pollution": False,
        "noise_modifier": 0.4  # Very quiet
    },
    "forest": {
        "temperature_modifier": -1.0,  # Cooler under canopy
        "humidity_modifier": 10.0,  # Higher humidity
        "pm2_5_modifier": 0.5,  # Filtered by vegetation
        "pm10_modifier": 0.5,  # Filtered by vegetation
        "co2_modifier": 0.7,  # Lower due to vegetation
        "no2_modifier": 0.6,  # Lower due to vegetation
        "ozone_modifier": 0.8,  # Lower under canopy
        "light_pollution": False,
        "noise_modifier": 0.7  # Natural sounds
    },
    "industrial": {
        "temperature_modifier": 3.0,  # Warmer due to industrial activity
        "humidity_modifier": -5.0,  # Often drier
        "pm2_5_modifier": 2.5,  # Much higher particulates
        "pm10_modifier": 2.5,  # Much higher particulates
        "co2_modifier": 1.8,  # Higher CO2 emissions
        "no2_modifier": 2.5,  # Higher NO2 emissions
        "ozone_modifier": 1.4,  # Higher due to industrial processes
        "light_pollution": True,
        "noise_modifier": 2.0  # Much louder
    }
}


# Seasonal and monthly pattern weights
SEASONAL_PATTERNS = {
    "northern_hemisphere": {
        "spring": {"months": [3, 4, 5], "temperature": 0.4, "humidity": 0.6, "precipitation": 0.7},
        "summer": {"months": [6, 7, 8], "temperature": 1.0, "humidity": 0.8, "precipitation": 0.5},
        "autumn": {"months": [9, 10, 11], "temperature": 0.5, "humidity": 0.7, "precipitation": 0.6},
        "winter": {"months": [12, 1, 2], "temperature": 0.0, "humidity": 0.5, "precipitation": 0.8}
    },
    "southern_hemisphere": {
        "spring": {"months": [9, 10, 11], "temperature": 0.4, "humidity": 0.6, "precipitation": 0.7},
        "summer": {"months": [12, 1, 2], "temperature": 1.0, "humidity": 0.8, "precipitation": 0.5},
        "autumn": {"months": [3, 4, 5], "temperature": 0.5, "humidity": 0.7, "precipitation": 0.6},
        "winter": {"months": [6, 7, 8], "temperature": 0.0, "humidity": 0.5, "precipitation": 0.8}
    },
    "equatorial": {
        "wet_season": {"months": [1, 2, 3, 4, 5, 6], "temperature": 0.8, "humidity": 0.9, "precipitation": 0.9},
        "dry_season": {"months": [7, 8, 9, 10, 11, 12], "temperature": 0.9, "humidity": 0.6, "precipitation": 0.3}
    }
}


class EnvironmentalParameterGenerator(DataGenerator):
    """
    Generator for realistic environmental parameter time series.
    
    This generator creates realistic patterns of environmental parameters such as
    temperature, humidity, air quality, etc., accounting for time-of-day variations,
    seasonal patterns, trends, and location characteristics.
    """
    
    def __init__(self):
        """Initialize the environmental parameter generator with default parameters."""
        super().__init__()
        
        # Set default parameters
        self.parameters.update({
            'parameter_type': 'temperature',    # The environmental parameter to generate
            'start_time': datetime.datetime.now(),  # When to start the time series
            'duration_hours': 24,               # Duration of time series to generate
            'time_step_minutes': 5,             # Time resolution
            'location_type': 'suburban',        # Type of location (urban, rural, etc.)
            'season': None,                     # Season (auto-detected from start_time if None)
            'climate_zone': 'temperate',        # Climate zone affects baselines
            'hemisphere': 'northern',           # Northern or southern hemisphere
            'indoor': False,                    # Whether this is an indoor or outdoor reading
            'building_type': 'residential',     # For indoor parameters: type of building
            'occupancy_pattern': 'standard',    # For indoor parameters: occupancy pattern
            'weather_events': [],               # List of weather events during the period
            'add_noise': True,                  # Whether to add realistic noise
            'random_seed': None                 # Seed for reproducibility
        })
    
    def _get_season(self, date: datetime.datetime, hemisphere: str) -> str:
        """
        Determine the season based on date and hemisphere.
        
        Args:
            date: The date to get season for
            hemisphere: 'northern' or 'southern'
            
        Returns:
            Season name ('spring', 'summer', 'autumn', 'winter', or for equatorial:
            'wet_season', 'dry_season')
        """
        month = date.month
        
        if hemisphere == 'northern':
            if month in [3, 4, 5]:
                return 'spring'
            elif month in [6, 7, 8]:
                return 'summer'
            elif month in [9, 10, 11]:
                return 'autumn'
            else:  # month in [12, 1, 2]
                return 'winter'
        elif hemisphere == 'southern':
            if month in [9, 10, 11]:
                return 'spring'
            elif month in [12, 1, 2]:
                return 'summer'
            elif month in [3, 4, 5]:
                return 'autumn'
            else:  # month in [6, 7, 8]
                return 'winter'
        elif hemisphere == 'equatorial':
            if month in [1, 2, 3, 4, 5, 6]:
                return 'wet_season'
            else:
                return 'dry_season'
        else:
            raise ValueError(f"Invalid hemisphere: {hemisphere}")
    
    def _get_parameter_range(self, parameter_type: str, location_type: str, season: str, 
                           indoor: bool, climate_zone: str) -> Tuple[float, float]:
        """
        Determine the appropriate range for a parameter.
        
        Args:
            parameter_type: Type of environmental parameter
            location_type: Type of location (urban, rural, etc.)
            season: Current season
            indoor: Whether this is indoor or outdoor
            climate_zone: Climate zone
            
        Returns:
            Tuple of (min_value, max_value)
        """
        # Get base range for parameter
        if parameter_type not in PARAMETER_DEFINITIONS:
            raise ValueError(f"Invalid parameter type: {parameter_type}")
        
        param_def = PARAMETER_DEFINITIONS[parameter_type]
        
        # Start with default range
        min_val, max_val = param_def["default_range"]
        
        # Adjust for indoor/outdoor
        if indoor and "typical_indoor_range" in param_def:
            min_val, max_val = param_def["typical_indoor_range"]
        elif not indoor and "typical_outdoor_range" in param_def:
            min_val, max_val = param_def["typical_outdoor_range"]
        
        # Adjust for location type
        if location_type in LOCATION_CHARACTERISTICS:
            loc_char = LOCATION_CHARACTERISTICS[location_type]
            
            # Apply location-specific modifiers
            if parameter_type == "temperature" and "temperature_modifier" in loc_char:
                modifier = loc_char["temperature_modifier"]
                min_val += modifier
                max_val += modifier
            elif parameter_type == "humidity" and "humidity_modifier" in loc_char:
                modifier = loc_char["humidity_modifier"]
                min_val += modifier
                max_val += modifier
                min_val = max(0, min_val)
                max_val = min(100, max_val)
            elif parameter_type in ["pm2_5", "pm10"] and f"{parameter_type}_modifier" in loc_char:
                modifier = loc_char[f"{parameter_type}_modifier"]
                min_val *= modifier
                max_val *= modifier
            elif parameter_type in ["co2", "no2", "ozone"] and f"{parameter_type}_modifier" in loc_char:
                modifier = loc_char[f"{parameter_type}_modifier"]
                min_val *= modifier
                max_val *= modifier
        
        # Adjust for climate zone
        if climate_zone == "tropical":
            if parameter_type == "temperature":
                min_val = max(18, min_val)
                max_val = max(30, max_val)
            elif parameter_type == "humidity":
                min_val = max(60, min_val)
                max_val = max(90, max_val)
        elif climate_zone == "arid":
            if parameter_type == "temperature":
                min_val += 5
                max_val += 10
            elif parameter_type == "humidity":
                min_val = max(10, min_val - 20)
                max_val = max(30, max_val - 30)
        elif climate_zone == "polar":
            if parameter_type == "temperature":
                min_val = min(-5, min_val - 15)
                max_val = min(10, max_val - 15)
        
        # Adjust for season
        if season in ["summer", "wet_season"] and parameter_type == "temperature":
            min_val += 5
            max_val += 5
        elif season == "winter" and parameter_type == "temperature":
            min_val -= 10
            max_val -= 10
        
        return (min_val, max_val)
    
    def _apply_diurnal_pattern(self, hour: int, parameter_type: str, indoor: bool) -> float:
        """
        Calculate diurnal (daily) pattern multiplier.
        
        Args:
            hour: Hour of the day (0-23)
            parameter_type: Type of environmental parameter
            indoor: Whether this is indoor or outdoor
            
        Returns:
            Multiplier value (0-1)
        """
        if parameter_type not in PARAMETER_DEFINITIONS:
            return 0.5  # Default mid-range
        
        param_def = PARAMETER_DEFINITIONS[parameter_type]
        
        # Check if this parameter has diurnal variation
        if not param_def.get("diurnal_variation", False):
            return 0.5  # No variation, use mid-range
        
        # Different patterns for different parameters
        if parameter_type == "temperature":
            # Temperature peaks around 14:00, lowest around 5:00
            if indoor:
                # Indoor temperatures have dampened diurnal pattern
                peak_hour = 15  # Slightly delayed compared to outdoor
                return 0.3 + 0.4 * math.sin(math.pi * (hour - peak_hour + 12) / 12)
            else:
                # Outdoor temperature follows solar pattern with delay
                peak_hour = 14
                return 0.1 + 0.8 * math.sin(math.pi * (hour - peak_hour + 12) / 12)
        
        elif parameter_type == "humidity":
            # Humidity is often inverse to temperature
            if indoor:
                # Indoor humidity has dampened pattern
                return 0.7 - 0.3 * math.sin(math.pi * (hour - 14 + 12) / 12)
            else:
                # Outdoor humidity often peaks in early morning
                return 0.9 - 0.6 * math.sin(math.pi * (hour - 14 + 12) / 12)
        
        elif parameter_type in ["co2", "tvoc"]:
            # CO2 and VOCs build up during occupied hours
            if indoor:
                # Peaks during active hours, dips at night
                if 7 <= hour <= 22:
                    return 0.3 + 0.6 * math.sin(math.pi * (hour - 17 + 8) / 14)
                else:
                    return 0.3
            else:
                # Outdoor CO2 has minimal diurnal variation
                return 0.5
        
        elif parameter_type in ["pm2_5", "pm10"]:
            # Particulates often peak during commuting hours
            if indoor:
                # Indoor follows outdoor with dampening and delay
                if 7 <= hour <= 9 or 16 <= hour <= 19:
                    return 0.7
                else:
                    return 0.4
            else:
                # Outdoor peaks during commute hours
                if 7 <= hour <= 9 or 16 <= hour <= 19:
                    return 0.9
                elif 10 <= hour <= 15:
                    return 0.6
                else:
                    return 0.3
        
        elif parameter_type == "ozone":
            # Ozone peaks in afternoon with solar radiation
            return 0.1 + 0.8 * math.sin(math.pi * (hour - 13 + 10) / 14)
        
        elif parameter_type == "light_level":
            # Light follows solar pattern
            if indoor:
                # Indoor light is dampened and depends on occupancy
                if 7 <= hour <= 22:
                    return 0.2 + 0.6 * math.sin(math.pi * (hour - 12 + 6) / 12)
                else:
                    return 0.0  # Dark at night
            else:
                # Outdoor follows solar pattern
                if 6 <= hour <= 18:
                    return math.sin(math.pi * (hour - 12) / 12)
                else:
                    return 0.0  # Dark at night
        
        elif parameter_type == "noise_level":
            # Noise follows human activity
            if indoor:
                # Indoor noise follows occupancy
                if 7 <= hour <= 22:
                    if 7 <= hour <= 9 or 17 <= hour <= 20:
                        return 0.8  # Peak morning and evening
                    else:
                        return 0.5  # Moderate during day
                else:
                    return 0.2  # Quiet at night
            else:
                # Outdoor noise follows human activity
                if 8 <= hour <= 18:
                    return 0.7  # Busy during day
                elif 19 <= hour <= 22:
                    return 0.5  # Moderate evening
                elif 23 <= hour or hour <= 5:
                    return 0.2  # Quiet late night
                else:
                    return 0.4  # Moderate early morning/late evening
        
        else:
            # Generic pattern for other parameters
            return 0.5 + 0.3 * math.sin(math.pi * (hour - 12) / 12)
    
    def _apply_weather_events(self, time_point: datetime.datetime, parameter_type: str, 
                            base_value: float, weather_events: List[Dict[str, Any]]) -> float:
        """
        Modify parameter values based on weather events.
        
        Args:
            time_point: The time point to check
            parameter_type: Type of environmental parameter
            base_value: Current parameter value before weather effects
            weather_events: List of weather event dictionaries
            
        Returns:
            Modified parameter value
        """
        if not weather_events:
            return base_value
        
        # Find any active weather events
        active_events = []
        for event in weather_events:
            start_time = event.get("start_time")
            end_time = event.get("end_time")
            
            if start_time <= time_point <= end_time:
                active_events.append(event)
        
        if not active_events:
            return base_value
        
        # Apply effects of each active event
        modified_value = base_value
        
        for event in active_events:
            event_type = event.get("type", "")
            intensity = event.get("intensity", 1.0)  # 0.0 to 1.0
            
            # Apply appropriate modifications based on event type and parameter
            if event_type == "rain":
                if parameter_type == "humidity":
                    modified_value += 20 * intensity
                elif parameter_type == "temperature":
                    modified_value -= 3 * intensity
                elif parameter_type == "light_level":
                    modified_value *= max(0.2, 1.0 - 0.6 * intensity)
                elif parameter_type == "soil_moisture":
                    modified_value += 30 * intensity
            
            elif event_type == "snow":
                if parameter_type == "temperature":
                    modified_value = min(modified_value, 2 - 5 * intensity)
                elif parameter_type == "humidity":
                    modified_value += 10 * intensity
                elif parameter_type == "light_level":
                    modified_value *= max(0.3, 1.0 - 0.5 * intensity)
            
            elif event_type == "storm":
                if parameter_type == "atmospheric_pressure":
                    modified_value -= 20 * intensity
                elif parameter_type == "wind_speed":
                    modified_value += 15 * intensity
                elif parameter_type == "light_level":
                    modified_value *= max(0.1, 1.0 - 0.8 * intensity)
                elif parameter_type == "humidity":
                    modified_value += 25 * intensity
            
            elif event_type == "heat_wave":
                if parameter_type == "temperature":
                    modified_value += 8 * intensity
                elif parameter_type == "humidity":
                    modified_value -= 15 * intensity
            
            elif event_type == "cold_snap":
                if parameter_type == "temperature":
                    modified_value -= 10 * intensity
            
            elif event_type == "fog":
                if parameter_type == "humidity":
                    modified_value = min(100, modified_value + 30 * intensity)
                elif parameter_type == "light_level":
                    modified_value *= max(0.2, 1.0 - 0.7 * intensity)
                elif parameter_type in ["pm2_5", "pm10"]:
                    modified_value -= modified_value * 0.3 * intensity
            
            elif event_type == "pollution_event":
                if parameter_type in ["pm2_5", "pm10", "ozone", "no2"]:
                    modified_value += modified_value * 0.5 * intensity
                elif parameter_type == "tvoc":
                    modified_value += modified_value * 0.3 * intensity
        
        # Ensure parameters stay within reasonable bounds
        if parameter_type == "humidity":
            modified_value = min(100, max(0, modified_value))
        elif parameter_type in ["pm2_5", "pm10", "co2", "tvoc", "no2", "ozone"]:
            modified_value = max(0, modified_value)
        
        return modified_value
    
    def _generate_time_series(self) -> Dict[str, Any]:
        """
        Generate a time series of environmental parameter values.
        
        Returns:
            Dictionary with time series data
        """
        # Set up parameters
        parameter_type = self.parameters['parameter_type']
        start_time = self.parameters['start_time']
        duration_hours = self.parameters['duration_hours']
        time_step_minutes = self.parameters['time_step_minutes']
        location_type = self.parameters['location_type']
        hemisphere = self.parameters['hemisphere']
        indoor = self.parameters['indoor']
        climate_zone = self.parameters['climate_zone']
        weather_events = self.parameters['weather_events']
        add_noise = self.parameters['add_noise']
        
        # Determine season if not specified
        season = self.parameters['season']
        if season is None:
            season = self._get_season(start_time, hemisphere)
        
        # Get parameter range based on all factors
        min_val, max_val = self._get_parameter_range(
            parameter_type, location_type, season, indoor, climate_zone
        )
        
        # Generate time points
        num_points = int(duration_hours * 60 / time_step_minutes) + 1
        times = []
        values = []
        
        # Get parameter definition for reference
        param_def = PARAMETER_DEFINITIONS.get(parameter_type, {})
        typical_rate_of_change = param_def.get("typical_rate_of_change", 0.1)
        noise_level = param_def.get("noise_level", 0.1)
        
        # Initialize with a reasonable starting value
        current_value = min_val + (max_val - min_val) * 0.5
        
        # Generate each time point
        for i in range(num_points):
            # Calculate current time
            current_time = start_time + datetime.timedelta(minutes=i * time_step_minutes)
            times.append(current_time)
            
            # Apply diurnal pattern
            hour = current_time.hour
            diurnal_factor = self._apply_diurnal_pattern(hour, parameter_type, indoor)
            target_value = min_val + (max_val - min_val) * diurnal_factor
            
            # Calculate value change (smooth transition to target)
            # How much can change in one time step
            max_step_change = typical_rate_of_change * (time_step_minutes / 60.0)
            
            # Move toward target value at limited rate
            value_diff = target_value - current_value
            if abs(value_diff) <= max_step_change:
                current_value = target_value
            else:
                current_value += max_step_change * (1 if value_diff > 0 else -1)
            
            # Apply weather events
            current_value = self._apply_weather_events(
                current_time, parameter_type, current_value, weather_events
            )
            
            # Add noise if requested
            if add_noise and noise_level > 0:
                noise = self.rng.normal(0, noise_level)
                current_value += noise
                
                # Ensure within reasonable bounds
                if parameter_type == "humidity":
                    current_value = min(100, max(0, current_value))
                elif parameter_type in ["pm2_5", "pm10", "co2", "tvoc", "no2", "ozone", "light_level"]:
                    current_value = max(0, current_value)
            
            values.append(current_value)
        
        # Create output dictionary
        unit = PARAMETER_DEFINITIONS.get(parameter_type, {}).get("unit", "")
        
        return {
            'parameter': parameter_type,
            'unit': unit,
            'location_type': location_type,
            'climate_zone': climate_zone,
            'season': season,
            'indoor': indoor,
            'times': times,
            'values': values,
            'min_value': min(values),
            'max_value': max(values),
            'mean_value': sum(values) / len(values),
            'metadata': {
                'start_time': start_time.isoformat(),
                'duration_hours': duration_hours,
                'time_step_minutes': time_step_minutes
            }
        }
    
    def generate(self, scenario: TestScenario, **kwargs) -> Dict[str, Any]:
        """
        Generate environmental parameter data based on scenario.
        
        Args:
            scenario: Test scenario to generate data for
            **kwargs: Additional parameters
            
        Returns:
            Generated environmental data
        """
        # Update parameters from scenario
        for key, value in scenario.parameters.items():
            if key in self.parameters:
                self.parameters[key] = value
        
        # Override with any explicit kwargs
        for key, value in kwargs.items():
            if key in self.parameters:
                self.parameters[key] = value
        
        # Initialize random number generator if needed
        if self.parameters['random_seed'] is not None:
            self.rng = np.random.RandomState(self.parameters['random_seed'])
        else:
            self.rng = np.random.RandomState()
            
        # Generate environmental data
        data = self._generate_time_series()
        
        # Add timestamp
        data['timestamp'] = datetime.datetime.now().isoformat()
        data['scenario_id'] = getattr(scenario, 'id', None)
        
        return data
