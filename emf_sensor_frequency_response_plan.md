# Plan: Frequency-Dependent Response for EMFSensor

This document outlines the plan to implement frequency-dependent response for the `EMFSensor` in the EnviroSense Digital Twin simulation.

## 1. Feature Overview

The `EMFSensor`'s sensitivity to AC electric fields will vary based on the dominant frequency of the field. This models a common characteristic of real-world EMF sensors.

## 2. Configuration (`EMFSensor.__init__`)

The following parameters will be configurable via `specific_params` during sensor initialization:

*   **`frequency_response_gain` (dict, optional):**
    *   A dictionary mapping specific frequencies (as strings, e.g., "50.0", "60") to gain factors (float).
    *   Example: `{"50.0": 1.0, "60.0": 0.95, "120.0": 0.85}`
    *   Default: `{}` (empty dictionary, meaning no specific frequency gains are applied by default, and `default_frequency_gain` will be used unless a match is found).
    *   Stored as: `self.frequency_response_gain`

*   **`frequency_tolerance_hz` (float, optional):**
    *   The tolerance in Hz for matching a `dominant_frequency_hz` to a key in `frequency_response_gain`.
    *   Example: `0.5` (meaning a 59.7 Hz signal could match a "60.0" Hz key if tolerance is >= 0.3).
    *   Default: `1.0` Hz.
    *   **Validation:** Must be non-negative. A `ValueError` will be raised if a negative value is provided.
    *   Stored as: `self.frequency_tolerance_hz`

*   **`default_frequency_gain` (float, optional):**
    *   The gain factor to apply if the `dominant_frequency_hz` does not match any entry in `frequency_response_gain` (neither exactly nor within tolerance).
    *   Default: `1.0`.
    *   Stored as: `self.default_frequency_gain`

## 3. Implementation Logic

### 3.1. `get_frequency_gain(self, dominant_freq_hz: Any) -> float` method:

This new helper method within `EMFSensor` will determine the appropriate gain.

*   **Input:** `dominant_freq_hz` (can be `float`, `int`, `None`, or other types).
*   **Output:** `float` (the gain factor).
*   **Logic:**
    1.  **Input Validation:** If `dominant_freq_hz` is not an `int` or `float` (or is `None`), log a warning (e.g., "Non-numeric dominant_frequency_hz ('{dominant_freq_hz}') received by EMFSensor {self.sensor_id}. Using default gain: {self.default_frequency_gain}") and return `self.default_frequency_gain`.
    2.  Convert valid `dominant_freq_hz` to `current_dominant_freq_float`.
    3.  **Exact Match Attempt:**
        *   Try matching `str(current_dominant_freq_float)` (e.g., "60.0") in `self.frequency_response_gain`.
        *   If `current_dominant_freq_float` is a whole number, also try matching `str(int(current_dominant_freq_float))` (e.g., "60").
        *   If an exact match is found, return the corresponding gain.
    4.  **Tolerance-Based Match:** If no exact match:
        *   Iterate through `self.frequency_response_gain.items()`.
        *   For each `freq_key_str, gain_value` in the dictionary:
            *   Use a `try-except ValueError` block to attempt converting `freq_key_str` to `config_freq_float`.
            *   If conversion fails, log a warning (e.g., "Non-numeric key '{freq_key_str}' in frequency_response_gain for sensor {self.sensor_id}. Skipping for tolerance match.") and continue to the next key.
            *   If conversion succeeds, check if `abs(current_dominant_freq_float - config_freq_float) <= self.frequency_tolerance_hz`.
            *   If within tolerance, return `gain_value`.
    5.  **Fallback:** If no exact or tolerance-based match is found, return `self.default_frequency_gain`.

### 3.2. `EMFSensor.apply_imperfections` Method:

*   The frequency-dependent response will be the **first** imperfection applied.
*   The method will call `self.get_frequency_gain(imperfect_reading.get("dominant_frequency_hz"))`.
*   The returned gain will be multiplied with `imperfect_reading["ac_field_strength_v_per_m"]`.
*   Subsequent imperfections (Drift, Noise, etc.) will operate on this frequency-adjusted value.

**Proposed Order of All Imperfections in `EMFSensor.apply_imperfections`:**
1.  Frequency-Dependent Response (New)
2.  Calibration Errors (Systematic Offset/Gain) (Future)
3.  Temperature Drift (Existing)
4.  Electromagnetic Interference (EMI) (Future)
5.  Random Gaussian Noise (Existing)

## 4. Metadata (`EMFSensor.get_ml_metadata`)

The following will be added to the dictionary returned by `get_ml_metadata`:
*   `"frequency_response_gain": self.frequency_response_gain`
*   `"frequency_tolerance_hz": self.frequency_tolerance_hz`
*   `"default_frequency_gain": self.default_frequency_gain`

## 5. Unit Testing (`TestEMFSensor` in `test_infrastructure_sensors.py`)

*   **New Test Method: `test_emf_sensor_init_validation`**
    *   Verify that initializing `EMFSensor` with a negative `frequency_tolerance_hz` raises a `ValueError`.
    *   Verify that 0 or positive `frequency_tolerance_hz` is accepted.

*   **New/Enhanced Test Method: `test_emf_frequency_dependent_response`**
    *   Test Case 1: Exact frequency match (e.g., key "60.0", input 60.0 Hz) applies configured gain.
    *   Test Case 2: Exact frequency match with integer string key (e.g., key "60", input 60.0 Hz) applies configured gain.
    *   Test Case 3: Frequency match within tolerance (e.g., key "60.0", tolerance 1.0 Hz, input 60.5 Hz) applies configured gain.
    *   Test Case 4: Frequency outside tolerance of any configured numeric key uses `default_frequency_gain`.
    *   Test Case 5: `frequency_response_gain` config is empty (`{}`) uses `default_frequency_gain`.
    *   Test Case 6: `frequency_response_gain` parameter is `None` during init (should default to `{}`, then use `default_frequency_gain`).
    *   Test Case 7: `dominant_frequency_hz` input to `get_frequency_gain` is `None`; uses `default_frequency_gain` (check for warning log).
    *   Test Case 8: `dominant_frequency_hz` input is non-numeric string (e.g., "unknown"); uses `default_frequency_gain` (check for warning log).
    *   Test Case 9: A non-default `default_frequency_gain` (e.g., 0.95) is configured and correctly used when no other match.
    *   Test Case 10: `frequency_response_gain` contains non-numeric keys; ensure they are skipped gracefully (check for warning log) and valid numeric keys are still processed for tolerance matching.
    *   Test Case 11 (Order of Operations): Briefly verify that frequency response is applied before other existing imperfections like drift or noise (may require mocking intermediate steps or careful value calculation).

## 6. Documentation Updates

*   Update docstrings for `EMFSensor.__init__` and `EMFSensor.apply_imperfections`.
*   Add docstring for the new `get_frequency_gain` method.
*   Update sensor configuration examples to include these new parameters.
*   Update the main development plan document ([`digital-twin-sensor-array-development-plan.md`](digital-twin-sensor-array-development-plan.md)) to mark this sub-task as completed.