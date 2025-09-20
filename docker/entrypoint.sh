#!/bin/bash
# Docker entrypoint script for Automated Drill-and-Blast System

set -e

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to wait for database
wait_for_db() {
    log "Checking database connectivity..."
    
    # For Supabase/PostgreSQL, check if we can connect
    if [[ -n "$DB_SUPABASE_URL" ]]; then
        log "Supabase configuration detected"
        
        # Validate required Supabase environment variables
        if [[ -z "$DB_SUPABASE_KEY" ]]; then
            log "ERROR: DB_SUPABASE_KEY is required for Supabase"
            exit 1
        fi
        
        if [[ -z "$DB_SUPABASE_SERVICE_KEY" ]]; then
            log "ERROR: DB_SUPABASE_SERVICE_KEY is required for Supabase"
            exit 1
        fi
        
        log "Supabase configuration validated"
        return 0
    fi
    
    # For other PostgreSQL databases
    if [[ "$DB_URL" == postgresql* ]]; then
        log "PostgreSQL database configuration detected"
        # Could add connection testing here if needed
        return 0
    fi
    
    log "Database connectivity check completed"
}

# Function to initialize database
init_database() {
    log "Initializing database..."
    python -m drill_blast_system.cli init-db
    log "Database initialization completed"
}

# Function to run database migrations (future use)
run_migrations() {
    log "Running database migrations..."
    # Future: alembic upgrade head
    log "Database migrations completed"
}

# Function to validate configuration
validate_config() {
    log "Validating configuration..."
    python -m drill_blast_system.cli check-config
    log "Configuration validation completed"
}

# Main execution
main() {
    log "Starting Automated Drill-and-Blast System..."
    
    # Set default environment variables if not provided
    export PYTHONPATH="${PYTHONPATH:-/app/src}"
    export ENVIRONMENT="${ENVIRONMENT:-production}"
    
    # Wait for external dependencies
    wait_for_db
    
    # Initialize database if needed
    if [[ "${INIT_DB:-true}" == "true" ]]; then
        init_database
    fi
    
    # Run migrations if needed
    if [[ "${RUN_MIGRATIONS:-false}" == "true" ]]; then
        run_migrations
    fi
    
    # Validate configuration
    if [[ "${VALIDATE_CONFIG:-true}" == "true" ]]; then
        validate_config
    fi
    
    # Execute the main command
    log "Starting application with command: $*"
    
    if [[ $# -eq 0 ]]; then
        # Default command
        exec python -m drill_blast_system.cli serve --host 0.0.0.0 --port 8000
    else
        # Execute provided command
        exec python -m drill_blast_system.cli "$@"
    fi
}

# Handle signals for graceful shutdown
trap 'log "Received shutdown signal, stopping..."; exit 0' SIGTERM SIGINT

# Run main function
main "$@"