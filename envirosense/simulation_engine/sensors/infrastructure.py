"""
This module will contain implementations for infrastructure monitoring sensors
such as ThermalCameraSensor, EMFSensor, AcousticSensor, VibrationSensor, etc.,
all inheriting from BaseSensor.
"""

import random # For noise generation
from typing import Dict, Any, Tuple, List
import numpy as np # For image array operations
import logging

logger = logging.getLogger(__name__)

try:
    from scipy.ndimage import gaussian_filter
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy.ndimage not found. Gaussian blur for ThermalCameraSensor will not be available.")

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
            logger.warning(f"environment_3d_state for ThermalCameraSensor {self.sensor_id} lacks 'get_thermal_field_view' method.")
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
                logger.error(f"Thermal field view from environment has unexpected dimensions for {self.sensor_id}.")
                return {"error": "Received malformed thermal image data from environment."}

            return {"thermal_image_celsius": thermal_image_array, "resolution": self.resolution.copy()}
            
        except Exception as e:
            logger.error(f"Error querying thermal field view for {self.sensor_id}: {e}", exc_info=True)
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
            logger.warning(f"EMA buffer dimensions mismatch for {self.sensor_id}. Re-initializing.")
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
                logger.warning(f"Could not apply thermal camera temperature compensation for {self.sensor_id}: {e}")
        elif self.environmental_compensation_params and \
             self.environmental_compensation_params.get("temperature") and \
             not hasattr(environment_3d_state, 'get_temperature_celsius'):
            logger.warning(f"Thermal camera temp comp config exists for {self.sensor_id} but env_state lacks 'get_temperature_celsius'. Skipping.")

        
        output_reading = {
            "thermal_image_celsius": imperfect_image,
            "resolution": true_reading["resolution"] # Pass along resolution
        }
        return output_reading

