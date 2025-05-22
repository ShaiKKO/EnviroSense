"""
Sensor data models for storing environmental measurements.

This module provides SQLAlchemy ORM models for persistent storage of sensor data.
"""

import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Union
from uuid import uuid4

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer, 
    String, Boolean, Text, Index
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, UUIDMixin, MetadataMixin


class Device(Base, UUIDMixin, TimestampMixin, MetadataMixin):
    """
    Represents a physical sensing device in the EnviroSense ecosystem.
    
    This model stores information about devices that collect environmental data.
    """
    
    __tablename__ = 'devices'
    
    # Device identifiers and basic properties
    serial_number = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=True)
    device_type = Column(String(64), nullable=False, index=True)
    firmware_version = Column(String(32), nullable=True)
    
    # Location information
    location_name = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    elevation = Column(Float, nullable=True)  # meters above sea level
    
    # Operational status
    is_active = Column(Boolean, default=True, nullable=False)
    last_seen = Column(DateTime, nullable=True)
    
    # Relationships
    sensor_readings = relationship(
        "SensorReading", 
        back_populates="device", 
        cascade="all, delete-orphan"
    )
    
    # Create indexes for common queries
    __table_args__ = (
        Index('idx_devices_type_active', device_type, is_active),
        Index('idx_devices_location', latitude, longitude),
        {'schema': 'sensor'}
    )


class Parameter(Base, UUIDMixin, TimestampMixin):
    """
    Represents an environmental parameter that can be measured by sensors.
    
    Examples include temperature, humidity, CO2 levels, etc.
    """
    
    __tablename__ = 'parameters'
    
    # Parameter properties
    name = Column(String(255), nullable=False, unique=True, index=True)
    code = Column(String(64), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    unit = Column(String(32), nullable=True)  # e.g., "°C", "ppm", "μg/m³"
    
    # Value constraints
    min_valid_value = Column(Float, nullable=True)
    max_valid_value = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)  # Number of decimal places
    
    # Relationships
    sensor_readings = relationship(
        "SensorReading",
        back_populates="parameter",
        cascade="all, delete-orphan"
    )
    __table_args__ = {'schema': 'sensor'}


class SensorReading(Base, UUIDMixin, TimestampMixin):
    """
    Represents an individual sensor reading for a specific parameter.
    """
    
    __tablename__ = 'sensor_readings'
    
    # Foreign keys
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey('sensor.devices.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    parameter_id = Column(
        UUID(as_uuid=True),
        ForeignKey('sensor.parameters.id'),
        nullable=False,
        index=True
    )
    
    # Reading information
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    value = Column(Float, nullable=False)
    raw_value = Column(Float, nullable=True)  # Pre-calibration value if applicable
    
    # Data quality information
    quality = Column(Integer, nullable=True)  # 0-100 quality score
    is_validated = Column(Boolean, default=False, nullable=False)
    uncertainty = Column(Float, nullable=True)  # +/- uncertainty range
    
    # Batch information for grouping related readings
    batch_id = Column(String(64), nullable=True, index=True)
    
    # Additional information in JSONB for flexibility
    additional_data = Column(MutableDict.as_mutable(JSONB), default=dict, nullable=True)
    
    # Relationships
    device = relationship("Device", back_populates="sensor_readings")
    parameter = relationship("Parameter", back_populates="sensor_readings")
    
    # Create compound indexes for common query patterns
    __table_args__ = (
        Index('idx_readings_device_param_time', device_id, parameter_id, timestamp),
        Index('idx_readings_time_range', timestamp),
        {'schema': 'sensor'}
    )


class AggregatedReading(Base, UUIDMixin):
    """
    Represents aggregated sensor readings over time periods.
    
    This model is used for downsampling high-frequency data to improve query performance.
    """
    
    __tablename__ = 'aggregated_readings'
    
    # Foreign keys
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey('sensor.devices.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    parameter_id = Column(
        UUID(as_uuid=True),
        ForeignKey('sensor.parameters.id'),
        nullable=False,
        index=True
    )
    
    # Time information
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    interval_minutes = Column(Integer, nullable=False)  # Duration in minutes
    
    # Aggregated values
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    avg_value = Column(Float, nullable=True)
    median_value = Column(Float, nullable=True)
    std_deviation = Column(Float, nullable=True)
    count = Column(Integer, nullable=False)
    
    # Create compound indexes for common query patterns
    __table_args__ = (
        Index('idx_agg_device_param_time', device_id, parameter_id, start_time, end_time),
        {'schema': 'sensor'}
    )
