"""
Example usage of the EnviroSense database adapter.

This script demonstrates how to use the database adapter to:
1. Register devices and parameters
2. Record sensor readings
3. Retrieve and analyze data
4. Use aggregation features
"""

import logging
from datetime import datetime, timedelta, UTC
import json
import random
import uuid
import math

from envirosense.Main_platform.database.adapter import db
from envirosense.Main_platform.database.models.sensor_data import Device, Parameter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_device_registration():
    """Example of registering devices"""
    try:
        # Register a Grid Guardian device
        grid_guardian = db.register_device(
            serial_number="GG-00002",
            name="Grid Guardian Beta",
            device_type="grid_guardian",
            firmware_version="1.1.0",
            latitude=40.7128,
            longitude=-74.0060,  # New York
            location_name="Power Substation B",
            metadata={"installation_type": "outdoor"}
        )
        logger.info(f"Registered Grid Guardian: {grid_guardian.name}")
        
        # Register a wearable device
        wearable = db.register_device(
            serial_number="ES-00002",
            name="EnviroSense Band Beta",
            device_type="wearable",
            firmware_version="1.0.5",
            location_name="Mobile Device",
            metadata={"wearer_id": "test-subject-002", "device_model": "ES-2025"}
        )
        logger.info(f"Registered wearable: {wearable.name}")
        
    except ValueError as e:
        # This will happen if the devices already exist
        logger.warning(f"Device registration error: {e}")
        
    # Find devices by type
    grid_guardians = db.find_devices_by_type("grid_guardian")
    logger.info(f"Found {len(grid_guardians)} Grid Guardian devices")
    
    # Find devices in geographic area (New York area)
    area_devices = db.find_devices_in_area(
        lat_min=40.0, lat_max=41.0,
        lon_min=-75.0, lon_max=-73.0
    )
    logger.info(f"Found {len(area_devices)} devices in the New York area")
    
    return grid_guardians[0] if grid_guardians else None


def example_parameter_registration():
    """Example of registering parameters"""
    try:
        # Register environmental parameters
        oxygen = db.register_parameter(
            code="o2",
            name="Oxygen",
            description="Oxygen concentration in air",
            unit="%",
            min_valid_value=0.0,
            max_valid_value=25.0
        )
        logger.info(f"Registered parameter: {oxygen.name}")
        
        voc = db.register_parameter(
            code="voc",
            name="Volatile Organic Compounds",
            description="Total VOC concentration",
            unit="ppb",
            min_valid_value=0.0,
            max_valid_value=10000.0
        )
        logger.info(f"Registered parameter: {voc.name}")
        
    except ValueError as e:
        # This will happen if the parameters already exist
        logger.warning(f"Parameter registration error: {e}")
    
    # Get all registered parameters
    all_params = []
    
    # Try to get some common parameters we expect to exist
    for code in ["temp", "humidity", "co", "no2", "o2", "voc"]:
        param = db.get_parameter_by_code(code)
        if param:
            all_params.append(param)
    
    logger.info(f"Found {len(all_params)} registered parameters")
    return all_params


def example_record_readings(device: Device, parameters: list[Parameter]):
    """Example of recording sensor readings"""
    if not device or not parameters:
        logger.warning("Missing device or parameters, skipping recording example")
        return None
    
    # Create a batch of readings
    readings_data = []
    now = datetime.now(UTC)
    
    # Generate 24 hours of hourly readings for all parameters
    for hour_offset in range(24, 0, -1):
        timestamp = now - timedelta(hours=hour_offset)
        
        for param in parameters:
            # Generate a realistic value based on parameter
            if param.code == "temp":
                # Temperature with daily cycle
                hour_of_day = timestamp.hour
                base_temp = 20  # Base temperature in C
                daily_variation = 5 * math.sin((hour_of_day - 6) * math.pi / 12)
                value = base_temp + daily_variation + random.uniform(-0.5, 0.5)
            elif param.code == "humidity":
                # Humidity inversely related to temperature cycle
                hour_of_day = timestamp.hour
                base_humidity = 50  # Base humidity %
                daily_variation = -10 * math.sin((hour_of_day - 6) * math.pi / 12)
                value = base_humidity + daily_variation + random.uniform(-3, 3)
            elif param.code == "co":
                # CO levels typically low with occasional spikes
                if random.random() < 0.1:  # 10% chance of elevated reading
                    value = random.uniform(3, 10)
                else:
                    value = random.uniform(0.1, 1.0)
            elif param.code == "no2":
                # NO2 levels higher during rush hours
                hour_of_day = timestamp.hour
                if hour_of_day in [7, 8, 9, 16, 17, 18]:  # Rush hours
                    value = random.uniform(10, 25)
                else:
                    value = random.uniform(5, 15)
            elif param.code == "o2":
                # Oxygen levels normally stable around 20.9%
                value = 20.9 + random.uniform(-0.2, 0.1)
            elif param.code == "voc":
                # VOCs with occasional spikes
                if random.random() < 0.2:  # 20% chance of elevated reading
                    value = random.uniform(500, 1500)
                else:
                    value = random.uniform(50, 300)
            else:
                # Generic randomized value
                min_val = param.min_valid_value or 0
                max_val = param.max_valid_value or 100
                value = random.uniform(min_val, max_val)
            
            # Add the reading data
            readings_data.append({
                "device_id": device.id,
                "parameter_id": param.id,
                "value": value,
                "timestamp": timestamp,
                "quality": random.randint(80, 100),  # Good quality data
                "is_validated": True,
                "uncertainty": value * 0.05  # 5% uncertainty
            })
    
    # Record the batch
    batch_id = db.record_readings_batch(readings_data)
    logger.info(f"Recorded {len(readings_data)} readings with batch ID: {batch_id}")
    return batch_id


