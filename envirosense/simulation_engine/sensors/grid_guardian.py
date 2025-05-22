from typing import Dict, Any, Tuple, List, Optional

from envirosense.simulation_engine.sensors.base import BaseSensor
from envirosense.simulation_engine.sensors.config import SensorConfiguration, IndividualSensorConfig
# We will need to import actual sensor classes once they are defined
# For now, we can use a factory pattern or direct instantiation if stubs are in known locations.
# Import the SENSOR_CLASS_REGISTRY
from .registry import SENSOR_CLASS_REGISTRY


class VirtualGridGuardian:
    """
    Manages a collection of virtual sensors simulating a Grid Guardian unit.
    It orchestrates sensor initialization, data sampling, and provides
    interfaces for ML training data generation.
    """

    def __init__(self,
                 guardian_id: str, # This might come from config, or be passed explicitly
                 config: SensorConfiguration,
                 # Optional: allow overriding default position from config
                 position_3d: Optional[Tuple[float, float, float]] = None):
        """
        Initializes the VirtualGridGuardian unit.

        Args:
            guardian_id: Unique identifier for this Grid Guardian instance.
                         If config.guardian_id exists, this should match or can be omitted.
            config: A SensorConfiguration object detailing the sensors and their settings.
            position_3d: Optional override for the Grid Guardian's 3D position.
                         If None, uses config.default_position_3d.
        """
        if not guardian_id and not config.guardian_id:
            raise ValueError("A guardian_id must be provided either directly or in the configuration.")
        
        self.guardian_id = guardian_id if guardian_id else config.guardian_id
        if guardian_id and config.guardian_id and guardian_id != config.guardian_id:
            # Potentially log a warning if they differ but proceed, or raise error
            print(f"Warning: Provided guardian_id '{guardian_id}' differs from config's '{config.guardian_id}'. Using '{self.guardian_id}'.")

        self.config = config
        self.position_3d = position_3d if position_3d is not None else self.config.default_position_3d
        
        self.sensors: Dict[str, BaseSensor] = {} # Store sensors by their unique ID
        self._initialize_sensors()

    def _initialize_sensors(self):
        """
        Initializes individual sensor instances based on the provided configuration.
        Sensor IDs will be generated if not provided in the config.
        """
        for i, sensor_conf in enumerate(self.config.sensors):
            sensor_id = sensor_conf.sensor_id if sensor_conf.sensor_id else f"{self.guardian_id}-{sensor_conf.sensor_type}-{i+1:02d}"
            
            if sensor_id in self.sensors:
                raise ValueError(f"Duplicate sensor_id '{sensor_id}' encountered during initialization.")

            sensor_class = SENSOR_CLASS_REGISTRY.get(sensor_conf.sensor_type)
            if not sensor_class:
                print(f"Warning: Unknown sensor type '{sensor_conf.sensor_type}' for sensor_id '{sensor_id}'. Skipping.")
                # Or raise ValueError(f"Unknown sensor type: {sensor_conf.sensor_type}")
                continue

            try:
                # Prepare arguments for the sensor's __init__
                # BaseSensor and its children expect sensor_id, sensor_type, position_3d, sampling_volume,
                # and then **kwargs which can take is_enabled, ground_truth_capability, etc.
                # specific_params from config are passed to the sensor's __init__ to handle.
                
                # Default sampling_volume if not in specific_params, can be refined
                default_sampling_volume = {"shape": "point", "description": "Default point sampling"}
                sampling_volume = sensor_conf.specific_params.get("sampling_volume", default_sampling_volume)


                sensor_instance = sensor_class(
                    sensor_id=sensor_id,
                    # sensor_type is implicitly handled by choosing the class, but can be passed if BaseSensor needs it
                    position_3d=self.position_3d, # Individual sensors can override this later if needed
                    sampling_volume=sampling_volume,
                    is_enabled=sensor_conf.is_enabled,
                    noise_characteristics=sensor_conf.noise_characteristics,
                    drift_parameters=sensor_conf.drift_parameters,
                    # Pass all specific_params; the sensor's __init__ will pick what it needs
                    specific_params=sensor_conf.specific_params
                )
                self.sensors[sensor_id] = sensor_instance
                # print(f"Initialized sensor: {sensor_id} of type {sensor_conf.sensor_type}")
            except Exception as e:
                print(f"Error initializing sensor {sensor_id} (type {sensor_conf.sensor_type}): {e}")
                # Decide if we want to continue or raise

    def sample_environment(self, environment_3d_state: Any) -> Dict[str, Dict[str, Any]]:
        """
        Collects readings from all enabled sensors based on the current environment state.

        Args:
            environment_3d_state: The current state of the 3D simulated environment.

        Returns:
            A dictionary where keys are sensor_ids and values are their readings.
        """
        all_readings: Dict[str, Dict[str, Any]] = {}
        for sensor_id, sensor in self.sensors.items():
            if sensor.is_enabled:
                try:
                    all_readings[sensor_id] = sensor.sample(environment_3d_state)
                except Exception as e:
                    # Log error and continue, or re-raise depending on desired robustness
                    print(f"Error sampling sensor {sensor_id}: {e}")
                    all_readings[sensor_id] = {"error": str(e)} 
        return all_readings

    def get_ground_truth_data(self, environment_3d_state: Any) -> Dict[str, Dict[str, Any]]:
        """
        Collects ground truth data from all enabled sensors capable of providing it.

        Args:
            environment_3d_state: The current state of the 3D simulated environment.

        Returns:
            A dictionary where keys are sensor_ids and values are their ground truth readings.
        """
        all_ground_truths: Dict[str, Dict[str, Any]] = {}
        for sensor_id, sensor in self.sensors.items():
            if sensor.is_enabled and sensor.ground_truth_capability:
                try:
                    all_ground_truths[sensor_id] = sensor.get_ground_truth(environment_3d_state)
                except Exception as e:
                    print(f"Error getting ground truth from sensor {sensor_id}: {e}")
                    all_ground_truths[sensor_id] = {"error": str(e)}
        return all_ground_truths

    def generate_training_sample(self,
                                 environment_3d_state: Any,
                                 scenario_labels: Optional[Dict[str, Any]] = None
                                 ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        """
        Generates a single training sample consisting of sensor readings and corresponding labels.
        Labels include ground truth from sensors and any scenario-level labels.

        Args:
            environment_3d_state: The current state of the 3D simulated environment.
            scenario_labels: Optional dictionary of labels provided by the current scenario
                             (e.g., {"event_type": "fire_precursor", "severity": "low"}).

        Returns:
            A tuple containing:
                - Sensor readings (Dict[sensor_id, reading_dict])
                - Combined labels (Dict[label_name, value]), including sensor ground truths
                  and scenario labels.
        """
        sensor_readings = self.sample_environment(environment_3d_state)
        sensor_ground_truths = self.get_ground_truth_data(environment_3d_state)

        combined_labels: Dict[str, Any] = {}
        if scenario_labels:
            combined_labels.update(scenario_labels)
        
        # Prefix sensor ground truths to avoid clashes, e.g., "gt_sensor_id_value"
        for sensor_id, gt_data in sensor_ground_truths.items():
            for key, value in gt_data.items():
                combined_labels[f"gt_{sensor_id}_{key}"] = value
        
        return sensor_readings, combined_labels

    # TODO: Implement generate_dataset(self, scenarios, num_samples_per_scenario) -> list:

    def get_sensor(self, sensor_id: str) -> Optional[BaseSensor]:
        """Retrieves a sensor instance by its ID."""
        return self.sensors.get(sensor_id)

    def enable_sensor(self, sensor_id: str, enable: bool = True) -> bool:
        """Enables or disables a specific sensor."""
        sensor = self.get_sensor(sensor_id)
        if sensor:
            if enable:
                sensor.enable()
            else:
                sensor.disable()
            return True
        return False # Sensor not found

    def __repr__(self) -> str:
        return (f"<VirtualGridGuardian(guardian_id='{self.guardian_id}', "
                f"num_sensors={len(self.sensors)}, position={self.position_3d})>")

# Example of how a sensor factory might be structured (for _initialize_sensors)
# This would typically be in a separate 'factory.py' or within this module if simple enough.
# from .environmental import VOCArraySensor # etc.
# SENSOR_CLASS_REGISTRY = {
#     "voc_array": VOCArraySensor,
#     "thermal_camera": ThermalCameraSensor,
#     # ...
# }
# def create_sensor_instance(sensor_config: IndividualSensorConfig, guardian_position: Tuple):
#     cls = SENSOR_CLASS_REGISTRY.get(sensor_config.sensor_type)
#     if not cls:
#         raise ValueError(f"Unknown sensor type: {sensor_config.sensor_type}")
#     
#     # Prepare arguments for the sensor's __init__
#     # This needs careful mapping from IndividualSensorConfig to specific sensor class __init__ args
#     init_args = {
#         "sensor_id": sensor_config.sensor_id or f"generated_id_{sensor_config.sensor_type}", # Ensure ID generation
#         "sensor_type": sensor_config.sensor_type,
#         "position_3d": guardian_position, # Default to guardian's position
#         "sampling_volume": sensor_config.specific_params.get("sampling_volume", {"shape":"point"}),
#         "is_enabled": sensor_config.is_enabled,
#         "noise_characteristics": sensor_config.noise_characteristics,
#         "drift_parameters": sensor_config.drift_parameters,
#         # **sensor_config.specific_params # Be careful with this, ensure specific_params match __init__ args
#     }
#     # Add specific params carefully
#     if sensor_config.specific_params:
#         # Example: if cls is VOCArraySensor: init_args["channels"] = sensor_config.specific_params.get("channels")
#         pass 
#
#     return cls(**init_args)