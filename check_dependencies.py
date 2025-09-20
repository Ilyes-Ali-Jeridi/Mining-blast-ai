#!/usr/bin/env python3
"""
Dependency checker for the Automated Drill-and-Blast System.
Checks if all required dependencies are installed.
"""

import subprocess
import sys
import shutil
from pathlib import Path

def check_python():
    """Check Python version."""
    version = sys.version_info
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} found")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("⚠️  Python 3.8+ is recommended")
        return False
    return True

def check_node_npm():
    """Check if Node.js and npm are available."""
    node_path = shutil.which('node')
    
    if not node_path:
        print("❌ Node.js not found!")
        print("   Please install Node.js from https://nodejs.org/")
        print("   Recommended version: 18.x or 20.x LTS")
        return False
    
    try:
        import platform
        is_windows = platform.system() == 'Windows'
        
        # Get Node.js version
        node_result = subprocess.run(['node', '--version'], capture_output=True, text=True, check=True, shell=is_windows)
        node_version = node_result.stdout.strip()
        print(f"✅ Node.js {node_version} found at: {node_path}")
        
        # Check npm by trying to run it
        npm_result = subprocess.run(['npm', '--version'], capture_output=True, text=True, check=True, shell=is_windows)
        npm_version = npm_result.stdout.strip()
        npm_path = shutil.which('npm') or "npm (in PATH)"
        print(f"✅ npm {npm_version} found at: {npm_path}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Node.js/npm commands: {e}")
        return False
    except FileNotFoundError:
        print("❌ npm command not found!")
        print("   npm usually comes with Node.js installation")
        print("   Try reinstalling Node.js from https://nodejs.org/")
        return False
    except Exception as e:
        print(f"❌ Unexpected error checking Node.js/npm: {e}")
        return False

def check_python_packages():
    """Check if required Python packages are installed."""
    required_packages = [
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('sqlalchemy', 'sqlalchemy'),
        ('psycopg2-binary', 'psycopg2'),
        ('pydantic', 'pydantic'),
        ('python-dotenv', 'dotenv')
    ]
    
    missing_packages = []
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"✅ {package_name} installed")
        except ImportError:
            print(f"❌ {package_name} not found")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\n📦 To install missing packages, run:")
        print(f"   pip install {' '.join(missing_packages)}")
        print("   Or: pip install -r requirements.txt")
        return False
    
    return True

def check_frontend_dependencies():
    """Check if frontend dependencies are installed."""
    frontend_dir = Path('frontend')
    
    if not frontend_dir.exists():
        print("❌ Frontend directory not found!")
        return False
    
    node_modules = frontend_dir / 'node_modules'
    package_json = frontend_dir / 'package.json'
    
    if not package_json.exists():
        print("❌ package.json not found in frontend directory!")
        return False
    
    print("✅ package.json found")
    
    if not node_modules.exists():
        print("⚠️  node_modules not found - run 'npm install' in frontend directory")
        return False
    
    print("✅ node_modules directory found")
    return True

def main():
    """Main dependency check function."""
    print("🔍 Checking Automated Drill-and-Blast System Dependencies")
    print("=" * 60)
    
    checks = [
        ("Python", check_python),
        ("Node.js & npm", check_node_npm),
        ("Python packages", check_python_packages),
        ("Frontend dependencies", check_frontend_dependencies)
    ]
    
    all_good = True
    
    for name, check_func in checks:
        print(f"\n📋 Checking {name}...")
        if not check_func():
            all_good = False
    
    print("\n" + "=" * 60)
    
    if all_good:
        print("🎉 All dependencies are ready!")
        print("You can now run: python run_dev.py")
    else:
        print("❌ Some dependencies are missing or need attention")
        print("Please install the missing dependencies and run this check again")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())