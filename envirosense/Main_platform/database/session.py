"""
SQLAlchemy session management for Aurora PostgreSQL.

This module provides session creation and management utilities optimized for Aurora PostgreSQL,
including read/write session separation and context managers for safe database operations.
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional, Callable, Any
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from .engine import get_writer_engine, get_reader_engine

logger = logging.getLogger(__name__)

# Create session factories for different operations
WriteSession = sessionmaker(bind=get_writer_engine())
ReadSession = sessionmaker(bind=get_reader_engine())

# Default session uses writer engine
Session = WriteSession


def get_session(for_write=True) -> SQLAlchemySession:
    """
    Get a new SQLAlchemy session.
    
    Args:
        for_write (bool): If True, return a session for write operations,
                          otherwise return a read-only session.
                          
    Returns:
        SQLAlchemySession: A new SQLAlchemy session object
    """
    if for_write:
        return WriteSession()
    else:
        return ReadSession()


@contextmanager
def session_scope(
    for_write: bool = True,
    on_error: Optional[Callable[[Exception], Any]] = None
) -> Generator[SQLAlchemySession, None, None]:
    """
    Context manager for handling SQLAlchemy session lifecycle.
    
    Automatically commits changes and handles rollback on errors.
    
    Args:
        for_write (bool): If True, use writer session, otherwise use reader session
        on_error (Callable): Optional callback function to handle exceptions
        
    Yields:
        SQLAlchemySession: SQLAlchemy session
        
    Example:
        ```python
        with session_scope() as session:
            sensor_data = SensorData(value=123.45, timestamp=datetime.now())
            session.add(sensor_data)
            # Auto-commits on exit, rolls back on exception
        ```
    """
    session = get_session(for_write=for_write)
    try:
        yield session
        if for_write:
            session.commit()
    except Exception as e:
        if for_write:
            session.rollback()
            logger.exception("Error in database session, rolling back")
        if on_error:
            on_error(e)
        raise
    finally:
        session.close()


class ReadOnlySession:
    """
    Context manager for read-only database operations.
    
    Ensures operations use the reader endpoint and cannot modify data.
    
    Example:
        ```python
        with ReadOnlySession() as session:
            result = session.query(SensorData).filter_by(device_id='123').all()
        ```
    """
    
    def __init__(self):
        self.session = None
    
    def __enter__(self):
        self.session = get_session(for_write=False)
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.session.close()