class EMFSensor(BaseSensor):
    def __init__(self, sensor_id: str, position_3d: Tuple[float, float, float], sampling_volume: Dict[str, Any], specific_params: Dict[str, Any], **kwargs):
        """
        Initializes an EMF (Electromagnetic Field) Sensor.

        Args:
            sensor_id (str): Unique identifier for the sensor.
            position_3d (Tuple[float, float, float]): 3D coordinates (x, y, z) of the sensor.
            sampling_volume (Dict[str, Any]): Defines the sensor's sampling characteristics (e.g., effective range).
            specific_params (Dict[str, Any]): Sensor-specific configuration parameters.
                Expected keys include:
                - "frequency_range_hz" (List[float], optional): Min and max frequency sensor is sensitive to. Default: [50.0, 60.0].
                - "frequency_response_gain" (Dict[str, float], optional): Gain factors for specific frequencies. Keys are frequency strings (e.g., "50.0"), values are gain multipliers. Default: {}.
                - "frequency_tolerance_hz" (float, optional): Tolerance for matching frequencies in `frequency_response_gain`. Default: 1.0.
                - "default_frequency_gain" (float, optional): Default gain if no specific frequency match. Default: 1.0.
                - "enable_spectrum_output" (bool, optional): Whether to include the 'spectrum' key in the output. Default: True.
                - "base_frequency" (float, optional): Nominal operating frequency (e.g., 50 or 60 Hz). Default: 60.0.
                - "harmonic_N_ratio" (float, optional): Ratio of Nth harmonic to fundamental (e.g., harmonic_3_ratio). Default: 0.1.
                - "frequency_noise" (bool, optional): Apply noise to harmonic strength. Default: True.
                - "corona_hf_noise_factor" (float, optional): Factor for high-frequency noise due to corona. Default: 0.15.
                - "orientation" (List[float], optional): Sensor's orientation vector [x,y,z]. Default: [0,0,1].
                - "orientation_uncertainty" (bool, optional): Apply uncertainty to orientation. Default: True.
                - "orientation_uncertainty_stddev" (float, optional): Std dev for orientation uncertainty. Default: 0.05.
                - "frequency_response_curve" (Dict[str, float], optional): Attenuation factors for spectrum components.
                - "frequency_response_temp_coeff_per_10c" (float, optional): Temperature coefficient for frequency response. Default: 0.001.
                - "frequency_response_ref_temp_c" (float, optional): Reference temperature for temp coefficient. Default: 25.0.
                - "emi_sources_config" (Dict[str, Any], optional): Configuration for EMI effects, e.g., {"radius_m": 50.0}.
                - "emi_frequency_coupling_factor" (float, optional): Factor for EMI frequency coupling. Default: 1000.0.
                - "emi_spectrum_impact_factor" (float, optional): Impact of EMI on spectrum noise floor. Default: 0.1.
                - "emi_field_strength_impact_factor" (float, optional): Impact of EMI on field strength reading. Default: 1.0.
                - "emi_field_strength_random_stddev" (float, optional): Std dev for random EMI effect on field strength. Default: 0.2.
                - "calibration_gain_error_factor" (float, optional): Multiplicative gain error. Default: 1.0.
                - "calibration_gain_drift_percent_per_hour" (float, optional): Gain drift rate in % per hour. Default: 0.0001.
                - "calibration_offset_v_per_m" (float, optional): Additive offset error in V/m. Default: 0.0.
                - "calibration_offset_drift_v_per_m_per_hour" (float, optional): Offset drift rate in V/m per hour. Default: 0.01.
                - "calibration_nonlinearity_factor" (float, optional): Factor for quadratic non-linearity. Default: 0.0001.
                - "axis_misalignment_effect_on_spectrum" (bool, optional): Apply misalignment effect to spectrum. Default: False.
                - "axis_misalignment_degrees" (float, optional): Angle of axis misalignment in degrees. Default: 1.0.
                - "apply_directional_sensitivity_to_scalar" (bool, optional): Apply directional sensitivity even if only scalar ground truth is available. Default: False.
                - "assumed_dominant_field_direction" (List[float], optional): Assumed field direction if only scalar ground truth. Default: [0,0,1].
                - "recalculate_harmonics_post_directionality" (bool, optional): Recalculate harmonics after directional sensitivity. Default: True.
                - "corona_severity_scale" (float, optional): Scale factor for corona severity label. Default: 100.0.
                - "corona_confidence" (float, optional): Confidence for corona anomaly label. Default: 0.9.
                - "arcing_severity_scale" (float, optional): Scale factor for arcing severity label. Default: 50.0.
                - "arcing_confidence" (float, optional): Confidence for arcing anomaly label. Default: 0.85.
                - "overload_threshold_v_per_m" (float, optional): Threshold for overload anomaly. Default: 500.0.
                - "overload_confidence" (float, optional): Confidence for overload anomaly label. Default: 0.95.
            **kwargs: Additional keyword arguments for BaseSensor.
        """
        super().__init__(sensor_id, "emf_sensor", position_3d, sampling_volume, **kwargs)
        self.config = specific_params 
        self.frequency_range_hz: List[float] = self.config.get("frequency_range_hz", [50.0, 60.0])
        self.frequency_response_gain: Dict[str, float] = self.config.get("frequency_response_gain", {})
        self.enable_spectrum_output: bool = self.config.get("enable_spectrum_output", True)
        
        tolerance = self.config.get("frequency_tolerance_hz", 1.0)
        if not isinstance(tolerance, (int, float)) or tolerance < 0:
            raise ValueError(f"frequency_tolerance_hz for sensor {sensor_id} must be a non-negative number. Got: {tolerance}")
        self.frequency_tolerance_hz: float = float(tolerance)
        
        default_gain = self.config.get("default_frequency_gain", 1.0)
        if not isinstance(default_gain, (int, float)):
            raise ValueError(f"default_frequency_gain for sensor {sensor_id} must be a number. Got: {default_gain}")
        self.default_frequency_gain: float = float(default_gain)

    def _calculate_drift(self, drift_type: str, base_rate: float, environment_state: Any) -> float:
        """
        Calculates the drift amount based on simulation time.

        Args:
            drift_type (str): Type of drift being calculated (e.g., "gain", "offset").
            base_rate (float): The base rate of drift (e.g., per hour).
            environment_state (Any): The current state of the simulation environment,
                                     expected to have 'simulation_time_seconds'.

        Returns:
            float: The calculated total drift amount. Returns 0.0 if simulation time is unavailable.
        """
        if not hasattr(environment_state, 'simulation_time_seconds'):
            logger.debug(f"Drift calculation for {self.sensor_id} ({drift_type}) skipped: env_state lacks 'simulation_time_seconds'.")
            return 0.0
        sim_time_hours = environment_state.simulation_time_seconds / 3600.0
        # More sophisticated drift models could be added here, e.g., using self.drift_parameters
        total_drift = base_rate * sim_time_hours
        return total_drift

    def _get_ambient_temperature(self, environment_state: Any) -> float:
        """
        Gets the ambient temperature at the sensor's location from the environment state.

        Args:
            environment_state (Any): The current state of the simulation environment,
                                     expected to have 'get_temperature_celsius'.

        Returns:
            float: Ambient temperature in Celsius. Returns a default (25.0 C) if unavailable.
        """
        default_temp_c = 25.0
        if environment_state and hasattr(environment_state, 'get_temperature_celsius'):
            try:
                ambient_temp_c = environment_state.get_temperature_celsius(self.position_3d, self.sampling_volume)
                return ambient_temp_c
            except Exception as e:
                logger.warning(f"Could not get ambient temperature for EMFSensor {self.sensor_id}: {e}. Using default {default_temp_c}C.")
                return default_temp_c
        logger.debug(f"EMFSensor {self.sensor_id} could not get ambient temperature: env_state lacks 'get_temperature_celsius' or was None. Using default {default_temp_c}C.")
        return default_temp_c

    def get_frequency_gain(self, dominant_freq_hz: Any) -> float:
        """
        Get gain factor for a given dominant frequency based on sensor's
        frequency response configuration, including tolerance matching.

        Args:
            dominant_freq_hz (Any): The dominant frequency to get gain for. Expected float or int.

        Returns:
            float: The gain factor for the given frequency. Uses default gain if no specific match.
        """
        if not isinstance(dominant_freq_hz, (int, float)):
            logger.debug(f"Non-numeric dominant_frequency_hz ('{dominant_freq_hz}') for EMFSensor {self.sensor_id}. Using default gain: {self.default_frequency_gain}")
            return self.default_frequency_gain
        current_dominant_freq_float = float(dominant_freq_hz)
        try: # Exact match for float string (e.g., "60.0") or int string (e.g., "60")
            freq_str_exact = str(current_dominant_freq_float)
            if freq_str_exact in self.frequency_response_gain:
                return self.frequency_response_gain[freq_str_exact]
            if current_dominant_freq_float == float(int(current_dominant_freq_float)): # Check if it's a whole number
                freq_int_str_exact = str(int(current_dominant_freq_float))
                if freq_int_str_exact in self.frequency_response_gain:
                    return self.frequency_response_gain[freq_int_str_exact]
        except ValueError: # Should not happen due to initial check, but safeguard
            logger.warning(f"Could not convert dominant_freq_hz '{current_dominant_freq_float}' to string for exact match for EMFSensor {self.sensor_id}.")
            pass # Proceed to tolerance matching
        
        for freq_key_str, gain_val in self.frequency_response_gain.items():
            try:
                config_freq_float = float(freq_key_str)
                if abs(current_dominant_freq_float - config_freq_float) <= self.frequency_tolerance_hz:
                    return gain_val
            except ValueError:
                logger.debug(f"Non-numeric key '{freq_key_str}' in frequency_response_gain for EMFSensor {self.sensor_id}. Skipping for tolerance match.")
                pass
        return self.default_frequency_gain

    def _analyze_frequency_spectrum(self, field_strength: float, environment_state: Any) -> Dict[str, Any]:
        """
        Analyzes or synthesizes an EMF frequency spectrum based on field strength and environment.
        Models fundamental, harmonics, and potential high-frequency noise from corona discharge.

        Args:
            field_strength (float): The magnitude of the fundamental field strength (e.g., in V/m).
            environment_state (Any): The current simulation environment state.

        Returns:
            Dict[str, Any]: A dictionary representing the spectrum, e.g.,
                            {'fundamental': float, 'harmonics': {'3th': float, ...}, 'high_frequency_noise': float (optional)}.
        """
        base_freq = self.config.get('base_frequency', 60.0)
        spectrum: Dict[str, Any] = {'fundamental': field_strength, 'harmonics': {}}
        for n in [3, 5, 7, 9]: # 3rd, 5th, 7th, 9th harmonics
            harmonic_strength = field_strength * (1.0 / n) * self.config.get(f'harmonic_{n}_ratio', 0.1)
            if self.config.get('frequency_noise', True):
                noise_factor = 1.0 + (np.random.normal(0, 0.02) * np.sqrt(n)) # Noise proportional to sqrt(harmonic_order)
                harmonic_strength *= noise_factor
            spectrum['harmonics'][f'{n}th'] = harmonic_strength
        
        corona_discharge_value = 0.0
        if hasattr(environment_state, 'get_field_value'):
            try:
                corona_discharge_value = environment_state.get_field_value('corona_discharge', self.position_3d)
            except Exception: # Catch if method exists but fails for this key/position
                logger.debug(f"Could not get 'corona_discharge' field value for {self.sensor_id}.")
                pass 
        if isinstance(corona_discharge_value, (int, float)) and corona_discharge_value > 0: # Check type before comparison
            spectrum['high_frequency_noise'] = field_strength * self.config.get('corona_hf_noise_factor', 0.15)
        return spectrum

    def _apply_directional_sensitivity(self, field_vector: np.ndarray, field_magnitude_override: float = None) -> float:
        """
        Models the directional sensitivity of the EMF sensor.
        The perceived field strength is modulated by the alignment between the
        field vector and the sensor's orientation.

        Args:
            field_vector (np.ndarray): The 3D vector of the electromagnetic field.
            field_magnitude_override (float, optional): If provided, this magnitude is used
                                                       instead of calculating from field_vector.
                                                       Useful if field_vector is just a direction.

        Returns:
            float: The field magnitude after applying directional sensitivity.
        """
        sensor_orientation = np.array(self.config.get('orientation', [0, 0, 1]), dtype=float)
        
        norm_field_vector = np.linalg.norm(field_vector)
        norm_sensor_orientation = np.linalg.norm(sensor_orientation)

        if norm_field_vector < 1e-9: return 0.0 # Handle zero field vector
        if norm_sensor_orientation < 1e-9: # Handle zero sensor orientation
             logger.warning(f"EMFSensor {self.sensor_id} has zero vector orientation. Directional sensitivity will result in 0 field strength.")
             return 0.0

        field_direction = field_vector / norm_field_vector
        sensor_norm = sensor_orientation / norm_sensor_orientation
        
        alignment_factor = abs(np.dot(field_direction, sensor_norm)) # Cosine sensitivity pattern
        
        if self.config.get('orientation_uncertainty', True):
            uncertainty_stddev = self.config.get('orientation_uncertainty_stddev', 0.05)
            uncertainty = np.random.normal(0, uncertainty_stddev)
            alignment_factor = np.clip(alignment_factor + uncertainty, 0, 1)
        
        field_magnitude = field_magnitude_override if field_magnitude_override is not None else norm_field_vector
        return field_magnitude * alignment_factor

    def _apply_frequency_response(self, spectrum: Dict[str, Any], environment_state: Any) -> Dict[str, Any]:
        """
        Applies frequency-dependent sensor response characteristics to a spectrum.
        Real sensors have varying sensitivity across frequency ranges, potentially
        affected by temperature.

        Args:
            spectrum (Dict[str, Any]): The input spectrum to modify.
            environment_state (Any): The current simulation environment state, for temperature.

        Returns:
            Dict[str, Any]: The spectrum after applying the frequency response.
        """
        response_curve = self.config.get('frequency_response_curve', {
            'fundamental': 1.0, '3th': 0.95, '5th': 0.85, '7th': 0.70, '9th': 0.50, 'high_frequency_noise': 0.30
        })
        
        temp = self._get_ambient_temperature(environment_state) # Pass environment_state
        temp_factor_per_10c = self.config.get('frequency_response_temp_coeff_per_10c', 0.001)
        reference_temp_for_coeff = self.config.get('frequency_response_ref_temp_c', 25.0)
        temp_factor = 1.0 - (abs(temp - reference_temp_for_coeff) / 10.0 * temp_factor_per_10c)
        temp_factor = np.clip(temp_factor, 0.5, 1.5) # Cap the temperature effect
        
        filtered_spectrum: Dict[str, Any] = {}
        for freq_component, value in spectrum.items():
            if freq_component == 'harmonics' and isinstance(value, dict):
                filtered_spectrum['harmonics'] = {}
                for harmonic, h_value in value.items():
                    if isinstance(h_value, (int, float)): # Ensure harmonic value is numeric
                        response = response_curve.get(harmonic, 0.5) # Default for unlisted harmonics
                        filtered_spectrum['harmonics'][harmonic] = h_value * response * temp_factor
                    else:
                        filtered_spectrum['harmonics'][harmonic] = h_value # Preserve non-numeric if any
            elif isinstance(value, (int, float)): # Handle fundamental, high_frequency_noise etc.
                response = response_curve.get(freq_component, 1.0) # Default for other components
                filtered_spectrum[freq_component] = value * response * temp_factor
            else: # Preserve other types of values if any
                filtered_spectrum[freq_component] = value
        return filtered_spectrum

    def _apply_emi_effects(self, reading: Dict[str, Any], environment_state: Any) -> Dict[str, Any]:
        """
        Simulates electromagnetic interference (EMI) from other sources affecting sensor readings.

        Args:
            reading (Dict[str, Any]): The current sensor reading data.
            environment_state (Any): The current simulation environment state.

        Returns:
            Dict[str, Any]: The reading data after applying EMI effects.
        """
        if not hasattr(environment_state, 'get_nearby_sources'):
            logger.debug(f"EMI effects for {self.sensor_id} skipped: env_state lacks 'get_nearby_sources'.")
            return reading
            
        emi_sources_config = self.config.get('emi_sources_config', {"radius_m": 50.0})
        radius = emi_sources_config.get("radius_m", 50.0)
        
        try:
            emi_sources = environment_state.get_nearby_sources('emi', self.position_3d, radius=radius)
        except Exception as e:
            logger.warning(f"Could not get EMI sources for {self.sensor_id}: {e}. Skipping EMI effects.")
            return reading
            
        total_interference_field = 0.0
        for source in emi_sources:
            source_position = source.get('position')
            if source_position is None: continue
            distance = np.linalg.norm(np.array(source_position) - np.array(self.position_3d))
            if distance < 1e-6: distance = 1e-6 # Avoid division by zero
            
            source_strength = source.get('strength', 1.0) # V/m or equivalent unit
            source_frequency = source.get('frequency', 1000.0)  # Hz
            
            base_sensor_freq = self.config.get('base_frequency', 60.0)
            freq_coupling_factor_param = self.config.get('emi_frequency_coupling_factor', 1000.0)
            # Ensure coupling factor is not zero to avoid division by zero if source_frequency == base_sensor_freq
            freq_coupling_denominator = max(1e-6, freq_coupling_factor_param)
            freq_coupling = np.exp(-abs(source_frequency - base_sensor_freq) / freq_coupling_denominator)
            
            interference_component = (source_strength * freq_coupling) / (distance**2 + 1.0) # +1 to avoid extreme values
            total_interference_field += interference_component
        
        emi_spectrum_impact = self.config.get('emi_spectrum_impact_factor', 0.1)
        emi_field_strength_impact = self.config.get('emi_field_strength_impact_factor', 1.0)
        
        if self.enable_spectrum_output and 'spectrum' in reading and isinstance(reading['spectrum'], dict):
            reading['spectrum']['emi_noise_floor_contribution'] = total_interference_field * emi_spectrum_impact
            
        if 'ac_field_strength_v_per_m' in reading and isinstance(reading['ac_field_strength_v_per_m'], (int, float)):
            random_effect_stddev = self.config.get('emi_field_strength_random_stddev', 0.2)
            random_interference_effect = np.random.normal(1.0, random_effect_stddev)
            reading['ac_field_strength_v_per_m'] += total_interference_field * emi_field_strength_impact * random_interference_effect
            reading['ac_field_strength_v_per_m'] = max(0, reading['ac_field_strength_v_per_m']) # Ensure non-negative
        return reading

    def _apply_calibration_errors(self, reading: Dict[str, Any], environment_state: Any) -> Dict[str, Any]:
        """
        Applies calibration errors to the sensor reading.
        Models gain error, offset error (both with drift), non-linearity,
        and a simplified axis misalignment effect on the spectrum.

        Args:
            reading (Dict[str, Any]): The current sensor reading data.
            environment_state (Any): The current simulation environment state.

        Returns:
            Dict[str, Any]: The reading data after applying calibration errors.
        """
        gain_error_config = self.config.get('calibration_gain_error_factor', 1.0)
        gain_drift_rate_ph = self.config.get('calibration_gain_drift_percent_per_hour', 0.0001) / 100.0
        gain_drift_factor = self._calculate_drift('gain', base_rate=gain_drift_rate_ph, environment_state=environment_state)
        actual_gain = gain_error_config * (1.0 + gain_drift_factor)
        
        offset_error_config = self.config.get('calibration_offset_v_per_m', 0.0)
        offset_drift_rate_ph = self.config.get('calibration_offset_drift_v_per_m_per_hour', 0.01)
        offset_drift_amount = self._calculate_drift('offset', base_rate=offset_drift_rate_ph, environment_state=environment_state)
        actual_offset = offset_error_config + offset_drift_amount
        
        nonlinearity_factor = self.config.get('calibration_nonlinearity_factor', 0.0001)
        
        if 'ac_field_strength_v_per_m' in reading and isinstance(reading['ac_field_strength_v_per_m'], (int, float)):
            field = reading['ac_field_strength_v_per_m']
            calibrated_field = actual_gain * field + actual_offset
            if abs(nonlinearity_factor) > 1e-9: # Apply non-linearity if factor is non-zero
                 calibrated_field += nonlinearity_factor * (field**2)
            reading['ac_field_strength_v_per_m'] = max(0, calibrated_field) # Ensure non-negative
            
        if self.enable_spectrum_output and 'spectrum' in reading and isinstance(reading['spectrum'], dict) and \
           self.config.get('axis_misalignment_effect_on_spectrum', False):
            misalignment_deg = self.config.get('axis_misalignment_degrees', 1.0)
            reduction_factor = np.cos(np.radians(misalignment_deg)) # Cosine of small angle is close to 1
            
            for key in reading['spectrum']:
                if isinstance(reading['spectrum'][key], (int, float)):
                    reading['spectrum'][key] *= reduction_factor
                elif key == 'harmonics' and isinstance(reading['spectrum'][key], dict):
                    for h_key in reading['spectrum'][key]:
                         if isinstance(reading['spectrum'][key][h_key], (int, float)):
                            reading['spectrum'][key][h_key] *= reduction_factor
        return reading

    def sample(self, environment_3d_state: Any) -> Dict[str, Any]:
        """
        Takes a sample from the environment, retrieves the ground truth,
        and then applies all configured imperfections.

        Args:
            environment_3d_state (Any): The current state of the simulation environment.

        Returns:
            Dict[str, Any]: The sensor reading after applying imperfections.
                           Returns a dict with an "error" key if ground truth fails.
        """
        true_readings = self.get_ground_truth(environment_3d_state)
        if "error" in true_readings:
            return true_readings
        return self.apply_imperfections(true_readings, environment_3d_state)

    def get_ground_truth(self, environment_state: Any) -> Dict[str, Any]:
        """
        Retrieves the ground truth EMF characteristics from the environment.
        This includes the AC field strength, potentially its vector, a true spectrum,
        and ML-specific anomaly labels (e.g., for corona, arcing, overload).

        Args:
            environment_state (Any): The current state of the simulation environment.
                                     Expected to have 'get_emf_characteristics_at_point'
                                     and optionally 'get_field_value'.

        Returns:
            Dict[str, Any]: A dictionary containing the ground truth data.
                            Includes "ac_field_strength_v_per_m", "anomaly_labels",
                            "spectrum_truth", and potentially "ac_field_vector_v_per_m".
                            Returns a dict with an "error" key on failure.
        """
        if not self.ground_truth_capability:
            return {"error": "Ground truth not supported or enabled for this sensor."}
        if not hasattr(environment_state, 'get_emf_characteristics_at_point'):
            logger.warning(f"environment_state for EMFSensor {self.sensor_id} lacks 'get_emf_characteristics_at_point' method.")
            return {"error": "Environment state does not support EMF characteristics queries."}
        try:
            emf_data = environment_state.get_emf_characteristics_at_point(
                position=self.position_3d,
                frequency_range_hz=self.frequency_range_hz
            )
            if not isinstance(emf_data, dict) or "ac_field_strength_v_per_m" not in emf_data:
                logger.error(f"EMF data from environment for {self.sensor_id} has unexpected format or is missing 'ac_field_strength_v_per_m'. Data: {emf_data}")
                return {"error": "Received malformed EMF data (missing field strength) from environment."}
            
            ground_truth_output = emf_data.copy()
            anomaly_labels = {'anomaly_type': 'none', 'severity': 0.0, 'confidence': 1.0}
            field_strength_gt = ground_truth_output.get("ac_field_strength_v_per_m", 0.0)

            if hasattr(environment_state, 'get_field_value'):
                try:
                    corona = environment_state.get_field_value('corona_discharge', self.position_3d)
                    if isinstance(corona, (int,float)) and corona > 0:
                        anomaly_labels['anomaly_type'] = 'corona_discharge'
                        anomaly_labels['severity'] = min(1.0, corona / self.config.get('corona_severity_scale', 100.0))
                        anomaly_labels['confidence'] = self.config.get('corona_confidence', 0.9)
                except Exception as e_corona:
                    logger.debug(f"Could not get/process 'corona_discharge' for {self.sensor_id}: {e_corona}")
                    pass # Keep default anomaly_labels
                try:
                    arcing = environment_state.get_field_value('arcing_intensity', self.position_3d)
                    if isinstance(arcing, (int,float)) and arcing > 0:
                        anomaly_labels['anomaly_type'] = 'arcing'
                        anomaly_labels['severity'] = min(1.0, arcing / self.config.get('arcing_severity_scale', 50.0))
                        anomaly_labels['confidence'] = self.config.get('arcing_confidence', 0.85)
                except Exception as e_arcing:
                    logger.debug(f"Could not get/process 'arcing_intensity' for {self.sensor_id}: {e_arcing}")
                    pass # Keep default anomaly_labels
            
            overload_threshold = self.config.get('overload_threshold_v_per_m', 500.0)
            if field_strength_gt > overload_threshold:
                anomaly_labels['anomaly_type'] = 'overload'
                anomaly_labels['severity'] = min(1.0, (field_strength_gt - overload_threshold) / overload_threshold)
                anomaly_labels['confidence'] = self.config.get('overload_confidence', 0.95)
            
            ground_truth_output['anomaly_labels'] = anomaly_labels
            ground_truth_output['spectrum_truth'] = self._analyze_frequency_spectrum(field_strength_gt, environment_state)
            return ground_truth_output
        except Exception as e:
            logger.error(f"Error querying EMF characteristics for {self.sensor_id}: {e}", exc_info=True)
            return {"error": f"Failed to get EMF characteristics: {e}"}

    def get_ml_metadata(self) -> Dict[str, Any]:
        """
        Returns metadata about the sensor relevant for ML training and data interpretation.
        Includes base sensor metadata and EMF-specific configurations.
        """
        base_metadata = {}
        # Ensure super().get_ml_metadata is callable and exists
        if hasattr(super(), 'get_ml_metadata') and callable(getattr(super(), 'get_ml_metadata', None)):
             base_metadata = super().get_ml_metadata() # type: ignore
        
        # Explicitly add core BaseSensor properties if not covered by super() or to ensure they are present
        base_metadata['sensor_id'] = self.sensor_id
        base_metadata['type'] = self.sensor_type
        base_metadata['position_3d'] = self.position_3d
        base_metadata['sampling_volume'] = self.sampling_volume
        base_metadata['ground_truth_capability'] = self.ground_truth_capability
        base_metadata['noise_characteristics'] = self.noise_characteristics
        base_metadata['drift_parameters'] = self.drift_parameters
        base_metadata['calibration_artifacts'] = self.calibration_artifacts
        base_metadata['environmental_compensation_params'] = self.environmental_compensation_params
        
        base_metadata.update({
            "frequency_range_hz": self.frequency_range_hz,
            "frequency_response_gain_config": self.frequency_response_gain,
            "frequency_tolerance_hz": self.frequency_tolerance_hz,
            "default_frequency_gain": self.default_frequency_gain,
            "enable_spectrum_output": self.enable_spectrum_output,
            "config_params": self.config, # Exposes all specific params used by this sensor
        })
        return base_metadata

    def apply_imperfections(self, true_reading: Dict[str, Any], environment_3d_state: Any) -> Dict[str, Any]:
        """
        Applies a series of configured imperfections to the true sensor reading.
        The order of application is:
        1. Directional Sensitivity (if vector data available or scalar application enabled).
        2. Spectrum Generation & Frequency Response (based on direction-adjusted strength).
        3. Calibration Errors (gain, offset, non-linearity, axis misalignment on spectrum).
        4. General Drift (on field strength, distinct from calibration drift).
        5. EMI Effects.
        6. Final Noise (on field strength).

        Args:
            true_reading (Dict[str, Any]): The ground truth sensor data.
            environment_3d_state (Any): The current simulation environment state.

        Returns:
            Dict[str, Any]: The sensor reading after all imperfections are applied.
        """
        imperfect_reading = true_reading.copy()
        if "ac_field_strength_v_per_m" not in imperfect_reading or not isinstance(imperfect_reading["ac_field_strength_v_per_m"], (int, float)):
            logger.warning(f"Missing or invalid 'ac_field_strength_v_per_m' in true_reading for {self.sensor_id}. Skipping imperfections.")
            return imperfect_reading # Return early if essential data is missing
        
        current_field_strength = imperfect_reading["ac_field_strength_v_per_m"]
        true_field_vector = imperfect_reading.get('ac_field_vector_v_per_m') 

        # 1. Directional Sensitivity
        if true_field_vector is not None and isinstance(true_field_vector, (list, np.ndarray)) and len(true_field_vector) == 3:
            try:
                current_field_strength = self._apply_directional_sensitivity(np.array(true_field_vector, dtype=float))
            except Exception as e_dir_sens:
                logger.warning(f"Error applying directional sensitivity with vector for {self.sensor_id}: {e_dir_sens}")
                # Keep current_field_strength as is from scalar ground truth
        elif self.config.get('apply_directional_sensitivity_to_scalar', False):
            dominant_dir_config = self.config.get('assumed_dominant_field_direction', [0,0,1])
            if not (isinstance(dominant_dir_config, list) and len(dominant_dir_config) == 3 and all(isinstance(c, (int,float)) for c in dominant_dir_config)):
                logger.warning(f"Invalid 'assumed_dominant_field_direction' for {self.sensor_id}. Using default [0,0,1].")
                dominant_dir_config = [0,0,1] # Fallback
            try:
                assumed_field_vector = np.array(dominant_dir_config, dtype=float) * current_field_strength
                current_field_strength = self._apply_directional_sensitivity(assumed_field_vector, field_magnitude_override=current_field_strength)
            except Exception as e_dir_sens_scalar:
                 logger.warning(f"Error applying directional sensitivity with scalar for {self.sensor_id}: {e_dir_sens_scalar}")
        imperfect_reading["ac_field_strength_v_per_m"] = current_field_strength

        # 2. Spectrum Generation & Frequency Response
        if self.enable_spectrum_output:
            base_spectrum_for_sensor_response: Dict[str, Any]
            # Use 'spectrum_truth' if available, but ensure its 'fundamental' matches the (potentially direction-adjusted) current_field_strength
            if 'spectrum_truth' in imperfect_reading and isinstance(imperfect_reading['spectrum_truth'], dict):
                base_spectrum_for_sensor_response = imperfect_reading['spectrum_truth'].copy()
                base_spectrum_for_sensor_response['fundamental'] = current_field_strength # Update fundamental
                # Optionally recalculate harmonics based on new fundamental if configured
                if self.config.get('recalculate_harmonics_post_directionality', True):
                    temp_spectrum_recalc = self._analyze_frequency_spectrum(current_field_strength, environment_3d_state)
                    base_spectrum_for_sensor_response['harmonics'] = temp_spectrum_recalc.get('harmonics', {})
            else: # Synthesize spectrum if not in ground truth
                base_spectrum_for_sensor_response = self._analyze_frequency_spectrum(current_field_strength, environment_3d_state)
            
            imperfect_reading['spectrum'] = self._apply_frequency_response(base_spectrum_for_sensor_response, environment_3d_state)
            
            # Update ac_field_strength_v_per_m based on the (potentially attenuated) fundamental in the imperfect spectrum
            if 'spectrum' in imperfect_reading and isinstance(imperfect_reading['spectrum'], dict) and \
               'fundamental' in imperfect_reading['spectrum'] and isinstance(imperfect_reading['spectrum']['fundamental'], (int, float)):
                imperfect_reading['ac_field_strength_v_per_m'] = imperfect_reading['spectrum']['fundamental']
        else: # If spectrum output is disabled
            imperfect_reading.pop('spectrum', None)


        # 3. Calibration Errors (Gain, Offset, Non-linearity, Axis Misalignment on spectrum if enabled)
        imperfect_reading = self._apply_calibration_errors(imperfect_reading, environment_3d_state)

        # 4. General Temperature Drift (distinct from calibration drift, applied to field strength)
        if self.drift_parameters and "baseline_drift_v_per_m_per_hour" in self.drift_parameters and \
           hasattr(environment_3d_state, 'simulation_time_seconds'):
            sim_time_hours = environment_3d_state.simulation_time_seconds / 3600.0
            # Assuming drift_parameters structure like: {"baseline_drift_v_per_m_per_hour": {"ac_field_strength_v_per_m": 0.01}}
            baseline_drift_rate_map = self.drift_parameters.get("baseline_drift_v_per_m_per_hour", {})
            if "ac_field_strength_v_per_m" in imperfect_reading and isinstance(imperfect_reading["ac_field_strength_v_per_m"], (int,float)):
                current_val_for_drift = imperfect_reading["ac_field_strength_v_per_m"]
                baseline_drift_rate = baseline_drift_rate_map.get("ac_field_strength_v_per_m", 0.0)
                total_baseline_drift_amount = baseline_drift_rate * sim_time_hours
                current_val_for_drift += total_baseline_drift_amount
                imperfect_reading["ac_field_strength_v_per_m"] = max(0.0, round(current_val_for_drift, 4))
        elif self.drift_parameters and "baseline_drift_v_per_m_per_hour" in self.drift_parameters: # Check if key exists before logging
             logger.debug(f"Drift params for baseline_drift_v_per_m_per_hour exist for EMFSensor {self.sensor_id} but env_state lacks 'simulation_time_seconds'. Skipping this drift.")
        
        # 5. EMI Effects
        imperfect_reading = self._apply_emi_effects(imperfect_reading, environment_3d_state)
        
        # 6. Final Noise (Gaussian noise on the final field strength)
        if self.noise_characteristics and self.noise_characteristics.get("type") == "gaussian":
            if "ac_field_strength_v_per_m" in imperfect_reading and isinstance(imperfect_reading["ac_field_strength_v_per_m"], (int,float)):
                mean = self.noise_characteristics.get("mean", 0.0)
                stddev = self.noise_characteristics.get("stddev_v_per_m", 0.0)
                if stddev > 0:
                    noise_val = random.gauss(mean, stddev)
                    imperfect_reading["ac_field_strength_v_per_m"] += noise_val
                    imperfect_reading["ac_field_strength_v_per_m"] = max(0.0, round(imperfect_reading["ac_field_strength_v_per_m"], 4))
        
        imperfect_reading.pop('spectrum_truth', None) # Remove ground truth spectrum from final output
        if not self.enable_spectrum_output: # Ensure spectrum is removed if disabled
            imperfect_reading.pop('spectrum', None)
            
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