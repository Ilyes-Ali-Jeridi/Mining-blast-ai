"""Debug genetic optimizer imports"""

print("Starting imports...")

try:
    from typing import List, Dict, Tuple, Optional, Any, Callable
    print("typing imports OK")
except Exception as e:
    print(f"typing import error: {e}")

try:
    import numpy as np
    print("numpy import OK")
except Exception as e:
    print(f"numpy import error: {e}")

try:
    import logging
    print("logging import OK")
except Exception as e:
    print(f"logging import error: {e}")

try:
    from dataclasses import dataclass
    print("dataclasses import OK")
except Exception as e:
    print(f"dataclasses import error: {e}")

try:
    import time
    print("time import OK")
except Exception as e:
    print(f"time import error: {e}")

try:
    import pygad
    PYGAD_AVAILABLE = True
    print("pygad import OK")
except ImportError:
    PYGAD_AVAILABLE = False
    pygad = None
    print("pygad not available")

try:
    from .data_structures import (
        OptimizationProblem, OptimizationResult, OptimizationStatus,
        BlastPlan, DrillHole, DecisionVariable
    )
    print("data_structures import OK")
except Exception as e:
    print(f"data_structures import error: {e}")

try:
    from .formulation import ObjectiveFunction, ConstraintManager
    print("formulation import OK")
except Exception as e:
    print(f"formulation import error: {e}")

print("All imports completed")