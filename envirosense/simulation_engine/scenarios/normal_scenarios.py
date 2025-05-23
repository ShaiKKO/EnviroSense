"""
This module will contain implementations for normal operation simulation scenarios,
all inheriting from BaseScenario. These scenarios are designed to generate
baseline data, test sensor responses to typical environmental changes, and
provide negative samples for ML training.
"""

import math # Added for sinusoidal calculations
from typing import Dict, Any, Optional, List, Literal, Union # Added List, Literal, Union

from pydantic import BaseModel, Field, validator

from .base import BaseScenario, ScenarioComplexity
# from envirosense.simulation_engine.physics_orchestrator import Environment3DOrchestrator # Example import

class DiurnalCycleParams(BaseModel):
    """
    Parameters for configuring the DiurnalCycleScenario.
    """
    min_temp_celsius: float = Field(
        default=10.0,
        description="Minimum daily temperature in Celsius."
    )
    max_temp_celsius: float = Field(
        default=25.0,
        description="Maximum daily temperature in Celsius."
    )
    temp_phase_offset_hours: float = Field(
        default=-2.0,
        description="Phase offset for temperature cycle in hours. E.g., -2.0 means temperature peaks around 14:00 (2 PM) if solar noon is 12:00."
    )
    max_solar_intensity_w_m2: float = Field(
        default=1000.0,
        ge=0,
        description="Maximum solar intensity at solar noon in Watts per square meter."
    )
    solar_phase_offset_hours: float = Field(
        default=0.0,
        description="Phase offset for solar intensity cycle in hours relative to midnight. E.g., 0.0 means solar intensity peaks at 12:00 noon."
    )
    min_humidity_percent: float = Field(
        default=40.0,
        ge=0,
        le=100,
        description="Minimum daily relative humidity in percent."
    )
    max_humidity_percent: float = Field(
        default=80.0,
        ge=0,
        le=100,
        description="Maximum daily relative humidity in percent."
    )
    humidity_phase_offset_hours: float = Field(
        default=10.0, # Typically humidity is higher in early morning, inverse to temp
        description="Phase offset for humidity cycle in hours. E.g., 10.0 might mean humidity peaks around 4 AM if temp peaks at 2 PM."
    )

    @validator('max_temp_celsius')
    def check_max_temp_greater_than_min(cls, v, values):
        if 'min_temp_celsius' in values and v < values['min_temp_celsius']:
            raise ValueError("max_temp_celsius must be greater than or equal to min_temp_celsius")
        return v

    @validator('max_humidity_percent')
    def check_max_humidity_greater_than_min(cls, v, values):
        if 'min_humidity_percent' in values and v < values['min_humidity_percent']:
            raise ValueError("max_humidity_percent must be greater than or equal to min_humidity_percent")
        return v
    
    class Config:
        extra = "forbid"


