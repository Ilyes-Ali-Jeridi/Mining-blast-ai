"""
Demo script for ML Pipeline functionality.
Starts the server and demonstrates the ML pipeline features.
"""

import os
import sys
import time
import subprocess
import signal
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def run_server():
    """Run the FastAPI server"""
    print("Starting ML Pipeline Demo Server...")
    
    # Set environment variables to skip heavy initialization
    os.environ['SKIP_DB_INIT'] = 'true'
    os.environ['SKIP_HEAVY_IMPORTS'] = 'true'
    
    try:
        # Import and run the server
        import uvicorn
        from src.drill_blast_system.api.main import app
        
        print("Server starting on http://localhost:8000")
        print("API documentation available at http://localhost:8000/docs")
        print("ML Pipeline endpoints available at http://localhost:8000/api/v1/ml/")
        print("\nPress Ctrl+C to stop the server")
        
        # Run the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            reload=False
        )
        
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        print("\nTrying alternative startup method...")
        
        # Alternative: run via command line
        try:
            cmd = [
                sys.executable, "-m", "uvicorn", 
                "src.drill_blast_system.api.main:app",
                "--host", "0.0.0.0",
                "--port", "8000",
                "--reload"
            ]
            
            process = subprocess.Popen(cmd, env=os.environ.copy())
            
            print("Server started via subprocess")
            print("Press Ctrl+C to stop")
            
            # Wait for interrupt
            try:
                process.wait()
            except KeyboardInterrupt:
                print("\nStopping server...")
                process.terminate()
                process.wait()
                
        except Exception as e2:
            print(f"Alternative startup also failed: {e2}")

def main():
    """Main demo function"""
    print("=== ML Pipeline Demo ===")
    print()
    print("This demo will start the FastAPI server with ML Pipeline functionality.")
    print("You can then:")
    print("1. Visit http://localhost:8000/docs to see the API documentation")
    print("2. Test the ML pipeline endpoints")
    print("3. Use the frontend at http://localhost:3000 (if running)")
    print()
    
    # Check if frontend is running
    try:
        import requests
        response = requests.get("http://localhost:3000", timeout=2)
        print("✓ Frontend appears to be running at http://localhost:3000")
    except:
        print("ℹ Frontend not detected. You can start it with:")
        print("  cd frontend && npm run dev")
    
    print()
    input("Press Enter to start the server...")
    
    run_server()

if __name__ == "__main__":
    main()