def example_data_retrieval(device: Device, parameters: list[Parameter], batch_id: str):
    """Example of retrieving and analyzing data"""
    if not device or not parameters or not batch_id:
        logger.warning("Missing device, parameters, or batch_id - skipping retrieval example")
        return
    
    # 1. Get latest readings for each parameter
    latest_readings = db.get_latest_device_readings(device.id)
    logger.info(f"Retrieved {len(latest_readings)} latest readings for {device.name}")
    
    # Display some of the latest readings
    for param in parameters[:2]:  # Just show a couple for brevity
        if str(param.id) in latest_readings:
            reading = latest_readings[str(param.id)]
            logger.info(f"Latest {param.name}: {reading.value} {param.unit} at {reading.timestamp}")
    
    # 2. Get readings for a specific time period
    now = datetime.now(UTC)
    start_time = now - timedelta(hours=12)
    end_time = now
    
    if parameters:
        param = parameters[0]  # Just use the first parameter for this example
        readings = db.get_device_readings(
            device_id=device.id,
            parameter_id=param.id,
            start_time=start_time,
            end_time=end_time
        )
        
        logger.info(f"Retrieved {len(readings)} {param.name} readings for the past 12 hours")
        
        if readings:
            # Show min, max, avg
            values = [r.value for r in readings]
            min_val = min(values)
            max_val = max(values)
            avg_val = sum(values) / len(values)
            
            logger.info(f"{param.name} statistics: Min={min_val:.2f}, Max={max_val:.2f}, Average={avg_val:.2f} {param.unit}")
    
    # 3. Get all readings from the batch
    from envirosense.Main_platform.database.repositories.sensor_repositories import sensor_reading_repository
    batch_readings = sensor_reading_repository.get_batch_readings(batch_id)
    logger.info(f"Retrieved {len(batch_readings)} readings from batch {batch_id}")


def example_aggregation(device: Device, parameters: list[Parameter]):
    """Example of data aggregation"""
    if not device or not parameters:
        logger.warning("Missing device or parameters - skipping aggregation example")
        return
    
    now = datetime.now(UTC)
    start_time = now - timedelta(days=1)
    end_time = now
    
    if parameters:
        # Create hourly aggregation for a parameter
        param = parameters[0]
        
        aggregated = db.create_aggregated_reading(
            device_id=device.id,
            parameter_id=param.id,
            start_time=start_time,
            end_time=end_time,
            interval_minutes=60  # Hourly aggregation
        )
        
        if aggregated:
            logger.info(f"Created hourly aggregation for {param.name}:")
            logger.info(f"  Time period: {aggregated.start_time} to {aggregated.end_time}")
            logger.info(f"  Min: {aggregated.min_value:.2f}, Max: {aggregated.max_value:.2f}")
            logger.info(f"  Average: {aggregated.avg_value:.2f}, Median: {aggregated.median_value:.2f}")
            logger.info(f"  Standard deviation: {aggregated.std_deviation:.2f}")
            logger.info(f"  Sample count: {aggregated.count}")


def main():
    """Main entry point for database adapter example"""
    logger.info("Starting EnviroSense database adapter example...")
    
    # Register devices and parameters
    device = example_device_registration()
    parameters = example_parameter_registration()
    
    # Record and retrieve data
    batch_id = example_record_readings(device, parameters)
    example_data_retrieval(device, parameters, batch_id)
    
    # Aggregate data
    example_aggregation(device, parameters)
    
    logger.info("Database adapter example completed successfully")


if __name__ == "__main__":
    main()