class DiurnalCycleScenario(BaseScenario):
    def __init__(self, scenario_id: str, name: Optional[str] = "Diurnal Cycle",
                 description: Optional[str] = "Simulates typical daily environmental changes (temperature, humidity, solar radiation).",
                 expected_duration_seconds: Optional[float] = 86400.0, # 24 hours
                 difficulty_level: ScenarioComplexity = ScenarioComplexity.LOW,
                 min_temp_celsius: float = 10.0,
                 max_temp_celsius: float = 25.0,
                 temp_phase_offset_hours: float = -2.0,
                 max_solar_intensity_w_m2: float = 1000.0,
                 solar_phase_offset_hours: float = 0.0,
                 min_humidity_percent: float = 40.0,
                 max_humidity_percent: float = 80.0,
                 humidity_phase_offset_hours: float = 10.0,
                 **kwargs): # Added **kwargs to catch any other base params
        
        # Pass through common parameters to BaseScenario
        # Note: difficulty_level is passed directly if it's part of kwargs or handled by BaseScenario
        # We are explicitly listing specific params for DiurnalCycleScenario here.
        # Any other params intended for BaseScenario should be in kwargs.
        super().__init__(scenario_id=scenario_id, name=name, description=description,
                         category="normal_operation_environmental",
                         difficulty_level=difficulty_level, # This will be passed to BaseScenario
                         expected_duration_seconds=expected_duration_seconds,
                         **kwargs) # Pass remaining kwargs to BaseScenario

        # Consolidate specific params into the Pydantic model
        param_dict = {
            "min_temp_celsius": min_temp_celsius,
            "max_temp_celsius": max_temp_celsius,
            "temp_phase_offset_hours": temp_phase_offset_hours,
            "max_solar_intensity_w_m2": max_solar_intensity_w_m2,
            "solar_phase_offset_hours": solar_phase_offset_hours,
            "min_humidity_percent": min_humidity_percent,
            "max_humidity_percent": max_humidity_percent,
            "humidity_phase_offset_hours": humidity_phase_offset_hours
        }
        self.params = DiurnalCycleParams(**param_dict)

    def _get_specific_params(self) -> Dict[str, Any]:
        """Returns the scenario-specific parameters as a dictionary."""
        return self.params.model_dump(mode='python')

    def _calculate_current_values(self) -> Dict[str, float]:
        """Calculates current temperature, solar intensity, and humidity based on time of day."""
        seconds_in_day = 86400.0
        current_day_seconds = self.current_time_seconds % seconds_in_day

        # Temperature calculation
        temp_angle_rad = ((current_day_seconds / seconds_in_day) * 2 * math.pi) + \
                         ((self.params.temp_phase_offset_hours / 24.0) * 2 * math.pi)
        temp_range = self.params.max_temp_celsius - self.params.min_temp_celsius
        current_temp = self.params.min_temp_celsius + (temp_range / 2.0) * (1 - math.cos(temp_angle_rad))

        # Solar intensity calculation
        solar_angle_rad = ((current_day_seconds / seconds_in_day) * 2 * math.pi) + \
                          ((self.params.solar_phase_offset_hours / 24.0) * 2 * math.pi)
        solar_intensity_factor = (1 - math.cos(solar_angle_rad)) / 2.0 # Ranges 0 to 1
        current_solar_intensity = self.params.max_solar_intensity_w_m2 * solar_intensity_factor
        # Ensure solar intensity is 0 during "night"
        # Using a simplified check: if the sun would be below horizon for a noon-peaking cycle
        time_fraction_day_centered_noon = (current_day_seconds / seconds_in_day) - 0.5 # -0.5 (midnight) to 0.5 (next midnight)
        if math.cos(time_fraction_day_centered_noon * 2 * math.pi) < 0: # Negative cosine part means "night" for solar
             current_solar_intensity = 0.0
        
        # Humidity calculation (e.g., inversely related to temperature or with its own phase)
        # For simplicity, let's make it have its own sinusoidal cycle
        humidity_angle_rad = ((current_day_seconds / seconds_in_day) * 2 * math.pi) + \
                             ((self.params.humidity_phase_offset_hours / 24.0) * 2 * math.pi)
        humidity_range = self.params.max_humidity_percent - self.params.min_humidity_percent
        # Using -cos for peak at offset, or +cos if offset implies trough at that time.
        # If humidity_phase_offset_hours = 10 (4 AM), and temp peak is 2 PM, this makes humidity peak when temp is low.
        current_humidity = self.params.min_humidity_percent + (humidity_range / 2.0) * (1 - math.cos(humidity_angle_rad))
        current_humidity = max(0.0, min(100.0, current_humidity)) # Clamp to 0-100

        return {
            "temperature_celsius": round(current_temp, 2),
            "solar_intensity_w_m2": round(current_solar_intensity, 2),
            "relative_humidity_percent": round(current_humidity, 1)
        }

    def setup_environment(self, environment_3d_orchestrator: Any) -> None:
        self.reset()
        initial_values = self._calculate_current_values()
        
        if hasattr(environment_3d_orchestrator, 'set_ambient_temperature'):
            environment_3d_orchestrator.set_ambient_temperature(initial_values["temperature_celsius"])
        if hasattr(environment_3d_orchestrator, 'set_solar_intensity'):
            environment_3d_orchestrator.set_solar_intensity(initial_values["solar_intensity_w_m2"])
        if hasattr(environment_3d_orchestrator, 'set_relative_humidity'):
            environment_3d_orchestrator.set_relative_humidity(initial_values["relative_humidity_percent"])
            
        print(f"Scenario {self.scenario_id}: Diurnal cycle initialized. Temp: {initial_values['temperature_celsius']}C, Solar: {initial_values['solar_intensity_w_m2']}W/m2.")

    def get_ground_truth_labels(self, environment_3d_state: Any) -> Dict[str, Any]:
        # For normal operation, labels might indicate no anomaly or specific environmental conditions
        current_hour = (self.current_time_seconds % 86400) / 3600
        # Simplified solar phase, real one would use solar position calculation
        solar_phase = "day" if 6 < current_hour < 18 else "night" 
        if 4 <= current_hour < 6: solar_phase = "dawn"
        if 18 <= current_hour < 20: solar_phase = "dusk"
            
        return {
            "event_type": "normal_diurnal_cycle",
            "is_anomaly": False,
            "time_of_day_approx_hour": round(current_hour, 1),
            "solar_phase": solar_phase,
            **self._calculate_current_values() # Add current simulated values to labels
        }

    def update(self, time_step_seconds: float, environment_3d_orchestrator: Any) -> None:
        super().update(time_step_seconds, environment_3d_orchestrator)
        
        current_values = self._calculate_current_values()
        
        if hasattr(environment_3d_orchestrator, 'set_ambient_temperature'):
            environment_3d_orchestrator.set_ambient_temperature(current_values["temperature_celsius"])
        if hasattr(environment_3d_orchestrator, 'set_solar_intensity'):
            environment_3d_orchestrator.set_solar_intensity(current_values["solar_intensity_w_m2"])
        if hasattr(environment_3d_orchestrator, 'set_relative_humidity'):
            environment_3d_orchestrator.set_relative_humidity(current_values["relative_humidity_percent"])
        
        # print(f"Scenario {self.scenario_id} updated. Time: {self.current_time_seconds:.0f}s. Temp: {current_values['temperature_celsius']}C, Solar: {current_values['solar_intensity_w_m2']}W/m2")


    def is_completed(self, environment_3d_state: Any) -> bool:
        if self.expected_duration_seconds is not None and \
           self.current_time_seconds >= self.expected_duration_seconds:
            return True
        return False

