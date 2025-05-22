"""
Database utility functions for EnviroSense PostgreSQL database.

This module provides helper functions for common database operations like 
data initialization, basic queries, and demonstrating ORM model usage.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

from sqlalchemy import func, and_, or_, desc, asc

from .session import session_scope
from .models.sensor_data import Device, Parameter, SensorReading, AggregatedReading
from .repositories.sensor_repositories import (
    device_repository, 
    parameter_repository,
    sensor_reading_repository,
    aggregated_reading_repository
)

logger = logging.getLogger(__name__)


def verify_database_connection() -> bool:
    """
    Verify database connection by performing a simple query.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        with session_scope(for_write=False) as session:
            # Simple query to check connection
            result = session.execute("SELECT 1").scalar()
            return result == 1
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return False


def create_sample_parameter(
    name: str, 
    code: str, 
    unit: str, 
    min_value: float = None, 
    max_value: float = None
) -> Parameter:
    """
    Create a sample parameter in the database.
    
    Args:
        name: Full name of the parameter
        code: Unique code for the parameter
        unit: Unit of measurement
        min_value: Minimum valid value
        max_value: Maximum valid value
        
    Returns:
        Parameter: The created parameter
    """
    try:
        parameter = parameter_repository.create(
            name=name,
            code=code,
            description=f"Measurement of {name}",
            unit=unit,
            min_valid_value=min_value,
            max_valid_value=max_value
        )
        logger.info(f"Created parameter: {code}")
        return parameter
    except Exception as e:
        logger.error(f"Error creating parameter {code}: {e}")
        raise


def create_sample_device(
    serial_number: str,
    name: str,
    device_type: str,
    latitude: float = None,
    longitude: float = None
) -> Device:
    """
    Create a sample device in the database.
    
    Args:
        serial_number: Unique serial number
        name: Device name
        device_type: Type of device
        latitude: Optional latitude coordinate
        longitude: Optional longitude coordinate
        
    Returns:
        Device: The created device
    """
    try:
        device = device_repository.create(
            serial_number=serial_number,
            name=name,
            device_type=device_type,
            latitude=latitude,
            longitude=longitude,
            firmware_version="1.0.0",
            is_active=True,
            last_seen=datetime.utcnow(),
            metadata={
                "installation_date": datetime.utcnow().isoformat(),
                "battery_level": 100,
                "configuration": {
                    "sampling_rate": 60,  # seconds
                    "transmission_interval": 300  # seconds
                }
            }
        )
        logger.info(f"Created device: {serial_number}")
        return device
    except Exception as e:
        logger.error(f"Error creating device {serial_number}: {e}")
        raise


def create_sample_readings(
    device_id: Union[str, uuid.UUID],
    parameter_id: Union[str, uuid.UUID],
    count: int = 10,
    start_time: Optional[datetime] = None,
    interval_seconds: int = 60,
    base_value: float = 20.0,
    variation: float = 5.0
) -> List[SensorReading]:
    """
    Create sample sensor readings for a device and parameter.
    
    Args:
        device_id: Device ID
        parameter_id: Parameter ID
        count: Number of readings to create
        start_time: Start time for the first reading (defaults to now - count*interval)
        interval_seconds: Seconds between readings
        base_value: Base value for the readings
        variation: Random variation range (+/-)
        
    Returns:
        List[SensorReading]: List of created readings
    """
    import random
    
    if start_time is None:
        start_time = datetime.utcnow() - timedelta(seconds=count * interval_seconds)
    
    readings = []
    batch_id = str(uuid.uuid4())
    
    try:
        for i in range(count):
            timestamp = start_time + timedelta(seconds=i * interval_seconds)
            # Generate a somewhat realistic value with some random variation
            value = base_value + (random.random() * 2 - 1) * variation
            
            reading = sensor_reading_repository.create_reading(
                device_id=device_id,
                parameter_id=parameter_id,
                value=value,
                timestamp=timestamp,
                batch_id=batch_id,
                quality=random.randint(80, 100),
                is_validated=True,
                uncertainty=value * 0.05  # 5% uncertainty
            )
            readings.append(reading)
        
        logger.info(f"Created {count} sample readings for device {device_id} and parameter {parameter_id}")
        return readings
    except Exception as e:
        logger.error(f"Error creating sample readings: {e}")
        raise


