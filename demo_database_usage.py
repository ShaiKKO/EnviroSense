"""
Demo script for EnviroSense PostgreSQL database integration.

This script demonstrates:
1. Connecting to the database
2. Creating sample device and parameter entries
3. Recording sensor readings
4. Querying data using various repository methods
"""

import logging
import uuid
from datetime import datetime, timedelta, UTC
import random

# Eagerly import and print connection string for debugging
from envirosense.Main_platform.database.config import get_connection_string
print(f"DEMO SCRIPT WRITER CONNECTION STRING: {get_connection_string(for_write=True)}")
print(f"DEMO SCRIPT READER CONNECTION STRING: {get_connection_string(for_write=False)}")

from envirosense.Main_platform.database.session import session_scope
from envirosense.Main_platform.database.models.sensor_data import Device, Parameter, SensorReading
from envirosense.Main_platform.database.repositories.sensor_repositories import (
    device_repository,
    parameter_repository,
    sensor_reading_repository,
    aggregated_reading_repository
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_devices():
    """Create sample device entries"""
    devices = [
        {
            "serial_number": "GG-00001",
            "name": "Grid Guardian Alpha",
            "device_type": "grid_guardian",
            "firmware_version": "1.0.0",
            "latitude": 39.7392,
            "longitude": -104.9903,  # Denver
            "last_seen": datetime.now(UTC),
            "metadata": {"location": "Power Substation A", "zone": "Industrial", "installation_date": datetime.now(UTC).isoformat()}
        },
        {
            "serial_number": "ES-00001",
            "name": "EnviroSense Band Alpha",
            "device_type": "wearable",
            "firmware_version": "1.0.0",
            "metadata": {"wearer_id": "test-subject-001", "sensitivity": "high"}
        },
        {
            "serial_number": "WS-00001",
            "name": "Wildland Sentinel Alpha",
            "device_type": "wildfire_detector",
            "firmware_version": "1.0.0",
            "latitude": 37.7749,
            "longitude": -122.4194,  # San Francisco
            "last_seen": datetime.now(UTC),
            "metadata": {"forest_zone": "Northern California", "tree_density": "high", "installation_date": (datetime.now(UTC) - timedelta(days=30)).isoformat()}
        }
    ]
    
    created_devices = []
    for device_data in devices:
        # Check if device already exists
        existing = device_repository.find_by_serial_number(device_data["serial_number"])
        if existing:
            logger.info(f"Device {device_data['serial_number']} already exists")
            created_devices.append(existing)
        else:
            # Create new device with UUID
            device_data["id"] = str(uuid.uuid4())
            device = device_repository.create(**device_data)
            logger.info(f"Created device: {device.name} ({device.serial_number})")
            created_devices.append(device)
    
    return created_devices


def create_sample_parameters():
    """Create sample parameter entries"""
    parameters = [
        {
            "code": "temp",
            "name": "Temperature",
            "description": "Ambient temperature",
            "unit": "°C",
            "min_valid_value": -40.0,
            "max_valid_value": 85.0
        },
        {
            "code": "co",
            "name": "Carbon Monoxide",
            "description": "Carbon monoxide concentration",
            "unit": "ppm",
            "min_valid_value": 0.0,
            "max_valid_value": 1000.0
        },
        {
            "code": "no2",
            "name": "Nitrogen Dioxide",
            "description": "Nitrogen dioxide concentration",
            "unit": "ppb",
            "min_valid_value": 0.0,
            "max_valid_value": 1000.0
        },
        {
            "code": "humidity",
            "name": "Relative Humidity",
            "description": "Relative humidity percentage",
            "unit": "%",
            "min_valid_value": 0.0,
            "max_valid_value": 100.0
        },
        {
            "code": "pm25",
            "name": "PM2.5",
            "description": "Particulate matter 2.5 micrometers or smaller",
            "unit": "µg/m³",
            "min_valid_value": 0.0,
            "max_valid_value": 500.0
        }
    ]
    
    created_params = []
    for param_data in parameters:
        # Check if parameter already exists by code or name
        existing_by_code = parameter_repository.find_by_code(param_data["code"])
        existing_by_name = parameter_repository.find_by_name(param_data["name"])
        
        if existing_by_code:
            logger.info(f"Parameter with code {param_data['code']} already exists")
            created_params.append(existing_by_code)
        elif existing_by_name:
            logger.info(f"Parameter with name {param_data['name']} already exists")
            created_params.append(existing_by_name)
        else:
            # Create new parameter with UUID
            param_data["id"] = str(uuid.uuid4())
            param = parameter_repository.create(**param_data)
            logger.info(f"Created parameter: {param.name} ({param.code})")
            created_params.append(param)
    
    return created_params


def generate_sample_readings(devices, parameters):
    """Generate sample sensor readings for the past 24 hours"""
    batch_id = f"demo-batch-{uuid.uuid4()}"
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=24)
    current_time = start_time
    
    readings = []
    
    # Generate a reading every 15 minutes for the past 24 hours
    while current_time <= end_time:
        for device in devices:
            for param in parameters:
                # Skip some combinations to make the data more realistic
                if random.random() < 0.2:
                    continue
                    
                # Generate a somewhat realistic value based on parameter type
                if param.code == "temp":
                    # Temperature values between 15-30 C with some variance
                    value = 20 + 5 * math.sin(current_time.timestamp() / 3600) + random.uniform(-1, 1)
                elif param.code == "humidity":
                    # Humidity between 30-70%
                    value = 50 + 20 * math.sin(current_time.timestamp() / 7200) + random.uniform(-5, 5)
                elif param.code == "co":
                    # CO levels normally low, occasional spikes
                    base = 1.0
                    if random.random() < 0.05:  # Occasional spike
                        base = random.uniform(5, 15)
                    value = base + random.uniform(0, 0.5)
                elif param.code == "no2":
                    # NO2 levels - urban pattern
                    rush_hour = (current_time.hour >= 7 and current_time.hour <= 9) or \
                               (current_time.hour >= 16 and current_time.hour <= 18)
                    base = 15.0 if rush_hour else 5.0
                    value = base + random.uniform(0, 10.0)
                elif param.code == "pm25":
                    # PM2.5 values - daily pattern with some randomness
                    base = 10 + 5 * math.sin(current_time.timestamp() / 43200)  # 12-hour cycle
                    value = base + random.lognormvariate(0, 0.5)
                else:
                    # Generic random value for any other parameter
                    value = random.uniform(
                        param.min_valid_value or 0, 
                        param.max_valid_value or 100
                    )
                
                # Create the reading
                reading = sensor_reading_repository.create_reading(
                    device_id=device.id,
                    parameter_id=param.id,
                    value=value,
                    timestamp=current_time,
                    batch_id=batch_id,
                    quality=1,  # Good quality
                    is_validated=True
                )
                readings.append(reading)
                
        # Increment by 15 minutes
        current_time += timedelta(minutes=15)
    
    logger.info(f"Generated {len(readings)} sample readings with batch ID: {batch_id}")
    return batch_id