class SeasonalVariationParams(BaseModel):
    """
    Parameters for configuring the SeasonalVariationScenario.
    """
    start_avg_temp_c: float = Field(
        default=10.0,
        description="Average temperature in Celsius at the start of the season."
    )
    end_avg_temp_c: float = Field(
        default=20.0,
        description="Average temperature in Celsius at the end of the season."
    )
    start_avg_humidity_percent: float = Field(
        default=60.0,
        ge=0,
        le=100,
        description="Average relative humidity in percent at the start of the season."
    )
    end_avg_humidity_percent: float = Field(
        default=60.0,
        ge=0,
        le=100,
        description="Average relative humidity in percent at the end of the season."
    )
    season_name: str = Field(
        default="Transitioning Season",
        description="A descriptive name for the season or transition period (e.g., 'Spring', 'Summer to Autumn')."
    )

    class Config:
        extra = "forbid"


class SeasonalVariationScenario(BaseScenario):
    def __init__(self, scenario_id: str, name: Optional[str] = "Seasonal Variation",
                 description: Optional[str] = "Simulates gradual changes in baseline environmental conditions over a longer period (e.g., weeks/months), representing seasonal shifts.",
                 expected_duration_seconds: Optional[float] = 86400.0 * 90, # Approx 3 months for a season
                 difficulty_level: ScenarioComplexity = ScenarioComplexity.LOW,
                 start_avg_temp_c: float = 10.0,
                 end_avg_temp_c: float = 20.0,
                 start_avg_humidity_percent: float = 60.0,
                 end_avg_humidity_percent: float = 60.0,
                 season_name: str = "Transitioning Season",
                 **kwargs):
        super().__init__(scenario_id=scenario_id, name=name, description=description,
                         category="normal_operation_long_term",
                         difficulty_level=difficulty_level,
                         expected_duration_seconds=expected_duration_seconds,
                         **kwargs)
        
        param_dict = {
            "start_avg_temp_c": start_avg_temp_c,
            "end_avg_temp_c": end_avg_temp_c,
            "start_avg_humidity_percent": start_avg_humidity_percent,
            "end_avg_humidity_percent": end_avg_humidity_percent,
            "season_name": season_name
        }
        self.params = SeasonalVariationParams(**param_dict)

    def _get_specific_params(self) -> Dict[str, Any]:
        """Returns the scenario-specific parameters as a dictionary."""
        return self.params.model_dump(mode='python')

    def _calculate_current_baseline_values(self) -> Dict[str, Any]:
        """Calculates current baseline environmental values by interpolating over the season."""
        if self.expected_duration_seconds is None or self.expected_duration_seconds == 0:
            progress = 0.0
        else:
            progress = min(self.current_time_seconds / self.expected_duration_seconds, 1.0)

        current_avg_temp_c = self.params.start_avg_temp_c + \
                             (self.params.end_avg_temp_c - self.params.start_avg_temp_c) * progress
        current_avg_humidity_percent = self.params.start_avg_humidity_percent + \
                                     (self.params.end_avg_humidity_percent - self.params.start_avg_humidity_percent) * progress

        return {
            "avg_temperature_celsius": round(current_avg_temp_c, 2),
            "avg_relative_humidity_percent": round(current_avg_humidity_percent, 1),
            "season_name": self.params.season_name,
            "seasonal_progress_percent": round(progress * 100, 1)
        }

    def setup_environment(self, environment_3d_orchestrator: Any) -> None:
        self.reset()
        initial_baseline = self._calculate_current_baseline_values()
        
        if hasattr(environment_3d_orchestrator, 'set_baseline_ambient_temperature'):
            environment_3d_orchestrator.set_baseline_ambient_temperature(initial_baseline["avg_temperature_celsius"])
        if hasattr(environment_3d_orchestrator, 'set_baseline_relative_humidity'):
            environment_3d_orchestrator.set_baseline_relative_humidity(initial_baseline["avg_relative_humidity_percent"])
            
        print(f"Scenario {self.scenario_id} ({self.params.season_name}): Seasonal variation initialized. Avg Temp: {initial_baseline['avg_temperature_celsius']}C, Avg RH: {initial_baseline['avg_relative_humidity_percent']}%.")

    def get_ground_truth_labels(self, environment_3d_state: Any) -> Dict[str, Any]:
        baseline_values = self._calculate_current_baseline_values()
        return {
            "event_type": "normal_seasonal_variation",
            "is_anomaly": False,
            **baseline_values
        }

    def update(self, time_step_seconds: float, environment_3d_orchestrator: Any) -> None:
        super().update(time_step_seconds, environment_3d_orchestrator)
        current_baseline = self._calculate_current_baseline_values()
        
        if hasattr(environment_3d_orchestrator, 'set_baseline_ambient_temperature'):
            environment_3d_orchestrator.set_baseline_ambient_temperature(current_baseline["avg_temperature_celsius"])
        if hasattr(environment_3d_orchestrator, 'set_baseline_relative_humidity'):
            environment_3d_orchestrator.set_baseline_relative_humidity(current_baseline["avg_relative_humidity_percent"])
        
        # print(f"Scenario {self.scenario_id} updated. Progress: {current_baseline['seasonal_progress_percent']}%")

    def is_completed(self, environment_3d_state: Any) -> bool:
        if self.expected_duration_seconds is not None and \
           self.current_time_seconds >= self.expected_duration_seconds:
            return True
        return False

