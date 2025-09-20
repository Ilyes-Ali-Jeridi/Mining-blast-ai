"""
Common Pydantic schemas used across the application.
"""

from typing import Any, Dict, List, Optional, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field, validator

T = TypeVar('T')


class ResponseModel(BaseModel, Generic[T]):
    """Generic response model for API endpoints."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable message about the operation")
    data: Optional[T] = Field(None, description="Response data payload")
    errors: Optional[List[str]] = Field(None, description="List of error messages if any")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {"result": "example"},
                "errors": None
            }
        }


class Coordinates(BaseModel):
    """3D coordinates with validation."""
    x: float = Field(..., description="X coordinate in meters")
    y: float = Field(..., description="Y coordinate in meters") 
    z: float = Field(..., description="Z coordinate in meters")
    
    class Config:
        schema_extra = {
            "example": {
                "x": 1000.0,
                "y": 2000.0,
                "z": 150.0
            }
        }


class Coordinates2D(BaseModel):
    """2D coordinates for polygons and areas."""
    x: float = Field(..., description="X coordinate in meters")
    y: float = Field(..., description="Y coordinate in meters")
    
    class Config:
        schema_extra = {
            "example": {
                "x": 1000.0,
                "y": 2000.0
            }
        }


class GeographicCoordinates(BaseModel):
    """Geographic coordinates (latitude/longitude)."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    
    class Config:
        schema_extra = {
            "example": {
                "latitude": -33.8688,
                "longitude": 151.2093
            }
        }


class ValidationError(BaseModel):
    """Validation error details."""
    field: str = Field(..., description="Field name that failed validation")
    message: str = Field(..., description="Validation error message")
    value: Optional[Any] = Field(None, description="Invalid value that caused the error")
    
    class Config:
        schema_extra = {
            "example": {
                "field": "bench_height",
                "message": "Bench height must be positive",
                "value": -5.0
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    items: List[T] = Field(..., description="List of items for current page")
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    size: int = Field(..., ge=1, le=1000, description="Number of items per page")
    pages: int = Field(..., ge=1, description="Total number of pages")
    
    class Config:
        schema_extra = {
            "example": {
                "items": [],
                "total": 150,
                "page": 1,
                "size": 20,
                "pages": 8
            }
        }


class DateRange(BaseModel):
    """Date range for filtering."""
    start_date: Optional[datetime] = Field(None, description="Start date (inclusive)")
    end_date: Optional[datetime] = Field(None, description="End date (inclusive)")
    
    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if v and 'start_date' in values and values['start_date']:
            if v < values['start_date']:
                raise ValueError('End date must be after start date')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z"
            }
        }


class NumericRange(BaseModel):
    """Numeric range with validation."""
    min_value: float = Field(..., description="Minimum value (inclusive)")
    max_value: float = Field(..., description="Maximum value (inclusive)")
    
    @validator('max_value')
    def max_greater_than_min(cls, v, values):
        if 'min_value' in values and v <= values['min_value']:
            raise ValueError('Maximum value must be greater than minimum value')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "min_value": 2.0,
                "max_value": 8.0
            }
        }


class FileReference(BaseModel):
    """File reference with metadata."""
    file_path: str = Field(..., description="Path to file in storage system")
    file_name: str = Field(..., description="Original file name")
    file_type: str = Field(..., description="File type/extension")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    content_type: Optional[str] = Field(None, description="MIME content type")
    upload_date: datetime = Field(..., description="File upload timestamp")
    description: Optional[str] = Field(None, description="File description")
    
    class Config:
        schema_extra = {
            "example": {
                "file_path": "sites/123/images/muckpile_001.jpg",
                "file_name": "muckpile_001.jpg",
                "file_type": "jpg",
                "file_size": 2048576,
                "content_type": "image/jpeg",
                "upload_date": "2024-01-15T10:30:00Z",
                "description": "Muckpile fragmentation analysis image"
            }
        }


class AuditInfo(BaseModel):
    """Audit information for tracking changes."""
    created_by: Optional[str] = Field(None, description="User who created the record")
    created_at: datetime = Field(..., description="Creation timestamp")
    modified_by: Optional[str] = Field(None, description="User who last modified the record")
    modified_at: datetime = Field(..., description="Last modification timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "created_by": "john.doe@company.com",
                "created_at": "2024-01-15T10:30:00Z",
                "modified_by": "jane.smith@company.com",
                "modified_at": "2024-01-16T14:45:00Z"
            }
        }


class ProgressUpdate(BaseModel):
    """Progress update for long-running operations."""
    operation_id: str = Field(..., description="Unique operation identifier")
    status: str = Field(..., description="Current operation status")
    progress_percent: float = Field(..., ge=0, le=100, description="Progress percentage")
    current_step: str = Field(..., description="Description of current step")
    estimated_remaining_seconds: Optional[int] = Field(None, ge=0, description="Estimated time remaining")
    message: Optional[str] = Field(None, description="Additional status message")
    
    class Config:
        schema_extra = {
            "example": {
                "operation_id": "opt_12345",
                "status": "running",
                "progress_percent": 65.5,
                "current_step": "Evaluating solution candidates",
                "estimated_remaining_seconds": 120,
                "message": "Found 15 feasible solutions so far"
            }
        }


class HealthCheck(BaseModel):
    """System health check response."""
    status: str = Field(..., description="Overall system status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Application version")
    database_status: str = Field(..., description="Database connection status")
    storage_status: str = Field(..., description="File storage status")
    services: Dict[str, str] = Field(..., description="Individual service statuses")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00Z",
                "version": "1.0.0",
                "database_status": "connected",
                "storage_status": "available",
                "services": {
                    "physics_engine": "ready",
                    "optimization_engine": "ready",
                    "safety_validator": "ready"
                }
            }
        }