"""
API routes module.
Contains all API endpoint definitions for the drill-and-blast system.
"""

from . import health, system, sites, blast_plans, safety, configuration, optimization, exports, auth, ml_pipeline, admin, measurement_data, simulations, synthetic

__all__ = [
    "health",
    "system", 
    "sites",
    "blast_plans",
    "safety",
    "configuration",
    "optimization",
    "exports", 
    "auth",
    "ml_pipeline",
    "admin",
    "measurement_data",
    "simulations",
    "synthetic"
]