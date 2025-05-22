"""
This module will contain implementations for environmental sensors
such as VOCArraySensor, ParticulateMatterSensor, TemperatureHumiditySensor, etc.,
all inheriting from BaseSensor.
"""

import random # For noise generation
from typing import Dict, Any, Tuple, List

from .base import BaseSensor

class VOCArraySensor(BaseSensor):
    def __init__(self, sensor_id: str, position_3d: Tuple[float, float, float], sampling_volume: Dict[str, Any], specific_params: Dict[str, Any], **kwargs):
        super().__init__(sensor_id, "voc_array", position_3d, sampling_volume, **kwargs)
        self.channels: List[str] = specific_params.get("channels", ["VOC_CH1", "VOC_CH2", "VOC_CH3", "VOC_CH4", "VOC_CH5", "VOC_CH6", "VOC_CH7", "VOC_CH8"])
        self.channel_units: str = specific_params.get("channel_units", "ppb")
        self.cross_sensitivity_matrix: Dict[str, Dict[str, float]] = specific_params.get("cross_sensitivity_matrix", {})
        # Example structure for cross_sensitivity_matrix:
        # {
        #   "target_chemical_A": {"interfering_chemical_B": 0.05, "interfering_chemical_C": 0.02},
        #   "target_chemical_B": {"interfering_chemical_A": 0.01}
        # }
        # This means sensor for A also picks up 5% of B's concentration and 2% of C's.
        
        # For Response Time Modeling (EMA)
        # Alpha = 1 means instant response, smaller alpha means slower response.
        # Alpha can be derived from a time constant (tau) and sample interval (dt): alpha = 1 - exp(-dt/tau)
        # Or, more simply, alpha = dt / (tau + dt)
        # For now, let's use a direct alpha if provided, or default to a relatively fast response.
        self.response_time_alpha: float = specific_params.get("response_time_alpha", 0.8)
        if not (0 < self.response_time_alpha <= 1.0):
            raise ValueError("response_time_alpha must be between 0 (exclusive) and 1 (inclusive).")
        self._ema_filtered_values: Dict[str, float] = {channel: 0.0 for channel in self.channels}
        self._first_sample_taken: bool = False
        
        # For Drift Modeling - drift_parameters is inherited from BaseSensor via **kwargs
        # and should be populated from sensor config.
        # Example drift_parameters:
        # {
        #   "baseline_drift_ppb_per_hour": {"CO": 0.1, "NO2": 0.05},
        #   "sensitivity_drift_percent_per_hour": {"CO": -0.01, "NO2": -0.005} # % change from initial sensitivity of 1.0
        # }


    def sample(self, environment_3d_state: Any) -> Dict[str, Any]:
        # Get the ideal, noise-free readings first
        true_sensor_values = self.get_ground_truth(environment_3d_state)
        
        if "error" in true_sensor_values: # Propagate error if GT failed
            return true_sensor_values
            
        # Apply imperfections to the true values
        # This is where cross-sensitivity, noise, drift, etc., will be modeled.
        return self.apply_imperfections(true_sensor_values, environment_3d_state)

    def get_ground_truth(self, environment_3d_state: Any) -> Dict[str, Any]:
        if not self.ground_truth_capability:
            return {"error": "Ground truth not supported or enabled for this sensor."}
        
        if not hasattr(environment_3d_state, 'get_chemical_concentration'):
            # This can happen if a very basic mock_env_state is passed that hasn't
            # been prepared by create_mock_environment_state or a real orchestrator.
            print(f"Warning: environment_3d_state for VOCArraySensor {self.sensor_id} lacks 'get_chemical_concentration' method.")
            return {"error": "Environment state does not support chemical concentration queries."}

        ground_truth_concentrations = {}
        try:
            for channel_name in self.channels:
                # Assuming channel_name directly maps to a chemical_id recognizable by the environment state.
                # This mapping might need to be more sophisticated later (e.g., from sensor config).
                concentration = environment_3d_state.get_chemical_concentration(
                    chemical_id=channel_name,
                    position=self.position_3d,
                    sampling_volume=self.sampling_volume
                )
                ground_truth_concentrations[channel_name] = round(concentration, 3) # Round to reasonable precision
        except Exception as e:
            print(f"Error querying chemical concentrations for {self.sensor_id}: {e}")
            return {"error": f"Failed to get chemical concentrations: {e}"}
            
        return {"concentrations_ppb": ground_truth_concentrations, "unit": self.channel_units}

    def get_ml_metadata(self) -> Dict[str, Any]:
        return {
            "sensor_id": self.sensor_id,
            "type": self.sensor_type,
            "channels": self.channels,
            "channel_units": self.channel_units,
            "response_time_alpha": self.response_time_alpha,
            "noise_characteristics": self.noise_characteristics,
            "drift_parameters": self.drift_parameters,
            "calibration_artifacts": self.calibration_artifacts, # From BaseSensor
            "environmental_compensation_params": self.environmental_compensation_params, # From BaseSensor
            "cross_sensitivity_matrix": self.cross_sensitivity_matrix,
            # Could also include current EMA filtered values if useful for ML state:
            # "_ema_filtered_values": self._ema_filtered_values
        }

    def apply_imperfections(self, true_reading: Dict[str, Any], environment_3d_state: Any) -> Dict[str, Any]:
        # Implement VOC array specific imperfections
        # e.g., cross-sensitivity, channel-specific noise, drift on each channel
        # Implement VOC array specific imperfections
        # For now, calls base or simple noise
        # import random # if using random for noise
        
        # Start with a copy of the true readings' structure
        # The true_reading format is {"concentrations_ppb": {channel: value, ...}, "unit": "ppb"}
        if "concentrations_ppb" not in true_reading:
            return {"error": "Invalid true_reading format for VOC apply_imperfections"}

        current_true_concentrations = true_reading["concentrations_ppb"]
        
        # 0. Apply Cross-Sensitivity to the true concentrations first
        # This modifies what the sensor "sees" before any other imperfections.
        perceived_true_concentrations = current_true_concentrations.copy()
        if self.cross_sensitivity_matrix:
            for target_channel in self.channels:
                if target_channel in current_true_concentrations: # Ensure we have a base value for the target
                    # Initialize perceived value with its actual true concentration
                    perceived_value = current_true_concentrations.get(target_channel, 0.0)
                    
                    # Add contributions from interfering chemicals
                    if target_channel in self.cross_sensitivity_matrix:
                        for interfering_chemical, sensitivity_factor in self.cross_sensitivity_matrix[target_channel].items():
                            interfering_true_conc = current_true_concentrations.get(interfering_chemical, 0.0)
                            perceived_value += interfering_true_conc * sensitivity_factor
                    
                    perceived_true_concentrations[target_channel] = perceived_value
        
        # The rest of the imperfections operate on these 'perceived_true_concentrations'
        effective_true_concentrations_for_ema = perceived_true_concentrations


        imperfect_concentrations = {}

        if not self._first_sample_taken:
            # For the very first sample, initialize EMA with true values
            for channel in self.channels:
                true_val = effective_true_concentrations_for_ema.get(channel, 0.0)
                self._ema_filtered_values[channel] = true_val
                imperfect_concentrations[channel] = true_val # Initial reading is the perceived true value
            self._first_sample_taken = True
        else:
            # Apply EMA filter for response time to the perceived true concentrations
            for channel in self.channels:
                true_val = effective_true_concentrations_for_ema.get(channel, 0.0)
                prev_ema = self._ema_filtered_values.get(channel, 0.0)
                
                current_ema = (true_val * self.response_time_alpha) + (prev_ema * (1.0 - self.response_time_alpha))
                self._ema_filtered_values[channel] = current_ema
                imperfect_concentrations[channel] = round(current_ema, 3) # Store the filtered value

        # TODO: Apply other imperfections AFTER response time modeling:
        # 1. Cross-sensitivity (modifies the 'true_val' effectively before EMA, or applied to EMA'd values if sensor electronics do filtering first)
        #    This needs careful thought on where it fits in the chain.
        #    If cross-sensitivity is inherent to the sensing element before its own response time,
        #    it should modify `current_true_concentrations` before EMA.
        #    If it's an electronic artifact after some filtering, it's different.
        #    Let's assume for now it's on the raw sensing before response time. (TODO for cross-sensitivity)

        # 2. Noise (applied to the EMA filtered values)
        if self.noise_characteristics and self.noise_characteristics.get("type") == "gaussian":
            global_mean = self.noise_characteristics.get("mean", 0.0)
            global_stddev = self.noise_characteristics.get("stddev", 0.0) # Default to 0 if not specified

            for channel in self.channels:
                if channel in imperfect_concentrations:
                    # Allow channel-specific overrides for noise parameters
                    channel_noise_params = self.noise_characteristics.get(channel, {})
                    mean = channel_noise_params.get("mean", global_mean)
                    stddev = channel_noise_params.get("stddev", global_stddev)
                    
                    if stddev > 0: # Only apply noise if stddev is meaningful
                        noise_val = random.gauss(mean, stddev)
                        imperfect_concentrations[channel] += noise_val
                    
                    # Ensure concentration doesn't go below zero due to noise
                    imperfect_concentrations[channel] = max(0.0, imperfect_concentrations[channel])
                    imperfect_concentrations[channel] = round(imperfect_concentrations[channel], 3)


        # 3. Drift (applied after noise, to the noisy, EMA-filtered values)
        # Uses environment_3d_state.simulation_time_seconds
        if self.drift_parameters and hasattr(environment_3d_state, 'simulation_time_seconds'):
            sim_time_hours = environment_3d_state.simulation_time_seconds / 3600.0

            baseline_drift_rate_map = self.drift_parameters.get("baseline_drift_ppb_per_hour", {})
            sensitivity_drift_rate_map = self.drift_parameters.get("sensitivity_drift_percent_per_hour", {})

            for channel in self.channels:
                if channel in imperfect_concentrations:
                    current_value = imperfect_concentrations[channel]
                    
                    # Apply baseline drift
                    baseline_drift_rate = baseline_drift_rate_map.get(channel, 0.0) # ppb per hour
                    total_baseline_drift = baseline_drift_rate * sim_time_hours
                    current_value += total_baseline_drift
                    
                    # Apply sensitivity drift
                    initial_sensitivity = 1.0
                    # sensitivity_drift_percent_per_hour: e.g., -0.1 means -0.1% per hour, so factor is -0.001
                    sensitivity_drift_factor_per_hour = sensitivity_drift_rate_map.get(channel, 0.0) / 100.0
                    
                    total_sensitivity_change_factor = sensitivity_drift_factor_per_hour * sim_time_hours
                    current_sensitivity = initial_sensitivity + total_sensitivity_change_factor
                    
                    # Clamp sensitivity e.g. 0.1x to 2x to prevent extreme values from misconfiguration
                    current_sensitivity = max(0.1, min(2.0, current_sensitivity))
                    
                    current_value *= current_sensitivity
                                        
                    imperfect_concentrations[channel] = max(0.0, round(current_value, 3)) # Ensure non-negative and round
        elif self.drift_parameters and not hasattr(environment_3d_state, 'simulation_time_seconds'):
             print(f"Warning: Drift parameters exist for {self.sensor_id} but environment_3d_state lacks 'simulation_time_seconds'. Skipping drift.")


        # 4. Calibration Artifacts (offsets, gains)
        if self.calibration_artifacts:
            offset_map = self.calibration_artifacts.get("offset_ppb", {})
            gain_factor_map = self.calibration_artifacts.get("gain_factor", {})

            for channel in self.channels:
                if channel in imperfect_concentrations:
                    current_value = imperfect_concentrations[channel]
                    
                    # Apply Gain Error first
                    gain_factor = gain_factor_map.get(channel, 1.0) # Default to perfect gain
                    current_value *= gain_factor
                    
                    # Apply Offset Error
                    offset = offset_map.get(channel, 0.0) # Default to no offset
                    current_value += offset
                                        
                    imperfect_concentrations[channel] = max(0.0, round(current_value, 3)) # Ensure non-negative and round
        

        # 5. Environmental Compensation Errors (e.g., temperature effects on electronics/baseline)
        if self.environmental_compensation_params and \
           self.environmental_compensation_params.get("temperature") and \
           hasattr(environment_3d_state, 'get_temperature_celsius'):
            
            temp_comp_config = self.environmental_compensation_params["temperature"]
            ref_temp_c = temp_comp_config.get("reference_temp_c", 25.0)
            offset_per_celsius_map = temp_comp_config.get("offset_ppb_per_celsius", {})

            try:
                # Assuming sensor's own position is relevant for its electronics' temperature
                ambient_temp_c = environment_3d_state.get_temperature_celsius(self.position_3d, self.sampling_volume)
                temp_delta_c = ambient_temp_c - ref_temp_c

                for channel in self.channels:
                    if channel in imperfect_concentrations and channel in offset_per_celsius_map:
                        temp_induced_offset = offset_per_celsius_map[channel] * temp_delta_c
                        imperfect_concentrations[channel] += temp_induced_offset
                        imperfect_concentrations[channel] = max(0.0, round(imperfect_concentrations[channel], 3))
            except Exception as e:
                print(f"Warning: Could not apply temperature compensation for {self.sensor_id}: {e}")
        elif self.environmental_compensation_params and \
             self.environmental_compensation_params.get("temperature") and \
             not hasattr(environment_3d_state, 'get_temperature_celsius'):
            print(f"Warning: Temp compensation config exists for {self.sensor_id} but env_state lacks 'get_temperature_celsius'. Skipping.")


        output_reading = {
            "concentrations_ppb": imperfect_concentrations,
            "unit": true_reading.get("unit", self.channel_units)
        }
        
        # BaseSensor.apply_imperfections is abstract, so no super call here unless it becomes concrete with common logic.
        return output_reading

