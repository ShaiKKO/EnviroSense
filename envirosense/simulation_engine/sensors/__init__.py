# This file makes the 'sensors' directory a Python package.

from .base import BaseSensor
from .config import SensorConfiguration, IndividualSensorConfig
from .grid_guardian import VirtualGridGuardian
from .registry import SENSOR_CLASS_REGISTRY

# Import sensor classes for __all__ and for direct use if needed,
# but their primary registration is in registry.py
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


__all__ = [
    "BaseSensor",
    "SensorConfiguration",
    "IndividualSensorConfig",
    "VirtualGridGuardian",
    "VOCArraySensor",
    "ParticulateMatterSensor",
    "TemperatureHumiditySensor",
    "BarometricPressureSensor",
    "WindSpeedDirectionSensor",
    "LightningDetectionSensor",
    "ThermalCameraSensor",
    "EMFSensor",
    "AcousticSensor",
    "VibrationSensor",
    "BatteryLevelSensor",
    "SolarPowerSensor",
    "InternalTemperatureSensor",
    "SENSOR_CLASS_REGISTRY",
]