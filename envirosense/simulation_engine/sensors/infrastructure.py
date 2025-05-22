"""
This module will contain implementations for infrastructure monitoring sensors
such as ThermalCameraSensor, EMFSensor, AcousticSensor, VibrationSensor, etc.,
all inheriting from BaseSensor.
"""

import random # For noise generation
from typing import Dict, Any, Tuple, List
import numpy as np # For image array operations
try:
    from scipy.ndimage import gaussian_filter
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: scipy.ndimage not found. Gaussian blur for ThermalCameraSensor will not be available.")

from .base import BaseSensor

class ThermalCameraSensor(BaseSensor):
    def __init__(self, sensor_id: str, position_3d: Tuple[float, float, float], sampling_volume: Dict[str, Any], specific_params: Dict[str, Any], **kwargs):
        super().__init__(sensor_id, "thermal_camera", position_3d, sampling_volume, **kwargs)
        self.resolution: List[int] = specific_params.get("resolution", [80, 60]) # width, height
        self.fov_degrees: List[float] = specific_params.get("fov_degrees", [90.0, 60.0]) # Horizontal, Vertical
        # sampling_volume here might represent the camera's frustum or focus depth

        # Dead/Hot pixel configuration
        self.dead_pixels: List[List[int]] = specific_params.get("dead_pixels", []) # List of [row, col]
        self.hot_pixels_config: Dict[str, Any] = specific_params.get("hot_pixels", {})
        # e.g., {"coordinates": [[r,c], ...], "hot_value_celsius": 200.0, "dead_value_celsius": -40.0}
        self.dead_pixel_value: float = self.hot_pixels_config.get("dead_value_celsius", -40.0) # Default for dead pixels
        self.hot_pixel_value: float = self.hot_pixels_config.get("hot_value_celsius", 200.0) # Default for hot pixels
        self.hot_pixel_coordinates: List[List[int]] = self.hot_pixels_config.get("coordinates", [])

        # Optical blur configuration
        self.optical_blur_config: Dict[str, Any] = specific_params.get("optical_blur", {})
        # e.g., {"type": "gaussian", "sigma": 0.5}


        self.response_time_alpha: float = specific_params.get("response_time_alpha", 0.7) # Default for thermal
        if not (0 < self.response_time_alpha <= 1.0):
            raise ValueError("response_time_alpha must be between 0 (exclusive) and 1 (inclusive).")
        
        # Initialize with a zero array of the correct dimensions
        self._ema_filtered_image: List[List[float]] = [[0.0 for _ in range(self.resolution[0])] for _ in range(self.resolution[1])]
        self._first_sample_taken: bool = False

    def sample(self, environment_3d_state: Any) -> Dict[str, Any]:
        true_image_data = self.get_ground_truth(environment_3d_state)
        if "error" in true_image_data:
            return true_image_data
        # Apply imperfections (noise, dead pixels, blur, calibration errors).
        return self.apply_imperfections(true_image_data, environment_3d_state)

    def get_ground_truth(self, environment_3d_state: Any) -> Dict[str, Any]:
        if not self.ground_truth_capability:
            return {"error": "Ground truth not supported or enabled for this sensor."}

        if not hasattr(environment_3d_state, 'get_thermal_field_view'):
            print(f"Warning: environment_3d_state for ThermalCameraSensor {self.sensor_id} lacks 'get_thermal_field_view' method.")
            return {"error": "Environment state does not support thermal field view queries."}

        try:
            # Assuming camera orientation needs to be defined or is part of its state/config
            # For now, using a placeholder orientation.
            # self.position_3d is the camera's location.
            # self.sampling_volume might define near/far clip planes or other view properties.
            camera_orientation_placeholder = {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}
            
            thermal_image_array = environment_3d_state.get_thermal_field_view(
                camera_position=self.position_3d,
                camera_orientation=camera_orientation_placeholder, # TODO: Make this configurable/dynamic
                fov_degrees=tuple(self.fov_degrees), # Ensure it's a tuple
                resolution=tuple(self.resolution)    # Ensure it's a tuple
            )
            
            # Basic validation of returned image structure
            if not isinstance(thermal_image_array, list) or \
               not all(isinstance(row, list) for row in thermal_image_array) or \
               len(thermal_image_array) != self.resolution[1] or \
               (len(thermal_image_array) > 0 and len(thermal_image_array[0]) != self.resolution[0]):
                print(f"Error: Thermal field view from environment has unexpected dimensions for {self.sensor_id}.")
                return {"error": "Received malformed thermal image data from environment."}

            return {"thermal_image_celsius": thermal_image_array, "resolution": self.resolution.copy()}
            
        except Exception as e:
            print(f"Error querying thermal field view for {self.sensor_id}: {e}")
            return {"error": f"Failed to get thermal field view: {e}"}

    def get_ml_metadata(self) -> Dict[str, Any]:
        return {
            "sensor_id": self.sensor_id,
            "type": self.sensor_type,
            "resolution": self.resolution,
            "fov_degrees": self.fov_degrees,
            "response_time_alpha": self.response_time_alpha,
            "noise_characteristics": self.noise_characteristics, # From BaseSensor
            "dead_pixels_config": self.dead_pixels,
            "hot_pixels_config": self.hot_pixels_config,
            "optical_blur_config": self.optical_blur_config,
            "calibration_artifacts": self.calibration_artifacts, # From BaseSensor
            "environmental_compensation_params": self.environmental_compensation_params # From BaseSensor
        }

    def apply_imperfections(self, true_reading: Dict[str, Any], environment_3d_state: Any) -> Dict[str, Any]:
        if "thermal_image_celsius" not in true_reading or "resolution" not in true_reading:
            return {"error": "Invalid true_reading format for ThermalCamera apply_imperfections"}

        current_true_image: List[List[float]] = true_reading["thermal_image_celsius"]
        res_w, res_h = true_reading["resolution"] # Should match self.resolution

        # Ensure dimensions match, otherwise re-initialize EMA buffer (or error)
        if len(self._ema_filtered_image) != res_h or \
           (res_h > 0 and len(self._ema_filtered_image[0]) != res_w):
            print(f"Warning: EMA buffer dimensions mismatch for {self.sensor_id}. Re-initializing.")
            self._ema_filtered_image = [[0.0 for _ in range(res_w)] for _ in range(res_h)]
            self._first_sample_taken = False # Force re-initialization

        imperfect_image: List[List[float]] = [[0.0 for _ in range(res_w)] for _ in range(res_h)]

        if not self._first_sample_taken:
            for r in range(res_h):
                for c in range(res_w):
                    true_pixel_val = current_true_image[r][c]
                    self._ema_filtered_image[r][c] = true_pixel_val
                    imperfect_image[r][c] = true_pixel_val
            self._first_sample_taken = True
        else:
            for r in range(res_h):
                for c in range(res_w):
                    true_pixel_val = current_true_image[r][c]
                    prev_ema_pixel = self._ema_filtered_image[r][c]
                    current_ema_pixel = (true_pixel_val * self.response_time_alpha) + \
                                        (prev_ema_pixel * (1.0 - self.response_time_alpha))
                    self._ema_filtered_image[r][c] = current_ema_pixel
                    imperfect_image[r][c] = round(current_ema_pixel, 2) # Round to reasonable precision for temps

        # 1. Pixel noise (random Gaussian noise per pixel) - Applied after EMA
        if self.noise_characteristics and self.noise_characteristics.get("type") == "gaussian_pixel":
            mean = self.noise_characteristics.get("mean", 0.0)
            stddev = self.noise_characteristics.get("stddev_celsius", 0.0)

            if stddev > 0:
                for r in range(res_h):
                    for c in range(res_w):
                        noise_val = random.gauss(mean, stddev)
                        imperfect_image[r][c] += noise_val
                        # Clamping temperature to a plausible range could be done here if needed
                        imperfect_image[r][c] = round(imperfect_image[r][c], 2)

        # 2. Dead/hot pixels (applied after noise)
        for r_dead, c_dead in self.dead_pixels:
            if 0 <= r_dead < res_h and 0 <= c_dead < res_w:
                imperfect_image[r_dead][c_dead] = self.dead_pixel_value
        
        for r_hot, c_hot in self.hot_pixel_coordinates:
            if 0 <= r_hot < res_h and 0 <= c_hot < res_w:
                imperfect_image[r_hot][c_hot] = self.hot_pixel_value

        # 3. Optical blur (applied after dead/hot pixels)
        if SCIPY_AVAILABLE and self.optical_blur_config and self.optical_blur_config.get("type") == "gaussian":
            sigma = self.optical_blur_config.get("sigma", 0.0)
            if sigma > 0:
                image_np = np.array(imperfect_image, dtype=float)
                blurred_image_np = gaussian_filter(image_np, sigma=sigma)
                imperfect_image = blurred_image_np.tolist()
                for r in range(res_h): # Round again after blur
                    for c in range(res_w):
                        imperfect_image[r][c] = round(imperfect_image[r][c], 2)

        # 4. Calibration errors (global offset/gain for now) - Applied after blur
        if self.calibration_artifacts:
            global_offset = self.calibration_artifacts.get("global_offset_celsius", 0.0)
            global_gain = self.calibration_artifacts.get("global_gain_factor", 1.0)

            if global_offset != 0.0 or global_gain != 1.0:
                for r in range(res_h):
                    for c in range(res_w):
                        pixel_val = imperfect_image[r][c]
                        # Apply gain first, then offset
                        pixel_val = (pixel_val * global_gain) + global_offset
                        # Optional: Clamp to a plausible absolute temperature range, e.g., -273.15 C to a very high value
                        # pixel_val = max(-273.15, pixel_val)
                        imperfect_image[r][c] = round(pixel_val, 2)
        
        # 5. Temperature compensation errors for camera electronics (affecting overall offset/gain of the image)
        if self.environmental_compensation_params and \
           self.environmental_compensation_params.get("temperature") and \
           hasattr(environment_3d_state, 'get_temperature_celsius'):
            
            temp_comp_config = self.environmental_compensation_params["temperature"]
            ref_temp_c = temp_comp_config.get("reference_temp_c", 25.0)
            offset_per_celsius = temp_comp_config.get("global_offset_celsius_per_celsius", 0.0)
            # gain_factor_per_celsius = temp_comp_config.get("global_gain_factor_per_celsius", 0.0) # For future gain comp

            try:
                # Assuming sensor's own position is relevant for its electronics' temperature
                # This might be different from the scene temperature it's viewing.
                # For simplicity, using self.position_3d for ambient temp around sensor.
                ambient_temp_c = environment_3d_state.get_temperature_celsius(self.position_3d, self.sampling_volume)
                temp_delta_c = ambient_temp_c - ref_temp_c

                if offset_per_celsius != 0.0:
                    temp_induced_offset = offset_per_celsius * temp_delta_c
                    for r in range(res_h):
                        for c in range(res_w):
                            imperfect_image[r][c] += temp_induced_offset
                            imperfect_image[r][c] = round(imperfect_image[r][c], 2)
                
                # TODO: Implement gain compensation if gain_factor_per_celsius is added
                # if gain_factor_per_celsius != 0.0:
                #     temp_induced_gain_factor_delta = gain_factor_per_celsius * temp_delta_c
                #     current_gain_factor = 1.0 + temp_induced_gain_factor_delta
                #     # Clamp current_gain_factor if necessary
                #     for r in range(res_h):
                #         for c in range(res_w):
                #             imperfect_image[r][c] *= current_gain_factor
                #             imperfect_image[r][c] = round(imperfect_image[r][c], 2)

            except Exception as e:
                print(f"Warning: Could not apply thermal camera temperature compensation for {self.sensor_id}: {e}")
        elif self.environmental_compensation_params and \
             self.environmental_compensation_params.get("temperature") and \
             not hasattr(environment_3d_state, 'get_temperature_celsius'):
            print(f"Warning: Thermal camera temp comp config exists for {self.sensor_id} but env_state lacks 'get_temperature_celsius'. Skipping.")

        
        output_reading = {
            "thermal_image_celsius": imperfect_image,
            "resolution": true_reading["resolution"] # Pass along resolution
        }
        return output_reading