class ParticulateMatterSensor(BaseSensor):
    def __init__(self, sensor_id: str, position_3d: Tuple[float, float, float], sampling_volume: Dict[str, Any], specific_params: Dict[str, Any], **kwargs):
        super().__init__(sensor_id, "particulate_matter", position_3d, sampling_volume, **kwargs)
        self.measures: List[str] = specific_params.get("measures", ["pm1.0", "pm2.5", "pm10"])
        self.unit: str = specific_params.get("unit", "ug_m3")

    def sample(self, environment_3d_state: Any) -> Dict[str, Any]:
        true_readings = self.get_ground_truth(environment_3d_state)
        return self.apply_imperfections(true_readings, environment_3d_state)

    def get_ground_truth(self, environment_3d_state: Any) -> Dict[str, Any]:
        if not self.ground_truth_capability: return {"error": "Ground truth not supported."}
        # Placeholder: query environment for PM concentrations
        ground_truth_values = {measure: 0.0 for measure in self.measures}
        return {"concentrations": ground_truth_values, "unit": self.unit}

    def get_ml_metadata(self) -> Dict[str, Any]:
        return {"sensor_id": self.sensor_id, "type": self.sensor_type, "measures": self.measures, "unit": self.unit}

    def apply_imperfections(self, true_reading: Dict[str, Any], environment_3d_state: Any) -> Dict[str, Any]:
        # For ParticulateMatterSensor, BaseSensor.apply_imperfections might not exist anymore or is abstract.
        # We need to provide a concrete implementation or ensure BaseSensor has a default if it's not abstract.
        # Assuming BaseSensor.apply_imperfections is now abstract, we just return a copy for stubs.
        return true_reading.copy() # Basic pass-through for now

