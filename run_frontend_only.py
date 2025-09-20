#!/usr/bin/env python3
"""
Frontend-only development server runner.
Runs just the React frontend for testing the map visualization.
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def check_node():
    """Check if Node.js is installed."""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Node.js found: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ Node.js not found!")
    print("Please install Node.js from https://nodejs.org/")
    print("Or use a package manager:")
    print("  - Windows: choco install nodejs")
    print("  - macOS: brew install node")
    print("  - Linux: sudo apt install nodejs npm")
    return False

def check_npm():
    """Check if npm is installed."""
    try:
        result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ npm found: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ npm not found!")
    return False

def run_frontend():
    """Run the React frontend development server."""
    print("⚛️  Starting React frontend server...")
    
    frontend_dir = Path(__file__).parent / 'frontend'
    
    if not frontend_dir.exists():
        print("❌ Frontend directory not found!")
        return None
    
    # Check if node_modules exists
    if not (frontend_dir / 'node_modules').exists():
        print("📦 Installing frontend dependencies...")
        npm_install = subprocess.run(['npm', 'install'], cwd=frontend_dir)
        if npm_install.returncode != 0:
            print("❌ Failed to install frontend dependencies!")
            return None
        print("✅ Dependencies installed successfully!")
    
    # Run the frontend
    print("🚀 Starting development server...")
    cmd = ['npm', 'run', 'dev']
    return subprocess.Popen(cmd, cwd=frontend_dir)

def main():
    """Main function to run frontend only."""
    print("⚛️  Frontend-Only Development Server")
    print("=" * 40)
    
    # Check prerequisites
    if not check_node() or not check_npm():
        print("\n❌ Prerequisites not met. Please install Node.js and npm first.")
        return
    
    try:
        # Start frontend
        frontend_process = run_frontend()
        if frontend_process:
            print("✅ Frontend server started!")
            print("   📍 App: http://localhost:5173")
            print("   🗺️  Navigate to 'Blast Plans' page and click 'Show Map'")
            print("\n🎉 Frontend is running!")
            print("Press Ctrl+C to stop the server")
            
            # Wait for process
            frontend_process.wait()
        else:
            print("❌ Failed to start frontend server")
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping server...")
        if 'frontend_process' in locals() and frontend_process:
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=5)
                print("✅ Frontend server stopped")
            except subprocess.TimeoutExpired:
                frontend_process.kill()
                print("🔪 Frontend server killed")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        print("👋 Development server stopped")

if __name__ == "__main__":
    main()