class EMFSensor(BaseSensor):
    def __init__(self, sensor_id: str, position_3d: Tuple[float, float, float], sampling_volume: Dict[str, Any], specific_params: Dict[str, Any], **kwargs):
        super().__init__(sensor_id, "emf_sensor", position_3d, sampling_volume, **kwargs)
        self.frequency_range_hz: List[float] = specific_params.get("frequency_range_hz", [50.0, 60.0])
        
        # Frequency-dependent response parameters
        self.frequency_response_gain: Dict[str, float] = specific_params.get("frequency_response_gain", {})
        
        tolerance = specific_params.get("frequency_tolerance_hz", 1.0)
        if not isinstance(tolerance, (int, float)) or tolerance < 0:
            raise ValueError(f"frequency_tolerance_hz for sensor {sensor_id} must be a non-negative number. Got: {tolerance}")
        self.frequency_tolerance_hz: float = float(tolerance)
        
        default_gain = specific_params.get("default_frequency_gain", 1.0)
        if not isinstance(default_gain, (int, float)):
            raise ValueError(f"default_frequency_gain for sensor {sensor_id} must be a number. Got: {default_gain}")
        self.default_frequency_gain: float = float(default_gain)

        # sampling_volume could define sensitivity pattern or effective range

    def get_frequency_gain(self, dominant_freq_hz: Any) -> float:
        """
        Get gain factor for a given dominant frequency based on sensor's
        frequency response configuration, including tolerance matching.
        Robust to non-numeric keys in config and non-numeric input dominant_freq_hz.
        Uses a configurable default gain.
        """
        if not isinstance(dominant_freq_hz, (int, float)):
            # print(f"Warning: Non-numeric dominant_frequency_hz ('{dominant_freq_hz}') for EMFSensor {self.sensor_id}. Using default gain: {self.default_frequency_gain}")
            return self.default_frequency_gain

        current_dominant_freq_float = float(dominant_freq_hz)

        # Attempt exact match first (keys are strings like "50.0", "60")
        try:
            # Try matching float string representation (e.g., "60.0")
            freq_str_exact = str(current_dominant_freq_float)
            if freq_str_exact in self.frequency_response_gain:
                return self.frequency_response_gain[freq_str_exact]
            
            # If it's a whole number, also try matching integer string representation (e.g., "60")
            if current_dominant_freq_float == float(int(current_dominant_freq_float)):
                freq_int_str_exact = str(int(current_dominant_freq_float))
                if freq_int_str_exact in self.frequency_response_gain:
                    return self.frequency_response_gain[freq_int_str_exact]
        except ValueError:
            # Should not be reached if initial isinstance check passes, but safeguard
            # print(f"Warning: Could not convert dominant_freq_hz '{current_dominant_freq_float}' to string for exact match for EMFSensor {self.sensor_id}.")
            pass # Proceed to tolerance matching

        # Tolerance-based matching
        for freq_key_str, gain in self.frequency_response_gain.items():
            try:
                config_freq_float = float(freq_key_str)
                if abs(current_dominant_freq_float - config_freq_float) <= self.frequency_tolerance_hz:
                    return gain
            except ValueError:
                # This key in config is not a valid float, skip it for tolerance matching.
                # print(f"Warning: Non-numeric key '{freq_key_str}' in frequency_response_gain for EMFSensor {self.sensor_id}. Skipping for tolerance match.")
                pass
            
        return self.default_frequency_gain

    def sample(self, environment_3d_state: Any) -> Dict[str, Any]:
        true_readings = self.get_ground_truth(environment_3d_state)
        if "error" in true_readings:
            return true_readings
        # Apply imperfections (noise, drift, frequency-dependent response, interference).
        return self.apply_imperfections(true_readings, environment_3d_state)

    def get_ground_truth(self, environment_3d_state: Any) -> Dict[str, Any]:
        if not self.ground_truth_capability:
            return {"error": "Ground truth not supported or enabled for this sensor."}

        if not hasattr(environment_3d_state, 'get_emf_characteristics_at_point'):
            print(f"Warning: environment_3d_state for EMFSensor {self.sensor_id} lacks 'get_emf_characteristics_at_point' method.")
            return {"error": "Environment state does not support EMF characteristics queries."}

        try:
            # Query the environment for EMF characteristics at the sensor's position
            # self.sampling_volume might influence the query (e.g., averaging over a small volume)
            emf_data = environment_3d_state.get_emf_characteristics_at_point(
                position=self.position_3d,
                frequency_range_hz=self.frequency_range_hz # Pass sensor's interest
                # sampling_details=self.sampling_volume # If needed by the environment
            )

            # Basic validation of returned data (example)
            if not isinstance(emf_data, dict) or \
               "ac_field_strength_v_per_m" not in emf_data or \
               "dominant_frequency_hz" not in emf_data:
                print(f"Error: EMF data from environment has unexpected format for {self.sensor_id}.")
                return {"error": "Received malformed EMF data from environment."}

            return emf_data # e.g., {"ac_field_strength_v_per_m": 0.1, "dominant_frequency_hz": 60.0, ...}

        except Exception as e:
            print(f"Error querying EMF characteristics for {self.sensor_id}: {e}")
            return {"error": f"Failed to get EMF characteristics: {e}"}

    def get_ml_metadata(self) -> Dict[str, Any]:
        return {
            "sensor_id": self.sensor_id,
            "type": self.sensor_type,
            "frequency_range_hz": self.frequency_range_hz,
            "frequency_response_gain": self.frequency_response_gain,
            "frequency_tolerance_hz": self.frequency_tolerance_hz,
            "default_frequency_gain": self.default_frequency_gain,
            # Include other relevant imperfection params from BaseSensor if set
            "noise_characteristics": self.noise_characteristics,
            "drift_parameters": self.drift_parameters,
            "calibration_artifacts": self.calibration_artifacts,
            "environmental_compensation_params": self.environmental_compensation_params
        }

    def apply_imperfections(self, true_reading: Dict[str, Any], environment_3d_state: Any) -> Dict[str, Any]:
        imperfect_reading = true_reading.copy()

        # 1. Frequency-Dependent Response (Applied first)
        if "ac_field_strength_v_per_m" in imperfect_reading:
            dominant_freq = imperfect_reading.get("dominant_frequency_hz") # Might be None or missing
            gain = self.get_frequency_gain(dominant_freq)
            if gain != 1.0: # Apply gain only if it's not neutral
                imperfect_reading["ac_field_strength_v_per_m"] *= gain
                imperfect_reading["ac_field_strength_v_per_m"] = max(0.0, round(imperfect_reading["ac_field_strength_v_per_m"], 4))
        
        # 2. Temperature Drift (Baseline drift on ac_field_strength_v_per_m)
        # Applied to the potentially frequency-adjusted value
        if self.drift_parameters and hasattr(environment_3d_state, 'simulation_time_seconds'):
            sim_time_hours = environment_3d_state.simulation_time_seconds / 3600.0
            
            baseline_drift_rate_map = self.drift_parameters.get("baseline_drift_v_per_m_per_hour", {})
            # sensitivity_drift_rate_map = self.drift_parameters.get("sensitivity_drift_percent_per_hour", {}) # For future

            if "ac_field_strength_v_per_m" in imperfect_reading:
                current_value = imperfect_reading["ac_field_strength_v_per_m"]
                
                # Apply baseline drift
                baseline_drift_rate = baseline_drift_rate_map.get("ac_field_strength_v_per_m", 0.0)
                total_baseline_drift = baseline_drift_rate * sim_time_hours
                current_value += total_baseline_drift
                
                # TODO: Apply sensitivity drift if configured
                # initial_sensitivity = 1.0
                # sensitivity_drift_factor_per_hour = sensitivity_drift_rate_map.get("ac_field_strength_v_per_m", 0.0) / 100.0
                # total_sensitivity_change_factor = sensitivity_drift_factor_per_hour * sim_time_hours
                # current_sensitivity = initial_sensitivity + total_sensitivity_change_factor
                # current_sensitivity = max(0.1, min(2.0, current_sensitivity))
                # current_value *= current_sensitivity
                
                imperfect_reading["ac_field_strength_v_per_m"] = max(0.0, round(current_value, 4)) # Ensure non-negative

        elif self.drift_parameters and not hasattr(environment_3d_state, 'simulation_time_seconds'):
            print(f"Warning: Drift params exist for EMFSensor {self.sensor_id} but env_state lacks 'simulation_time_seconds'. Skipping drift.")

        # 2. Noise (applied after drift)
        if self.noise_characteristics and self.noise_characteristics.get("type") == "gaussian":
            if "ac_field_strength_v_per_m" in imperfect_reading:
                mean = self.noise_characteristics.get("mean", 0.0)
                stddev = self.noise_characteristics.get("stddev_v_per_m", 0.0)
                if stddev > 0:
                    noise_val = random.gauss(mean, stddev)
                    imperfect_reading["ac_field_strength_v_per_m"] += noise_val
                    imperfect_reading["ac_field_strength_v_per_m"] = max(0.0, round(imperfect_reading["ac_field_strength_v_per_m"], 4))
        
        # TODO: Implement other EMF sensor specific imperfections:
        # - Frequency-dependent response
        # - Electromagnetic interference effects
        # - Calibration and orientation errors
        
        return imperfect_reading