class TemperatureHumiditySensor(BaseSensor):
    def __init__(self, sensor_id: str, position_3d: Tuple[float, float, float], sampling_volume: Dict[str, Any], **kwargs):
        super().__init__(sensor_id, "temp_humidity", position_3d, sampling_volume, **kwargs)

    def sample(self, environment_3d_state: Any) -> Dict[str, Any]:
        true_readings = self.get_ground_truth(environment_3d_state)
        return self.apply_imperfections(true_readings, environment_3d_state)

    def get_ground_truth(self, environment_3d_state: Any) -> Dict[str, Any]:
        if not self.ground_truth_capability: return {"error": "Ground truth not supported."}
        # Placeholder: query environment for temperature and humidity
        return {"temperature_celsius": 25.0, "humidity_percent": 50.0}

    def get_ml_metadata(self) -> Dict[str, Any]:
        return {"sensor_id": self.sensor_id, "type": self.sensor_type}

    def apply_imperfections(self, true_reading: Dict[str, Any], environment_3d_state: Any) -> Dict[str, Any]:
        return true_reading.copy()

class BarometricPressureSensor(BaseSensor):
    def __init__(self, sensor_id: str, position_3d: Tuple[float, float, float], sampling_volume: Dict[str, Any], **kwargs):
        super().__init__(sensor_id, "barometric_pressure", position_3d, sampling_volume, **kwargs)
        self.unit: str = kwargs.get("specific_params", {}).get("unit", "hPa")


    def sample(self, environment_3d_state: Any) -> Dict[str, Any]:
        true_readings = self.get_ground_truth(environment_3d_state)
        return self.apply_imperfections(true_readings, environment_3d_state)

    def get_ground_truth(self, environment_3d_state: Any) -> Dict[str, Any]:
        if not self.ground_truth_capability: return {"error": "Ground truth not supported."}
        # Placeholder: query environment for pressure
        return {"pressure": 1012.5, "unit": self.unit}

    def get_ml_metadata(self) -> Dict[str, Any]:
        return {"sensor_id": self.sensor_id, "type": self.sensor_type, "unit": self.unit}

    def apply_imperfections(self, true_reading: Dict[str, Any], environment_3d_state: Any) -> Dict[str, Any]:
        return true_reading.copy()

