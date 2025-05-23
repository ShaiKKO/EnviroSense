# EnviroSense™: EMFSensor Advanced Features for ML Data Generation

The `EMFSensor` within the EnviroSense™ digital twin is designed with several advanced features and configurable parameters. These facilitate the generation of diverse and realistic data suitable for training and testing machine learning models for electromagnetic field anomaly detection. This document provides notes on leveraging these features.

## 1. Configuring Core EMF Detection Parameters

When initializing an `EMFSensor` instance, the `specific_params` dictionary is crucial for controlling its behavior:

*   **`frequency_range_hz`** (List[float], optional): Defines the sensor's primary sensitivity range (e.g., `[50.0, 60.0]`). The `get_ground_truth` method uses this when querying the environment for baseline EMF characteristics.
    *   Example: `{"frequency_range_hz": [45.0, 65.0]}`
*   **`config` attribute**: All `specific_params` passed during initialization are stored in `sensor.config` and used throughout the sensor's methods to control various imperfections and behaviors.

## 2. Spectrum Analysis and Output

The sensor can generate and output a frequency spectrum, which is vital for detecting anomalies like arcing or corona discharge.

*   **`enable_spectrum_output`** (bool, default: `True` in `EMFSensor.__init__`): Controls whether the detailed `spectrum` dictionary is included in the sensor's final output from `apply_imperfections`. If `False`, the `spectrum` key will be removed.
    *   The output spectrum (if enabled) can include:
        *   `fundamental`: Strength of the base frequency.
        *   `harmonics`: A dictionary of harmonic strengths (e.g., `{"3th": value, "5th": value}`).
        *   `high_frequency_noise`: An indicator for corona discharge.
        *   `emi_noise_floor_contribution`: Noise added due to simulated EMI.
*   **`base_frequency`** (float, default: `60.0` in `EMFSensor.config`): Used by `_analyze_frequency_spectrum` as the fundamental frequency for calculating harmonic frequencies.
    *   Example: `{"base_frequency": 50.0}`
*   **`harmonic_N_ratio`** (float, default: `0.1` for 7th/9th, configurable for 3rd/5th via e.g., `harmonic_3_ratio`): Controls the relative strength of the Nth harmonic compared to the fundamental in `_analyze_frequency_spectrum`.
    *   Example: `{"harmonic_3_ratio": 0.15, "harmonic_5_ratio": 0.08}`
*   **`frequency_noise`** (bool, default: `True` in `EMFSensor.config`): If true, adds random noise to the calculated strength of harmonics during spectrum analysis.
    *   Example: `{"frequency_noise": False}`
*   **`corona_hf_noise_factor`** (float, default: `0.15` in `EMFSensor.config`): Multiplier for the fundamental strength to determine the `high_frequency_noise` level when corona discharge is detected (based on `environment_state.get_field_value('corona_discharge', ...)`).
    *   Example: `{"corona_hf_noise_factor": 0.25}`

## 3. Frequency-Dependent Response

The sensor models how its sensitivity changes with the dominant frequency of the measured field and how its internal components respond to different frequencies in a generated spectrum.

