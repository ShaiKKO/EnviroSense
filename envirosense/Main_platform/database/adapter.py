"""
Database adapter for EnviroSense PostgreSQL integration.

This module provides a high-level adapter for the EnviroSense application
to interact with the PostgreSQL database in a clean, abstracted way.
"""

import logging
import uuid
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Union, Any, Tuple
from uuid import UUID

from .models.sensor_data import Device, Parameter, SensorReading, AggregatedReading
from .repositories.sensor_repositories import (
    device_repository,
    parameter_repository,
    sensor_reading_repository,
    aggregated_reading_repository
)

logger = logging.getLogger(__name__)


class DatabaseAdapter:
    """
    High-level adapter for EnviroSense database operations.
    
    This class provides a clean interface for the application to interact with
    the database, abstracting away the details of repositories and transactions.
    """
    
    @staticmethod
    def register_device(
        serial_number: str,
        name: str,
        device_type: str,
        firmware_version: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        location_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Device:
        """
        Register a new device in the system.
        
        Args:
            serial_number: Unique serial number of the device
            name: Human-readable name
            device_type: Type of device (e.g., 'grid_guardian', 'wearable')
            firmware_version: Current firmware version
            latitude: Installation latitude (if applicable)
            longitude: Installation longitude (if applicable)
            location_name: Human-readable location name
            metadata: Additional device information as JSON-compatible dict
            
        Returns:
            The created Device object
            
        Raises:
            ValueError: If a device with the given serial number already exists
        """
        # Check if device already exists
        existing = device_repository.find_by_serial_number(serial_number)
        if existing:
            raise ValueError(f"Device with serial number '{serial_number}' already exists")
        
        # Set defaults
        if metadata is None:
            metadata = {}
            
        # Create device
        device_data = {
            "id": str(uuid.uuid4()),
            "serial_number": serial_number,
            "name": name,
            "device_type": device_type,
            "firmware_version": firmware_version,
            "latitude": latitude,
            "longitude": longitude,
            "location_name": location_name,
            "is_active": True,
            "last_seen": datetime.now(UTC),
            "metadata": metadata
        }
        
        device = device_repository.create(**device_data)
        logger.info(f"Registered new device: {name} ({serial_number})")
        return device
    
    @staticmethod
    def update_device_location(
        device_id: Union[str, UUID],
        latitude: float,
        longitude: float
    ) -> Optional[Device]:
        """
        Update a device's geographic location.
        
        Args:
            device_id: The device ID
            latitude: New latitude
            longitude: New longitude
            
        Returns:
            Updated Device object or None if device not found
        """
        device = device_repository.update(
            device_id,
            latitude=latitude,
            longitude=longitude,
            last_seen=datetime.now(UTC)
        )
        
        if device:
            logger.info(f"Updated location for device {device.name}: {latitude}, {longitude}")
        else:
            logger.warning(f"Device with ID {device_id} not found for location update")
            
        return device
    
    @staticmethod
    def deactivate_device(device_id: Union[str, UUID]) -> bool:
        """
        Deactivate a device.
        
        Args:
            device_id: The device ID
            
        Returns:
            True if successful, False if device not found
        """
        device = device_repository.update(device_id, is_active=False)
        if device:
            logger.info(f"Deactivated device: {device.name}")
            return True
        return False
    
    @staticmethod
    def register_parameter(
        code: str,
        name: str,
        description: Optional[str] = None,
        unit: Optional[str] = None,
        min_valid_value: Optional[float] = None,
        max_valid_value: Optional[float] = None
    ) -> Parameter:
        """
        Register a new parameter type in the system.
        
        Args:
            code: Unique parameter code (e.g., 'temp', 'co')
            name: Human-readable name
            description: Detailed description
            unit: Unit of measurement
            min_valid_value: Minimum valid reading value
            max_valid_value: Maximum valid reading value
            
        Returns:
            The created Parameter object
            
        Raises:
            ValueError: If a parameter with the given code already exists
        """
        # Check if parameter already exists
        existing = parameter_repository.find_by_code(code)
        if existing:
            raise ValueError(f"Parameter with code '{code}' already exists")
        
        # Create parameter
        param_data = {
            "id": str(uuid.uuid4()),
            "code": code,
            "name": name,
            "description": description,
            "unit": unit,
            "min_valid_value": min_valid_value,
            "max_valid_value": max_valid_value
        }
        
        param = parameter_repository.create(**param_data)
        logger.info(f"Registered new parameter: {name} ({code})")
        return param
    
    @staticmethod
    def record_sensor_reading(
        device_id: Union[str, UUID],
        parameter_id: Union[str, UUID],
        value: float,
        timestamp: Optional[datetime] = None,
        batch_id: Optional[str] = None,
        quality: Optional[int] = None,
        is_validated: bool = False,
        uncertainty: Optional[float] = None,
        raw_value: Optional[float] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> SensorReading:
        """
        Record a new sensor reading.
        
        Args:
            device_id: The device that took the reading
            parameter_id: The parameter being measured
            value: The processed/calibrated value
            timestamp: Time of the reading (defaults to now)
            batch_id: Optional batch identifier for grouped readings
            quality: Quality indicator (0-100, higher is better)
            is_validated: Whether this reading has been validated
            uncertainty: Measurement uncertainty
            raw_value: Raw sensor value before processing
            additional_data: Additional reading metadata
            
        Returns:
            The created SensorReading object
        """
        # Update device's last_seen timestamp
        device_repository.update_last_seen(device_id)
        
        # Record the reading
        reading = sensor_reading_repository.create_reading(
            device_id=device_id,
            parameter_id=parameter_id,
            value=value,
            timestamp=timestamp,
            batch_id=batch_id,
            quality=quality,
            is_validated=is_validated,
            uncertainty=uncertainty,
            raw_value=raw_value,
            additional_data=additional_data
        )
        
        return reading
    
    @staticmethod
    def record_readings_batch(
        readings: List[Dict[str, Any]]
    ) -> str:
        """
        Record multiple sensor readings in a single batch.
        
        Args:
            readings: List of reading dictionaries with keys matching record_sensor_reading params
            
        Returns:
            Batch ID for the recorded readings
            
        Note:
            This method applies a single batch ID to all readings if not provided
        """
        batch_id = f"batch-{uuid.uuid4()}"
        recorded = []
        
        for reading_data in readings:
            # Use the provided batch_id or the generated one
            if 'batch_id' not in reading_data:
                reading_data['batch_id'] = batch_id
                
            # Record the reading
            reading = DatabaseAdapter.record_sensor_reading(**reading_data)
            recorded.append(reading)
            
        logger.info(f"Recorded batch of {len(recorded)} readings with ID: {batch_id}")
        return batch_id
    
    @staticmethod
    def get_device_readings(
        device_id: Union[str, UUID],
        parameter_id: Optional[Union[str, UUID]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[SensorReading]:
        """
        Get sensor readings for a specific device.
        
        Args:
            device_id: The device ID
            parameter_id: Optional parameter to filter by
            start_time: Optional start time for the query
            end_time: Optional end time for the query
            limit: Maximum number of readings to return
            
        Returns:
            List of SensorReading objects
        """
        return sensor_reading_repository.get_readings_for_device(
            device_id=device_id,
            parameter_id=parameter_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
    
    @staticmethod
    def get_latest_device_readings(
        device_id: Union[str, UUID],
        parameter_ids: Optional[List[Union[str, UUID]]] = None
    ) -> Dict[str, SensorReading]:
        """
        Get the latest readings for a device across multiple parameters.
        
        Args:
            device_id: The device ID
            parameter_ids: List of parameter IDs to fetch (all if None)
            
        Returns:
            Dictionary mapping parameter IDs to their latest readings
        """
        if parameter_ids is None:
            # Get all parameters if none specified
            parameters = parameter_repository.get_all()
            parameter_ids = [param.id for param in parameters]
        
        result = {}
        for param_id in parameter_ids:
            reading = sensor_reading_repository.get_latest_reading(device_id, param_id)
            if reading:
                result[str(param_id)] = reading
                
        return result
    
    @staticmethod
    def create_aggregated_reading(
        device_id: Union[str, UUID],
        parameter_id: Union[str, UUID],
        start_time: datetime,
        end_time: datetime,
        interval_minutes: int = 60
    ) -> Optional[AggregatedReading]:
        """
        Create an aggregated reading from raw sensor readings.
        
        Args:
            device_id: The device ID
            parameter_id: The parameter ID
            start_time: Start time for aggregation period
            end_time: End time for aggregation period
            interval_minutes: Aggregation interval in minutes
            
        Returns:
            AggregatedReading object if readings exist, None otherwise
        """
        # Get raw readings for the period
        readings = sensor_reading_repository.get_readings_for_device(
            device_id=device_id,
            parameter_id=parameter_id,
            start_time=start_time,
            end_time=end_time,
            limit=10000  # High limit to ensure we get all readings
        )
        
        if not readings:
            logger.warning(f"No readings found for aggregation: device {device_id}, " 
                         f"parameter {parameter_id}, period {start_time} to {end_time}")
            return None
        
        # Calculate aggregated values
        values = [r.value for r in readings]
        values.sort()  # For median calculation
        
        min_value = min(values)
        max_value = max(values)
        avg_value = sum(values) / len(values)
        count = len(values)
        
        # Calculate median
        if count % 2 == 0:
            median_value = (values[count//2 - 1] + values[count//2]) / 2
        else:
            median_value = values[count//2]
            
        # Calculate standard deviation
        std_deviation = None
        if count > 1:
            variance = sum((x - avg_value) ** 2 for x in values) / count
            std_deviation = variance ** 0.5
        
        # Create aggregated reading
        agg_reading = aggregated_reading_repository.create_aggregation(
            device_id=device_id,
            parameter_id=parameter_id,
            start_time=start_time,
            end_time=end_time,
            min_value=min_value,
            max_value=max_value,
            avg_value=avg_value,
            median_value=median_value,
            std_deviation=std_deviation,
            count=count
        )
        
        logger.info(f"Created aggregated reading for device {device_id}, parameter {parameter_id}, "
                  f"period {start_time} to {end_time}, {count} readings")
        
        return agg_reading
    
    @staticmethod
    def get_aggregated_readings(
        device_id: Union[str, UUID],
        parameter_id: Union[str, UUID],
        start_time: datetime,
        end_time: datetime,
        interval_minutes: Optional[int] = None
    ) -> List[AggregatedReading]:
        """
        Get aggregated readings for a device and parameter.
        
        Args:
            device_id: The device ID
            parameter_id: The parameter ID
            start_time: Start time for the query
            end_time: End time for the query
            interval_minutes: Optional filter for specific intervals
            
        Returns:
            List of AggregatedReading objects
        """
        return aggregated_reading_repository.get_aggregated_data(
            device_id=device_id,
            parameter_id=parameter_id,
            start_time=start_time,
            end_time=end_time,
            interval_minutes=interval_minutes
        )
    
    @staticmethod
    def find_devices_by_type(device_type: str) -> List[Device]:
        """
        Find all devices of a specific type.
        
        Args:
            device_type: The device type to filter by
            
        Returns:
            List of matching Device objects
        """
        return device_repository.filter(device_type=device_type)
    
    @staticmethod
    def find_devices_in_area(
        lat_min: float, 
        lat_max: float, 
        lon_min: float, 
        lon_max: float
    ) -> List[Device]:
        """
        Find devices within a geographic bounding box.
        
        Args:
            lat_min: Minimum latitude
            lat_max: Maximum latitude
            lon_min: Minimum longitude
            lon_max: Maximum longitude
            
        Returns:
            List of Device objects in the specified area
        """
        return device_repository.find_devices_in_area(
            lat_min=lat_min,
            lat_max=lat_max,
            lon_min=lon_min,
            lon_max=lon_max
        )
    
    @staticmethod
    def get_parameter_by_code(code: str) -> Optional[Parameter]:
        """
        Get a parameter by its code.
        
        Args:
            code: The parameter code (e.g., 'temp', 'co')
            
        Returns:
            Parameter object if found, None otherwise
        """
        return parameter_repository.find_by_code(code)


# Create a singleton instance for use throughout the application
db = DatabaseAdapter()
database_adapter = db  # Alias for backward compatibility
