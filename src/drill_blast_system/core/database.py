"""
Database configuration and base model classes.
Implements requirement 10.2: SQLAlchemy with Supabase PostgreSQL database and base model classes.
"""

from typing import Any, Dict, Optional, List
from datetime import datetime

from sqlalchemy import create_engine, MetaData, Column, Integer, DateTime, String, JSON, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import supabase

from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)

# SQLAlchemy base class
Base = declarative_base()

# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

Base.metadata = MetaData(naming_convention=convention)


class BaseModel(Base):
    """
    Base model class with common fields and methods.
    """
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update model instance from dictionary."""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"


class AuditLogEntry(BaseModel):
    """
    Immutable audit log entries for compliance and debugging.
    """
    __tablename__ = "audit_log"
    
    event_type = Column(String(100), nullable=False, index=True)
    event_data = Column(JSON, nullable=False)
    user_id = Column(String(100), nullable=True, index=True)
    session_id = Column(String(100), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    
    def __init__(self, **kwargs):
        """Initialize audit log entry with immutable timestamp."""
        super().__init__(**kwargs)
        # Ensure created_at is set and cannot be changed
        if 'created_at' not in kwargs:
            self.created_at = datetime.utcnow()


class SystemConfiguration(BaseModel):
    """
    System configuration storage with versioning.
    """
    __tablename__ = "system_configuration"
    
    config_key = Column(String(100), nullable=False, unique=True, index=True)
    config_value = Column(JSON, nullable=False)
    config_type = Column(String(50), nullable=False)  # 'physics', 'safety', 'optimization', etc.
    description = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)  # Using Boolean for PostgreSQL


# Database engine and session management
class DatabaseManager:
    """
    Database connection and session management with Supabase support.
    """
    
    def __init__(self):
        """Initialize database manager."""
        self.settings = get_settings()
        self.engine = None
        self.SessionLocal = None
        self.supabase_client = None
        self._initialize_engine()
        self._initialize_supabase()
    
    def _initialize_engine(self) -> None:
        """Initialize SQLAlchemy engine for PostgreSQL."""
        # Build database URL from Supabase settings if available
        logger.info(f"Database settings - supabase_url: {self.settings.database.supabase_url}")
        logger.info(f"Database settings - supabase_service_key: {'***' if self.settings.database.supabase_service_key else None}")
        
        # Use the configured database URL (SQLite or PostgreSQL)
        db_url = self.settings.database.url
        
        if db_url.startswith('sqlite'):
            logger.info("Using SQLite database for development")
        elif self.settings.database.supabase_url and self.settings.database.supabase_service_key:
            # Extract database connection details from Supabase URL
            supabase_url = self.settings.database.supabase_url
            # Convert Supabase URL to PostgreSQL connection string
            # Format: postgresql://postgres:[service_key]@db.[project-ref].supabase.co:5432/postgres
            try:
                # Extract project reference from URL like https://cwkkrflahefikapwlcyj.supabase.co
                project_ref = supabase_url.replace("https://", "").replace("http://", "").split(".")[0]
                db_url = f"postgresql://postgres:{self.settings.database.supabase_service_key}@db.{project_ref}.supabase.co:5432/postgres"
                logger.info(f"Using Supabase database connection for project: {project_ref}")
            except Exception as e:
                logger.error(f"Failed to parse Supabase URL: {e}")
                logger.info("Falling back to configured database URL")
        else:
            logger.info("Using configured database connection")
        
        # Database configuration with appropriate settings for SQLite vs PostgreSQL
        if db_url.startswith('sqlite'):
            # SQLite configuration
            self.engine = create_engine(
                db_url,
                echo=self.settings.database.echo,
                connect_args={"check_same_thread": False}  # Allow SQLite to be used with FastAPI
            )
        else:
            # PostgreSQL configuration with connection pooling
            self.engine = create_engine(
                db_url,
                pool_size=self.settings.database.pool_size,
                max_overflow=self.settings.database.max_overflow,
                poolclass=QueuePool,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,   # Recycle connections every hour
                echo=self.settings.database.echo
            )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info(
            "Database engine initialized",
            database_type="PostgreSQL (Supabase)",
            echo=self.settings.database.echo
        )
    
    def _initialize_supabase(self) -> None:
        """Initialize Supabase client for additional features."""
        if self.settings.database.supabase_url and self.settings.database.supabase_key:
            try:
                self.supabase_client = supabase.create_client(
                    self.settings.database.supabase_url,
                    self.settings.database.supabase_key
                )
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.warning("Failed to initialize Supabase client", error=str(e))
                self.supabase_client = None
    
    def create_tables(self) -> None:
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error("Failed to create database tables", error=str(e))
            raise
    
    def get_session(self) -> Session:
        """
        Get a database session.
        
        Returns:
            Session: SQLAlchemy session
        """
        return self.SessionLocal()
    
    def close(self) -> None:
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Session:
    """
    Dependency function to get database session.
    Used with FastAPI dependency injection.
    
    Yields:
        Session: Database session
    """
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()


def init_database() -> None:
    """
    Initialize database with tables and default configuration.
    """
    logger.info("Initializing database...")
    
    # Create tables
    db_manager.create_tables()
    
    # Insert default configuration if not exists
    db = db_manager.get_session()
    try:
        # Check if default physics configuration exists
        physics_config = db.query(SystemConfiguration).filter(
            SystemConfiguration.config_key == "default_physics_parameters"
        ).first()
        
        if not physics_config:
            # Insert default physics parameters
            default_physics = SystemConfiguration(
                config_key="default_physics_parameters",
                config_value={
                    "kuz_ram": {
                        "rock_factor_a": 7.0,
                        "uniformity_index": 1.25
                    },
                    "ppv": {
                        "k": 1.4,
                        "a": 0.333,
                        "b": 1.6
                    }
                },
                config_type="physics",
                description="Default physics model parameters",
                version=1,
                is_active=True
            )
            db.add(default_physics)
        
        # Check if default safety configuration exists
        safety_config = db.query(SystemConfiguration).filter(
            SystemConfiguration.config_key == "default_safety_limits"
        ).first()
        
        if not safety_config:
            # Insert default safety limits
            default_safety = SystemConfiguration(
                config_key="default_safety_limits",
                config_value={
                    "max_charge_per_hole": 50.0,
                    "max_charge_per_delay": 200.0,
                    "powder_factor_min": 0.05,
                    "powder_factor_max": 1.5,
                    "ppv_default_limit": 5.0
                },
                config_type="safety",
                description="Default safety constraint limits",
                version=1,
                is_active=True
            )
            db.add(default_safety)
        
        db.commit()
        logger.info("Default configuration inserted successfully")
        
    except Exception as e:
        db.rollback()
        logger.error("Failed to insert default configuration", error=str(e))
        raise
    finally:
        db.close()


def create_audit_log_entry(
    db: Session,
    event_type: str,
    event_data: Dict[str, Any],
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> AuditLogEntry:
    """
    Create an audit log entry.
    
    Args:
        db: Database session
        event_type: Type of event being logged
        event_data: Event data dictionary
        user_id: Optional user identifier
        session_id: Optional session identifier
        ip_address: Optional IP address
        user_agent: Optional user agent string
        
    Returns:
        AuditLogEntry: Created audit log entry
    """
    audit_entry = AuditLogEntry(
        event_type=event_type,
        event_data=event_data,
        user_id=user_id,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    
    return audit_entry


class SupabaseStorageManager:
    """
    Supabase storage management for file uploads and downloads.
    """
    
    def __init__(self):
        """Initialize Supabase storage manager."""
        self.settings = get_settings()
        self.supabase_client = db_manager.supabase_client
        self.bucket_name = self.settings.storage.supabase_bucket_name
        self.logger = get_logger(__name__)
    
    def upload_file(self, file_path: str, file_data: bytes, content_type: str = None) -> Optional[str]:
        """
        Upload file to Supabase storage.
        
        Args:
            file_path: Path within the bucket
            file_data: File content as bytes
            content_type: MIME type of the file
            
        Returns:
            str: Public URL of uploaded file, None if failed
        """
        if not self.supabase_client:
            self.logger.warning("Supabase client not available, falling back to local storage")
            return None
        
        try:
            # Upload file to Supabase storage
            response = self.supabase_client.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file_data,
                file_options={"content-type": content_type} if content_type else None
            )
            
            if response.get("error"):
                self.logger.error("Failed to upload file to Supabase", error=response["error"])
                return None
            
            # Get public URL
            public_url = self.supabase_client.storage.from_(self.bucket_name).get_public_url(file_path)
            
            self.logger.info("File uploaded to Supabase storage", file_path=file_path, url=public_url)
            return public_url
            
        except Exception as e:
            self.logger.error("Exception during file upload to Supabase", error=str(e))
            return None
    
    def download_file(self, file_path: str) -> Optional[bytes]:
        """
        Download file from Supabase storage.
        
        Args:
            file_path: Path within the bucket
            
        Returns:
            bytes: File content, None if failed
        """
        if not self.supabase_client:
            self.logger.warning("Supabase client not available")
            return None
        
        try:
            response = self.supabase_client.storage.from_(self.bucket_name).download(file_path)
            
            if isinstance(response, bytes):
                return response
            else:
                self.logger.error("Failed to download file from Supabase", file_path=file_path)
                return None
                
        except Exception as e:
            self.logger.error("Exception during file download from Supabase", error=str(e))
            return None
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete file from Supabase storage.
        
        Args:
            file_path: Path within the bucket
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.supabase_client:
            self.logger.warning("Supabase client not available")
            return False
        
        try:
            response = self.supabase_client.storage.from_(self.bucket_name).remove([file_path])
            
            if response.get("error"):
                self.logger.error("Failed to delete file from Supabase", error=response["error"])
                return False
            
            self.logger.info("File deleted from Supabase storage", file_path=file_path)
            return True
            
        except Exception as e:
            self.logger.error("Exception during file deletion from Supabase", error=str(e))
            return False
    
    def list_files(self, folder_path: str = "") -> List[Dict[str, Any]]:
        """
        List files in Supabase storage bucket.
        
        Args:
            folder_path: Optional folder path to list
            
        Returns:
            List[Dict]: List of file information
        """
        if not self.supabase_client:
            self.logger.warning("Supabase client not available")
            return []
        
        try:
            response = self.supabase_client.storage.from_(self.bucket_name).list(folder_path)
            
            if isinstance(response, list):
                return response
            else:
                self.logger.error("Failed to list files from Supabase", folder_path=folder_path)
                return []
                
        except Exception as e:
            self.logger.error("Exception during file listing from Supabase", error=str(e))
            return []


# Global storage manager instance
storage_manager = SupabaseStorageManager()