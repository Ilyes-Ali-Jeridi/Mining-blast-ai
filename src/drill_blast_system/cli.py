"""
Command Line Interface for the Automated Drill-and-Blast System.
Implements requirement 10.5: CLI interface for headless operation.
"""

import sys
import click
from pathlib import Path
from typing import Optional

from .core.config import get_settings, create_default_config_file
from .core.logging import setup_logging, get_logger
from .core.database import init_database
from .api.main import run_server

# Initialize logging for CLI
setup_logging(log_level="INFO", enable_rich=True)
logger = get_logger(__name__)


@click.group()
@click.version_option(version="0.1.0", prog_name="drill-blast-system")
@click.option("--config", "-c", type=click.Path(exists=True), help="Configuration file path")
@click.option("--log-level", default="INFO", help="Logging level")
@click.option("--log-file", type=click.Path(), help="Log file path")
@click.pass_context
def cli(ctx, config: Optional[str], log_level: str, log_file: Optional[str]):
    """
    Automated Drill-and-Blast System CLI.
    
    A comprehensive solution for generating safety-validated drill-and-blast plans.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Store configuration
    ctx.obj['config_file'] = config
    ctx.obj['log_level'] = log_level
    ctx.obj['log_file'] = log_file
    
    # Setup logging with CLI parameters
    log_file_path = Path(log_file) if log_file else None
    setup_logging(
        log_level=log_level,
        log_file=log_file_path,
        enable_rich=True
    )


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload (development)")
@click.option("--workers", default=1, help="Number of worker processes")
def serve(host: str, port: int, reload: bool, workers: int):
    """
    Start the FastAPI server.
    """
    logger.info("Starting Automated Drill-and-Blast System server...")
    
    try:
        # Override settings with CLI parameters
        settings = get_settings()
        settings.api.host = host
        settings.api.port = port
        settings.api.reload = reload
        settings.api.workers = workers
        
        # Start server
        run_server()
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Failed to start server", error=str(e))
        sys.exit(1)


@cli.command()
@click.option("--force", is_flag=True, help="Force database recreation")
def init_db(force: bool):
    """
    Initialize the database with tables and default data.
    """
    logger.info("Initializing database...")
    
    try:
        if force:
            logger.warning("Force flag specified - this will recreate all tables")
            click.confirm("Are you sure you want to recreate the database?", abort=True)
        
        init_database()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        sys.exit(1)


@cli.command()
@click.option("--output", "-o", default="config.yaml", help="Output configuration file path")
@click.option("--force", is_flag=True, help="Overwrite existing file")
def create_config(output: str, force: bool):
    """
    Create a default configuration file.
    """
    config_path = Path(output)
    
    if config_path.exists() and not force:
        logger.error(f"Configuration file {config_path} already exists. Use --force to overwrite.")
        sys.exit(1)
    
    try:
        create_default_config_file(config_path)
        logger.info(f"Default configuration created at {config_path}")
        
    except Exception as e:
        logger.error("Failed to create configuration file", error=str(e))
        sys.exit(1)


@cli.command()
def check_config():
    """
    Validate the current configuration.
    """
    logger.info("Checking configuration...")
    
    try:
        settings = get_settings()
        
        # Display key configuration values
        click.echo(f"App Name: {settings.app_name}")
        click.echo(f"Version: {settings.app_version}")
        click.echo(f"Environment: {settings.environment}")
        click.echo(f"Debug Mode: {settings.debug}")
        click.echo(f"Database URL: {settings.database.url}")
        if settings.database.supabase_url:
            click.echo(f"Supabase URL: {settings.database.supabase_url}")
            click.echo(f"Supabase Storage: {'Enabled' if settings.storage.use_supabase_storage else 'Disabled'}")
        click.echo(f"API Host: {settings.api.host}:{settings.api.port}")
        
        # Validate critical settings
        validation_errors = []
        
        if settings.physics.default_rock_factor_a <= 0:
            validation_errors.append("Invalid rock factor A (must be > 0)")
        
        if settings.physics.default_max_charge_per_hole <= 0:
            validation_errors.append("Invalid max charge per hole (must be > 0)")
        
        if settings.physics.default_ppv_limit <= 0:
            validation_errors.append("Invalid PPV limit (must be > 0)")
        
        if validation_errors:
            click.echo("\nConfiguration Errors:")
            for error in validation_errors:
                click.echo(f"  - {error}")
            sys.exit(1)
        else:
            click.echo("\nConfiguration is valid ✓")
        
    except Exception as e:
        logger.error("Configuration validation failed", error=str(e))
        sys.exit(1)


@cli.command()
def version():
    """
    Display version information.
    """
    settings = get_settings()
    
    click.echo(f"{settings.app_name}")
    click.echo(f"Version: {settings.app_version}")
    click.echo(f"Environment: {settings.environment}")
    click.echo("Built for mining engineering applications")


@cli.group()
def db():
    """
    Database management commands.
    """
    pass


@db.command()
def status():
    """
    Check database status and connectivity.
    """
    logger.info("Checking database status...")
    
    try:
        from .core.database import db_manager
        
        # Test database connection
        db = db_manager.get_session()
        try:
            result = db.execute("SELECT 1").scalar()
            if result == 1:
                click.echo("Database connection: OK ✓")
            else:
                click.echo("Database connection: FAILED ✗")
                sys.exit(1)
        finally:
            db.close()
        
        # Check table existence
        try:
            db = db_manager.get_session()
            audit_count = db.execute("SELECT COUNT(*) FROM audit_log").scalar()
            config_count = db.execute("SELECT COUNT(*) FROM system_configuration").scalar()
            
            click.echo(f"Audit log entries: {audit_count}")
            click.echo(f"Configuration entries: {config_count}")
            
        except Exception as e:
            click.echo(f"Table check failed: {e}")
            click.echo("Run 'drill-blast-system init-db' to initialize tables")
        finally:
            db.close()
        
    except Exception as e:
        logger.error("Database status check failed", error=str(e))
        sys.exit(1)


@db.command()
@click.option("--backup-file", "-b", help="Backup file path")
def backup(backup_file: Optional[str]):
    """
    Create a database backup.
    """
    if not backup_file:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"drill_blast_backup_{timestamp}.db"
    
    logger.info(f"Creating database backup: {backup_file}")
    
    try:
        import shutil
        from .core.database import get_settings
        
        settings = get_settings()
        
        # For PostgreSQL/Supabase, use pg_dump if available
        if "postgresql" in settings.database.url:
            try:
                import subprocess
                # Use pg_dump for PostgreSQL backup
                result = subprocess.run([
                    "pg_dump", 
                    settings.database.url,
                    "-f", backup_file
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    click.echo(f"Database backup created: {backup_file}")
                else:
                    click.echo(f"Backup failed: {result.stderr}")
                    sys.exit(1)
            except FileNotFoundError:
                click.echo("pg_dump not found. Please install PostgreSQL client tools.")
                sys.exit(1)
        else:
            click.echo("Backup not implemented for this database type")
            sys.exit(1)
        
    except Exception as e:
        logger.error("Database backup failed", error=str(e))
        sys.exit(1)


def main():
    """
    Main entry point for the CLI.
    """
    try:
        cli()
    except Exception as e:
        logger.error("CLI execution failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()