*   **For `get_frequency_gain` (used internally, e.g., if a single dominant frequency's gain is needed):**
    *   **`frequency_response_gain`** (Dict[str, float], default: `{}` in `EMFSensor.config`): Maps frequency strings (e.g., `"50.0"`, `"60"`) to gain multipliers.
    *   **`frequency_tolerance_hz`** (float, default: `1.0` in `EMFSensor.config`): Tolerance for matching a dominant frequency to keys in `frequency_response_gain`.
    *   **`default_frequency_gain`** (float, default: `1.0` in `EMFSensor.config`): Gain applied if no specific frequency matches within tolerance.
*   **For `_apply_frequency_response` (applied to the full spectrum):**
    *   **`frequency_response_curve`** (Dict[str, float], default: predefined curve in `_apply_frequency_response` method, can be overridden via `EMFSensor.config`): This dictionary dictates how different components of the *generated spectrum* (e.g., "fundamental", "3th", "high_frequency_noise") are attenuated or amplified.
        *   Example: `{"frequency_response_curve": {"fundamental": 0.95, "3th": 0.8, "high_frequency_noise": 0.2}}`
    *   **`frequency_response_temp_coeff_per_10c`** (float, default: `0.001` in `EMFSensor.config`): Temperature coefficient affecting the frequency response curve.
    *   **`frequency_response_ref_temp_c`** (float, default: `25.0` in `EMFSensor.config`): Reference temperature for the temperature coefficient.

## 4. Directional Sensitivity

Models how the sensor's orientation relative to the EMF vector affects the measured strength.

*   **`orientation`** (List[float], default: `[0,0,1]` (Z-axis) in `EMFSensor.config`): Defines the sensor's primary sensitivity axis.
*   **`orientation_uncertainty`** (bool, default: `True` in `EMFSensor.config`): If true, adds a small random variation to the alignment calculation.
*   **`orientation_uncertainty_stddev`** (float, default: `0.05` in `EMFSensor.config`): Standard deviation for the orientation uncertainty.
*   **`apply_directional_sensitivity_to_scalar`** (bool, default: `False` in `EMFSensor.config`): If `True` and only a scalar ground truth field strength is available (no vector), directional sensitivity will be applied assuming a dominant field direction.
*   **`assumed_dominant_field_direction`** (List[float], default: `[0,0,1]` in `EMFSensor.config`): Used if `apply_directional_sensitivity_to_scalar` is `True`.

## 5. Electromagnetic Interference (EMI) Effects

Simulates the impact of nearby EMI sources.

*   **`emi_sources_config`** (Dict[str, Any], default: `{"radius_m": 50.0}` in `EMFSensor.config`): Primarily used to pass the `radius_m` for querying nearby EMI sources from the environment.
*   **`emi_frequency_coupling_factor`** (float, default: `1000.0` in `EMFSensor.config`): Influences how strongly EMI from a source couples with the sensor based on frequency differences.
*   **`emi_spectrum_impact_factor`** (float, default: `0.1` in `EMFSensor.config`): Factor determining how much the total interference field contributes to the `emi_noise_floor_contribution` in the spectrum.
*   **`emi_field_strength_impact_factor`** (float, default: `1.0` in `EMFSensor.config`): Factor determining how much the total interference field directly adds to the measured `ac_field_strength_v_per_m`.
*   **`emi_field_strength_random_stddev`** (float, default: `0.2` in `EMFSensor.config`): Standard deviation for a random multiplier applied to the EMI's impact on field strength, simulating constructive/destructive interference variability.

## 6. Calibration Errors and Drift

Models inaccuracies and changes in sensor response over time.

*   **`calibration_gain_error_factor`** (float, default: `1.0` in `EMFSensor.config`): A base multiplicative error for the sensor's gain.
*   **`calibration_gain_drift_percent_per_hour`** (float, default: `0.0001` in `EMFSensor.config`): Percentage by which the gain drifts per hour.
*   **`calibration_offset_v_per_m`** (float, default: `0.0` in `EMFSensor.config`): A base additive offset error to the reading.
*   **`calibration_offset_drift_v_per_m_per_hour`** (float, default: `0.01` in `EMFSensor.config`): Amount the offset drifts per hour.
*   **`calibration_nonlinearity_factor`** (float, default: `0.0001` in `EMFSensor.config`): Factor for a simplified quadratic non-linearity term applied to the field strength.
*   **`axis_misalignment_effect_on_spectrum`** (bool, default: `False` in `EMFSensor.config`): If `True`, applies a reduction to all spectrum components based on `axis_misalignment_degrees`.
*   **`axis_misalignment_degrees`** (float, default: `1.0` in `EMFSensor.config`): The angle of misalignment used if the spectrum effect is enabled.
*   **General Drift (from `BaseSensor`'s `drift_parameters`)**: The `EMFSensor` also inherits `drift_parameters` (e.g., `{"baseline_drift_v_per_m_per_hour": {"ac_field_strength_v_per_m": 0.01}}`) which can apply a separate, general drift to `ac_field_strength_v_per_m` in `apply_imperfections`. This is distinct from the calibration-specific drifts.

## 7. Noise Characteristics

Standard noise modeling inherited from `BaseSensor`.

*   **`noise_characteristics`** (Dict, default: `None` from `BaseSensor`): Typically configured with `{"type": "gaussian", "mean": 0.0, "stddev_v_per_m": value}` to add Gaussian noise to the final `ac_field_strength_v_per_m`.

## 8. Ground Truth Anomaly Labeling

The `EMFSensor.get_ground_truth()` method attempts to generate anomaly labels by querying the `environment_state`:

*   **Corona Discharge**: Checks `environment_state.get_field_value('corona_discharge', self.position_3d)`.
    *   Configurable via: `corona_severity_scale` (float, default: `100.0`), `corona_confidence` (float, default: `0.9`).
*   **Arcing**: Checks `environment_state.get_field_value('arcing_intensity', self.position_3d)`.
    *   Configurable via: `arcing_severity_scale` (float, default: `50.0`), `arcing_confidence` (float, default: `0.85`).
*   **Overload**: Compares `ac_field_strength_v_per_m` against `overload_threshold_v_per_m`.
    *   Configurable via: `overload_threshold_v_per_m` (float, default: `500.0`), `overload_confidence` (float, default: `0.95`).

Scenarios are responsible for making the `environment_state` provide appropriate values for `'corona_discharge'` and `'arcing_intensity'` when these events occur, which the sensor then uses for labeling.

## Example `specific_params` for `EMFSensor`

```python
emf_sensor_params = {
    "frequency_range_hz": [40.0, 70.0],
    "enable_spectrum_output": True,
    "base_frequency": 50.0,
    "harmonic_3_ratio": 0.2,
    "orientation": [0.707, 0.707, 0.0], # Oriented in XY plane
    "orientation_uncertainty_stddev": 0.02,
    "emi_field_strength_impact_factor": 0.3,
    "calibration_gain_error_factor": 1.02,
    "calibration_offset_v_per_m": 0.05,
    "axis_misalignment_effect_on_spectrum": True,
    "axis_misalignment_degrees": 2.5,
    "noise_characteristics": {"type": "gaussian", "mean": 0.0, "stddev_v_per_m": 0.01},
    "drift_parameters": { # General drift from BaseSensor
        "baseline_drift_v_per_m_per_hour": {"ac_field_strength_v_per_m": 0.005}
    },
    # Parameters for anomaly labeling thresholds if defaults are not desired
    "corona_severity_scale": 120.0,
    "arcing_confidence": 0.9,
}

# emf_sensor = EMFSensor(sensor_id="emf001", ..., specific_params=emf_sensor_params)
```

By carefully configuring these parameters within scenarios and sensor setups, a wide variety of EMF data, including normal operation, various anomalies, and diverse noise/interference conditions, can be generated for robust ML model development.