class RainEventDetails(BaseModel):
    intensity: Literal["light", "moderate", "heavy", "torrential"] = "moderate"
    duration_hours: float = Field(default=1.0, gt=0, description="Duration of the rain event in hours.")
    precipitation_rate_mm_hr: Optional[float] = Field(
        default=None, ge=0,
        description="Average precipitation rate in mm/hr. If None, can be inferred from intensity by orchestrator."
    )
    # Example: wind_effect_on_rain_factor: float = Field(default=0.1, ge=0, le=1.0)

    class Config:
        extra = "forbid"

class WindEventDetails(BaseModel):
    max_wind_speed_mps: float = Field(gt=0, description="Maximum sustained wind speed in meters per second.")
    dominant_direction_degrees: float = Field(ge=0, lt=360, description="Dominant wind direction in degrees (0-359).")
    gust_speed_mps: Optional[float] = Field(
        default=None, ge=0,
        description="Peak gust speed in m/s. If None, can be calculated (e.g., 1.5 * max_wind_speed_mps by orchestrator)."
    )
    duration_hours: float = Field(default=2.0, gt=0, description="Duration of the high wind event in hours.")
    
    class Config:
        extra = "forbid"

class TemperatureEventDetails(BaseModel):
    event_type: Literal["heatwave", "cold_snap"]
    temperature_peak_delta_c: float = Field(
        description="Peak temperature change from baseline in Celsius (positive for heatwave, negative for cold_snap)."
    )
    ramp_duration_hours: float = Field(gt=0, description="Duration to reach peak temperature change in hours.")
    peak_duration_hours: float = Field(ge=0, description="Duration at peak temperature change in hours.")
    return_to_baseline_duration_hours: float = Field(gt=0, description="Duration to return to baseline after peak in hours.")

    @validator('temperature_peak_delta_c')
    def check_delta_sign_matches_type(cls, v, values):
        event_type = values.get('event_type')
        if event_type == "heatwave" and v <= 0:
            raise ValueError("temperature_peak_delta_c must be positive for a heatwave.")
        if event_type == "cold_snap" and v >= 0:
            raise ValueError("temperature_peak_delta_c must be negative for a cold_snap.")
        return v

    class Config:
        extra = "forbid"

