"""
Core data models for the drill-and-blast system.
Implements requirements 1.7, 9.4, 9.5 for data persistence and validation.
"""

# Import the base and database components first
from ..core.database import Base, BaseModel

# Import all models to ensure they're registered with SQLAlchemy
from .site import Site
from .blast_record import BlastRecord, BlastStatus
from .measurement_data import MeasurementData, MeasurementType, MeasurementQuality
from .configuration import Configuration, ConfigurationType, ConfigurationScope
from ..auth.models import User, UserRole, Session, AuditLog

__all__ = [
    "Base",
    "BaseModel",
    "Site",
    "BlastRecord", 
    "BlastStatus",
    "MeasurementData",
    "MeasurementType", 
    "MeasurementQuality",
    "Configuration",
    "ConfigurationType",
    "ConfigurationScope",
    "User",
    "UserRole",
    "Session",
    "AuditLog"
]