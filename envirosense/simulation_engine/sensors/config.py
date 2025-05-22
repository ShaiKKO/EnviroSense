from typing import Dict, Any, List, Optional, Union, Tuple
from pydantic import BaseModel, validator, Field

class IndividualSensorConfig(BaseModel):
    """
    Configuration for a single sensor instance within the VirtualGridGuardian.
    This allows specifying sensor-specific operational parameters and
    imperfection model settings.
    """
    sensor_type: str = Field(..., description="Type of the sensor (e.g., 'voc_array', 'thermal_camera').")
    sensor_id: Optional[str] = Field(None, description="Optional unique ID for this sensor instance. If None, one might be generated.")
    is_enabled: bool = Field(True, description="Whether this sensor is enabled by default.")
    
    # Parameters for imperfection models
    noise_characteristics: Optional[Dict[str, Any]] = Field(None, description="Parameters for the sensor's noise model.")
    drift_parameters: Optional[Dict[str, Any]] = Field(None, description="Parameters for the sensor's drift model.")
    calibration_artifacts: Optional[Dict[str, Any]] = Field(None, description="Parameters for calibration artifacts.")
    response_time_ms: Optional[float] = Field(None, description="Sensor response time in milliseconds.")
    
    # Sensor-specific operational parameters (e.g., resolution, channels)
    # These can be further validated in sensor-specific config models if needed
    specific_params: Dict[str, Any] = Field({}, description="Dictionary for any other sensor-specific parameters.")

    # Example for a VOC sensor's specific_params:
    # specific_params: {
    #     "channels": ["CO", "NO2", "VOC_mix1"],
    #     "cross_sensitivity_matrix": { ... }
    # }
    # Example for a Thermal Camera's specific_params:
    # specific_params: {
    #     "resolution": [80, 60], # width, height
    #     "optical_blur_sigma": 0.5
    # }

    class Config:
        extra = 'forbid' # Forbid any extra fields not defined

class SensorConfiguration(BaseModel):
    """
    Overall configuration for the VirtualGridGuardian's sensor array.
    It defines which sensors are part of the array and their individual settings.
    """
    guardian_id: str = Field(..., description="Unique identifier for the Grid Guardian unit.")
    default_position_3d: Tuple[float, float, float] = Field((0.0, 0.0, 0.0), description="Default (x,y,z) position for the Grid Guardian unit.")
    
    sensors: List[IndividualSensorConfig] = Field(..., description="List of configurations for each sensor in the array.")

    # ML training data generation settings (can be expanded)
    ml_training_settings: Dict[str, Any] = Field({}, description="Global settings for ML training data generation, e.g., range of imperfections to apply across scenarios.")
    
    # Scenario-specific sensor behavior overrides (can be expanded)
    # This might be a dictionary mapping scenario_ids to lists of sensor_id/type and override_params
    scenario_overrides: Dict[str, Any] = Field({}, description="Defines sensor behavior overrides for specific scenarios.")

    @validator('sensors')
    def check_sensor_ids_unique_if_provided(cls, sensors_list: List[IndividualSensorConfig]):
        ids = [s.sensor_id for s in sensors_list if s.sensor_id is not None]
        if len(ids) != len(set(ids)):
            raise ValueError('Provided sensor_ids must be unique within the configuration.')
        return sensors_list

    class Config:
        extra = 'forbid'

# Example Usage (can be moved to a doc or example file later)
if __name__ == '__main__':
    example_config_data = {
        "guardian_id": "GG-Pole-123",
        "default_position_3d": (39.75, -104.98, 10.0),
        "sensors": [
            {
                "sensor_type": "voc_array",
                "sensor_id": "gg123-voc-01",
                "is_enabled": True,
                "noise_characteristics": {"type": "gaussian", "stddev_ppb": 5.0},
                "drift_parameters": {"rate_ppb_per_day": 0.1},
                "specific_params": {
                    "channels": ["CO", "NO2", "O3", "SO2", "H2S", "NH3", "VOC_General1", "VOC_General2"],
                    "channel_units": ["ppb"] * 8 # Example
                }
            },
            {
                "sensor_type": "thermal_camera",
                "sensor_id": "gg123-thermal-01",
                "noise_characteristics": {"type": "gaussian_pixel", "stddev_celsius": 0.2},
                "specific_params": {
                    "resolution": [80, 60],
                    "fov_degrees": [90, 60] # Horizontal, Vertical
                }
            },
            {
                "sensor_type": "emf_sensor",
                "sensor_id": "gg123-emf-01",
                "specific_params": {
                    "frequency_range_hz": [50, 60]
                }
            },
            { # Example of a sensor disabled by default
                "sensor_type": "particulate_matter",
                "sensor_id": "gg123-pm-01",
                "is_enabled": False,
                "specific_params": {"measures": ["pm1.0", "pm2.5", "pm10"]}
            }
        ],
        "ml_training_settings": {
            "apply_random_imperfection_scaling": True,
            "imperfection_scale_range": [0.5, 1.5]
        }
    }

    try:
        config = SensorConfiguration(**example_config_data)
        print("SensorConfiguration parsed successfully:")
        print(config.json(indent=2))

        # Test access
        print(f"\nGuardian ID: {config.guardian_id}")
        if config.sensors:
            print(f"First sensor type: {config.sensors[0].sensor_type}")
            print(f"First sensor specific params: {config.sensors[0].specific_params}")

    except ValueError as e:
        print(f"Error parsing SensorConfiguration: {e}")