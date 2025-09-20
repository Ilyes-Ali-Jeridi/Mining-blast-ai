"""
Configuration management system with environment variables and config files.
Implements requirement 10.4: Configuration management system.
"""

import os
from pathlib import Path
from typing import Optional, List
from functools import lru_cache

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(default="sqlite:///./drill_blast_system.db", description="Database URL")
    echo: bool = Field(default=False, description="Enable SQL query logging")
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Max connection overflow")
    
    # Supabase specific settings
    supabase_url: Optional[str] = Field(default=None, description="Supabase project URL")
    supabase_key: Optional[str] = Field(default=None, description="Supabase anon/service key")
    supabase_service_key: Optional[str] = Field(default=None, description="Supabase service role key")
    
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class APISettings(BaseSettings):
    """API server configuration settings."""
    
    host: str = Field(default="127.0.0.1", description="API host")
    port: int = Field(default=8000, description="API port")
    reload: bool = Field(default=False, description="Enable auto-reload in development")
    workers: int = Field(default=1, description="Number of worker processes")
    log_level: str = Field(default="info", description="Log level")
    
    # CORS settings
    cors_origins: List[str] = Field(default=["http://localhost:3000"], description="Allowed CORS origins")
    cors_credentials: bool = Field(default=True, description="Allow credentials in CORS")
    cors_methods: List[str] = Field(default=["*"], description="Allowed CORS methods")
    cors_headers: List[str] = Field(default=["*"], description="Allowed CORS headers")
    
    model_config = SettingsConfigDict(env_prefix="API_")


class SecuritySettings(BaseSettings):
    """Security and authentication settings."""
    
    # JWT settings
    secret_key: str = Field(default="dev-secret-key-change-in-production", description="Secret key for JWT")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_hours: int = Field(default=8, description="Access token expiration in hours")
    
    # Session settings
    session_expire_hours: int = Field(default=24, description="Session expiration in hours")
    remember_me_expire_days: int = Field(default=30, description="Remember me session expiration in days")
    
    # Password policy
    min_password_length: int = Field(default=8, description="Minimum password length")
    require_password_complexity: bool = Field(default=True, description="Require complex passwords")
    max_failed_login_attempts: int = Field(default=5, description="Max failed login attempts before lockout")
    lockout_duration_minutes: int = Field(default=30, description="Account lockout duration in minutes")
    
    # Rate limiting
    login_rate_limit_attempts: int = Field(default=5, description="Login rate limit attempts")
    login_rate_limit_window_minutes: int = Field(default=15, description="Login rate limit window in minutes")
    
    # Safety validation settings
    require_engineer_signoff: bool = Field(default=True, description="Require engineer sign-off for exports")
    audit_trail_enabled: bool = Field(default=True, description="Enable audit trail logging")
    
    model_config = SettingsConfigDict(env_prefix="SECURITY_")


class PhysicsSettings(BaseSettings):
    """Physics model configuration settings."""
    
    # Kuz-Ram default parameters
    default_rock_factor_a: float = Field(default=7.0, description="Default Kuz-Ram rock factor A")
    
    # PPV model default parameters
    default_ppv_k: float = Field(default=1.4, description="Default PPV constant k")
    default_ppv_a: float = Field(default=1/3, description="Default PPV exponent a")
    default_ppv_b: float = Field(default=1.6, description="Default PPV exponent b")
    
    # Safety defaults
    default_max_charge_per_hole: float = Field(default=50.0, description="Default max charge per hole (kg)")
    default_max_charge_per_delay: float = Field(default=200.0, description="Default max charge per delay (kg)")
    default_ppv_limit: float = Field(default=5.0, description="Default PPV limit (mm/s)")
    
    model_config = SettingsConfigDict(env_prefix="PHYSICS_")


class OptimizationSettings(BaseSettings):
    """Optimization engine configuration settings."""
    
    # Solver timeouts
    cp_sat_timeout_seconds: int = Field(default=300, description="CP-SAT solver timeout")
    scipy_timeout_seconds: int = Field(default=600, description="SciPy optimizer timeout")
    genetic_timeout_seconds: int = Field(default=900, description="Genetic algorithm timeout")
    
    # Algorithm preferences
    default_algorithms: List[str] = Field(default=["cp_sat", "scipy"], description="Default optimization algorithms")
    max_concurrent_optimizations: int = Field(default=3, description="Max concurrent optimization jobs")
    
    model_config = SettingsConfigDict(env_prefix="OPT_")