class WeatherEventParams(BaseModel):
    """
    Main parameters for WeatherEventScenario, including the type and specific details.
    """
    weather_event_type: Literal["rain_storm", "high_wind", "temperature_event"]
    event_details: Union[RainEventDetails, WindEventDetails, TemperatureEventDetails]

    @validator('event_details', always=True)
    def check_event_details_match_type(cls, v, values):
        event_type = values.get('weather_event_type')
        if not event_type:
            return v
        
        if event_type == "rain_storm" and not isinstance(v, RainEventDetails):
            raise ValueError(f"For weather_event_type '{event_type}', event_details must be RainEventDetails, got {type(v)}")
        elif event_type == "high_wind" and not isinstance(v, WindEventDetails):
            raise ValueError(f"For weather_event_type '{event_type}', event_details must be WindEventDetails, got {type(v)}")
        elif event_type == "temperature_event" and not isinstance(v, TemperatureEventDetails):
            raise ValueError(f"For weather_event_type '{event_type}', event_details must be TemperatureEventDetails, got {type(v)}")
        return v
    
    class Config:
        extra = "forbid"


class WeatherEventScenario(BaseScenario):
    def __init__(self, scenario_id: str, name: Optional[str] = "Weather Event",
                 description: Optional[str] = "Simulates specific weather events.",
                 expected_duration_seconds: Optional[float] = None, # Will be derived from event_details if not set
                 difficulty_level: ScenarioComplexity = ScenarioComplexity.MEDIUM,
                 weather_event_type: Literal["rain_storm", "high_wind", "temperature_event"] = "rain_storm",
                 event_details_data: Optional[Dict[str, Any]] = None,
                 **kwargs):

        # Determine expected_duration_seconds from event_details if not provided
        parsed_event_details: Union[RainEventDetails, WindEventDetails, TemperatureEventDetails]
        if weather_event_type == "rain_storm":
            parsed_event_details = RainEventDetails(**(event_details_data or {}))
            if expected_duration_seconds is None:
                expected_duration_seconds = parsed_event_details.duration_hours * 3600.0
        elif weather_event_type == "high_wind":
            parsed_event_details = WindEventDetails(**(event_details_data or {}))
            if expected_duration_seconds is None:
                expected_duration_seconds = parsed_event_details.duration_hours * 3600.0
        elif weather_event_type == "temperature_event":
            parsed_event_details = TemperatureEventDetails(**(event_details_data or {}))
            if expected_duration_seconds is None:
                expected_duration_seconds = (parsed_event_details.ramp_duration_hours +
                                           parsed_event_details.peak_duration_hours +
                                           parsed_event_details.return_to_baseline_duration_hours) * 3600.0
        else:
            raise ValueError(f"Unsupported weather_event_type: {weather_event_type}")

        super().__init__(scenario_id=scenario_id, name=name, description=description,
                         category="normal_operation_weather",
                         difficulty_level=difficulty_level,
                         expected_duration_seconds=expected_duration_seconds,
                         **kwargs)
        
        self.params = WeatherEventParams(
            weather_event_type=weather_event_type,
            event_details=parsed_event_details
        )
        self.event_active = False

    def _get_specific_params(self) -> Dict[str, Any]:
        """Returns the scenario-specific parameters as a dictionary."""
        return self.params.model_dump(mode='python')

    def setup_environment(self, environment_3d_orchestrator: Any) -> None:
        self.reset()
        self.event_active = True
        if hasattr(environment_3d_orchestrator, 'start_weather_event'):
            # Pass the Pydantic model directly, or its dict representation
            environment_3d_orchestrator.start_weather_event(
                event_type=self.params.weather_event_type,
                params=self.params.event_details, # Pass the specific details model
                duration_seconds=self.expected_duration_seconds
            )
        print(f"Scenario {self.scenario_id}: Weather event '{self.params.weather_event_type}' started with details: {self.params.event_details.model_dump_json(indent=2)}.")

    def get_ground_truth_labels(self, environment_3d_state: Any) -> Dict[str, Any]:
        labels = {
            "event_type": "normal_weather_event",
            "weather_condition": self.params.weather_event_type,
            "is_anomaly": False,
            "event_active": self.event_active,
        }
        # Add specific details from the event_details model
        if isinstance(self.params.event_details, RainEventDetails):
            labels["rain_intensity"] = self.params.event_details.intensity
            if self.params.event_details.precipitation_rate_mm_hr is not None:
                labels["precipitation_rate_mm_hr"] = self.params.event_details.precipitation_rate_mm_hr
        elif isinstance(self.params.event_details, WindEventDetails):
            labels["max_wind_speed_mps"] = self.params.event_details.max_wind_speed_mps
            labels["dominant_direction_degrees"] = self.params.event_details.dominant_direction_degrees
            if self.params.event_details.gust_speed_mps is not None:
                labels["gust_speed_mps"] = self.params.event_details.gust_speed_mps
        elif isinstance(self.params.event_details, TemperatureEventDetails):
            labels["temperature_event_type"] = self.params.event_details.event_type
            labels["temperature_peak_delta_c"] = self.params.event_details.temperature_peak_delta_c
        return labels

    def update(self, time_step_seconds: float, environment_3d_orchestrator: Any) -> None:
        super().update(time_step_seconds, environment_3d_orchestrator)
        if self.event_active and self.is_completed(None):
            self.event_active = False
            if hasattr(environment_3d_orchestrator, 'end_weather_event'):
                environment_3d_orchestrator.end_weather_event(event_type=self.params.weather_event_type)
            print(f"Scenario {self.scenario_id}: Weather event '{self.params.weather_event_type}' ended.")

    def is_completed(self, environment_3d_state: Any) -> bool:
        if self.expected_duration_seconds is not None and \
           self.current_time_seconds >= self.expected_duration_seconds:
            return True
        return False

class BaselineOperationParams(BaseModel):
    """
    Parameters for configuring the BaselineOperationScenario.
    Defines stable environmental conditions.
    """
    target_temperature_celsius: float = Field(
        default=20.0,
        description="Target stable ambient temperature in Celsius."
    )
    target_relative_humidity_percent: float = Field(
        default=50.0,
        ge=0,
        le=100,
        description="Target stable relative humidity in percent."
    )
    target_solar_intensity_w_m2: float = Field(
        default=100.0,
        ge=0,
        description="Target stable solar intensity in Watts per square meter (e.g., overcast or indoor equivalent)."
    )
    wind_speed_mps: float = Field(
        default=0.0,
        ge=0,
        description="Target stable wind speed in meters per second."
    )
    precipitation_type: Literal["none", "drizzle", "light_rain"] = Field(
        default="none",
        description="Type of stable precipitation, if any."
    )
    equipment_states: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional dictionary defining states for specific equipment, e.g., {'hvac': 'idle'}."
    )

    class Config:
        extra = "forbid"


class BaselineOperationScenario(BaseScenario):
    def __init__(self, scenario_id: str, name: Optional[str] = "Baseline Equipment Operation",
                 description: Optional[str] = "Simulates typical, uneventful operation of the Grid Guardian unit and surrounding environment under stable conditions.",
                 expected_duration_seconds: Optional[float] = 3600.0 * 8, # 8 hours example
                 difficulty_level: ScenarioComplexity = ScenarioComplexity.VERY_LOW,
                 target_temperature_celsius: float = 20.0,
                 target_relative_humidity_percent: float = 50.0,
                 target_solar_intensity_w_m2: float = 100.0,
                 wind_speed_mps: float = 0.0,
                 precipitation_type: Literal["none", "drizzle", "light_rain"] = "none",
                 equipment_states: Optional[Dict[str, Any]] = None,
                 **kwargs):
        super().__init__(scenario_id=scenario_id, name=name, description=description,
                         category="normal_operation_baseline",
                         difficulty_level=difficulty_level,
                         expected_duration_seconds=expected_duration_seconds,
                         **kwargs)
        
        param_dict = {
            "target_temperature_celsius": target_temperature_celsius,
            "target_relative_humidity_percent": target_relative_humidity_percent,
            "target_solar_intensity_w_m2": target_solar_intensity_w_m2,
            "wind_speed_mps": wind_speed_mps,
            "precipitation_type": precipitation_type,
            "equipment_states": equipment_states
        }
        self.params = BaselineOperationParams(**param_dict)

    def _get_specific_params(self) -> Dict[str, Any]:
        """Returns the scenario-specific parameters as a dictionary."""
        return self.params.model_dump(mode='python')

    def setup_environment(self, environment_3d_orchestrator: Any) -> None:
        self.reset()
        
        # Attempt to set individual parameters if specific methods exist
        if hasattr(environment_3d_orchestrator, 'set_ambient_temperature'):
            environment_3d_orchestrator.set_ambient_temperature(self.params.target_temperature_celsius)
        if hasattr(environment_3d_orchestrator, 'set_relative_humidity'):
            environment_3d_orchestrator.set_relative_humidity(self.params.target_relative_humidity_percent)
        if hasattr(environment_3d_orchestrator, 'set_solar_intensity'):
            environment_3d_orchestrator.set_solar_intensity(self.params.target_solar_intensity_w_m2)
        if hasattr(environment_3d_orchestrator, 'set_wind_conditions'): # Assuming a method for wind
            environment_3d_orchestrator.set_wind_conditions(speed_mps=self.params.wind_speed_mps, direction_degrees=0) # Default direction
        if hasattr(environment_3d_orchestrator, 'set_precipitation'): # Assuming a method for precipitation
            environment_3d_orchestrator.set_precipitation(type=self.params.precipitation_type, intensity=0) # Default intensity for "none"

        # Fallback or primary method for setting all baseline conditions
        if hasattr(environment_3d_orchestrator, 'set_baseline_conditions'):
             environment_3d_orchestrator.set_baseline_conditions(self.params.model_dump(exclude_none=True))
        
        # TODO: Add logic for self.params.equipment_states if orchestrator supports it

        print(f"Scenario {self.scenario_id}: Baseline operation conditions set. Temp: {self.params.target_temperature_celsius}C, RH: {self.params.target_relative_humidity_percent}%, Solar: {self.params.target_solar_intensity_w_m2}W/m2.")

    def get_ground_truth_labels(self, environment_3d_state: Any) -> Dict[str, Any]:
        labels = {
            "event_type": "normal_baseline_operation",
            "is_anomaly": False,
            "target_temperature_celsius": self.params.target_temperature_celsius,
            "target_relative_humidity_percent": self.params.target_relative_humidity_percent,
            "target_solar_intensity_w_m2": self.params.target_solar_intensity_w_m2,
            "wind_speed_mps": self.params.wind_speed_mps,
            "precipitation_type": self.params.precipitation_type
        }
        if self.params.equipment_states:
            labels["equipment_states"] = self.params.equipment_states
        return labels

    def update(self, time_step_seconds: float, environment_3d_orchestrator: Any) -> None:
        super().update(time_step_seconds, environment_3d_orchestrator)
        # Environment is intended to be stable. The orchestrator, having been set up,
        # should maintain these conditions or apply very minor, inherent fluctuations.
        # No specific update logic needed here unless the baseline itself is meant to subtly drift
        # or if the orchestrator needs a periodic "maintain_stable_conditions" call.
        pass

    def is_completed(self, environment_3d_state: Any) -> bool:
        if self.expected_duration_seconds is not None and \
           self.current_time_seconds >= self.expected_duration_seconds:
            return True
        return False

__all__ = [
    "DiurnalCycleScenario",
    "SeasonalVariationScenario",
    "WeatherEventScenario",
    "BaselineOperationScenario"
]