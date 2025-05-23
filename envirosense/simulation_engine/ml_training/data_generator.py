"""
This module will contain the MLDataGenerator class, responsible for
orchestrating the generation of ML training datasets using various scenarios
and sensor configurations.
"""

from typing import Dict, Any, List, Optional, Union, Callable
import time # For progress tracking or timestamping datasets
import pandas as pd # For DataFrame export
import os # For path joining and directory creation
import h5py # For HDF5 export
import json # For serializing complex objects for HDF5 and loading schemas
import numpy as np # For HDF5 string data
import uuid # For generating unique IDs for Avro records
import datetime # For timestamps in Avro records
import fastavro # For Avro serialization
import numbers # For type checking
import math # For math operations like sqrt, isclose

# Assuming VirtualGridGuardian will be imported
# from envirosense.simulation_engine.sensors import VirtualGridGuardian
from envirosense.simulation_engine.scenarios.base import BaseScenario # Adjusted import
# from envirosense.simulation_engine.physics_orchestrator import Environment3DOrchestrator # Or similar

# Define schema names for clarity (matching namespaces and names in .avsc files)
SRB_SCHEMA_NAME = "com.envirosense.schema.sensor.SensorReadingBase"
TR_SCHEMA_NAME = "com.envirosense.schema.sensor.ThermalReading"
VR_SCHEMA_NAME = "com.envirosense.schema.sensor.VOCReading"
EMFR_SCHEMA_NAME = "com.envirosense.schema.sensor.EMFReading"
AR_SCHEMA_NAME = "com.envirosense.schema.sensor.AcousticReading"
PMR_SCHEMA_NAME = "com.envirosense.schema.sensor.ParticulateMatterReading"
SRM_SCHEMA_NAME = "com.envirosense.schema.collection.SensorReadingsMap"
GTL_SCHEMA_NAME = "com.envirosense.schema.ml.GroundTruthLabels"
MLS_SCHEMA_NAME = "com.envirosense.schema.ml.MLDataSample"
SD_SCHEMA_NAME = "com.envirosense.schema.scenario.ScenarioDefinition"
SRP_SCHEMA_NAME = "com.envirosense.schema.scenario.ScenarioRunPackage"