class FileStorageSettings(BaseSettings):
    """File storage configuration settings."""
    
    # Local storage (fallback)
    upload_dir: Path = Field(default=Path("./uploads"), description="Local upload directory")
    report_dir: Path = Field(default=Path("./reports"), description="Local report output directory")
    temp_dir: Path = Field(default=Path("./temp"), description="Local temporary files directory")
    measurement_data_path: Path = Field(default=Path("./uploads/measurements"), description="Measurement data storage path")
    max_upload_size: int = Field(default=100 * 1024 * 1024, description="Max upload size in bytes (100MB)")
    
    # Supabase storage settings
    use_supabase_storage: bool = Field(default=True, description="Use Supabase storage for files")
    supabase_bucket_name: str = Field(default="drill-blast-files", description="Supabase storage bucket name")
    
    model_config = SettingsConfigDict(env_prefix="STORAGE_")
    
    @validator("upload_dir", "report_dir", "temp_dir", "measurement_data_path")
    def create_directories(cls, v):
        """Ensure directories exist."""
        if not v.exists():
            v.mkdir(parents=True, exist_ok=True)
        return v


class MLPipelineSettings(BaseSettings):
    """Machine Learning pipeline configuration settings."""
    
    # SAM (Segment Anything Model) settings
    sam_model_path: Optional[str] = Field(default=None, description="Path to SAM model checkpoint")
    sam_device: str = Field(default="cpu", description="Device for SAM inference (cpu/cuda)")
    sam_model_type: str = Field(default="vit_b", description="SAM model type (vit_b/vit_l/vit_h)")
    
    # Image processing settings
    enable_preprocessing: bool = Field(default=True, description="Enable automatic image preprocessing")
    max_image_size: int = Field(default=2048, description="Maximum image dimension for processing")
    min_fragment_area_pixels: int = Field(default=100, description="Minimum fragment area in pixels")
    max_fragment_area_pixels: int = Field(default=50000, description="Maximum fragment area in pixels")
    
    # Scale detection settings
    known_marker_sizes_mm: List[float] = Field(
        default=[25.0, 50.0, 100.0, 200.0, 300.0], 
        description="Known scale marker sizes in mm"
    )
    scale_detection_method: str = Field(default="template_matching", description="Scale detection method")
    
    # Quality assessment settings
    min_acceptable_quality: float = Field(default=0.6, description="Minimum acceptable measurement quality")
    min_reliable_quality: float = Field(default=0.8, description="Minimum quality for reliable measurements")
    min_fragments_for_training: int = Field(default=50, description="Minimum fragments needed for ML training")
    
    # Residual learning settings
    enable_residual_learning: bool = Field(default=True, description="Enable XGBoost residual model learning")
    min_training_samples: int = Field(default=50, description="Minimum samples needed to train residual model")
    residual_model_retrain_threshold: int = Field(default=100, description="New samples threshold for retraining")
    
    # Processing limits
    max_concurrent_analyses: int = Field(default=3, description="Maximum concurrent fragmentation analyses")
    analysis_timeout_seconds: int = Field(default=300, description="Timeout for fragmentation analysis")
    
    model_config = SettingsConfigDict(env_prefix="ML_")


class Settings(BaseSettings):
    """Main application settings."""
    
    # Application info
    app_name: str = Field(default="Automated Drill-and-Blast System", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Environment (development/production)")
    debug: bool = Field(default=True, description="Enable debug mode")
    
    # Component settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    api: APISettings = Field(default_factory=APISettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    physics: PhysicsSettings = Field(default_factory=PhysicsSettings)
    optimization: OptimizationSettings = Field(default_factory=OptimizationSettings)
    storage: FileStorageSettings = Field(default_factory=FileStorageSettings)
    ml_pipeline: MLPipelineSettings = Field(default_factory=MLPipelineSettings)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment setting."""
        if v not in ["development", "staging", "production"]:
            raise ValueError("Environment must be one of: development, staging, production")
        return v
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    Returns:
        Settings: Application configuration settings
    """
    return Settings()


def load_config_from_file(config_path: Optional[Path] = None) -> dict:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        dict: Configuration dictionary
    """
    import yaml
    
    if config_path is None:
        config_path = Path("config.yaml")
    
    if not config_path.exists():
        return {}
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def create_default_config_file(config_path: Path = Path("config.yaml")) -> None:
    """
    Create a default configuration file.
    
    Args:
        config_path: Path where to create the config file
    """
    import yaml
    
    default_config = {
        "app_name": "Automated Drill-and-Blast System",
        "environment": "development",
        "debug": True,
        "database": {
            "url": "postgresql://user:pass@localhost:5432/drill_blast_system",
            "echo": False,
            "supabase_url": "https://your-project.supabase.co",
            "supabase_key": "your-anon-key"
        },
        "api": {
            "host": "127.0.0.1",
            "port": 8000,
            "cors_origins": ["http://localhost:3000"]
        },
        "security": {
            "require_engineer_signoff": True,
            "audit_trail_enabled": True
        },
        "physics": {
            "default_rock_factor_a": 7.0,
            "default_ppv_k": 1.4,
            "default_max_charge_per_hole": 50.0
        }
    }
    
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(default_config, f, default_flow_style=False, indent=2)