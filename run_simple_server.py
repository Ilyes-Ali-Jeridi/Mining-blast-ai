"""
Simple server runner for ML Pipeline demo.
Bypasses complex startup sequence to avoid lifespan issues.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set environment variables to skip problematic initialization
os.environ['SKIP_DB_INIT'] = 'true'
os.environ['SKIP_HEAVY_IMPORTS'] = 'true'

def create_simple_app():
    """Create a simplified FastAPI app for ML Pipeline demo"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    # Create simple app without complex lifespan
    app = FastAPI(
        title="ML Pipeline Demo",
        description="Simplified server for ML Pipeline functionality",
        version="1.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Import and include ML pipeline routes
    try:
        from src.drill_blast_system.api.routes import ml_pipeline
        app.include_router(ml_pipeline.router, prefix="/api/v1/ml", tags=["ml-pipeline"])
        print("✓ ML Pipeline routes loaded successfully")
    except Exception as e:
        print(f"⚠ Error loading ML Pipeline routes: {e}")
    
    # Add basic health check
    @app.get("/")
    async def root():
        return {"message": "ML Pipeline Demo Server", "status": "running"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "ml-pipeline-demo"}
    
    return app

def main():
    """Run the simplified server"""
    print("=== ML Pipeline Demo Server ===")
    print("Starting simplified server...")
    
    try:
        import uvicorn
        
        # Create the app
        app = create_simple_app()
        
        print("\nServer starting on:")
        print("  - Local: http://localhost:8000")
        print("  - API Docs: http://localhost:8000/docs")
        print("  - ML Pipeline: http://localhost:8000/api/v1/ml/")
        print("\nPress Ctrl+C to stop")
        
        # Run with minimal configuration
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
            access_log=False,
            reload=False
        )
        
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
    except Exception as e:
        print(f"✗ Server error: {e}")
        print("\nTrying command line approach...")
        
        # Fallback to command line
        import subprocess
        cmd = [
            sys.executable, "-c",
            """
import os
os.environ['SKIP_DB_INIT'] = 'true'
os.environ['SKIP_HEAVY_IMPORTS'] = 'true'
exec(open('run_simple_server.py').read())
"""
        ]
        
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            print("\n✓ Server stopped")

if __name__ == "__main__":
    main()