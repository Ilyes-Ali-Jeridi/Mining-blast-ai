#!/usr/bin/env python3
"""
Development server runner for the Automated Drill-and-Blast System.
Runs both the FastAPI backend and React frontend in development mode.
"""

import subprocess
import sys
import os
import time
import signal
import shutil
from pathlib import Path

def check_node_npm():
    """Check if Node.js and npm are available."""
    try:
        import platform
        is_windows = platform.system() == 'Windows'
        
        # Check Node.js
        node_result = subprocess.run(['node', '--version'], capture_output=True, text=True, check=True, shell=is_windows)
        node_version = node_result.stdout.strip()
        node_path = shutil.which('node') or "node (in PATH)"
        print(f"✅ Node.js {node_version} found at: {node_path}")
        
        # Check npm
        npm_result = subprocess.run(['npm', '--version'], capture_output=True, text=True, check=True, shell=is_windows)
        npm_version = npm_result.stdout.strip()
        npm_path = shutil.which('npm') or "npm (in PATH)"
        print(f"✅ npm {npm_version} found at: {npm_path}")
        
        return True
    except subprocess.CalledProcessError:
        print("❌ Node.js or npm command failed!")
        return False
    except FileNotFoundError:
        print("❌ Node.js or npm not found! Please install Node.js from https://nodejs.org/")
        return False

def setup_environment():
    """Set up environment variables for development."""
    env_file = Path('.env')
    
    if not env_file.exists():
        print("📝 Creating .env file from .env.example...")
        example_file = Path('.env.example')
        if example_file.exists():
            # Copy .env.example to .env and modify for Supabase
            with open(example_file, 'r') as f:
                content = f.read()
            
            # Use Supabase configuration instead of local PostgreSQL
            content = content.replace(
                'DB_URL=postgresql://postgres:password@localhost:5432/drill_blast_system',
                '# DB_URL=postgresql://postgres:password@localhost:5432/drill_blast_system  # Local PostgreSQL (disabled)'
            )
            
            with open(env_file, 'w') as f:
                f.write(content)
            
            print("✅ Created .env file with Supabase configuration")
        else:
            print("⚠️  No .env.example found, creating minimal .env file...")
            with open(env_file, 'w') as f:
                f.write("""# Development environment configuration
APP_NAME="Automated Drill-and-Blast System"
ENVIRONMENT=development
DEBUG=true


# API configuration
API_HOST=127.0.0.1
API_PORT=8000
API_RELOAD=true

# Security settings
SECURITY_SECRET_KEY=dev-secret-key-change-in-production
""")
            print("✅ Created minimal .env file")

def run_backend():
    """Run the FastAPI backend server."""
    print("🚀 Starting FastAPI backend server...")
    
    # Change to project root
    os.chdir(Path(__file__).parent)
    
    # Set environment variables for development
    env = os.environ.copy()
    env.update({
        'PYTHONPATH': str(Path.cwd() / 'src'),
        'API_HOST': '127.0.0.1',
        'API_PORT': '8000',
        'DEBUG': 'true',
        'RELOAD': 'true'
    })
    
    # Run the backend
    cmd = [sys.executable, '-m', 'uvicorn', 'drill_blast_system.api.main:app', 
           '--host', '127.0.0.1', '--port', '8000', '--reload']
    
    return subprocess.Popen(cmd, env=env, cwd=Path.cwd())

def run_frontend():
    """Run the React frontend development server."""
    print("⚛️  Starting React frontend server...")
    
    frontend_dir = Path(__file__).parent / 'frontend'
    
    if not frontend_dir.exists():
        print("❌ Frontend directory not found!")
        return None
    
    # Check if Node.js and npm are available
    if not check_node_npm():
        return None
    
    # Check if node_modules exists
    if not (frontend_dir / 'node_modules').exists():
        print("📦 Installing frontend dependencies...")
        try:
            import platform
            is_windows = platform.system() == 'Windows'
            npm_install = subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True, shell=is_windows)
            print("✅ Frontend dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install frontend dependencies: {e}")
            return None
        except FileNotFoundError:
            print("❌ npm command not found. Please install Node.js and npm")
            return None
    
    # Run the frontend
    cmd = ['npm', 'run', 'dev']
    try:
        import platform
        is_windows = platform.system() == 'Windows'
        return subprocess.Popen(cmd, cwd=frontend_dir, shell=is_windows)
    except FileNotFoundError:
        print("❌ npm command not found. Please install Node.js and npm")
        return None

def main():
    """Main function to run both servers."""
    print("🔧 Starting Automated Drill-and-Blast System Development Servers")
    print("=" * 60)
    
    # Setup environment
    setup_environment()
    
    processes = []
    
    try:
        # Start backend
        backend_process = run_backend()
        if backend_process:
            processes.append(backend_process)
            print("✅ Backend server started (PID: {})".format(backend_process.pid))
            print("   📍 API: http://127.0.0.1:8000")
            print("   📚 Docs: http://127.0.0.1:8000/docs")
        else:
            print("❌ Failed to start backend server")
            return
        
        # Wait a moment for backend to start
        time.sleep(3)
        
        # Start frontend
        frontend_process = run_frontend()
        if frontend_process:
            processes.append(frontend_process)
            print("✅ Frontend server started (PID: {})".format(frontend_process.pid))
            print("   📍 App: http://localhost:5173")
        else:
            print("⚠️  Frontend server failed to start, but backend is running")
        
        if len(processes) > 0:
            print(f"\n🎉 {len(processes)} server(s) are running!")
            print("Press Ctrl+C to stop all servers")
            
            # Wait for processes
            while True:
                time.sleep(1)
                # Check if any process has died
                for process in processes[:]:  # Create a copy to iterate over
                    if process.poll() is not None:
                        print(f"⚠️  Process {process.pid} has stopped")
                        processes.remove(process)
                        if not processes:
                            print("All processes have stopped")
                            return
        else:
            print("❌ No servers could be started")
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
    
    finally:
        # Clean up processes
        for process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ Stopped process {process.pid}")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"🔪 Killed process {process.pid}")
            except Exception as e:
                print(f"❌ Error stopping process {process.pid}: {e}")
        
        print("👋 All servers stopped")

if __name__ == "__main__":
    main()
