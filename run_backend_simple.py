#!/usr/bin/env python3
"""
Simple backend runner that bypasses database initialization for testing.
This allows the API to start even when database connection fails.
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

# Set environment variables
os.environ['PYTHONPATH'] = str(src_path)
os.environ['SKIP_DB_INIT'] = 'true'  # Flag to skip database initialization

if __name__ == "__main__":
    print("🚀 Starting FastAPI backend (simple mode - no database)")
    print("   📍 API: http://127.0.0.1:8000")
    print("   📚 Docs: http://127.0.0.1:8000/docs")
    print("   ⚠️  Database features will be disabled")
    
    uvicorn.run(
        "drill_blast_system.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )