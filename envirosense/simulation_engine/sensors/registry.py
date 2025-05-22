from .environmental import (
    VOCArraySensor,
    ParticulateMatterSensor,
    TemperatureHumiditySensor,
    BarometricPressureSensor,
    WindSpeedDirectionSensor,
    LightningDetectionSensor
)

from .infrastructure import (
    ThermalCameraSensor,
    EMFSensor,
    AcousticSensor,
    VibrationSensor
)

from .system import (
    BatteryLevelSensor,
    SolarPowerSensor,
    InternalTemperatureSensor
)

# Define a SENSOR_CLASS_REGISTRY for the factory pattern
# This will be used by VirtualGridGuardian to instantiate sensors
SENSOR_CLASS_REGISTRY = {
    "voc_array": VOCArraySensor,
    "particulate_matter": ParticulateMatterSensor,
    "temp_humidity": TemperatureHumiditySensor,
    "barometric_pressure": BarometricPressureSensor,
    "wind_sensor": WindSpeedDirectionSensor,
    "lightning_detector": LightningDetectionSensor,
    "thermal_camera": ThermalCameraSensor,
    "emf_sensor": EMFSensor,
    "acoustic_sensor": AcousticSensor,
    "vibration_sensor": VibrationSensor,
    "battery_level": BatteryLevelSensor,
    "solar_power": SolarPowerSensor,
    "internal_temperature": InternalTemperatureSensor,
    # Add other sensor type strings and their corresponding classes here
}