class WindSpeedDirectionSensor(BaseSensor):
    def __init__(self, sensor_id: str, position_3d: Tuple[float, float, float], sampling_volume: Dict[str, Any], **kwargs):
        super().__init__(sensor_id, "wind_sensor", position_3d, sampling_volume, **kwargs)

    def sample(self, environment_3d_state: Any) -> Dict[str, Any]:
        true_readings = self.get_ground_truth(environment_3d_state)
        return self.apply_imperfections(true_readings, environment_3d_state)

    def get_ground_truth(self, environment_3d_state: Any) -> Dict[str, Any]:
        if not self.ground_truth_capability: return {"error": "Ground truth not supported."}
        # Placeholder: query environment for wind vector
        return {"speed_mps": 5.0, "direction_degrees": 180.0} # Speed in m/s, Direction in degrees from North

    def get_ml_metadata(self) -> Dict[str, Any]:
        return {"sensor_id": self.sensor_id, "type": self.sensor_type}

    def apply_imperfections(self, true_reading: Dict[str, Any], environment_3d_state: Any) -> Dict[str, Any]:
        return true_reading.copy()

class LightningDetectionSensor(BaseSensor):
    def __init__(self, sensor_id: str, position_3d: Tuple[float, float, float], sampling_volume: Dict[str, Any], **kwargs):
        # Sampling volume might represent detection range/area
        super().__init__(sensor_id, "lightning_detector", position_3d, sampling_volume, **kwargs)
        self.detection_count_since_last_sample = 0

    def sample(self, environment_3d_state: Any) -> Dict[str, Any]:
        # This sensor is more event-driven.
        # It would check environment_3d_state for any lightning events within its range/time window.
        # For a stub, it might just report a count.
        # self.detection_count_since_last_sample = environment_3d_state.get_lightning_strikes_count(self.position_3d, self.sampling_volume.get('radius_km', 10))
        true_readings = self.get_ground_truth(environment_3d_state) # This might be tricky for event based
        # Imperfections could be false positives, missed detections, inaccurate distance.
        output = self.apply_imperfections(true_readings, environment_3d_state)
        # Reset count after sample or manage it based on time window
        # self.detection_count_since_last_sample = 0
        return output


    def get_ground_truth(self, environment_3d_state: Any) -> Dict[str, Any]:
        if not self.ground_truth_capability: return {"error": "Ground truth not supported."}
        # Placeholder: query environment for actual lightning events
        # This is complex, as it's event-based. For a stub, maybe just a boolean or count.
        # actual_strikes = environment_3d_state.get_true_lightning_events(...)
        return {"detected_strikes_count": 0, "last_strike_distance_km": None} # Example structure

    def get_ml_metadata(self) -> Dict[str, Any]:
        return {"sensor_id": self.sensor_id, "type": self.sensor_type}

    def apply_imperfections(self, true_reading: Dict[str, Any], environment_3d_state: Any) -> Dict[str, Any]:
        # e.g. false positives, missed detections
        return true_reading.copy()