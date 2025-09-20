"""
Configuration repository for configuration-specific database operations.
Implements requirements 9.4, 9.5 for configuration management with versioning.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc

from .base import BaseRepository
from ..models.configuration import Configuration, ConfigurationType, ConfigurationScope
from ..core.logging import get_logger

logger = get_logger(__name__)


class ConfigurationRepository(BaseRepository[Configuration]):
    """
    Repository for Configuration entity with specialized query methods.
    
    Provides configuration-specific database operations including:
    - Configuration management by type and scope
    - Version control and history tracking
    - Default configuration handling
    - Validation and approval workflows
    """
    
    def __init__(self, db: Session):
        """Initialize configuration repository."""
        super().__init__(db, Configuration)
    
    def get_by_key(
        self,
        config_key: str,
        config_scope: ConfigurationScope = ConfigurationScope.GLOBAL,
        site_id: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> Optional[Configuration]:
        """
        Get configuration by key and scope.
        
        Args:
            config_key: Configuration key
            config_scope: Configuration scope
            site_id: Site ID for site-scoped configs
            user_id: User ID for user-scoped configs
            
        Returns:
            Configuration instance or None if not found
        """
        try:
            query = self.db.query(Configuration).filter(
                and_(
                    Configuration.config_key == config_key,
                    Configuration.config_scope == config_scope,
                    Configuration.is_active == True
                )
            )
            
            if config_scope == ConfigurationScope.SITE:
                query = query.filter(Configuration.site_id == site_id)
            elif config_scope == ConfigurationScope.USER:
                query = query.filter(Configuration.user_id == user_id)
            
            # Get the latest version
            config = query.order_by(desc(Configuration.version)).first()
            
            logger.debug(
                "Retrieved configuration by key",
                config_key=config_key,
                config_scope=config_scope,
                site_id=site_id,
                user_id=user_id,
                found=config is not None
            )
            
            return config
            
        except Exception as e:
            logger.error(
                "Failed to get configuration by key",
                config_key=config_key,
                config_scope=config_scope,
                error=str(e)
            )
            raise
    
    def get_by_type(
        self,
        config_type: ConfigurationType,
        config_scope: ConfigurationScope = ConfigurationScope.GLOBAL,
        site_id: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> List[Configuration]:
        """
        Get configurations by type and scope.
        
        Args:
            config_type: Configuration type
            config_scope: Configuration scope
            site_id: Site ID for site-scoped configs
            user_id: User ID for user-scoped configs
            
        Returns:
            List of configurations of specified type
        """
        try:
            query = self.db.query(Configuration).filter(
                and_(
                    Configuration.config_type == config_type,
                    Configuration.config_scope == config_scope,
                    Configuration.is_active == True
                )
            )
            
            if config_scope == ConfigurationScope.SITE:
                query = query.filter(Configuration.site_id == site_id)
            elif config_scope == ConfigurationScope.USER:
                query = query.filter(Configuration.user_id == user_id)
            
            configs = query.order_by(Configuration.config_name).all()
            
            logger.debug(
                "Retrieved configurations by type",
                config_type=config_type,
                config_scope=config_scope,
                site_id=site_id,
                user_id=user_id,
                count=len(configs)
            )
            
            return configs
            
        except Exception as e:
            logger.error(
                "Failed to get configurations by type",
                config_type=config_type,
                config_scope=config_scope,
                error=str(e)
            )
            raise
    
    def get_default_configurations(self, config_type: Optional[ConfigurationType] = None) -> List[Configuration]:
        """
        Get default configurations.
        
        Args:
            config_type: Optional configuration type filter
            
        Returns:
            List of default configurations
        """
        filters = {
            "is_default": True,
            "is_active": True,
            "config_scope": ConfigurationScope.GLOBAL
        }
        
        if config_type:
            filters["config_type"] = config_type
        
        return self.find_by_filters(
            filters=filters,
            order_by="config_type"
        )
    
    def get_site_configurations(self, site_id: int) -> List[Configuration]:
        """
        Get all configurations for a specific site.
        
        Args:
            site_id: Site ID
            
        Returns:
            List of site-specific configurations
        """
        return self.find_by_filters(
            filters={
                "config_scope": ConfigurationScope.SITE,
                "site_id": site_id,
                "is_active": True
            },
            order_by="config_type"
        )
    
    def get_user_configurations(self, user_id: str) -> List[Configuration]:
        """
        Get all configurations for a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of user-specific configurations
        """
        return self.find_by_filters(
            filters={
                "config_scope": ConfigurationScope.USER,
                "user_id": user_id,
                "is_active": True
            },
            order_by="config_type"
        )
    
    def get_configuration_history(self, config_key: str, config_scope: ConfigurationScope) -> List[Configuration]:
        """
        Get configuration version history.
        
        Args:
            config_key: Configuration key
            config_scope: Configuration scope
            
        Returns:
            List of configuration versions ordered by version number
        """
        return self.find_by_filters(
            filters={
                "config_key": config_key,
                "config_scope": config_scope
            },
            order_by="version",
            order_desc=True
        )
    
    def get_unvalidated_configurations(self) -> List[Configuration]:
        """
        Get configurations that haven't been validated.
        
        Returns:
            List of unvalidated configurations
        """
        return self.find_by_filters(
            filters={
                "is_validated": False,
                "is_active": True
            },
            order_by="created_at"
        )
    
    def get_configurations_by_tag(self, tag: str) -> List[Configuration]:
        """
        Get configurations by tag.
        
        Args:
            tag: Configuration tag
            
        Returns:
            List of configurations with the specified tag
        """
        try:
            configs = self.db.query(Configuration).filter(
                and_(
                    Configuration.is_active == True,
                    Configuration.tags.op('@>')([tag])
                )
            ).order_by(Configuration.config_name).all()
            
            logger.debug(
                "Retrieved configurations by tag",
                tag=tag,
                count=len(configs)
            )
            
            return configs
            
        except Exception as e:
            logger.error(
                "Failed to get configurations by tag",
                tag=tag,
                error=str(e)
            )
            raise
    
    def get_effective_configuration(
        self,
        config_key: str,
        site_id: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> Optional[Configuration]:
        """
        Get effective configuration with scope precedence.
        
        Precedence order: User > Site > Global
        
        Args:
            config_key: Configuration key
            site_id: Optional site ID
            user_id: Optional user ID
            
        Returns:
            Most specific configuration or None if not found
        """
        try:
            # Try user-specific first
            if user_id:
                user_config = self.get_by_key(
                    config_key,
                    ConfigurationScope.USER,
                    user_id=user_id
                )
                if user_config:
                    logger.debug(
                        "Found user-specific configuration",
                        config_key=config_key,
                        user_id=user_id
                    )
                    return user_config
            
            # Try site-specific next
            if site_id:
                site_config = self.get_by_key(
                    config_key,
                    ConfigurationScope.SITE,
                    site_id=site_id
                )
                if site_config:
                    logger.debug(
                        "Found site-specific configuration",
                        config_key=config_key,
                        site_id=site_id
                    )
                    return site_config
            
            # Fall back to global
            global_config = self.get_by_key(
                config_key,
                ConfigurationScope.GLOBAL
            )
            
            if global_config:
                logger.debug(
                    "Found global configuration",
                    config_key=config_key
                )
            else:
                logger.warning(
                    "No configuration found",
                    config_key=config_key,
                    site_id=site_id,
                    user_id=user_id
                )
            
            return global_config
            
        except Exception as e:
            logger.error(
                "Failed to get effective configuration",
                config_key=config_key,
                site_id=site_id,
                user_id=user_id,
                error=str(e)
            )
            raise
    
    def create_configuration_revision(
        self,
        config_id: int,
        new_config_value: Dict[str, Any],
        modified_by: str,
        change_reason: str = ""
    ) -> Optional[Configuration]:
        """
        Create a new revision of an existing configuration.
        
        Args:
            config_id: Original configuration ID
            new_config_value: New configuration value
            modified_by: User creating the revision
            change_reason: Reason for the change
            
        Returns:
            New configuration revision or None if original not found
        """
        try:
            original_config = self.get_by_id(config_id)
            if not original_config:
                logger.warning(
                    "Original configuration not found for revision",
                    config_id=config_id
                )
                return None
            
            # Create revision using model method
            revision = original_config.create_revision(
                new_config_value,
                modified_by,
                change_reason
            )
            
            # Save to database
            self.db.add(revision)
            self.db.commit()
            self.db.refresh(revision)
            
            logger.info(
                "Configuration revision created",
                original_config_id=config_id,
                revision_id=revision.id,
                version=revision.version,
                modified_by=modified_by
            )
            
            return revision
            
        except Exception as e:
            self.db.rollback()
            logger.error(
                "Failed to create configuration revision",
                config_id=config_id,
                modified_by=modified_by,
                error=str(e)
            )
            raise
    
    def validate_configuration(
        self,
        config_id: int,
        validated_by: str,
        validation_notes: Optional[str] = None
    ) -> Optional[Configuration]:
        """
        Validate a configuration.
        
        Args:
            config_id: Configuration ID
            validated_by: Validator identifier
            validation_notes: Optional validation notes
            
        Returns:
            Updated configuration or None if not found
        """
        try:
            update_data = {
                "is_validated": True,
                "validated_by": validated_by,
                "validation_date": datetime.utcnow(),
                "validation_notes": validation_notes
            }
            
            updated_config = self.update(config_id, update_data)
            
            if updated_config:
                logger.info(
                    "Configuration validated",
                    config_id=config_id,
                    validated_by=validated_by
                )
            
            return updated_config
            
        except Exception as e:
            logger.error(
                "Failed to validate configuration",
                config_id=config_id,
                error=str(e)
            )
            raise
    
    def set_as_default(self, config_id: int) -> Optional[Configuration]:
        """
        Set configuration as default (and unset others of same type).
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Updated configuration or None if not found
        """
        try:
            config = self.get_by_id(config_id)
            if not config:
                return None
            
            # Unset other defaults of same type and scope
            self.db.query(Configuration).filter(
                and_(
                    Configuration.config_type == config.config_type,
                    Configuration.config_scope == config.config_scope,
                    Configuration.is_default == True,
                    Configuration.id != config_id
                )
            ).update({"is_default": False})
            
            # Set this one as default
            updated_config = self.update(config_id, {"is_default": True})
            
            if updated_config:
                logger.info(
                    "Configuration set as default",
                    config_id=config_id,
                    config_type=config.config_type,
                    config_scope=config.config_scope
                )
            
            return updated_config
            
        except Exception as e:
            self.db.rollback()
            logger.error(
                "Failed to set configuration as default",
                config_id=config_id,
                error=str(e)
            )
            raise
    
    def deactivate_configuration(self, config_id: int) -> bool:
        """
        Deactivate a configuration (soft delete).
        
        Args:
            config_id: Configuration ID
            
        Returns:
            True if deactivated, False if not found
        """
        try:
            updated = self.update(config_id, {"is_active": False})
            
            if updated:
                logger.info("Configuration deactivated", config_id=config_id)
                return True
            else:
                logger.warning("Configuration not found for deactivation", config_id=config_id)
                return False
                
        except Exception as e:
            logger.error(
                "Failed to deactivate configuration",
                config_id=config_id,
                error=str(e)
            )
            raise
    
    def get_physics_parameters(
        self,
        site_id: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get effective physics parameters.
        
        Args:
            site_id: Optional site ID
            user_id: Optional user ID
            
        Returns:
            Physics parameters dictionary or None
        """
        try:
            config = self.get_effective_configuration(
                "default_physics_parameters",
                site_id=site_id,
                user_id=user_id
            )
            
            if config:
                return config.config_value
            
            logger.warning(
                "No physics parameters found",
                site_id=site_id,
                user_id=user_id
            )
            return None
            
        except Exception as e:
            logger.error(
                "Failed to get physics parameters",
                site_id=site_id,
                user_id=user_id,
                error=str(e)
            )
            raise
    
    def get_safety_limits(
        self,
        site_id: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get effective safety limits.
        
        Args:
            site_id: Optional site ID
            user_id: Optional user ID
            
        Returns:
            Safety limits dictionary or None
        """
        try:
            config = self.get_effective_configuration(
                "default_safety_limits",
                site_id=site_id,
                user_id=user_id
            )
            
            if config:
                return config.config_value
            
            logger.warning(
                "No safety limits found",
                site_id=site_id,
                user_id=user_id
            )
            return None
            
        except Exception as e:
            logger.error(
                "Failed to get safety limits",
                site_id=site_id,
                user_id=user_id,
                error=str(e)
            )
            raise
    
    def get_configuration_statistics(self) -> Dict[str, Any]:
        """
        Get configuration statistics summary.
        
        Returns:
            Dictionary with configuration statistics
        """
        try:
            total_configs = self.count({"is_active": True})
            
            # Count by type
            type_counts = {}
            for config_type in ConfigurationType:
                count = self.count({
                    "config_type": config_type,
                    "is_active": True
                })
                type_counts[config_type.value] = count
            
            # Count by scope
            scope_counts = {}
            for scope in ConfigurationScope:
                count = self.count({
                    "config_scope": scope,
                    "is_active": True
                })
                scope_counts[scope.value] = count
            
            # Other statistics
            validated_count = self.count({
                "is_validated": True,
                "is_active": True
            })
            default_count = self.count({
                "is_default": True,
                "is_active": True
            })
            
            statistics = {
                "total_configurations": total_configs,
                "type_counts": type_counts,
                "scope_counts": scope_counts,
                "validated_count": validated_count,
                "unvalidated_count": total_configs - validated_count,
                "default_count": default_count
            }
            
            logger.debug("Generated configuration statistics", statistics=statistics)
            
            return statistics
            
        except Exception as e:
            logger.error("Failed to get configuration statistics", error=str(e))
            raise
    
    def cleanup_old_versions(self, keep_versions: int = 5) -> int:
        """
        Clean up old configuration versions, keeping only the latest N versions.
        
        Args:
            keep_versions: Number of versions to keep per configuration
            
        Returns:
            Number of configurations cleaned up
        """
        try:
            cleanup_count = 0
            
            # Get all unique configuration keys and scopes
            unique_configs = self.db.query(
                Configuration.config_key,
                Configuration.config_scope,
                Configuration.site_id,
                Configuration.user_id
            ).distinct().all()
            
            for config_key, config_scope, site_id, user_id in unique_configs:
                # Get all versions for this configuration
                query = self.db.query(Configuration).filter(
                    and_(
                        Configuration.config_key == config_key,
                        Configuration.config_scope == config_scope
                    )
                )
                
                if config_scope == ConfigurationScope.SITE:
                    query = query.filter(Configuration.site_id == site_id)
                elif config_scope == ConfigurationScope.USER:
                    query = query.filter(Configuration.user_id == user_id)
                
                versions = query.order_by(desc(Configuration.version)).all()
                
                # Mark old versions as inactive
                if len(versions) > keep_versions:
                    old_versions = versions[keep_versions:]
                    for old_version in old_versions:
                        if old_version.is_active:
                            old_version.is_active = False
                            cleanup_count += 1
            
            self.db.commit()
            
            logger.info(
                "Cleaned up old configuration versions",
                keep_versions=keep_versions,
                cleanup_count=cleanup_count
            )
            
            return cleanup_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(
                "Failed to cleanup old configuration versions",
                keep_versions=keep_versions,
                error=str(e)
            )
            raise