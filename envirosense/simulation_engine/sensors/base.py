import abc
from typing import Dict, Any, Tuple

class BaseSensor(abc.ABC):
    """
    Abstract base class for all simulated sensors in the EnviroSense Digital Twin.

    This class defines the common interface and properties for sensors, including
    ML-specific features for generating training data.
    """

    def __init__(self,
                 sensor_id: str,
                 sensor_type: str,
                 position_3d: Tuple[float, float, float],
                 sampling_volume: Dict[str, Any], # e.g., {'shape': 'cube', 'size': 0.1} for a 0.1m cube
                 is_enabled: bool = True,
                 ground_truth_capability: bool = True,
                 noise_characteristics: Dict[str, Any] = None,
                 drift_parameters: Dict[str, Any] = None,
                 **kwargs):
        """
        Initializes the BaseSensor.

        Args:
            sensor_id: Unique identifier for the sensor.
            sensor_type: Type of the sensor (e.g., 'voc_array', 'thermal_camera').
            position_3d: Tuple representing (x, y, z) coordinates of the sensor.
            sampling_volume: Dictionary describing the 3D volume the sensor samples from.
            is_enabled: Whether the sensor is currently active.
            ground_truth_capability: Whether the sensor can provide ideal ground truth readings.
            noise_characteristics: Parameters defining the sensor's noise model.
            drift_parameters: Parameters defining the sensor's drift model.
        """
        if not sensor_id or not isinstance(sensor_id, str):
            raise ValueError("sensor_id must be a non-empty string.")
        if not sensor_type or not isinstance(sensor_type, str):
            raise ValueError("sensor_type must be a non-empty string.")

        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self._is_enabled = is_enabled
        self.position_3d = position_3d
        self.sampling_volume = sampling_volume
        self.ground_truth_capability = ground_truth_capability
        self.noise_characteristics = noise_characteristics if noise_characteristics is not None else {}
        self.drift_parameters = drift_parameters if drift_parameters is not None else {}
        self.calibration_artifacts = kwargs.get('calibration_artifacts', {}) # Store calibration_artifacts
        self.environmental_compensation_params = kwargs.get('environmental_compensation_params', {}) # Store env compensation params
        # Further initialization for operational time, etc., for drift can be added here or in subclasses

    @property
    def is_enabled(self) -> bool:
        """Returns True if the sensor is enabled, False otherwise."""
        return self._is_enabled

    @abc.abstractmethod
    def sample(self, environment_3d_state: Any) -> Dict[str, Any]:
        """
        Generates a sensor reading based on the current 3D environment state.
        This reading should include applied imperfections.

        Args:
            environment_3d_state: An object representing the current state of the
                                  simulated 3D environment.

        Returns:
            A dictionary containing the sensor readings (e.g., {'temperature': 25.5}).
        """
        pass

    @abc.abstractmethod
    def get_ground_truth(self, environment_3d_state: Any) -> Dict[str, Any]:
        """
        Retrieves the ideal, noise-free ground truth reading from the environment.
        This method should only be available if ground_truth_capability is True.

        Args:
            environment_3d_state: An object representing the current state of the
                                  simulated 3D environment.

        Returns:
            A dictionary containing the ground truth sensor values.
            Returns an empty dict or raises an error if not capable.
        """
        if not self.ground_truth_capability:
            # Or raise NotImplementedError("Sensor does not support ground truth.")
            return {} 
        pass

    @abc.abstractmethod
    def get_ml_metadata(self) -> Dict[str, Any]:
        """
        Returns metadata relevant for ML training, such as current imperfection levels,
        sensor state, or calibration status.

        Returns:
            A dictionary containing ML-relevant metadata.
        """
        pass

    # Made this method abstract as its implementation is highly sensor-specific
    # and often needs environment_3d_state for time-based or temp-based effects.
    # If a common pass-through is desired, subclasses can call super() if they don't implement it.
    @abc.abstractmethod
    def apply_imperfections(self, true_reading: Dict[str, Any], environment_3d_state: Any) -> Dict[str, Any]:
        """
        Applies various sensor imperfections (noise, drift, etc.) to a true reading.
        This method is called by `sample()` after `get_ground_truth()` is called.
        Subclasses must override this to implement specific imperfection models.

        Args:
            true_reading: The ideal, noise-free reading from the environment,
                          as returned by `get_ground_truth()`.
            environment_3d_state: The current state of the 3D environment, which might
                                  be needed for time-based drift, temperature effects on
                                  electronics, etc.

        Returns:
            The reading with imperfections applied.
        """
        # Example base behavior if not abstract (though subclasses should really handle this):
        # return true_reading.copy()
        pass


    def enable(self) -> None:
        """Enables the sensor."""
        self._is_enabled = True
        # print(f"Sensor {self.sensor_id} enabled.") # Optional logging

    def disable(self) -> None:
        """Disables the sensor."""
        self._is_enabled = False
        # print(f"Sensor {self.sensor_id} disabled.") # Optional logging

    def update_position(self, new_position_3d: Tuple[float, float, float]) -> None:
        """
        Updates the sensor's 3D position.

        Args:
            new_position_3d: The new (x, y, z) coordinates.
        """
        self.position_3d = new_position_3d
        # print(f"Sensor {self.sensor_id} position updated to {self.position_3d}.") # Optional logging

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(sensor_id='{self.sensor_id}', "
                f"sensor_type='{self.sensor_type}', is_enabled={self.is_enabled}, "
                f"position_3d={self.position_3d})")