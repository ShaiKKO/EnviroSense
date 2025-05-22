"""
Base classes and mixins for SQLAlchemy ORM models.

This module provides the base declarative base and common mixins for all EnviroSense database models.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import MutableDict

# Create the base class for all models
Base = declarative_base()


class TimestampMixin:
    """
    Mixin to add created_at and updated_at timestamps to models.
    
    Automatically manages creation and update timestamps.
    """
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )


class UUIDMixin:
    """
    Mixin to add a UUID primary key to models.
    
    Uses PostgreSQL's native UUID type for better performance and indexing.
    """
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False
    )


class MetadataMixin:
    """
    Mixin to add a flexible metadata JSON field to models.
    
    Uses PostgreSQL's JSONB type for efficient storage and querying of schemaless data.
    """
    
    metadata = Column(
        MutableDict.as_mutable(JSONB),
        default=dict,
        nullable=False
    )
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a value from the metadata dictionary."""
        return self.metadata.get(key, default)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set a value in the metadata dictionary."""
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value


class AuditMixin:
    """
    Mixin to add audit tracking fields to models.
    
    Tracks creation and modification information.
    """
    
    created_by = Column(String(255), nullable=True)
    modified_by = Column(String(255), nullable=True)
