"""
EnviroSense Aurora PostgreSQL integration.

This package provides integration with Aurora PostgreSQL for EnviroSense,
supporting high-performance read/write operations with proper failover handling.
"""

from .adapter import DatabaseAdapter, database_adapter
from .engine import get_reader_engine, get_writer_engine, init_engines
from .session import session_scope, ReadOnlySession, get_session
from .models.base import Base, TimestampMixin, UUIDMixin, MetadataMixin, AuditMixin
from .repositories.base import BaseRepository

__all__ = [
    # Adapter
    'DatabaseAdapter',
    'database_adapter',
    
    # Engines
    'get_reader_engine',
    'get_writer_engine',
    'init_engines',
    
    # Sessions
    'session_scope',
    'ReadOnlySession',
    'get_session',
    
    # Models
    'Base',
    'TimestampMixin',
    'UUIDMixin',
    'MetadataMixin',
    'AuditMixin',
    
    # Repositories
    'BaseRepository',
]

# Version information
__version__ = '0.1.0'
