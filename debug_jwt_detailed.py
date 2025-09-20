"""Debug JWT token issue in detail."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def debug_jwt_detailed():
    """Debug JWT token creation and verification in detail."""
    try:
        from jose import jwt, JWTError
        from datetime import datetime, timedelta
        from drill_blast_system.core.config import get_settings
        
        settings = get_settings()
        secret_key = settings.security.secret_key
        algorithm = settings.security.algorithm
        
        print(f"Secret key: {secret_key}")
        print(f"Algorithm: {algorithm}")
        
        # Create token manually
        payload = {
            "sub": 1, 
            "username": "testuser", 
            "role": "engineer",
            "exp": datetime.utcnow() + timedelta(hours=8)
        }
        
        print(f"Payload: {payload}")
        
        # Encode token
        token = jwt.encode(payload, secret_key, algorithm=algorithm)
        print(f"Token: {token}")
        
        # Decode token
        try:
            decoded = jwt.decode(token, secret_key, algorithms=[algorithm])
            print(f"Decoded: {decoded}")
            print("✓ JWT token works correctly")
        except JWTError as e:
            print(f"✗ JWT decode error: {e}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_jwt_detailed()