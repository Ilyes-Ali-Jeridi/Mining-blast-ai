"""
Integration test for the complete measurement data ingestion system.
Tests the full workflow from frontend to backend.
"""

import asyncio
import tempfile
import os
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
import requests
import json
from datetime import datetime

# Test configuration
API_BASE_URL = "http://localhost