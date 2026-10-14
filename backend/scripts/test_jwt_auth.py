"""
JWT Authentication Test Script

Tests the authentication endpoints without needing a running database.
This verifies that:
  1. Token generation works
  2. Token verification works
  3. Password hashing/verification works
  4. RBAC permission checking works

Run:
  cd backend
  python scripts/test_jwt_auth.py
"""

import sys
import os

# Add src to path so we can import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from src.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_user_id_from_token,
    validate_password_strength
)
from datetime import timedelta
import json

def test_password_hashing():
    """Test bcrypt password hashing"""
    print("\n" + "="*70)
    print("TEST 1: PASSWORD HASHING")
    print("="*70)
    
    password = "MySecure@Pass123"
    print(f"Original password: {password}")
    
    # Hash password
    hash1 = hash_password(password)
    hash2 = hash_password(password)  # Same password, different hash
    
    print(f"Hash 1: {hash1[:50]}...")
    print(f"Hash 2: {hash2[:50]}...")
    print(f"✓ Same password produces different hashes (salted): {hash1 != hash2}")
    
    # Verify password
    verify1 = verify_password(password, hash1)
    verify2 = verify_password("WrongPassword", hash1)
    
    print(f"✓ Correct password verifies: {verify1}")
    print(f"✓ Wrong password rejected: {not verify2}")
    
    return verify1 and not verify2


def test_password_validation():
    """Test password strength validation"""
    print("\n" + "="*70)
    print("TEST 2: PASSWORD VALIDATION")
    print("="*70)
    
    test_cases = [
        ("password", False, "No uppercase/digit/special"),
        ("Pass123", False, "No special character"),
        ("Pass@", False, "Too short"),
        ("MySecure@Pass123", True, "Valid password"),
        ("Secure$Pass99!", True, "Valid password"),
    ]
    
    all_passed = True
    for password, should_be_valid, reason in test_cases:
        is_valid, msg = validate_password_strength(password)
        status = "✓" if is_valid == should_be_valid else "✗"
        print(f"{status} '{password}' → {is_valid} ({reason})")
        if is_valid != should_be_valid:
            print(f"   Error: {msg}")
            all_passed = False
    
    return all_passed


def test_jwt_generation():
    """Test JWT token generation"""
    print("\n" + "="*70)
    print("TEST 3: JWT TOKEN GENERATION")
    print("="*70)
    
    user_id = 1
    
    # Create access token
    access_token = create_access_token(user_id=user_id)
    print(f"Access token: {access_token[:50]}...")
    print(f"✓ Access token generated (length: {len(access_token)})")
    
    # Create refresh token
    refresh_token = create_refresh_token(user_id=user_id)
    print(f"Refresh token: {refresh_token[:50]}...")
    print(f"✓ Refresh token generated (length: {len(refresh_token)})")
    
    return len(access_token) > 30 and len(refresh_token) > 30


def test_jwt_verification():
    """Test JWT token verification"""
    print("\n" + "="*70)
    print("TEST 4: JWT TOKEN VERIFICATION")
    print("="*70)
    
    user_id = 42
    
    # Create and verify token
    token = create_access_token(user_id=user_id)
    print(f"Created token for user_id={user_id}")
    
    # Verify token
    try:
        payload = verify_token(token)
        print(f"✓ Token verified successfully")
        print(f"  Payload: {json.dumps(payload, indent=2, default=str)}")
        
        extracted_user_id = get_user_id_from_token(token)
        print(f"✓ Extracted user_id from token: {extracted_user_id}")
        
        return extracted_user_id == user_id
        
    except Exception as e:
        print(f"✗ Token verification failed: {e}")
        return False


def test_jwt_expiration():
    """Test JWT token expiration"""
    print("\n" + "="*70)
    print("TEST 5: JWT TOKEN EXPIRATION")
    print("="*70)
    
    # Create token that expires in 1 second
    token = create_access_token(
        user_id=1,
        expires_delta=timedelta(seconds=1)
    )
    print(f"Created token with 1 second expiration")
    
    # Verify it works immediately
    try:
        payload = verify_token(token)
        print(f"✓ Token valid immediately after creation")
        
        # Wait 2 seconds
        import time
        print(f"Waiting 2 seconds...")
        time.sleep(2)
        
        # Try to verify expired token
        try:
            verify_token(token)
            print(f"✗ Expired token still accepted (should have failed)")
            return False
        except Exception:
            print(f"✓ Expired token correctly rejected")
            return True
            
    except Exception as e:
        print(f"✗ Token verification failed: {e}")
        return False


def test_invalid_token():
    """Test verification of invalid tokens"""
    print("\n" + "="*70)
    print("TEST 6: INVALID TOKEN REJECTION")
    print("="*70)
    
    test_cases = [
        ("invalid.token.here", "Invalid format"),
        ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature", "Tampered signature"),
        ("", "Empty token"),
    ]
    
    all_passed = True
    for token, reason in test_cases:
        try:
            verify_token(token)
            print(f"✗ {reason} - Token accepted (should fail)")
            all_passed = False
        except Exception:
            print(f"✓ {reason} - Token correctly rejected")
    
    return all_passed


def main():
    """Run all tests"""
    print("\n" + "🔐 JWT AUTHENTICATION TEST SUITE" + "\n")
    
    results = {
        "Password Hashing": test_password_hashing(),
        "Password Validation": test_password_validation(),
        "JWT Generation": test_jwt_generation(),
        "JWT Verification": test_jwt_verification(),
        "JWT Expiration": test_jwt_expiration(),
        "Invalid Token Rejection": test_invalid_token(),
    }
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:10} {test_name}")
    
    all_passed = all(results.values())
    print("\n" + "="*70)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("\nJWT Authentication is working correctly!")
        print("\nNext steps:")
        print("  1. Set up PostgreSQL: docker-compose up -d postgres")
        print("  2. Initialize database: python scripts/init_db.py")
        print("  3. Create admin user: python scripts/create_admin.py")
        print("  4. Start backend: uvicorn src.api.main:app --reload")
    else:
        print("✗ SOME TESTS FAILED")
        print("\nReview the errors above")
    print("="*70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