class AcousticSensor(BaseSensor):
    def __init__(self, sensor_id: str, position_3d: Tuple[float, float, float], sampling_volume: Dict[str, Any], specific_params: Dict[str, Any], **kwargs):
        super().__init__(sensor_id, "acoustic_sensor", position_3d, sampling_volume, **kwargs)
        self.frequency_range_hz: List[float] = specific_params.get("frequency_range_hz", [20.0, 20000.0])
        # sampling_volume could define microphone directionality/sensitivity pattern

    def sample(self, environment_3d_state: Any) -> Dict[str, Any]:
        true_readings = self.get_ground_truth(environment_3d_state)
        # Apply imperfections (noise, frequency response variations, clipping).
        return self.apply_imperfections(true_readings, environment_3d_state)

    def get_ground_truth(self, environment_3d_state: Any) -> Dict[str, Any]:
        if not self.ground_truth_capability: return {"error": "Ground truth not supported."}
        # Placeholder: query environment for acoustic levels / specific signatures (e.g., arcing, corona)
        # This might return a waveform snippet or spectral data.
        return {"sound_pressure_level_db": 30.0, "dominant_frequencies_hz": [1000.0, 2500.0], "event_detected": "none"}

    def get_ml_metadata(self) -> Dict[str, Any]:
        return {
            "sensor_id": self.sensor_id,
            "type": self.sensor_type,
            "frequency_range_hz": self.frequency_range_hz
        }

    def apply_imperfections(self, true_reading: Dict[str, Any], environment_3d_state: Any) -> Dict[str, Any]:
        # Implement acoustic sensor specific imperfections
        # e.g., background noise, microphone frequency response, clipping, wind noise
        return true_reading.copy() # For stub

