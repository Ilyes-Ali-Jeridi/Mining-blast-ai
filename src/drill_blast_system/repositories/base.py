"""
Base repository class with common CRUD operations.
Implements generic repository pattern for all entities.
"""

from typing import Generic, TypeVar, Type, List, Optional, Dict, Any
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, desc, asc, func

from ..core.database import BaseModel
from ..core.logging import get_logger

T = TypeVar('T', bound=BaseModel)

logger = get_logger(__name__)


class BaseRepository(Generic[T], ABC):
    """
    Base repository class providing common CRUD operations.
    
    This class implements the repository pattern to abstract database operations
    and provide a consistent interface for data access across all entities.
    """
    
    def __init__(self, db: Session, model: Type[T]):
        """
        Initialize repository with database session and model class.
        
        Args:
            db: SQLAlchemy database session
            model: SQLAlchemy model class
        """
        self.db = db
        self.model = model
        self.logger = get_logger(f"{__name__}.{model.__name__}Repository")
    
    def create(self, obj_data: Dict[str, Any]) -> T:
        """
        Create a new entity.
        
        Args:
            obj_data: Dictionary of entity data
            
        Returns:
            Created entity instance
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            db_obj = self.model(**obj_data)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            
            self.logger.info(
                "Entity created successfully",
                entity_type=self.model.__name__,
                entity_id=db_obj.id
            )
            
            return db_obj
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(
                "Failed to create entity",
                entity_type=self.model.__name__,
                error=str(e)
            )
            raise
    
    def get_by_id(self, entity_id: int) -> Optional[T]:
        """
        Get entity by ID.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Entity instance or None if not found
        """
        try:
            entity = self.db.query(self.model).filter(self.model.id == entity_id).first()
            
            if entity:
                self.logger.debug(
                    "Entity retrieved by ID",
                    entity_type=self.model.__name__,
                    entity_id=entity_id
                )
            else:
                self.logger.debug(
                    "Entity not found by ID",
                    entity_type=self.model.__name__,
                    entity_id=entity_id
                )
            
            return entity
            
        except SQLAlchemyError as e:
            self.logger.error(
                "Failed to get entity by ID",
                entity_type=self.model.__name__,
                entity_id=entity_id,
                error=str(e)
            )
            raise
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[T]:
        """
        Get all entities with pagination and ordering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field name to order by
            order_desc: Whether to order in descending order
            
        Returns:
            List of entity instances
        """
        try:
            query = self.db.query(self.model)
            
            # Apply ordering
            if order_by and hasattr(self.model, order_by):
                order_field = getattr(self.model, order_by)
                if order_desc:
                    query = query.order_by(desc(order_field))
                else:
                    query = query.order_by(asc(order_field))
            
            # Apply pagination
            entities = query.offset(skip).limit(limit).all()
            
            self.logger.debug(
                "Retrieved entities",
                entity_type=self.model.__name__,
                count=len(entities),
                skip=skip,
                limit=limit
            )
            
            return entities
            
        except SQLAlchemyError as e:
            self.logger.error(
                "Failed to get entities",
                entity_type=self.model.__name__,
                error=str(e)
            )
            raise
    
    def update(self, entity_id: int, update_data: Dict[str, Any]) -> Optional[T]:
        """
        Update entity by ID.
        
        Args:
            entity_id: Entity ID
            update_data: Dictionary of fields to update
            
        Returns:
            Updated entity instance or None if not found
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            entity = self.get_by_id(entity_id)
            if not entity:
                self.logger.warning(
                    "Entity not found for update",
                    entity_type=self.model.__name__,
                    entity_id=entity_id
                )
                return None
            
            # Update fields
            for field, value in update_data.items():
                if hasattr(entity, field):
                    setattr(entity, field, value)
            
            self.db.commit()
            self.db.refresh(entity)
            
            self.logger.info(
                "Entity updated successfully",
                entity_type=self.model.__name__,
                entity_id=entity_id,
                updated_fields=list(update_data.keys())
            )
            
            return entity
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(
                "Failed to update entity",
                entity_type=self.model.__name__,
                entity_id=entity_id,
                error=str(e)
            )
            raise
    
    def delete(self, entity_id: int) -> bool:
        """
        Delete entity by ID.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            entity = self.get_by_id(entity_id)
            if not entity:
                self.logger.warning(
                    "Entity not found for deletion",
                    entity_type=self.model.__name__,
                    entity_id=entity_id
                )
                return False
            
            self.db.delete(entity)
            self.db.commit()
            
            self.logger.info(
                "Entity deleted successfully",
                entity_type=self.model.__name__,
                entity_id=entity_id
            )
            
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(
                "Failed to delete entity",
                entity_type=self.model.__name__,
                entity_id=entity_id,
                error=str(e)
            )
            raise
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities with optional filters.
        
        Args:
            filters: Optional dictionary of filter conditions
            
        Returns:
            Number of entities matching filters
        """
        try:
            query = self.db.query(func.count(self.model.id))
            
            if filters:
                query = self._apply_filters(query, filters)
            
            count = query.scalar()
            
            self.logger.debug(
                "Counted entities",
                entity_type=self.model.__name__,
                count=count,
                filters=filters
            )
            
            return count
            
        except SQLAlchemyError as e:
            self.logger.error(
                "Failed to count entities",
                entity_type=self.model.__name__,
                error=str(e)
            )
            raise
    
    def exists(self, entity_id: int) -> bool:
        """
        Check if entity exists by ID.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            True if entity exists, False otherwise
        """
        try:
            exists = self.db.query(
                self.db.query(self.model).filter(self.model.id == entity_id).exists()
            ).scalar()
            
            self.logger.debug(
                "Checked entity existence",
                entity_type=self.model.__name__,
                entity_id=entity_id,
                exists=exists
            )
            
            return exists
            
        except SQLAlchemyError as e:
            self.logger.error(
                "Failed to check entity existence",
                entity_type=self.model.__name__,
                entity_id=entity_id,
                error=str(e)
            )
            raise
    
    def find_by_field(self, field_name: str, field_value: Any) -> List[T]:
        """
        Find entities by field value.
        
        Args:
            field_name: Name of the field to search
            field_value: Value to search for
            
        Returns:
            List of matching entities
        """
        try:
            if not hasattr(self.model, field_name):
                raise ValueError(f"Field '{field_name}' does not exist on {self.model.__name__}")
            
            field = getattr(self.model, field_name)
            entities = self.db.query(self.model).filter(field == field_value).all()
            
            self.logger.debug(
                "Found entities by field",
                entity_type=self.model.__name__,
                field_name=field_name,
                field_value=field_value,
                count=len(entities)
            )
            
            return entities
            
        except SQLAlchemyError as e:
            self.logger.error(
                "Failed to find entities by field",
                entity_type=self.model.__name__,
                field_name=field_name,
                error=str(e)
            )
            raise
    
    def find_by_filters(
        self,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[T]:
        """
        Find entities by multiple filters.
        
        Args:
            filters: Dictionary of filter conditions
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field name to order by
            order_desc: Whether to order in descending order
            
        Returns:
            List of matching entities
        """
        try:
            query = self.db.query(self.model)
            query = self._apply_filters(query, filters)
            
            # Apply ordering
            if order_by and hasattr(self.model, order_by):
                order_field = getattr(self.model, order_by)
                if order_desc:
                    query = query.order_by(desc(order_field))
                else:
                    query = query.order_by(asc(order_field))
            
            # Apply pagination
            entities = query.offset(skip).limit(limit).all()
            
            self.logger.debug(
                "Found entities by filters",
                entity_type=self.model.__name__,
                filters=filters,
                count=len(entities)
            )
            
            return entities
            
        except SQLAlchemyError as e:
            self.logger.error(
                "Failed to find entities by filters",
                entity_type=self.model.__name__,
                filters=filters,
                error=str(e)
            )
            raise
    
    def _apply_filters(self, query, filters: Dict[str, Any]):
        """
        Apply filters to a query.
        
        Args:
            query: SQLAlchemy query object
            filters: Dictionary of filter conditions
            
        Returns:
            Query with filters applied
        """
        for field_name, field_value in filters.items():
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                
                # Handle different filter types
                if isinstance(field_value, dict):
                    # Range filters: {"min": 10, "max": 20}
                    if "min" in field_value:
                        query = query.filter(field >= field_value["min"])
                    if "max" in field_value:
                        query = query.filter(field <= field_value["max"])
                    
                    # IN filters: {"in": [1, 2, 3]}
                    if "in" in field_value:
                        query = query.filter(field.in_(field_value["in"]))
                    
                    # LIKE filters: {"like": "pattern%"}
                    if "like" in field_value:
                        query = query.filter(field.like(field_value["like"]))
                
                elif isinstance(field_value, list):
                    # IN filter with list
                    query = query.filter(field.in_(field_value))
                
                else:
                    # Exact match
                    query = query.filter(field == field_value)
        
        return query
    
    def bulk_create(self, objects_data: List[Dict[str, Any]]) -> List[T]:
        """
        Create multiple entities in bulk.
        
        Args:
            objects_data: List of entity data dictionaries
            
        Returns:
            List of created entity instances
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            db_objects = [self.model(**obj_data) for obj_data in objects_data]
            self.db.add_all(db_objects)
            self.db.commit()
            
            # Refresh all objects to get IDs
            for db_obj in db_objects:
                self.db.refresh(db_obj)
            
            self.logger.info(
                "Bulk created entities",
                entity_type=self.model.__name__,
                count=len(db_objects)
            )
            
            return db_objects
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(
                "Failed to bulk create entities",
                entity_type=self.model.__name__,
                count=len(objects_data),
                error=str(e)
            )
            raise
    
    def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """
        Update multiple entities in bulk.
        
        Args:
            updates: List of update dictionaries with 'id' and update fields
            
        Returns:
            Number of entities updated
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            updated_count = 0
            
            for update_data in updates:
                if 'id' not in update_data:
                    continue
                
                entity_id = update_data.pop('id')
                result = self.db.query(self.model).filter(
                    self.model.id == entity_id
                ).update(update_data)
                
                updated_count += result
            
            self.db.commit()
            
            self.logger.info(
                "Bulk updated entities",
                entity_type=self.model.__name__,
                updated_count=updated_count
            )
            
            return updated_count
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(
                "Failed to bulk update entities",
                entity_type=self.model.__name__,
                error=str(e)
            )
            raise
    
    def bulk_delete(self, entity_ids: List[int]) -> int:
        """
        Delete multiple entities in bulk.
        
        Args:
            entity_ids: List of entity IDs to delete
            
        Returns:
            Number of entities deleted
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            deleted_count = self.db.query(self.model).filter(
                self.model.id.in_(entity_ids)
            ).delete(synchronize_session=False)
            
            self.db.commit()
            
            self.logger.info(
                "Bulk deleted entities",
                entity_type=self.model.__name__,
                deleted_count=deleted_count
            )
            
            return deleted_count
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(
                "Failed to bulk delete entities",
                entity_type=self.model.__name__,
                entity_ids=entity_ids,
                error=str(e)
            )
            raise