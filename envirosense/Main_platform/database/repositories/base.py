"""
Base repository class for database operations.

This module provides the foundation for the Repository pattern implementation in EnviroSense,
offering generic CRUD operations and query capabilities.
"""

import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union, cast
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Query, Session

from ..models.base import Base
from ..session import session_scope

# Type variable for the model classes
T = TypeVar('T', bound=Base)

logger = logging.getLogger(__name__)


class BaseRepository(Generic[T]):
    """
    Base repository class for CRUD operations on a model.
    
    This class implements the Repository pattern and provides generic
    operations for working with SQLAlchemy models. It's designed to be
    extended by model-specific repository classes.
    
    Attributes:
        model_class (Type[T]): The SQLAlchemy model class this repository works with
    """
    
    def __init__(self, model_class: Type[T]):
        """
        Initialize the repository with a model class.
        
        Args:
            model_class (Type[T]): The SQLAlchemy model class this repository works with
        """
        self.model_class = model_class
    
    def create(self, **kwargs) -> T:
        """
        Create a new entity in the database.
        
        Args:
            **kwargs: Attributes for the new entity
            
        Returns:
            T: The created entity
            
        Raises:
            SQLAlchemyError: If there was an error creating the entity
        """
        with session_scope() as session:
            entity = self.model_class(**kwargs)
            session.add(entity)
            session.flush()  # Ensure we get generated values like IDs
            # Detach from session
            session.expunge(entity)
            return entity
    
    def get_by_id(self, entity_id: Union[str, UUID], for_update: bool = False) -> Optional[T]:
        """
        Get an entity by its ID.
        
        Args:
            entity_id (Union[str, UUID]): The entity ID
            for_update (bool): If True, lock the row for update
            
        Returns:
            Optional[T]: The entity if found, None otherwise
        """
        with session_scope(for_write=for_update) as session:
            query = session.query(self.model_class).filter(self.model_class.id == entity_id)
            
            if for_update:
                query = query.with_for_update()
            
            entity = query.first()
            if entity:
                session.expunge(entity)
            return entity
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """
        Get all entities with optional pagination.
        
        Args:
            limit (Optional[int]): Maximum number of entities to return
            offset (int): Number of entities to skip
            
        Returns:
            List[T]: List of entities
        """
        with session_scope(for_write=False) as session:
            query = session.query(self.model_class)
            
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
                
            entities = query.all()
            for entity in entities:
                session.expunge(entity)
            return entities
    
    def update(self, entity_id: Union[str, UUID], **kwargs) -> Optional[T]:
        """
        Update an existing entity.
        
        Args:
            entity_id (Union[str, UUID]): The ID of the entity to update
            **kwargs: Attributes to update
            
        Returns:
            Optional[T]: The updated entity if found, None otherwise
            
        Raises:
            SQLAlchemyError: If there was an error updating the entity
        """
        with session_scope() as session:
            entity = session.query(self.model_class).filter(
                self.model_class.id == entity_id
            ).with_for_update().first()
            
            if not entity:
                return None
            
            for key, value in kwargs.items():
                setattr(entity, key, value)
                
            session.flush()
            session.expunge(entity)
            return entity
    
    def delete(self, entity_id: Union[str, UUID]) -> bool:
        """
        Delete an entity by its ID.
        
        Args:
            entity_id (Union[str, UUID]): The ID of the entity to delete
            
        Returns:
            bool: True if the entity was deleted, False if not found
            
        Raises:
            SQLAlchemyError: If there was an error deleting the entity
        """
        with session_scope() as session:
            entity = session.query(self.model_class).filter(
                self.model_class.id == entity_id
            ).first()
            
            if not entity:
                return False
                
            session.delete(entity)
            return True
    
    def count(self, **filters) -> int:
        """
        Count entities with optional filters.
        
        Args:
            **filters: Filter conditions
            
        Returns:
            int: Count of matching entities
        """
        with session_scope(for_write=False) as session:
            query = session.query(self.model_class)
            
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
                    
            return query.count()
    
    def exists(self, entity_id: Union[str, UUID]) -> bool:
        """
        Check if an entity with the given ID exists.
        
        Args:
            entity_id (Union[str, UUID]): The entity ID to check
            
        Returns:
            bool: True if the entity exists, False otherwise
        """
        with session_scope(for_write=False) as session:
            return session.query(
                session.query(self.model_class).filter(
                    self.model_class.id == entity_id
                ).exists()
            ).scalar()
    
    def filter(self, limit: Optional[int] = None, offset: int = 0, **filters) -> List[T]:
        """
        Get entities matching the given filters.
        
        Args:
            limit (Optional[int]): Maximum number of entities to return
            offset (int): Number of entities to skip
            **filters: Filter conditions
            
        Returns:
            List[T]: List of matching entities
        """
        with session_scope(for_write=False) as session:
            query = session.query(self.model_class)
            
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
                    
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
                
            entities = query.all()
            for entity in entities:
                session.expunge(entity)
            return entities