class VibrationSensor(BaseSensor):
    def __init__(self, sensor_id: str, position_3d: Tuple[float, float, float], sampling_volume: Dict[str, Any], specific_params: Dict[str, Any], **kwargs):
        super().__init__(sensor_id, "vibration_sensor", position_3d, sampling_volume, **kwargs)
        self.axes: List[str] = specific_params.get("axes", ["x", "y", "z"])
        self.sensitivity_g_per_hz: float = specific_params.get("sensitivity_g_per_hz", 0.01)
        # sampling_volume here might be less relevant, more about attachment point

    def sample(self, environment_3d_state: Any) -> Dict[str, Any]:
        true_readings = self.get_ground_truth(environment_3d_state)
        # Apply imperfections (noise, axis cross-talk, mounting resonance effects).
        return self.apply_imperfections(true_readings, environment_3d_state)

    def get_ground_truth(self, environment_3d_state: Any) -> Dict[str, Any]:
        if not self.ground_truth_capability: return {"error": "Ground truth not supported."}
        # Placeholder: query environment for vibration levels on each axis
        # This might return acceleration data (waveform or summary stats) for each axis.
        ground_truth_values = {axis: {"peak_g": 0.01, "rms_g": 0.005} for axis in self.axes}
        return {"vibration_g": ground_truth_values}

    def get_ml_metadata(self) -> Dict[str, Any]:
        return {
            "sensor_id": self.sensor_id,
            "type": self.sensor_type,
            "axes": self.axes,
            "sensitivity_g_per_hz": self.sensitivity_g_per_hz
        }

    def apply_imperfections(self, true_reading: Dict[str, Any], environment_3d_state: Any) -> Dict[str, Any]:
        # Implement vibration sensor specific imperfections
        # e.g., noise, axis cross-talk, mounting resonance effects, temperature effects on sensitivity
        return true_reading.copy() # For stub