def demo_queries(devices, parameters, batch_id):
    """Demonstrate various query operations"""
    # 1. Get latest reading for a specific device and parameter
    device = devices[0]
    param = parameters[0]
    latest = sensor_reading_repository.get_latest_reading(device.id, param.id)
    if latest:
        logger.info(f"Latest {param.name} reading for {device.name}: {latest.value} {param.unit} at {latest.timestamp}")
    else:
        logger.info(f"No readings found for {device.name} and parameter {param.name}")
    
    # 2. Get readings for a device in the past hour
    device = devices[1]
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=1)
    readings = sensor_reading_repository.get_readings_for_device(
        device_id=device.id,
        start_time=start_time,
        end_time=end_time,
        limit=100
    )
    logger.info(f"Found {len(readings)} readings for {device.name} in the past hour")
    
    # 3. Get all readings in a batch
    batch_readings = sensor_reading_repository.get_batch_readings(batch_id)
    logger.info(f"Total readings in batch {batch_id}: {len(batch_readings)}")
    
    # 4. Find devices in geographic area
    area_devices = device_repository.find_devices_in_area(
        lat_min=37.0, lat_max=40.0, 
        lon_min=-125.0, lon_max=-100.0
    )
    logger.info(f"Found {len(area_devices)} devices in the specified geographic area")
    
    # 5. Count total parameters
    param_count = parameter_repository.count()
    logger.info(f"Total parameters in database: {param_count}")


def main():
    """Main entry point for database demo"""
    logger.info("Starting EnviroSense database integration demo...")
    
    # Import math here for value generation
    global math
    import math
    
    # Create sample data
    devices = create_sample_devices()
    parameters = create_sample_parameters()
    
    # Generate sample readings
    batch_id = generate_sample_readings(devices, parameters)
    
    # Demo queries
    demo_queries(devices, parameters, batch_id)
    
    logger.info("Database demo completed successfully")


if __name__ == "__main__":
    main()
