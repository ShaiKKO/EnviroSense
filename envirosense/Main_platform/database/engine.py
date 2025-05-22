"""
SQLAlchemy engine configuration for Aurora PostgreSQL.

This module provides optimized database engines for EnviroSense's Aurora PostgreSQL integration.
"""

import logging
from sqlalchemy import create_engine
from .config import get_connection_string, get_engine_kwargs

logger = logging.getLogger(__name__)

# Create separate engines for read and write operations to leverage Aurora's architecture
writer_engine = None
reader_engine = None


def init_engines(echo=False):
    """
    Initialize the SQLAlchemy engines for read and write operations.
    
    Args:
        echo (bool): If True, enable SQL query logging (useful for development)
        
    Returns:
        tuple: (writer_engine, reader_engine)
    """
    global writer_engine, reader_engine
    
    kwargs = get_engine_kwargs()
    kwargs["echo"] = echo
    
    # Create writer engine (for INSERT, UPDATE, DELETE operations)
    writer_conn_str = get_connection_string(for_write=True)
    writer_engine = create_engine(writer_conn_str, **kwargs)
    logger.info("Initialized writer engine for PostgreSQL")
    
    # Create reader engine (for SELECT operations)
    # Falls back to writer endpoint if no reader endpoint is configured
    reader_conn_str = get_connection_string(for_write=False)
    reader_engine = create_engine(reader_conn_str, **kwargs)
    logger.info("Initialized reader engine for PostgreSQL")
    
    return writer_engine, reader_engine


def get_writer_engine():
    """Get the engine for write operations, initializing if necessary."""
    global writer_engine
    if writer_engine is None:
        init_engines()
    return writer_engine


def get_reader_engine():
    """Get the engine for read operations, initializing if necessary."""
    global reader_engine
    if reader_engine is None:
        init_engines()
    return reader_engine


# Initialize engines on module import
init_engines(echo=True)
