"""
Repositories for sensor data operations.

This module provides specialized repositories for working with sensor data models.
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Tuple, Union
from uuid import UUID

from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.orm import Session

from ..models.sensor_data import Device, Parameter, SensorReading, AggregatedReading
from .base import BaseRepository

logger = logging.getLogger(__name__)


class DeviceRepository(BaseRepository[Device]):
    """Repository for Device model operations."""
    
    def __init__(self):
        super().__init__(Device)
    
    def find_by_serial_number(self, serial_number: str) -> Optional[Device]:
        """Find a device by its serial number."""
        from ..session import session_scope
        with session_scope(for_write=False) as session:
            device = session.query(Device).filter(
                Device.serial_number == serial_number
            ).first()
            if device:
                session.expunge(device)
            return device
    
    def find_active_devices(self, device_type: Optional[str] = None) -> List[Device]:
        """Find all active devices, optionally filtered by type."""
        from ..session import session_scope
        with session_scope(for_write=False) as session:
            query = session.query(Device).filter(Device.is_active == True)
            
            if device_type:
                query = query.filter(Device.device_type == device_type)
                
            devices = query.all()
            for device in devices:
                session.expunge(device)
                
            return devices
    
    def find_devices_in_area(
        self, 
        lat_min: float, 
        lat_max: float, 
        lon_min: float, 
        lon_max: float
    ) -> List[Device]:
        """Find devices within a geographic bounding box."""
        from ..session import session_scope
        with session_scope(for_write=False) as session:
            devices = session.query(Device).filter(
                Device.latitude >= lat_min,
                Device.latitude <= lat_max,
                Device.longitude >= lon_min,
                Device.longitude <= lon_max
            ).all()
            
            for device in devices:
                session.expunge(device)
                
            return devices
    
    def update_last_seen(self, device_id: Union[str, UUID]) -> None:
        """Update the last_seen timestamp for a device."""
        self.update(device_id, last_seen=datetime.now(UTC))


class ParameterRepository(BaseRepository[Parameter]):
    """Repository for Parameter model operations."""
    
    def __init__(self):
        super().__init__(Parameter)
    
    def find_by_code(self, code: str) -> Optional[Parameter]:
        """Find a parameter by its code."""
        from ..session import session_scope
        with session_scope(for_write=False) as session:
            parameter = session.query(Parameter).filter(
                Parameter.code == code
            ).first()
            if parameter:
                session.expunge(parameter)
            return parameter

    def find_by_name(self, name: str) -> Optional[Parameter]:
        """Find a parameter by its name."""
        from ..session import session_scope
        with session_scope(for_write=False) as session:
            parameter = session.query(Parameter).filter(
                Parameter.name == name
            ).first()
            if parameter:
                session.expunge(parameter)
            return parameter
    
    def get_all_parameters(self) -> List[Parameter]:
        """Get all available parameters."""
        return self.get_all()


class SensorReadingRepository(BaseRepository[SensorReading]):
    """Repository for SensorReading model operations."""
    
    def __init__(self):
        super().__init__(SensorReading)
    
    def create_reading(
        self,
        device_id: Union[str, UUID],
        parameter_id: Union[str, UUID],
        value: float,
        timestamp: Optional[datetime] = None,
        **kwargs
    ) -> SensorReading:
        """
        Create a new sensor reading.
        
        Args:
            device_id: The ID of the device that took the reading
            parameter_id: The ID of the parameter being measured
            value: The measured value
            timestamp: The time of the reading (defaults to now)
            **kwargs: Additional fields for the reading
            
        Returns:
            The created SensorReading object
        """
        if timestamp is None:
            timestamp = datetime.now(UTC)
            
        return self.create(
            device_id=device_id,
            parameter_id=parameter_id,
            value=value,
            timestamp=timestamp,
            **kwargs
        )
    
    def get_readings_for_device(
        self,
        device_id: Union[str, UUID],
        parameter_id: Optional[Union[str, UUID]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[SensorReading]:
        """
        Get readings for a specific device with optional filters.
        
        Args:
            device_id: The device ID
            parameter_id: Optional parameter ID to filter by
            start_time: Optional start time for filtering
            end_time: Optional end time for filtering
            limit: Maximum number of readings to return
            
        Returns:
            List of sensor readings
        """
        from ..session import session_scope
        with session_scope(for_write=False) as session:
            query = session.query(SensorReading).filter(
                SensorReading.device_id == device_id
            )
            
            if parameter_id:
                query = query.filter(SensorReading.parameter_id == parameter_id)
                
            if start_time:
                query = query.filter(SensorReading.timestamp >= start_time)
                
            if end_time:
                query = query.filter(SensorReading.timestamp <= end_time)
                
            # Order by timestamp descending (newest first)
            query = query.order_by(desc(SensorReading.timestamp)).limit(limit)
            
            readings = query.all()
            for reading in readings:
                session.expunge(reading)
                
            return readings
    
    def get_latest_reading(
        self,
        device_id: Union[str, UUID],
        parameter_id: Union[str, UUID]
    ) -> Optional[SensorReading]:
        """
        Get the most recent reading for a device and parameter.
        
        Args:
            device_id: The device ID
            parameter_id: The parameter ID
            
        Returns:
            The most recent sensor reading, or None if not found
        """
        from ..session import session_scope
        with session_scope(for_write=False) as session:
            reading = session.query(SensorReading).filter(
                SensorReading.device_id == device_id,
                SensorReading.parameter_id == parameter_id
            ).order_by(desc(SensorReading.timestamp)).first()
            
            if reading:
                session.expunge(reading)
                
            return reading
    
    def get_batch_readings(self, batch_id: str) -> List[SensorReading]:
        """
        Get all readings associated with a batch ID.
        
        Args:
            batch_id: The batch identifier
            
        Returns:
            List of sensor readings in the batch
        """
        from ..session import session_scope
        with session_scope(for_write=False) as session:
            readings = session.query(SensorReading).filter(
                SensorReading.batch_id == batch_id
            ).order_by(asc(SensorReading.timestamp)).all()
            
            for reading in readings:
                session.expunge(reading)
                
            return readings


class AggregatedReadingRepository(BaseRepository[AggregatedReading]):
    """Repository for AggregatedReading model operations."""
    
    def __init__(self):
        super().__init__(AggregatedReading)
    
    def create_aggregation(
        self,
        device_id: Union[str, UUID],
        parameter_id: Union[str, UUID],
        start_time: datetime,
        end_time: datetime,
        min_value: float,
        max_value: float,
        avg_value: float,
        median_value: Optional[float] = None,
        std_deviation: Optional[float] = None,
        count: int = 0
    ) -> AggregatedReading:
        """
        Create a new aggregated reading.
        
        Args:
            device_id: The device ID
            parameter_id: The parameter ID
            start_time: The start time of the aggregation period
            end_time: The end time of the aggregation period
            min_value: The minimum value during the period
            max_value: The maximum value during the period
            avg_value: The average value during the period
            median_value: The median value during the period (optional)
            std_deviation: The standard deviation during the period (optional)
            count: The number of readings aggregated
            
        Returns:
            The created AggregatedReading object
        """
        interval_minutes = int((end_time - start_time).total_seconds() / 60)
        
        return self.create(
            device_id=device_id,
            parameter_id=parameter_id,
            start_time=start_time,
            end_time=end_time,
            interval_minutes=interval_minutes,
            min_value=min_value,
            max_value=max_value,
            avg_value=avg_value,
            median_value=median_value,
            std_deviation=std_deviation,
            count=count
        )
    
    def get_aggregated_data(
        self,
        device_id: Union[str, UUID],
        parameter_id: Union[str, UUID],
        start_time: datetime,
        end_time: datetime,
        interval_minutes: Optional[int] = None
    ) -> List[AggregatedReading]:
        """
        Get aggregated readings for a specific device and parameter.
        
        Args:
            device_id: The device ID
            parameter_id: The parameter ID
            start_time: The start time for the query
            end_time: The end time for the query
            interval_minutes: Optional filter for specific aggregation intervals
            
        Returns:
            List of aggregated readings
        """
        from ..session import session_scope
        with session_scope(for_write=False) as session:
            query = session.query(AggregatedReading).filter(
                AggregatedReading.device_id == device_id,
                AggregatedReading.parameter_id == parameter_id,
                AggregatedReading.start_time >= start_time,
                AggregatedReading.end_time <= end_time
            )
            
            if interval_minutes:
                query = query.filter(AggregatedReading.interval_minutes == interval_minutes)
                
            query = query.order_by(asc(AggregatedReading.start_time))
            
            aggregations = query.all()
            for agg in aggregations:
                session.expunge(agg)
                
            return aggregations


# Create singleton instances for use throughout the application
device_repository = DeviceRepository()
parameter_repository = ParameterRepository()
sensor_reading_repository = SensorReadingRepository()
aggregated_reading_repository = AggregatedReadingRepository()