def create_sample_aggregation(
    device_id: Union[str, uuid.UUID],
    parameter_id: Union[str, uuid.UUID],
    readings: List[SensorReading]
) -> AggregatedReading:
    """
    Create a sample aggregated reading from a list of readings.
    
    Args:
        device_id: Device ID
        parameter_id: Parameter ID
        readings: List of readings to aggregate
        
    Returns:
        AggregatedReading: The created aggregated reading
    """
    if not readings:
        raise ValueError("Cannot create aggregation from empty readings list")
    
    # Sort readings by timestamp
    sorted_readings = sorted(readings, key=lambda r: r.timestamp)
    
    # Calculate aggregation values
    values = [r.value for r in sorted_readings]
    min_value = min(values)
    max_value = max(values)
    avg_value = sum(values) / len(values)
    
    # Sort values for median
    sorted_values = sorted(values)
    if len(sorted_values) % 2 == 0:
        median_value = (sorted_values[len(sorted_values)//2 - 1] + sorted_values[len(sorted_values)//2]) / 2
    else:
        median_value = sorted_values[len(sorted_values)//2]
    
    # Calculate standard deviation
    mean = avg_value
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std_deviation = variance ** 0.5
    
    try:
        aggregation = aggregated_reading_repository.create_aggregation(
            device_id=device_id,
            parameter_id=parameter_id,
            start_time=sorted_readings[0].timestamp,
            end_time=sorted_readings[-1].timestamp,
            min_value=min_value,
            max_value=max_value,
            avg_value=avg_value,
            median_value=median_value,
            std_deviation=std_deviation,
            count=len(readings)
        )
        logger.info(f"Created aggregation for device {device_id} and parameter {parameter_id}")
        return aggregation
    except Exception as e:
        logger.error(f"Error creating aggregation: {e}")
        raise


def get_parameter_by_code(code: str) -> Optional[Parameter]:
    """
    Get a parameter by its code.
    
    Args:
        code: Parameter code
        
    Returns:
        Optional[Parameter]: The parameter if found, None otherwise
    """
    return parameter_repository.find_by_code(code)


def get_device_by_serial(serial_number: str) -> Optional[Device]:
    """
    Get a device by its serial number.
    
    Args:
        serial_number: Device serial number
        
    Returns:
        Optional[Device]: The device if found, None otherwise
    """
    return device_repository.find_by_serial_number(serial_number)


def get_recent_readings(
    device_id: Union[str, uuid.UUID],
    parameter_id: Optional[Union[str, uuid.UUID]] = None,
    limit: int = 10
) -> List[SensorReading]:
    """
    Get recent readings for a device.
    
    Args:
        device_id: Device ID
        parameter_id: Optional parameter ID filter
        limit: Maximum number of readings to return
        
    Returns:
        List[SensorReading]: List of recent readings
    """
    return sensor_reading_repository.get_readings_for_device(
        device_id=device_id,
        parameter_id=parameter_id,
        limit=limit
    )


def initialize_sample_data():
    """
    Initialize sample data in the database.
    
    Creates basic parameters, devices, and readings for testing purposes.
    """
    # Create environmental parameters
    parameters = {
        "temperature": create_sample_parameter("Temperature", "TEMP", "°C", -50, 150),
        "humidity": create_sample_parameter("Humidity", "HUM", "%", 0, 100),
        "co2": create_sample_parameter("Carbon Dioxide", "CO2", "ppm", 0, 5000),
        "voc": create_sample_parameter("Volatile Organic Compounds", "VOC", "ppb", 0, 1000),
        "pm25": create_sample_parameter("Particulate Matter 2.5", "PM25", "μg/m³", 0, 500)
    }
    
    # Create devices
    devices = {
        "indoor": create_sample_device("GG-001-INDOOR", "Office Environmental Monitor", "GRID_GUARDIAN_BASIC", 40.7128, -74.0060),
        "outdoor": create_sample_device("GG-002-OUTDOOR", "Outdoor Air Quality Sensor", "GRID_GUARDIAN_WEATHER", 40.7130, -74.0050)
    }
    
    # Create readings for each device and parameter
    for device_name, device in devices.items():
        for param_name, param in parameters.items():
            # Different base values for indoor vs outdoor and different parameters
            base_values = {
                "temperature": 22.0 if device_name == "indoor" else 15.0,
                "humidity": 40.0 if device_name == "indoor" else 60.0,
                "co2": 800.0 if device_name == "indoor" else 400.0,
                "voc": 200.0 if device_name == "indoor" else 50.0,
                "pm25": 15.0 if device_name == "indoor" else 30.0
            }
            
            # Create hourly readings for the past 24 hours
            readings = create_sample_readings(
                device_id=device.id,
                parameter_id=param.id,
                count=24,
                start_time=datetime.utcnow() - timedelta(hours=24),
                interval_seconds=3600,  # hourly
                base_value=base_values[param_name],
                variation=base_values[param_name] * 0.2  # 20% variation
            )
            
            # Create aggregation
            create_sample_aggregation(device.id, param.id, readings)
    
    logger.info("Sample data initialization complete")


def query_demonstration():
    """Run sample queries to demonstrate database access."""
    # Get all devices
    devices = device_repository.get_all()
    print(f"Found {len(devices)} devices:")
    for device in devices:
        print(f"  - {device.name} (SN: {device.serial_number})")
    
    # Get all parameters
    parameters = parameter_repository.get_all()
    print(f"\nFound {len(parameters)} parameters:")
    for param in parameters:
        print(f"  - {param.name} ({param.code}): {param.unit}")
    
    # Get readings for the first device and parameter
    if devices and parameters:
        device = devices[0]
        param = parameters[0]
        readings = get_recent_readings(device.id, param.id, 5)
        print(f"\nRecent {param.name} readings for {device.name}:")
        for reading in readings:
            print(f"  - {reading.timestamp}: {reading.value} {param.unit}")
        
        # Get aggregations
        with session_scope(for_write=False) as session:
            agg = session.query(AggregatedReading).filter(
                AggregatedReading.device_id == device.id,
                AggregatedReading.parameter_id == param.id
            ).first()
            
            if agg:
                print(f"\nAggregation for {param.name} on {device.name}:")
                print(f"  Period: {agg.start_time} to {agg.end_time}")
                print(f"  Min: {agg.min_value} {param.unit}")
                print(f"  Max: {agg.max_value} {param.unit}")
                print(f"  Avg: {agg.avg_value} {param.unit}")
                print(f"  Count: {agg.count} readings")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Verify connection
    if verify_database_connection():
        print("Database connection successful!")
        
        # Initialize sample data if requested
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == "--init":
            print("Initializing sample data...")
            initialize_sample_data()
        
        # Run query demonstration
        query_demonstration()
    else:
        print("Failed to connect to database!")