class MLDataGenerator:
    """
    Orchestrates the generation of Machine Learning training datasets.

    This class takes a configured VirtualGridGuardian, a list of scenarios,
    and various generation parameters to produce datasets suitable for
    training detection algorithms. It incorporates data validation and
    flexible export options (Avro, DataFrame/CSV, HDF5).

    Internal `raw_sample` Contract:
    --------------------------------
    The `generate_*` methods (e.g., `generate_training_dataset`) produce a list
    of Python dictionaries, internally referred to as `raw_sample`. Each
    `raw_sample` dictionary represents a single data point before it's
    transformed into a final export format (e.g., Avro `MLDataSample`) by the
    `_export_data` method. The `_validate_generated_data` method also operates
    on this list of `raw_sample` dictionaries.

    The `raw_sample` dictionary is expected to have the following key structure:

    - `timestamp_scenario_seconds` (float):
        Simulation time in seconds from scenario start.
        *Source: `BaseScenario.current_time_seconds`*
    - `scenario_id` (str):
        Identifier of the source scenario.
        *Source: `BaseScenario.scenario_id`*
    - `sensor_readings` (Dict[str, Dict[str, Any]]):
        Sensor instance ID (str) to sensor reading payload (dict). Each payload
        MUST conform to its specific Avro sensor schema (e.g., `ThermalReading.avsc`).
        *Source: `VirtualGridGuardian.generate_training_sample()`*
    - `labels` (Dict[str, Any]):
        Ground truth labels. Keys/values MUST map to `GroundTruthLabels.avsc` fields.
        *Source: `VirtualGridGuardian.generate_training_sample()` (incorporating
        `BaseScenario.get_ground_truth_labels()`)*
    - `extracted_class_label` (Optional[str]):
        Simplified class label for stratification (e.g., 'NORMAL', 'FIRE').
        *Source: Populated by specific `generate_*` methods.*
    - `sample_metadata` (Optional[Dict[str, Any]]):
        Additional metadata (e.g., 'data_augmentation_type'). Values should be
        simple types (str, bool, number) or JSON-serializable.
        *Source: Populated by specific `generate_*` methods.*

    The `_export_data` method uses these `raw_sample` dictionaries to construct
    the final `MLDataSample` Avro records (generating `sample_id` and
    `generation_timestamp_utc` at export time) or to create flattened
    DataFrame/CSV representations.
    `generation_timestamp_utc` at the time of export.
    """

    def __init__(self,
                 grid_guardian: Any, # Should be VirtualGridGuardian instance
                 environment_orchestrator: Any, # Manages the 3D environment state
                 simulation_engine_version: str = "0.0.0-unknown",
                 default_time_step_seconds: float = 1.0,
                 default_output_dir: str = "ml_datasets",
                 schema_base_dir: str = "envirosense/schemas/avro/",
                 _parsed_schemas_for_testing: Optional[Dict[str, Any]] = None): # Added for testing
        """
        Initializes the MLDataGenerator.

        Args:
            grid_guardian: An initialized VirtualGridGuardian instance.
            environment_orchestrator: An instance capable of setting up and evolving
                                      the 3D environment based on scenario directives.
            simulation_engine_version: Version string of the external simulation engine.
            default_time_step_seconds: The default simulation time step for data generation.
            default_output_dir: Default directory to save generated datasets.
            schema_base_dir: Base directory where .avsc schema files are located.
            _parsed_schemas_for_testing: Optional. If provided, these schemas will be used
                                         instead of loading from `schema_base_dir`. For testing purposes.
        """
        self.grid_guardian = grid_guardian
        self.environment_orchestrator = environment_orchestrator
        self.simulation_engine_version = simulation_engine_version
        self.data_generator_version = "0.1.0" # Version of this MLDataGenerator
        self.default_time_step_seconds = default_time_step_seconds
        self.default_output_dir = default_output_dir
        self.schema_base_dir = schema_base_dir
        os.makedirs(self.default_output_dir, exist_ok=True)

        if _parsed_schemas_for_testing is not None:
            self.parsed_schemas: Dict[str, Any] = _parsed_schemas_for_testing
        else:
            self.parsed_schemas: Dict[str, Any] = {}
            self._load_all_schemas()
        
        self._ml_data_sample_schema_obj = self.parsed_schemas.get(MLS_SCHEMA_NAME)
        if not self._ml_data_sample_schema_obj:
            raise RuntimeError(f"Failed to load critical schema: {MLS_SCHEMA_NAME}. Parsed schemas: {list(self.parsed_schemas.keys())}")
        # self._scenario_run_package_schema_obj = self.parsed_schemas.get(SRP_SCHEMA_NAME) # For later use

    def _load_all_schemas(self):
        """Loads and parses all known Avro schemas in dependency order."""
        # Base and simple types first
        self._load_schema_file(SRB_SCHEMA_NAME, "SensorReadingBase.avsc")
        self._load_schema_file(GTL_SCHEMA_NAME, "GroundTruthLabels.avsc")
        self._load_schema_file(SD_SCHEMA_NAME, "ScenarioDefinition.avsc")

        # Sensor types (depend on SensorReadingBase being known to fastavro through parsed_schemas)
        self._load_schema_file(TR_SCHEMA_NAME, "ThermalReading.avsc")
        self._load_schema_file(VR_SCHEMA_NAME, "VOCReading.avsc")
        self._load_schema_file(EMFR_SCHEMA_NAME, "EMFReading.avsc")
        self._load_schema_file(AR_SCHEMA_NAME, "AcousticReading.avsc")
        self._load_schema_file(PMR_SCHEMA_NAME, "ParticulateMatterReading.avsc")
        
        # Collections and composite types
        self._load_schema_file(SRM_SCHEMA_NAME, "SensorReadingsMap.avsc")
        self._load_schema_file(MLS_SCHEMA_NAME, "MLDataSample.avsc")
        self._load_schema_file(SRP_SCHEMA_NAME, "ScenarioRunPackage.avsc")

    def _load_schema_file(self, schema_name: str, file_name: str):
        """Helper to load a single schema file and add it to parsed_schemas."""
        path = os.path.join(self.schema_base_dir, file_name)
        try:
            with open(path, 'r') as f:
                schema_json_def = json.load(f)
            # Pass all already parsed schemas to fastavro.parse_schema
            # to allow it to resolve named type references.
            self.parsed_schemas[schema_name] = fastavro.parse_schema(schema_json_def, self.parsed_schemas)
            print(f"Successfully loaded and parsed schema: {schema_name} from {file_name}")
        except FileNotFoundError:
            raise FileNotFoundError(f"Schema file not found: {path}. Ensure schema_base_dir is correct.")
        except Exception as e:
            raise RuntimeError(f"Error loading/parsing schema {schema_name} from {path}: {e}")

    def generate_training_dataset(self,
                                  scenarios: List[BaseScenario], 
                                  samples_per_scenario: Union[int, List[int]],
                                  output_format: str = "list_of_dicts", # "dataframe_csv", "dataframe_parquet", "hdf5", "avro"
                                  dataset_name: Optional[str] = None,
                                  imperfection_settings: Optional[Dict[str, Any]] = None,
                                  time_step_seconds: Optional[float] = None
                                 ) -> Any: # Return type depends on output_format (e.g., path, list, DataFrame)
        """
        Generates a training dataset by running specified scenarios.
        """
        current_time_step = time_step_seconds if time_step_seconds is not None else self.default_time_step_seconds
        all_generated_samples: List[Dict[str, Any]] = [] 

        if isinstance(samples_per_scenario, int):
            num_samples_list = [samples_per_scenario] * len(scenarios)
        elif isinstance(samples_per_scenario, list) and len(samples_per_scenario) == len(scenarios):
            num_samples_list = samples_per_scenario
        else:
            raise ValueError("samples_per_scenario must be an int or a list matching the length of scenarios.")

        print(f"Starting dataset generation for {len(scenarios)} scenarios...")

        for i, scenario_instance in enumerate(scenarios):
            target_samples = num_samples_list[i]
            print(f"  Running scenario: {scenario_instance.scenario_id} ({scenario_instance.name}) for {target_samples} samples...")
            
            scenario_instance.setup_environment(self.environment_orchestrator)
            
            # TODO: Apply imperfection_settings to self.grid_guardian sensors

            generated_count = 0
            # Assuming get_current_state() exists on environment_orchestrator
            while generated_count < target_samples and not scenario_instance.is_completed(self.environment_orchestrator.get_current_state()): 
                scenario_instance.update(current_time_step, self.environment_orchestrator)
                self.environment_orchestrator.update(current_time_step) 
                current_env_state = self.environment_orchestrator.get_current_state()

                # Upstream Contract:
                # - sensor_readings: Dict[str, Dict[str, Any]] from VirtualGridGuardian,
                #   where each inner dict MUST conform to its specific Avro sensor schema.
                # - scenario_and_sensor_labels: Dict[str, Any] from VirtualGridGuardian,
                #   which incorporates BaseScenario.get_ground_truth_labels() and MUST
                #   contain keys mappable to GroundTruthLabels.avsc fields.
                sensor_readings, scenario_and_sensor_labels = self.grid_guardian.generate_training_sample(
                    current_env_state,
                    scenario_labels=scenario_instance.get_ground_truth_labels(current_env_state)
                )
                
                # This is the raw internal format
                all_generated_samples.append({
                    "timestamp_scenario_seconds": scenario_instance.current_time_seconds,
                    "scenario_id": scenario_instance.scenario_id,
                    "sensor_readings": sensor_readings, # This is a dict from VirtualGridGuardian
                    "labels": scenario_and_sensor_labels # This is also a dict
                })
                generated_count += 1

                if generated_count % 100 == 0: 
                    print(f"    Generated {generated_count}/{target_samples} samples for {scenario_instance.scenario_id}...")
            
            print(f"  Finished scenario: {scenario_instance.scenario_id}. Generated {generated_count} samples.")

        print(f"Total samples generated: {len(all_generated_samples)}")
        
        validation_errors = self._validate_generated_data(all_generated_samples)
        if validation_errors:
            print(f"Warning: Data validation issues found: {validation_errors}")

        return self._export_data(all_generated_samples, output_format, dataset_name)

    def _validate_generated_data(self, data: List[Dict[str, Any]]) -> List[str]:
        """
        Performs comprehensive validation on the list of generated `raw_sample` dictionaries.

        This method iterates through each `raw_sample` and calls helper validation
        functions to check against rules inspired by `docs/DATA_GOVERNANCE.md` and
        the Avro schemas.

        Args:
            data: A list of `raw_sample` dictionaries to validate.

        Returns:
            A list of strings, where each string is a description of a validation error found.
            An empty list indicates no errors were found.
        """
        all_errors: List[str] = []
        if not data:
            all_errors.append("Validation Error: Dataset is empty.")
            return all_errors

        for i, raw_sample in enumerate(data):
            sample_errors = self._validate_single_raw_sample(raw_sample, i)
            all_errors.extend(sample_errors)

        if all_errors:
            # Log detailed errors for easier debugging
            print(f"Data validation found {len(all_errors)} issues:")
            for err_idx, err_msg in enumerate(all_errors):
                print(f"  Validation Error {err_idx + 1}: {err_msg}")
        else:
            print("Comprehensive data validation passed for all raw samples.")
        return all_errors

    def _validate_single_raw_sample(self, raw_sample: Dict[str, Any], sample_idx: int) -> List[str]:
        """Validates a single raw_sample dictionary."""
        errors: List[str] = []
        sample_prefix = f"Sample {sample_idx}:"

        if not isinstance(raw_sample, dict):
            errors.append(f"{sample_prefix} Is not a dictionary.")
            return errors # Stop further validation for this malformed sample

        # Validate top-level structure and required keys
        expected_top_level_keys = {"timestamp_scenario_seconds", "scenario_id", "sensor_readings", "labels"}
        missing_keys = expected_top_level_keys - raw_sample.keys()
        if missing_keys:
            errors.append(f"{sample_prefix} Missing top-level keys: {missing_keys}.")

        # Validate `scenario_id`
        scenario_id = raw_sample.get("scenario_id")
        if not isinstance(scenario_id, str) or not scenario_id:
            errors.append(f"{sample_prefix} 'scenario_id' must be a non-empty string, got: {scenario_id}.")

        # Validate `timestamp_scenario_seconds`
        ts_scenario_seconds = raw_sample.get("timestamp_scenario_seconds")
        if not isinstance(ts_scenario_seconds, numbers.Number) or ts_scenario_seconds < 0:
            errors.append(f"{sample_prefix} 'timestamp_scenario_seconds' must be a non-negative number, got: {ts_scenario_seconds}.")

        # Validate `extracted_class_label` (optional)
        extracted_label = raw_sample.get("extracted_class_label")
        if extracted_label is not None and not isinstance(extracted_label, str):
            errors.append(f"{sample_prefix} 'extracted_class_label' if present, must be a string, got: {type(extracted_label)}.")

        # Validate `sample_metadata` (optional)
        sample_meta = raw_sample.get("sample_metadata")
        if sample_meta is not None:
            if not isinstance(sample_meta, dict):
                errors.append(f"{sample_prefix} 'sample_metadata' if present, must be a dictionary, got: {type(sample_meta)}.")
            else:
                for k, v in sample_meta.items():
                    if not isinstance(v, (str, bool, int, float, numbers.Number, type(None))):
                        errors.append(f"{sample_prefix} 'sample_metadata' value for key '{k}' has invalid type {type(v)}. Must be simple type.")

        # Validate `sensor_readings`
        sensor_readings_dict = raw_sample.get("sensor_readings")
        if not isinstance(sensor_readings_dict, dict):
            errors.append(f"{sample_prefix} 'sensor_readings' is not a dictionary, got: {type(sensor_readings_dict)}.")
        else:
            for s_id, reading_payload in sensor_readings_dict.items(): # Renamed sensor_id to s_id for clarity
                if not isinstance(s_id, str) or not s_id:
                     errors.append(f"{sample_prefix} Sensor ID in 'sensor_readings' must be a non-empty string.")
                if not isinstance(reading_payload, dict):
                    errors.append(f"{sample_prefix} Reading payload for sensor '{s_id}' is not a dictionary.")
                    continue
                errors.extend(self._validate_sensor_reading_base_fields(reading_payload, sample_idx, s_id))
                errors.extend(self._validate_specific_sensor_reading(reading_payload, sample_idx, s_id))

        # Validate `labels` (GroundTruthLabels)
        labels_dict = raw_sample.get("labels")
        if not isinstance(labels_dict, dict):
            errors.append(f"{sample_prefix} 'labels' is not a dictionary, got: {type(labels_dict)}.")
        else:
            errors.extend(self._validate_ground_truth_labels_dict(labels_dict, sample_idx))
            
        return errors

    def _validate_sensor_reading_base_fields(self, reading_dict: Dict[str, Any], sample_idx: int, sensor_id_key: str) -> List[str]:
        """Validates fields common to SensorReadingBase. sensor_id_key is the key from the map."""
        errors: List[str] = []
        base_prefix = f"Sample {sample_idx}, Sensor '{sensor_id_key}' (Base):"

        # timestamp_usec
        ts_usec = reading_dict.get("timestamp_usec")
        if not isinstance(ts_usec, int) or ts_usec <= 0:
            errors.append(f"{base_prefix} 'timestamp_usec' must be a positive integer, got: {ts_usec}.")
        
        payload_sensor_id = reading_dict.get("sensor_id")
        if payload_sensor_id is not None: # SensorReadingBase.avsc has sensor_id, it should be in the payload
            if not isinstance(payload_sensor_id, str) or not payload_sensor_id:
                errors.append(f"{base_prefix} Payload 'sensor_id' field must be a non-empty string, got: '{payload_sensor_id}'.")
            elif payload_sensor_id != sensor_id_key:
                 errors.append(f"{base_prefix} Mismatch between map key sensor_id ('{sensor_id_key}') and payload field sensor_id ('{payload_sensor_id}').")
        else: # If sensor_id is not in the payload dict at all
            errors.append(f"{base_prefix} Payload missing 'sensor_id' field, expected from SensorReadingBase.")


        # latitude (optional in SensorReadingBase.avsc)
        latitude = reading_dict.get("latitude")
        if latitude is not None:
            if not isinstance(latitude, numbers.Number) or not (-90 <= latitude <= 90):
                errors.append(f"{base_prefix} 'latitude' must be a number between -90 and 90, got: {latitude}.")

        # longitude (optional in SensorReadingBase.avsc)
        longitude = reading_dict.get("longitude")
        if longitude is not None:
            if not isinstance(longitude, numbers.Number) or not (-180 <= longitude <= 180):
                errors.append(f"{base_prefix} 'longitude' must be a number between -180 and 180, got: {longitude}.")

        # altitude_m (optional in SensorReadingBase.avsc)
        altitude = reading_dict.get("altitude_m")
        if altitude is not None:
            if not isinstance(altitude, numbers.Number) or not (-500 <= altitude <= 10000): # Plausible range
                errors.append(f"{base_prefix} 'altitude_m' must be a number within plausible range (-500 to 10000), got: {altitude}.")
        return errors

    def _validate_specific_sensor_reading(self, reading_dict: Dict[str, Any], sample_idx: int, sensor_id: str) -> List[str]:
        """Dispatcher for specific sensor type validation rules based on key presence."""
        errors: List[str] = []
        prefix = f"Sample {sample_idx}, Sensor '{sensor_id}' (Specific):"

        # Infer type based on characteristic keys from DATA_GOVERNANCE.md
        # This is a heuristic. A more robust way might involve checking schema name if available.
        # For now, key presence is used as per the plan.
        if "spl_dba" in reading_dict or "frequency_bands_hz_spl_dba" in reading_dict:
            errors.extend(self._validate_acoustic_reading(reading_dict, prefix))
        elif "frequency_hz" in reading_dict and ("magnitude_v_m" in reading_dict or "magnitude_t" in reading_dict or "orientation_quaternion" in reading_dict): # EMF
            errors.extend(self._validate_emf_reading(reading_dict, prefix))
        elif "pm1_0_ug_m3" in reading_dict or "pm2_5_ug_m3" in reading_dict or "pm10_0_ug_m3" in reading_dict:
            errors.extend(self._validate_pm_reading(reading_dict, prefix))
        elif "temperature_c" in reading_dict: # Thermal is simple, check it before more complex ones if keys overlap
            errors.extend(self._validate_thermal_reading(reading_dict, prefix))
        elif "compound_id" in reading_dict and "concentration_ppb" in reading_dict: # VOC
            errors.extend(self._validate_voc_reading(reading_dict, prefix))
        # Add more specific sensor type detections if needed
        
        return errors

    def _validate_acoustic_reading(self, r: Dict[str, Any], p: str) -> List[str]:
        err: List[str] = []
        spl = r.get("spl_dba")
        if spl is not None and (not isinstance(spl, numbers.Number) or not (0 <= spl <= 194)):
            err.append(f"{p} 'spl_dba' must be a number between 0 and 194, got: {spl}.")
        
        bands = r.get("frequency_bands_hz_spl_dba")
        if bands is not None:
            if not isinstance(bands, dict):
                err.append(f"{p} 'frequency_bands_hz_spl_dba' must be a dict, got: {type(bands)}.")
            else:
                for freq_key, val in bands.items():
                    try:
                        # Avro map keys are strings. Convert to float for numeric check.
                        freq_num = float(freq_key)
                        if freq_num <= 0:
                            err.append(f"{p} Frequency key '{freq_key}' in 'frequency_bands_hz_spl_dba' must be positive.")
                    except ValueError:
                         err.append(f"{p} Frequency key '{freq_key}' in 'frequency_bands_hz_spl_dba' is not a valid number.")
                    if not isinstance(val, numbers.Number) or val < 0:
                        err.append(f"{p} SPL value for freq key '{freq_key}' must be non-negative, got: {val}.")
        return err

    def _validate_emf_reading(self, r: Dict[str, Any], p: str) -> List[str]:
        err: List[str] = []
        freq = r.get("frequency_hz")
        if freq is not None and (not isinstance(freq, numbers.Number) or freq <= 0):
            err.append(f"{p} 'frequency_hz' must be a positive number, got: {freq}.")
        
        mag_vm = r.get("magnitude_v_m")
        if mag_vm is not None and (not isinstance(mag_vm, numbers.Number) or mag_vm < 0):
            err.append(f"{p} 'magnitude_v_m' must be non-negative, got: {mag_vm}.")
        
        mag_t = r.get("magnitude_t")
        if mag_t is not None and (not isinstance(mag_t, numbers.Number) or mag_t < 0):
            err.append(f"{p} 'magnitude_t' must be non-negative, got: {mag_t}.")

        orient_q = r.get("orientation_quaternion")
        if orient_q is not None:
            if not isinstance(orient_q, list) or len(orient_q) != 4 or not all(isinstance(x, numbers.Number) for x in orient_q):
                err.append(f"{p} 'orientation_quaternion' must be a list of 4 numbers, got: {orient_q}.")
            else:
                try:
                    norm_sq = sum(x*x for x in orient_q) # type: ignore
                    if not math.isclose(norm_sq, 1.0, rel_tol=1e-5):
                        err.append(f"{p} 'orientation_quaternion' norm squared ({norm_sq}) is not close to 1.")
                except TypeError:
                     err.append(f"{p} 'orientation_quaternion' contains non-numeric values for norm calculation.")
        return err

    def _validate_pm_reading(self, r: Dict[str, Any], p: str) -> List[str]:
        err: List[str] = []
        pm1_0 = r.get("pm1_0_ug_m3")
        pm2_5 = r.get("pm2_5_ug_m3")
        pm10_0 = r.get("pm10_0_ug_m3")

        valid_pm1_0 = isinstance(pm1_0, numbers.Number) and pm1_0 >= 0
        valid_pm2_5 = isinstance(pm2_5, numbers.Number) and pm2_5 >= 0
        valid_pm10_0 = isinstance(pm10_0, numbers.Number) and pm10_0 >= 0

        if pm1_0 is not None and not valid_pm1_0:
            err.append(f"{p} 'pm1_0_ug_m3' must be non-negative number, got: {pm1_0}.")
        if pm2_5 is not None and not valid_pm2_5:
            err.append(f"{p} 'pm2_5_ug_m3' must be non-negative number, got: {pm2_5}.")
        if pm10_0 is not None and not valid_pm10_0:
            err.append(f"{p} 'pm10_0_ug_m3' must be non-negative number, got: {pm10_0}.")

        if valid_pm1_0 and valid_pm2_5 and pm1_0 > pm2_5: # type: ignore
            err.append(f"{p} Consistency check failed: pm1_0 ({pm1_0}) > pm2_5 ({pm2_5}).")
        if valid_pm2_5 and valid_pm10_0 and pm2_5 > pm10_0: # type: ignore
            err.append(f"{p} Consistency check failed: pm2_5 ({pm2_5}) > pm10_0 ({pm10_0}).")
        return err

    def _validate_thermal_reading(self, r: Dict[str, Any], p: str) -> List[str]:
        err: List[str] = []
        temp_c = r.get("temperature_c")
        if temp_c is not None and (not isinstance(temp_c, numbers.Number) or not (-273.15 <= temp_c <= 1000)): # Wider plausible upper range
            err.append(f"{p} 'temperature_c' must be a number in a plausible range (e.g., >= -273.15, <= 1000), got: {temp_c}.")
        return err

    def _validate_voc_reading(self, r: Dict[str, Any], p: str) -> List[str]:
        err: List[str] = []
        compound_id = r.get("compound_id")
        # Assuming compound_id should be a non-empty string if present.
        # Actual validation against a known list of VOCs is out of scope for this generic validator.
        if compound_id is not None and (not isinstance(compound_id, str) or not compound_id):
            err.append(f"{p} 'compound_id' must be a non-empty string, got: {compound_id}.")
        
        conc_ppb = r.get("concentration_ppb")
        if conc_ppb is not None and (not isinstance(conc_ppb, numbers.Number) or conc_ppb < 0):
            err.append(f"{p} 'concentration_ppb' must be non-negative number, got: {conc_ppb}.")
        return err

    def _validate_ground_truth_labels_dict(self, labels: Dict[str, Any], sample_idx: int) -> List[str]:
        """Validates the 'labels' dictionary part of a raw_sample, mapping to GroundTruthLabels.avsc."""
        errors: List[str] = []
        label_prefix = f"Sample {sample_idx}, Labels:"

        # event_type (String, required in Avro, but check if present in raw labels)
        event_type = labels.get("event_type")
        if event_type is None: # If it's not in raw_labels, it might be an issue for Avro export if required
             errors.append(f"{label_prefix} 'event_type' is missing from raw labels (required for Avro).")
        elif not isinstance(event_type, str) or not event_type:
            errors.append(f"{label_prefix} 'event_type' must be a non-empty string, got: '{event_type}'.")
        
        # event_subtype (Optional String)
        event_subtype = labels.get("event_subtype")
        if event_subtype is not None and (not isinstance(event_subtype, str) or not event_subtype):
             errors.append(f"{label_prefix} 'event_subtype' if present, must be a non-empty string, got: '{event_subtype}'.")

        # is_anomaly (Boolean, required in Avro, defaults to false)
        is_anomaly = labels.get("is_anomaly")
        if is_anomaly is None: # If not in raw_labels, Avro default will apply. No error here for raw validation.
            pass
        elif not isinstance(is_anomaly, bool):
            errors.append(f"{label_prefix} 'is_anomaly' must be a boolean, got: {type(is_anomaly)}.")

        # anomaly_severity_score (Optional Float)
        severity = labels.get("anomaly_severity_score")
        if severity is not None:
            if not isinstance(severity, numbers.Number) or not (0.0 <= severity <= 1.0):
                errors.append(f"{label_prefix} 'anomaly_severity_score' must be a number between 0.0 and 1.0, got: {severity}.")
        
        # anomaly_tags (Optional Array of Strings)
        tags = labels.get("anomaly_tags")
        if tags is not None:
            if not isinstance(tags, list) or not all(isinstance(t, str) and t for t in tags): # each tag non-empty
                errors.append(f"{label_prefix} 'anomaly_tags' must be a list of non-empty strings, got: {tags}.")

        # scenario_specific_details (Optional Map of String to SimpleType)
        details = labels.get("scenario_specific_details")
        if details is not None:
            if not isinstance(details, dict):
                errors.append(f"{label_prefix} 'scenario_specific_details' must be a dict, got: {type(details)}.")
            else:
                for k, v in details.items():
                    if not isinstance(k, str):
                         errors.append(f"{label_prefix} Key '{k}' in 'scenario_specific_details' is not a string.")
                    if not isinstance(v, (str, bool, int, float, numbers.Number, type(None))):
                        errors.append(f"{label_prefix} Value for key '{k}' in 'scenario_specific_details' has invalid type {type(v)}. Must be a simple type (string, boolean, number, or null).")
        
        # sensor_specific_ground_truth (Optional Map of String to Map)
        # This is complex; for now, just check if it's a dict of dicts if present.
        # Deeper validation would require knowing the schemas for sensor-specific ground truths.
        sensor_gt = labels.get("sensor_specific_ground_truth")
        if sensor_gt is not None:
            if not isinstance(sensor_gt, dict):
                errors.append(f"{label_prefix} 'sensor_specific_ground_truth' must be a dict, got: {type(sensor_gt)}.")
            else:
                for k, v_map in sensor_gt.items():
                    if not isinstance(k, str):
                        errors.append(f"{label_prefix} Key '{k}' in 'sensor_specific_ground_truth' is not a string.")
                    if not isinstance(v_map, dict):
                        errors.append(f"{label_prefix} Value for key '{k}' in 'sensor_specific_ground_truth' is not a dict, got: {type(v_map)}.")
        return errors

    def _export_data(self, data: List[Dict[str, Any]], output_format: str, dataset_name: Optional[str]) -> Any:
        """
        Handles exporting the generated data (list of `raw_sample` dicts) to the specified format.

        This method supports various output formats including:
        - "list_of_dicts": Returns the data as is.
        - "avro": Exports data as an Avro file conforming to `MLDataSample.avsc`.
        - "dataframe_csv": Exports data as a flattened CSV file via a Pandas DataFrame.
        - "dataframe_parquet": Exports data as a flattened Parquet file via a Pandas DataFrame.
        - "hdf5": Exports data to an HDF5 file.

        It populates necessary metadata like `sample_id` and `generation_timestamp_utc`
        for Avro exports and handles data flattening for DataFrame-based exports.

        Args:
            data: The list of `raw_sample` dictionaries to export.
            output_format: The desired output format string.
            dataset_name: An optional name for the dataset, used for file naming.
                          If None, a timestamped name is generated.

        Returns:
            The path to the exported file for file-based formats, the list of dicts
            for "list_of_dicts", or None if an error occurs that prevents export.
        """
        if dataset_name is None:
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            dataset_name = f"dataset_{timestamp_str}"

        if output_format == "list_of_dicts":
            return data
        elif output_format == "avro":
            if not self._ml_data_sample_schema_obj:
                print("CRITICAL ERROR: MLDataSample Avro schema not loaded. Cannot export to Avro.")
                # Consider raising an error here or returning a more indicative failure
                return None # Or raise RuntimeError

            avro_file_path = os.path.join(self.default_output_dir, f"{dataset_name}.avro")
            ml_data_samples_for_avro: List[Dict[str, Any]] = []
            export_errors: List[str] = []

            for idx, raw_sample in enumerate(data):
                try:
                    current_utc_ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
                    
                    # Ensure raw_sample components are dictionaries to prevent .get() errors on non-dicts
                    raw_sensor_readings = raw_sample.get("sensor_readings")
                    if not isinstance(raw_sensor_readings, dict):
                        export_errors.append(f"Sample {idx}: 'sensor_readings' is not a dict, found {type(raw_sensor_readings)}. Skipping sample for Avro.")
                        continue
                    
                    raw_labels = raw_sample.get("labels")
                    if not isinstance(raw_labels, dict):
                        export_errors.append(f"Sample {idx}: 'labels' is not a dict, found {type(raw_labels)}. Skipping sample for Avro.")
                        continue

                    # 1. Construct SensorReadingsMap part
                    sensor_readings_map_record = {
                        "map_timestamp_utc": current_utc_ts, # Consistent with MLDataSample generation time
                        "readings": raw_sensor_readings # Assumes this dict conforms to Avro map structure
                    }

                    # 2. Construct GroundTruthLabels part
                    # Ensure all required fields for GroundTruthLabels are present or have defaults handled by Avro
                    # or explicitly provided here.
                    # From GroundTruthLabels.avsc: event_type (string), is_anomaly (boolean) are required.
                    # scenario_id is also required.
                    gtl_scenario_id = raw_sample.get("scenario_id", "unknown_scenario_in_gtl")
                    gtl_event_type = raw_labels.get("event_type")
                    if gtl_event_type is None: # Required by schema
                        export_errors.append(f"Sample {idx}: 'event_type' missing in raw_labels. Defaulting to 'UNKNOWN_EVENT_TYPE' for Avro.")
                        gtl_event_type = "UNKNOWN_EVENT_TYPE"


                    ground_truth_labels_record = {
                        "label_timestamp_utc": current_utc_ts,
                        "scenario_id": gtl_scenario_id,
                        "event_type": gtl_event_type,
                        "event_subtype": raw_labels.get("event_subtype"), # Optional
                        "is_anomaly": raw_labels.get("is_anomaly", False), # Default if missing
                        "anomaly_severity_score": raw_labels.get("anomaly_severity_score"), # Optional
                        "anomaly_tags": raw_labels.get("anomaly_tags", []), # Default if missing
                        "scenario_specific_details": raw_labels.get("scenario_specific_details"), # Optional
                        "sensor_specific_ground_truth": raw_labels.get("sensor_specific_ground_truth") # Optional
                    }
                    
                    # 3. Construct MLDataSample record
                    ml_scenario_id = raw_sample.get("scenario_id", "unknown_scenario_in_ml_sample")
                    if ml_scenario_id == "unknown_scenario_in_ml_sample":
                         export_errors.append(f"Sample {idx}: 'scenario_id' missing in raw_sample. Defaulting for Avro.")
                    
                    ml_timestamp_sec = raw_sample.get("timestamp_scenario_seconds")
                    if ml_timestamp_sec is None:
                        export_errors.append(f"Sample {idx}: 'timestamp_scenario_seconds' missing. Defaulting to 0.0 for Avro.")
                        ml_timestamp_sec = 0.0


                    ml_sample_record = {
                        "sample_id": str(uuid.uuid4()),
                        "scenario_id": ml_scenario_id,
                        "scenario_timestep_seconds": ml_timestamp_sec,
                        "generation_timestamp_utc": current_utc_ts,
                        "sensor_readings_map": sensor_readings_map_record,
                        "ground_truth_labels": ground_truth_labels_record,
                        "extracted_class_label": raw_sample.get("extracted_class_label"), # Optional
                        "sample_metadata": raw_sample.get("sample_metadata") # Optional
                    }
                    ml_data_samples_for_avro.append(ml_sample_record)

                except KeyError as ke:
                    export_errors.append(f"Sample {idx}: KeyError during Avro record construction: {ke}. Skipping sample.")
                except TypeError as te:
                    export_errors.append(f"Sample {idx}: TypeError during Avro record construction: {te}. Skipping sample.")
                except Exception as e_rec: # Catch any other unexpected error for a single record
                    export_errors.append(f"Sample {idx}: Unexpected error during Avro record construction: {e_rec}. Skipping sample.")


            if export_errors:
                print(f"WARNING: Encountered {len(export_errors)} errors during Avro record preparation. Some samples may have been skipped or defaulted:")
                for err_msg in export_errors:
                    print(f"  - {err_msg}")
            
            if not ml_data_samples_for_avro:
                print("Error: No valid samples to write to Avro after processing. Aborting Avro export.")
                return None # Or raise

            try:
                with open(avro_file_path, "wb") as fo:
                    fastavro.writer(fo, self._ml_data_sample_schema_obj, ml_data_samples_for_avro)
                print(f"Dataset saved to Avro file: {avro_file_path}")
                return avro_file_path
            except fastavro.schema.SchemaValidationException as sve:
                print(f"CRITICAL AVRO SCHEMA ERROR writing to {avro_file_path}: {sve}")
                print("This usually means the data being written does not conform to the Avro schema.")
                print("Please check the `ml_data_samples_for_avro` structure against `MLDataSample.avsc`.")
                return None # Or raise
            except Exception as e_write:
                print(f"Error writing Avro file {avro_file_path}: {e_write}")
                return None # Or raise

        elif output_format == "dataframe_csv" or output_format == "dataframe_parquet":
            processed_samples_for_df: List[Dict[str, Any]] = []
            df_export_errors: List[str] = []

            for idx, raw_sample in enumerate(data):
                flat_sample: Dict[str, Any] = {}
                try:
                    # Core MLDataSample fields (excluding complex nested ones initially)
                    # Generate a sample_id here as it's good practice for tabular data too,
                    # even if MLDataSample.avsc's sample_id is primarily for Avro.
                    flat_sample["ml_sample_id"] = str(uuid.uuid4())
                    flat_sample["scenario_id"] = raw_sample.get("scenario_id")
                    flat_sample["scenario_timestep_seconds"] = raw_sample.get("timestamp_scenario_seconds")
                    # Add generation_timestamp_utc for consistency with Avro output
                    flat_sample["generation_timestamp_utc"] = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
                    flat_sample["extracted_class_label"] = raw_sample.get("extracted_class_label")

                    # Flatten sensor_readings
                    sensor_readings = raw_sample.get("sensor_readings")
                    if isinstance(sensor_readings, dict):
                        for sensor_id_key, reading_payload in sensor_readings.items():
                            if isinstance(reading_payload, dict):
                                for key, value in reading_payload.items():
                                    col_name = f"sensor_{sensor_id_key}_{key}" # Prefixed by sensor_id
                                    if isinstance(value, (list, dict)):
                                        try:
                                            flat_sample[col_name] = json.dumps(value) # Serialize complex types
                                        except TypeError: # Fallback for un-serializable objects
                                            flat_sample[col_name] = str(value)
                                            df_export_errors.append(f"Sample {idx}, Sensor {sensor_id_key}, Key {key}: JSON serialization failed. Used str().")
                                    else:
                                        flat_sample[col_name] = value
                            else:
                                df_export_errors.append(f"Sample {idx}: Sensor reading payload for '{sensor_id_key}' was not a dict: {type(reading_payload)}. Storing as string.")
                                flat_sample[f"sensor_{sensor_id_key}_payload_raw"] = str(reading_payload)
                    elif sensor_readings is not None: # If 'sensor_readings' exists but isn't a dict
                         df_export_errors.append(f"Sample {idx}: 'sensor_readings' was not a dict (type: {type(sensor_readings)}). Skipping its fields.")


                    # Flatten ground_truth_labels
                    labels = raw_sample.get("labels")
                    if isinstance(labels, dict):
                        for key, value in labels.items():
                            col_name = f"label_{key}"
                            if isinstance(value, (list, dict)):
                                try:
                                    flat_sample[col_name] = json.dumps(value)
                                except TypeError:
                                    flat_sample[col_name] = str(value)
                                    df_export_errors.append(f"Sample {idx}, Label {key}: JSON serialization failed. Used str().")
                            else:
                                flat_sample[col_name] = value
                    elif labels is not None:
                         df_export_errors.append(f"Sample {idx}: 'labels' was not a dict (type: {type(labels)}). Skipping its fields.")

                    # Flatten sample_metadata
                    sample_metadata = raw_sample.get("sample_metadata")
                    if isinstance(sample_metadata, dict):
                        for key, value in sample_metadata.items():
                            col_name = f"meta_{key}"
                            if isinstance(value, (list, dict)):
                                try:
                                    flat_sample[col_name] = json.dumps(value)
                                except TypeError:
                                    flat_sample[col_name] = str(value)
                                    df_export_errors.append(f"Sample {idx}, Meta {key}: JSON serialization failed. Used str().")
                            else:
                                flat_sample[col_name] = value
                    elif sample_metadata is not None:
                        df_export_errors.append(f"Sample {idx}: 'sample_metadata' was not a dict (type: {type(sample_metadata)}). Skipping its fields.")
                    
                    processed_samples_for_df.append(flat_sample)

                except Exception as e_flat: # Catch-all for unexpected errors during a single sample's flattening
                    df_export_errors.append(f"Sample {idx}: Critical error during flattening for DataFrame: {e_flat}. Skipping this sample.")
            
            if df_export_errors:
                print(f"WARNING: Encountered {len(df_export_errors)} issues during DataFrame/CSV preparation. Some data may have been altered or samples skipped:")
                for err_msg in df_export_errors:
                    print(f"  - {err_msg}")

            if not processed_samples_for_df:
                print("Error: No data to export to DataFrame after processing. Aborting DataFrame/CSV export.")
                return None # Or raise RuntimeError

            try:
                df = pd.DataFrame(processed_samples_for_df)
            except Exception as e_df: # Error creating DataFrame from the list of dicts
                print(f"CRITICAL: Error creating DataFrame from processed samples: {e_df}.")
                # As a last resort, try pandas' own json_normalize on the original data,
                # though this might not have the desired column naming or structure.
                print("Attempting DataFrame creation with pd.json_normalize on original data as a last resort...")
                try:
                    df = pd.json_normalize(data, sep='_') # Use original 'data'
                except Exception as e_norm:
                    print(f"CRITICAL: Fallback pd.json_normalize also failed: {e_norm}. Cannot export to DataFrame.")
                    return None # Or raise RuntimeError
            
            # Proceed to save the DataFrame
            if output_format == "dataframe_csv":
                file_path = os.path.join(self.default_output_dir, f"{dataset_name}.csv")
                try:
                    df.to_csv(file_path, index=False)
                    print(f"Dataset saved to CSV file: {file_path}")
                    return file_path
                except Exception as e_csv:
                    print(f"Error writing CSV file {file_path}: {e_csv}")
                    return None # Or raise
            elif output_format == "dataframe_parquet":
                file_path = os.path.join(self.default_output_dir, f"{dataset_name}.parquet")
                try:
                    # Parquet can handle various types; pyarrow is generally preferred.
                    df.to_parquet(file_path, index=False, engine='auto')
                    print(f"Dataset saved to Parquet file: {file_path}")
                    return file_path
                except Exception as e_parq: # Catch broad errors, could be missing engine, type issues etc.
                    print(f"Error saving to Parquet: {e_parq}. This might be due to complex data types not handled by the chosen engine, or the engine (e.g., 'pyarrow') not being installed.")
                    csv_fallback_path = os.path.join(self.default_output_dir, f"{dataset_name}_fallback.csv")
                    try:
                        df.to_csv(csv_fallback_path, index=False)
                        print(f"Dataset saved as CSV fallback to {csv_fallback_path} due to Parquet error.")
                        return csv_fallback_path
                    except Exception as e_csv_fallback:
                        print(f"Error writing CSV fallback file {csv_fallback_path}: {e_csv_fallback}")
                        return None # Or raise
            
        elif output_format == "hdf5":
            file_path = os.path.join(self.default_output_dir, f"{dataset_name}.h5")
            try:
                with h5py.File(file_path, 'w') as hf:
                    if not data:
                        print("Warning: No data to save to HDF5.")
                        return file_path 
                    all_keys = set()
                    for sample in data:
                        all_keys.update(sample.keys())
                    
                    for key in all_keys:
                        column_data = []
                        is_complex_type = False
                        for sample in data:
                            value = sample.get(key)
                            if isinstance(value, (dict, list)):
                                column_data.append(json.dumps(value)) 
                                is_complex_type = True
                            elif value is None:
                                column_data.append("") 
                            else:
                                column_data.append(value)
                        
                        try:
                            if is_complex_type or any(isinstance(x, str) for x in column_data):
                                dt = h5py.string_dtype(encoding='utf-8')
                                hf.create_dataset(key, data=np.array(column_data, dtype=dt))
                            else:
                                hf.create_dataset(key, data=column_data)
                        except Exception as e_ds:
                            print(f"Warning: Could not create HDF5 dataset for key '{key}'. Error: {e_ds}. Storing as string.")
                            dt = h5py.string_dtype(encoding='utf-8')
                            string_column_data = [str(sample.get(key, "")) for sample in data]
                            hf.create_dataset(key, data=np.array(string_column_data, dtype=dt))

                print(f"Dataset saved to {file_path}")
                return file_path
            except Exception as e_h5:
                print(f"Error saving to HDF5: {e_h5}. Try ensuring h5py is correctly installed.")
                return data 
        else:
            print(f"Warning: Output format '{output_format}' not yet fully implemented or recognized. Returning list of dicts.")
            return data
        
        return None

    def compute_dataset_statistics(self,
                                   dataset: List[Dict[str, Any]],
                                   label_key_for_distribution: str = "event_type"
                                  ) -> Dict[str, Any]:
        """
        Computes basic statistics for a given dataset (list of sample dicts).
        """
        if not dataset:
            return {"error": "Dataset is empty. No statistics computed."}

        stats: Dict[str, Any] = {
            "total_samples": len(dataset),
            "unique_scenarios": set(),
            "label_distribution": {},
            "sensor_reading_stats": {} 
        }

        label_counts: Dict[str, int] = {}
        sensor_values_to_track: Dict[str, List[float]] = {}
        if dataset[0].get("sensor_readings"):
            for sr_key, sr_val in dataset[0]["sensor_readings"].items():
                if isinstance(sr_val, (int, float)): 
                     sensor_values_to_track[f"reading.{sr_key}"] = []
                elif isinstance(sr_val, dict): 
                    for sub_sr_key, sub_sr_val in sr_val.items():
                        if isinstance(sub_sr_val, (int, float)):
                            sensor_values_to_track[f"reading.{sr_key}.{sub_sr_key}"] = []
                        if len(sensor_values_to_track) >= 5: break # Limit tracked sensor values
                if len(sensor_values_to_track) >= 5: break


        for sample in dataset:
            stats["unique_scenarios"].add(sample.get("scenario_id", "unknown_scenario"))
            
            labels = sample.get("labels", {})
            if isinstance(labels, dict):
                label_value = labels.get(label_key_for_distribution, "unknown_label")
                label_counts[label_value] = label_counts.get(label_value, 0) + 1
            
            sensor_readings = sample.get("sensor_readings", {})
            if isinstance(sensor_readings, dict):
                for key_to_track in sensor_values_to_track.keys():
                    path = key_to_track.split('.')
                    current_val = sensor_readings
                    try:
                        for p_item in path[1:]: 
                            current_val = current_val[p_item]
                        if isinstance(current_val, (int, float)):
                            sensor_values_to_track[key_to_track].append(float(current_val))
                    except (KeyError, TypeError):
                        pass 

        stats["unique_scenarios"] = list(stats["unique_scenarios"]) 
        stats["label_distribution"] = label_counts
        
        for key, values in sensor_values_to_track.items():
            if values:
                stats["sensor_reading_stats"][key] = {
                    "count": len(values),
                    "min": round(min(values), 3),
                    "max": round(max(values), 3),
                    "mean": round(sum(values) / len(values), 3),
                    "stddev": round(np.std(values), 3) if len(values) > 1 else 0.0
                }
            else:
                 stats["sensor_reading_stats"][key] = {"count": 0}


        print(f"Dataset statistics computed: {stats['total_samples']} samples, {len(stats['unique_scenarios'])} scenarios.")
        return stats
    
    def generate_balanced_dataset(self,
                                  scenarios_and_configs: List[Dict[str, Any]], 
                                  label_extractor: Callable[[Dict[str, Any]], str], 
                                  output_format: str = "list_of_dicts",
                                  dataset_name: Optional[str] = None,
                                  imperfection_settings: Optional[Dict[str, Any]] = None,
                                  time_step_seconds: Optional[float] = None,
                                  max_samples_per_scenario_run: int = 10000
                                 ) -> Any:
        """
        Generates a dataset attempting to balance classes based on specified labels.
        """
        current_time_step = time_step_seconds if time_step_seconds is not None else self.default_time_step_seconds
        
        collected_samples_by_class: Dict[str, List[Dict[str, Any]]] = {}
        samples_needed_by_class: Dict[str, int] = {}
        
        for config in scenarios_and_configs:
            target_val = config["target_label_value"]
            samples_needed = config["samples_needed"]
            if target_val not in samples_needed_by_class:
                samples_needed_by_class[target_val] = 0
            samples_needed_by_class[target_val] += samples_needed
            if target_val not in collected_samples_by_class:
                collected_samples_by_class[target_val] = []

        print(f"Starting balanced dataset generation. Targets: {samples_needed_by_class}")

        for config_idx, config_item in enumerate(scenarios_and_configs):
            scenario_instance = config_item["scenario"]
            target_label_key = config_item["target_label_key"]
            target_label_value = config_item["target_label_value"] 
            
            if len(collected_samples_by_class.get(target_label_value, [])) >= samples_needed_by_class.get(target_label_value, 0):
                print(f"  Already have enough samples for '{target_label_value}'. Skipping scenario {scenario_instance.scenario_id}.")
                continue

            print(f"  Running scenario for balancing: {scenario_instance.scenario_id} (targets {target_label_key}=='{target_label_value}')")
            scenario_instance.setup_environment(self.environment_orchestrator)
            # TODO: Apply imperfection_settings

            generated_this_run = 0
            while generated_this_run < max_samples_per_scenario_run and \
                  len(collected_samples_by_class.get(target_label_value, [])) < samples_needed_by_class.get(target_label_value, 0) and \
                  not scenario_instance.is_completed(self.environment_orchestrator.get_current_state()):

                scenario_instance.update(current_time_step, self.environment_orchestrator)
                self.environment_orchestrator.update(current_time_step)
                current_env_state = self.environment_orchestrator.get_current_state()
                
                # Upstream Contract: (Same as in generate_training_dataset)
                # - sensor_readings: Dict from VirtualGridGuardian (Avro-compatible sensor data)
                # - full_labels: Dict from VirtualGridGuardian (GroundTruthLabels.avsc compatible)
                sensor_readings, full_labels = self.grid_guardian.generate_training_sample(
                    current_env_state,
                    scenario_labels=scenario_instance.get_ground_truth_labels(current_env_state)
                )
                
                extracted_class_label = label_extractor(full_labels)

                if extracted_class_label == target_label_value:
                    if len(collected_samples_by_class.get(target_label_value, [])) < samples_needed_by_class.get(target_label_value, 0):
                        sample_data = {
                            "timestamp_scenario_seconds": scenario_instance.current_time_seconds,
                            "scenario_id": scenario_instance.scenario_id,
                            "sensor_readings": sensor_readings,
                            "labels": full_labels,
                            "extracted_class_label": extracted_class_label 
                        }
                        collected_samples_by_class.setdefault(extracted_class_label, []).append(sample_data)
                
                elif extracted_class_label in samples_needed_by_class and \
                     len(collected_samples_by_class.get(extracted_class_label, [])) < samples_needed_by_class.get(extracted_class_label, 0):
                     sample_data = {
                            "timestamp_scenario_seconds": scenario_instance.current_time_seconds,
                            "scenario_id": scenario_instance.scenario_id,
                            "sensor_readings": sensor_readings,
                            "labels": full_labels,
                            "extracted_class_label": extracted_class_label
                        }
                     collected_samples_by_class.setdefault(extracted_class_label, []).append(sample_data)
                
                generated_this_run +=1
                if generated_this_run % 200 == 0:
                    current_counts_str = {k: len(v) for k,v in collected_samples_by_class.items()}
                    print(f"    Run {config_idx+1}, Scenario {scenario_instance.scenario_id}: {generated_this_run} samples. Current class counts: {current_counts_str}")

            current_counts_str = {k: len(v) for k,v in collected_samples_by_class.items()}
            print(f"  Finished scenario run for {scenario_instance.scenario_id}. Generated {generated_this_run} samples. Class counts: {current_counts_str}")

        all_balanced_samples = []
        for class_list in collected_samples_by_class.values():
            all_balanced_samples.extend(class_list)
        
        print(f"Total balanced samples collected: {len(all_balanced_samples)}")
        final_counts_str = {k: len(v) for k,v in collected_samples_by_class.items()}
        print(f"Final class distribution: {final_counts_str}")

        validation_errors = self._validate_generated_data(all_balanced_samples)
        if validation_errors:
            print(f"Warning: Balanced data validation issues found: {validation_errors}")

        return self._export_data(all_balanced_samples, output_format, dataset_name)

    def generate_edge_cases(self,
                            base_scenarios: List[BaseScenario],
                            modification_strategies: List[Callable[[BaseScenario], BaseScenario]], # Functions that modify a scenario
                            target_count_per_strategy: int,
                            output_format: str = "list_of_dicts",
                            dataset_name: Optional[str] = None,
                            imperfection_settings: Optional[Dict[str, Any]] = None,
                            time_step_seconds: Optional[float] = None,
                            samples_per_modified_scenario: int = 100 # How many samples from each modified scenario
                           ) -> Any:
        """
        Generates edge case datasets by applying modification strategies to base scenarios.
        """
        print(f"Starting edge case generation...")
        all_edge_case_samples: List[Dict[str, Any]] = []
        current_time_step = time_step_seconds if time_step_seconds is not None else self.default_time_step_seconds

        for strategy_idx, strategy_func in enumerate(modification_strategies):
            print(f"  Applying strategy {strategy_idx + 1}/{len(modification_strategies)}: {strategy_func.__name__ if hasattr(strategy_func, '__name__') else 'Unnamed Strategy'}")
            generated_for_strategy = 0
            
            for base_scenario_idx, base_scenario in enumerate(base_scenarios):
                if generated_for_strategy >= target_count_per_strategy:
                    break 
                
                # Create a fresh copy or re-initialize the base scenario to avoid state leakage
                # This assumes BaseScenario can be deepcopied or re-instantiated from its definition
                try:
                    # If scenarios have a to_definition_dict and from_definition_dict
                    scenario_def = base_scenario.to_scenario_definition_dict()
                    modified_scenario_instance = type(base_scenario).from_scenario_definition_dict(scenario_def)
                except Exception as e:
                    print(f"    Could not reliably copy scenario {base_scenario.scenario_id} for modification, skipping. Error: {e}")
                    continue

                modified_scenario_instance = strategy_func(modified_scenario_instance) # Apply modification
                modified_scenario_instance.name = f"{base_scenario.name}_edge_strat{strategy_idx+1}"
                modified_scenario_instance.scenario_id = f"{base_scenario.scenario_id}_edge_s{strategy_idx+1}_b{base_scenario_idx}"


                print(f"    Running modified scenario: {modified_scenario_instance.scenario_id} ({modified_scenario_instance.name}) for {samples_per_modified_scenario} samples.")
                modified_scenario_instance.setup_environment(self.environment_orchestrator)
                # TODO: Apply imperfection_settings

                generated_this_run = 0
                while generated_this_run < samples_per_modified_scenario and \
                      not modified_scenario_instance.is_completed(self.environment_orchestrator.get_current_state()):
                    
                    modified_scenario_instance.update(current_time_step, self.environment_orchestrator)
                    self.environment_orchestrator.update(current_time_step)
                    current_env_state = self.environment_orchestrator.get_current_state()

                    # Upstream Contract: (Same as in generate_training_dataset)
                    # - sensor_readings: Dict from VirtualGridGuardian (Avro-compatible sensor data)
                    # - full_labels: Dict from VirtualGridGuardian (GroundTruthLabels.avsc compatible)
                    sensor_readings, full_labels = self.grid_guardian.generate_training_sample(
                        current_env_state,
                        scenario_labels=modified_scenario_instance.get_ground_truth_labels(current_env_state)
                    )
                    
                    sample_data = {
                        "timestamp_scenario_seconds": modified_scenario_instance.current_time_seconds,
                        "scenario_id": modified_scenario_instance.scenario_id,
                        "sensor_readings": sensor_readings,
                        "labels": full_labels,
                        "sample_metadata": {
                            "edge_case_strategy": strategy_func.__name__ if hasattr(strategy_func, '__name__') else 'Unnamed Strategy'
                        }
                    }
                    all_edge_case_samples.append(sample_data)
                    generated_this_run += 1
                
                generated_for_strategy += generated_this_run
                print(f"    Finished modified scenario {modified_scenario_instance.scenario_id}. Generated {generated_this_run} samples.")

        print(f"Total edge case samples generated: {len(all_edge_case_samples)}")
        validation_errors = self._validate_generated_data(all_edge_case_samples) # Basic validation
        if validation_errors:
            print(f"Warning: Edge case data validation issues found: {validation_errors}")

        return self._export_data(all_edge_case_samples, output_format, dataset_name or "edge_case_dataset")


    def generate_temporal_sequences(self,
                                    scenario: BaseScenario,
                                    sequence_length: int,
                                    overlap: int = 0,
                                    output_format: str = "list_of_dicts",
                                    dataset_name: Optional[str] = None,
                                    imperfection_settings: Optional[Dict[str, Any]] = None,
                                    time_step_seconds: Optional[float] = None,
                                    max_total_samples: int = 10000 # Safety break
                                   ) -> Any:
        """
        Generates a flat list of data samples from a single scenario run,
        annotating each sample with sequence information.

        Each sample in the output list is a `raw_sample` dictionary, augmented
        with `sample_metadata` indicating its `sequence_id` and `sequence_index`.
        This output is directly compatible with `_export_data`.
        """
        if overlap >= sequence_length:
            raise ValueError("Overlap must be less than sequence_length.")

        current_time_step = time_step_seconds if time_step_seconds is not None else self.default_time_step_seconds
        all_flattened_samples: List[Dict[str, Any]] = []
        
        print(f"Starting temporal sequence generation for scenario: {scenario.scenario_id} ({scenario.name})")
        print(f"Sequence length: {sequence_length}, Overlap: {overlap}")

        scenario.setup_environment(self.environment_orchestrator)
        # TODO: Apply imperfection_settings

        step_size = sequence_length - overlap
        current_window: List[Dict[str, Any]] = [] # Stores samples for the current sliding window
        total_samples_processed = 0
        sequence_counter = 0

        while not scenario.is_completed(self.environment_orchestrator.get_current_state()) and total_samples_processed < max_total_samples:
            scenario.update(current_time_step, self.environment_orchestrator)
            self.environment_orchestrator.update(current_time_step)
            current_env_state = self.environment_orchestrator.get_current_state()

            # Upstream Contract: (Same as in generate_training_dataset)
            # - sensor_readings: Dict from VirtualGridGuardian (Avro-compatible sensor data)
            # - full_labels: Dict from VirtualGridGuardian (GroundTruthLabels.avsc compatible)
            sensor_readings, full_labels = self.grid_guardian.generate_training_sample(
                current_env_state,
                scenario_labels=scenario.get_ground_truth_labels(current_env_state)
            )
            
            # This is the base raw_sample for this timestep
            base_sample_data = {
                "timestamp_scenario_seconds": scenario.current_time_seconds,
                "scenario_id": scenario.scenario_id,
                "sensor_readings": sensor_readings,
                "labels": full_labels,
                "sample_metadata": {} # Initialize sample_metadata
            }
            current_window.append(base_sample_data)
            total_samples_processed += 1

            if len(current_window) == sequence_length:
                sequence_counter += 1
                current_sequence_id = f"{scenario.scenario_id}_seq{sequence_counter}"
                
                # Add all samples from this completed sequence to the flattened list
                # with appropriate sequence metadata
                for i, sample_in_sequence in enumerate(current_window):
                    # Create a copy to avoid modifying the sample in current_window if it's reused
                    processed_sample = sample_in_sequence.copy()
                    processed_sample["sample_metadata"] = {
                        **(processed_sample.get("sample_metadata") or {}), # Preserve existing metadata if any
                        "sequence_id": current_sequence_id,
                        "sequence_index": i,
                        "sequence_total_length": sequence_length
                    }
                    all_flattened_samples.append(processed_sample)
                
                # Slide the window: remove `step_size` elements from the beginning
                current_window = current_window[step_size:]
            
            if total_samples_processed % 200 == 0:
                 print(f"  Processed {total_samples_processed} total samples. {len(all_flattened_samples)} samples added to dataset from {sequence_counter} sequences.")

        # Note: Partial sequences at the end are not processed by this logic,
        # only full sequences of `sequence_length` contribute to `all_flattened_samples`.
        
        print(f"Finished temporal sequence generation. Total individual samples generated: {len(all_flattened_samples)} from {sequence_counter} sequences.")
        
        validation_errors = self._validate_generated_data(all_flattened_samples)
        if validation_errors:
            print(f"Warning: Temporal sequence data validation issues found: {validation_errors}")

        return self._export_data(all_flattened_samples, output_format, dataset_name or f"temporal_seq_{scenario.scenario_id}")