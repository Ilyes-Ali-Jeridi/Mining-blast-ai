"""
Logging and error handling infrastructure.
Implements requirement 10.6: Basic logging and error handling infrastructure.
"""

import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

import structlog
from rich.console import Console
from rich.logging import RichHandler


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    enable_json: bool = False,
    enable_rich: bool = True
) -> None:
    """
    Set up structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        enable_json: Enable JSON structured logging
        enable_rich: Enable rich console formatting
    """
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    if enable_json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    handlers = []
    
    # Console handler
    if enable_rich:
        console = Console(stderr=True)
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True
        )
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
    
    handlers.append(console_handler)
    
    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
            )
        )
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=handlers,
        format="%(message)s"
    )
    
    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        structlog.BoundLogger: Configured logger instance
    """
    return structlog.get_logger(name)


class AuditLogger:
    """
    Specialized logger for audit trail and compliance logging.
    Implements immutable audit logging for safety compliance.
    """
    
    def __init__(self, audit_file: Optional[Path] = None):
        """
        Initialize audit logger.
        
        Args:
            audit_file: Optional dedicated audit log file
        """
        self.logger = get_logger("audit")
        self.audit_file = audit_file or Path("logs/audit.log")
        
        # Ensure audit log directory exists
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Set up dedicated audit file handler
        if self.audit_file:
            audit_handler = logging.FileHandler(self.audit_file, mode='a')
            audit_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - AUDIT - %(message)s"
                )
            )
            
            audit_logger = logging.getLogger("audit")
            audit_logger.addHandler(audit_handler)
            audit_logger.setLevel(logging.INFO)
    
    def log_engineer_signoff(
        self,
        engineer_name: str,
        blast_plan_id: str,
        plan_hash: str,
        safety_status: Dict[str, Any]
    ) -> None:
        """
        Log engineer sign-off for audit trail.
        
        Args:
            engineer_name: Name of signing engineer
            blast_plan_id: Unique blast plan identifier
            plan_hash: Hash of the blast plan for integrity
            safety_status: Safety validation results
        """
        self.logger.info(
            "Engineer sign-off recorded",
            event_type="engineer_signoff",
            engineer_name=engineer_name,
            blast_plan_id=blast_plan_id,
            plan_hash=plan_hash,
            safety_status=safety_status,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def log_safety_validation(
        self,
        blast_plan_id: str,
        validation_result: Dict[str, Any],
        constraints_checked: Dict[str, Any]
    ) -> None:
        """
        Log safety validation results.
        
        Args:
            blast_plan_id: Unique blast plan identifier
            validation_result: Safety validation results
            constraints_checked: All constraints that were validated
        """
        self.logger.info(
            "Safety validation performed",
            event_type="safety_validation",
            blast_plan_id=blast_plan_id,
            validation_result=validation_result,
            constraints_checked=constraints_checked,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def log_plan_export(
        self,
        blast_plan_id: str,
        export_format: str,
        engineer_name: str,
        file_hash: Optional[str] = None
    ) -> None:
        """
        Log blast plan export for audit trail.
        
        Args:
            blast_plan_id: Unique blast plan identifier
            export_format: Export format (PDF, CSV, JSON, etc.)
            engineer_name: Name of engineer performing export
            file_hash: Optional hash of exported file
        """
        self.logger.info(
            "Blast plan exported",
            event_type="plan_export",
            blast_plan_id=blast_plan_id,
            export_format=export_format,
            engineer_name=engineer_name,
            file_hash=file_hash,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def log_optimization_run(
        self,
        blast_plan_id: str,
        algorithm: str,
        parameters: Dict[str, Any],
        result_summary: Dict[str, Any]
    ) -> None:
        """
        Log optimization algorithm execution.
        
        Args:
            blast_plan_id: Unique blast plan identifier
            algorithm: Optimization algorithm used
            parameters: Algorithm parameters
            result_summary: Summary of optimization results
        """
        self.logger.info(
            "Optimization algorithm executed",
            event_type="optimization_run",
            blast_plan_id=blast_plan_id,
            algorithm=algorithm,
            parameters=parameters,
            result_summary=result_summary,
            timestamp=datetime.utcnow().isoformat()
        )


class ErrorHandler:
    """
    Centralized error handling and reporting.
    """
    
    def __init__(self):
        """Initialize error handler."""
        self.logger = get_logger("error_handler")
    
    def handle_physics_model_error(
        self,
        model_name: str,
        parameters: Dict[str, Any],
        error: Exception
    ) -> Dict[str, Any]:
        """
        Handle physics model calculation errors.
        
        Args:
            model_name: Name of the physics model
            parameters: Model parameters that caused the error
            error: The exception that occurred
            
        Returns:
            dict: Error response with fallback suggestions
        """
        self.logger.error(
            "Physics model calculation failed",
            model_name=model_name,
            parameters=parameters,
            error=str(error),
            error_type=type(error).__name__
        )
        
        return {
            "error": "Physics model calculation failed",
            "model": model_name,
            "message": str(error),
            "fallback_suggestion": "Using conservative default parameters",
            "recovery_action": "review_input_parameters"
        }
    
    def handle_optimization_error(
        self,
        algorithm: str,
        problem_size: Dict[str, int],
        error: Exception
    ) -> Dict[str, Any]:
        """
        Handle optimization algorithm errors.
        
        Args:
            algorithm: Optimization algorithm name
            problem_size: Size metrics of the optimization problem
            error: The exception that occurred
            
        Returns:
            dict: Error response with recovery suggestions
        """
        self.logger.error(
            "Optimization algorithm failed",
            algorithm=algorithm,
            problem_size=problem_size,
            error=str(error),
            error_type=type(error).__name__
        )
        
        return {
            "error": "Optimization failed",
            "algorithm": algorithm,
            "message": str(error),
            "recovery_suggestions": [
                "Try reducing problem complexity",
                "Relax constraints if feasible",
                "Use alternative optimization algorithm"
            ]
        }
    
    def handle_safety_validation_error(
        self,
        validation_type: str,
        constraints: Dict[str, Any],
        error: Exception
    ) -> Dict[str, Any]:
        """
        Handle safety validation errors.
        
        Args:
            validation_type: Type of safety validation
            constraints: Safety constraints being validated
            error: The exception that occurred
            
        Returns:
            dict: Error response with safety implications
        """
        self.logger.critical(
            "Safety validation error - CRITICAL",
            validation_type=validation_type,
            constraints=constraints,
            error=str(error),
            error_type=type(error).__name__
        )
        
        return {
            "error": "Safety validation failed",
            "validation_type": validation_type,
            "message": str(error),
            "safety_impact": "CRITICAL - Plan cannot be validated as safe",
            "required_action": "Manual safety review required before proceeding"
        }