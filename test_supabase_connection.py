#!/usr/bin/env python3
"""
Test Supabase database connection and setup.
"""

import os
import sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_supabase_connection():
    """Test connection to Supabase database."""
    
    # Get Supabase settings
    supabase_url = os.getenv('DB_SUPABASE_URL')
    service_key = os.getenv('DB_SUPABASE_SERVICE_KEY')
    
    print(f"🔍 Testing Supabase Connection")
    print(f"   Supabase URL: {supabase_url}")
    print(f"   Service Key: {'***' + service_key[-10:] if service_key and len(service_key) > 10 else 'Not set'}")
    
    if not supabase_url or not service_key:
        print("❌ Missing Supabase configuration")
        return False
    
    # Extract project reference
    try:
        project_ref = supabase_url.replace("https://", "").replace("http://", "").split(".")[0]
        db_url = f"postgresql://postgres:{service_key}@db.{project_ref}.supabase.co:5432/postgres"
        
        print(f"   Project Ref: {project_ref}")
        print(f"   Database Host: db.{project_ref}.supabase.co")
        
        # Test connection
        print("\n🔌 Testing database connection...")
        
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Connected successfully!")
        print(f"   PostgreSQL Version: {version}")
        
        # Check if tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print(f"\n📊 Existing tables ({len(tables)}):")
        for table in tables:
            print(f"   - {table[0]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def run_migrations():
    """Run database migrations."""
    
    supabase_url = os.getenv('DB_SUPABASE_URL')
    service_key = os.getenv('DB_SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not service_key:
        print("❌ Missing Supabase configuration")
        return False
    
    try:
        project_ref = supabase_url.replace("https://", "").replace("http://", "").split(".")[0]
        db_url = f"postgresql://postgres:{service_key}@db.{project_ref}.supabase.co:5432/postgres"
        
        print("\n🚀 Running database migrations...")
        
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Run migrations in order
        migration_files = [
            "supabase/migrations/001_initial_schema.sql",
            "supabase/migrations/002_core_models.sql"
        ]
        
        for migration_file in migration_files:
            if Path(migration_file).exists():
                print(f"   Running {migration_file}...")
                
                with open(migration_file, 'r') as f:
                    migration_sql = f.read()
                
                try:
                    cursor.execute(migration_sql)
                    print(f"   ✅ {migration_file} completed")
                except Exception as e:
                    print(f"   ⚠️  {migration_file} error (might be already applied): {e}")
            else:
                print(f"   ❌ Migration file not found: {migration_file}")
        
        cursor.close()
        conn.close()
        
        print("✅ Migrations completed!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Supabase Database Setup Tool")
    print("=" * 50)
    
    # Test connection first
    if test_supabase_connection():
        # Run migrations if connection works
        run_migrations()
    else:
        print("\n💡 Troubleshooting tips:")
        print("   1. Check if your Supabase project is active")
        print("   2. Verify the DB_SUPABASE_URL and DB_SUPABASE_SERVICE_KEY in .env")
        print("   3. Ensure your network can reach Supabase servers")
        print("   4. Check if the service key has the correct permissions")