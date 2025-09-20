#!/usr/bin/env python3
"""
Debug script to check environment variable loading.
"""

import os
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from drill_blast_system.core.config import get_settings

def main():
    print("🔍 Debugging Environment Variables and Settings")
    print("=" * 60)
    
    # SECURITY: Check if we should run in production
    try:
        from drill_blast_system.core.config import get_settings
        settings = get_settings()
        if settings.environment == "production":
            print("❌ Debug output disabled in production environment for security")
            return
    except Exception:
        # If we can't load settings, continue with basic checks
        pass
    
    # Check environment variables
    print("\n📋 Environment Variables:")
    env_vars = [
        'DB_URL',
        'DB_SUPABASE_URL', 
        'DB_SUPABASE_KEY',
        'DB_SUPABASE_SERVICE_KEY',
        'DB_ECHO'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if 'KEY' in var:
                print(f"   {var}: {'***' + value[-10:] if len(value) > 10 else '***'}")
            else:
                print(f"   {var}: {value}")
        else:
            print(f"   {var}: (not set)")
    
    # Check .env file
    env_file = Path('.env')
    print(f"\n📄 .env file exists: {env_file.exists()}")
    
    if env_file.exists():
        print("   .env file contents:")
        with open(env_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    if 'KEY' in line:
                        key, value = line.split('=', 1)
                        print(f"   {line_num:2d}: {key}={'***' + value[-10:] if len(value) > 10 else '***'}")
                    else:
                        print(f"   {line_num:2d}: {line}")
    
    # Load settings
    print("\n⚙️  Loading Settings:")
    try:
        settings = get_settings()
        print("   ✅ Settings loaded successfully")
        
        print(f"\n📊 Database Settings:")
        print(f"   url: {settings.database.url}")
        print(f"   supabase_url: {settings.database.supabase_url}")
        print(f"   supabase_key: {'***' + settings.database.supabase_key[-10:] if settings.database.supabase_key and len(settings.database.supabase_key) > 10 else settings.database.supabase_key}")
        print(f"   supabase_service_key: {'***' + settings.database.supabase_service_key[-10:] if settings.database.supabase_service_key and len(settings.database.supabase_service_key) > 10 else settings.database.supabase_service_key}")
        print(f"   echo: {settings.database.echo}")
        
    except Exception as e:
        print(f"   ❌ Failed to load settings: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()