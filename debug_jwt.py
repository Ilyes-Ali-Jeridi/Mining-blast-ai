"""Debug JWT token issue."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def debug_jwt():
    """Debug JWT token creation and verification."""
    try:
        from drill_blast_system.auth.security import create_access_token, verify_token
        from drill_blast_system.core.config import get_settings
        
        # Check settings
        settings = get_settings()
        print(f"Secret key: {settings.security.secret_key[:10]}...")
        print(f"Algorithm: {settings.security.algorithm}")
        
        # Create token
        payload = {"sub": 1, "username": "testuser", "role": "engineer"}
        print(f"Creating token with payload: {payload}")
        
        token = create_access_token(payload)
        print(f"Token created: {token[:50]}...")
        
        # Verify token
        decoded = verify_token(token)
        print(f"Decoded payload: {decoded}")
        
        if decoded:
            print("✓ JWT token verification successful")
        else:
            print("✗ JWT token verification failed")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_jwt()