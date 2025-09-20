"""
Automated Drill-and-Blast System

A comprehensive, production-grade solution for generating complete, 
safety-validated drill-and-blast plans for mining operations.
"""

__version__ = "0.1.0"
__author__ = "Mining Engineering Team"
__email__ = "engineering@mining.com"

from .core.config import get_settings
from .core.logging import setup_logging

__all__ = ["get_settings", "setup_logging"]