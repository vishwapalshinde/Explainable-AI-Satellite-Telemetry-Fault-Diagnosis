"""
Security Utilities

This module handles:
  1. Password hashing with bcrypt (registration)
  2. Password verification (login)
  3. JWT token generation (access tokens)
  4. JWT token verification (validating tokens)

Why separate password hashing from JWT?
  - Hashing: One-way encryption for storage (user can't be recovered)
  - JWT: Token-based stateless auth (user identity in token, signed by server)
  
Flow:
  1. Registration: hash_password("MyPass123") → bcrypt hash → store in DB
  2. Login: verify_password("MyPass123", stored_hash) → True/False
  3. Token: create_access_token(user_id) → JWT token with expiration
  4. Verify: verify_token(jwt_token) → user_id or raise exception
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Password hashing
from passlib.context import CryptContext

# JWT tokens
from jose import JWTError, jwt
from pydantic import BaseModel

# ============================================================================
# PASSWORD HASHING CONFIGURATION
# ============================================================================
# 
# bcrypt: Industry-standard password hashing
# 
# Why bcrypt?
#   1. One-way: hash cannot be reversed to get password
#   2. Slow: ~0.1 second per hash (prevents brute force)
#   3. Salted: Each hash is unique (same password → different hash)
#   4. Adaptive: Can increase iterations as computers get faster
#
# Alternatives:
#   - scrypt: Even slower, more secure (overkill for most apps)
#   - Argon2: Winner of Password Hashing Competition (best option)
#   - PBKDF2: Older, simpler, less flexible
#
# For this project: Use bcrypt (good balance of security + performance)
#
# How bcrypt works:
#   Input:  "MyPass123"
#   Output: "$2b$12$R9h/cIPz0gi.URNNX3kh2eO8LbqZhYpW4c/4t/8dN8EkzaW8F16He"
#           └─┬─┘ └┬┘ └─────────────┬──────────────────────────┬───────────┘
#           algorithm  rounds    salt (embedded in hash)    encrypted hash
#
# Rounds: How many times to apply hash function
#   - 12 rounds = ~0.1 seconds on modern CPU
#   - Prevents timing attacks (all hashes take same time)
# ============================================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],           # Use bcrypt algorithm
    deprecated="auto"              # Auto-upgrade deprecated hashes
)


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using bcrypt.
    
    Args:
        password: Plain-text password from user
    
    Returns:
        bcrypt hash string (safe to store in database)
    
    Example:
        >>> hash = hash_password("MyPass123")
        >>> hash
        "$2b$12$R9h/cIPz0gi.URNNX3kh2eO8LbqZhYpW4c/4t/8dN8EkzaW8F16He"
    
    Security Notes:
        - Each call produces different hash (random salt)
        - Hash includes algorithm version and rounds
        - Cannot reverse hash to get password
        - Slow by design (0.1s per hash)
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify plain-text password against bcrypt hash.
    
    Args:
        plain_password: Password from login form
        hashed_password: Stored bcrypt hash from database
    
    Returns:
        True if password matches, False otherwise
    
    Example:
        >>> stored_hash = "$2b$12$R9h/cIPz0gi.URNNX3kh2eO8LbqZhYpW4c/4t/8dN8EkzaW8F16He"
        >>> verify_password("MyPass123", stored_hash)
        True
        >>> verify_password("WrongPassword", stored_hash)
        False
    
    Security Notes:
        - Also slow (~0.1s) - intentional to stop brute force
        - Timing constant: takes same time regardless of match
        - Uses bcrypt.checkpw() internally
    
    Attack Prevention:
        - Brute force: Can't try 1M passwords/second (0.1s per attempt)
        - Timing attack: All comparisons take same time (no early exit)
        - Rainbow tables: Salted hashes don't match pre-computed tables
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# JWT TOKEN CONFIGURATION
# ============================================================================
#
# JWT: JSON Web Token
#   - Token-based stateless authentication
#   - No session storage needed (compare with traditional sessions)
#   - Signed by server, verified by server
#   - Contains user ID, expiration, signature
#
# Anatomy of JWT:
#   eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE3MTU2MzI4MDB9.Y5KkO9Z8vF...
#   └──────────────────────┬──────────────────────┘└────────────────────────┬─────────────────────┘└─────┬─────┘
#         Header (algorithm)              Payload (user_id, expiration)         Signature (HMAC)
#
# How verification works:
#   1. Client sends: "eyJhbGc...Z8vF..."
#   2. Server signs payload with SECRET_KEY
#   3. If signature matches: token is valid
#   4. If someone tampers with payload: signature won't match
#   5. If expiration passed: reject token
#
# Advantages:
#   - No database lookup on every request (payload contains user_id)
#   - Scales to distributed systems (any server can verify)
#   - Works with mobile apps (no cookies needed)
#
# Disadvantages:
#   - Can't revoke tokens immediately (only solution: blacklist)
#   - Token contains data (don't put secrets in JWT)
# ============================================================================

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"  # HMAC with SHA256
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "24"))  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))  # 7 days

# ============================================================================
# TOKEN PAYLOAD MODELS
# ============================================================================

class TokenPayload(BaseModel):
    """What goes inside a JWT token."""
    user_id: int
    exp: datetime  # Expiration time


class TokenResponse(BaseModel):
    """What we send to client after login."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"  # Standard: "bearer" tokens in Authorization header
    expires_in: int  # Seconds until expiration


# ============================================================================
# TOKEN CREATION
# ============================================================================

def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: Database user ID
        expires_delta: Custom expiration (default: 24 hours)
    
    Returns:
        JWT token string
    
    Example:
        >>> token = create_access_token(user_id=1)
        >>> token
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE3MTU2MzI4MDB9.Y5KkO9Z8vF..."
    
    Token Contents:
        {
            "user_id": 1,
            "exp": 1715632800,  # Unix timestamp
            "iat": 1715546400,  # Issued at
        }
    
    Security Notes:
        - Token is signed with SECRET_KEY
        - Cannot be forged (signature won't match)
        - Expires automatically
        - Client stores and sends with each request
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"user_id": user_id, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: int) -> str:
    """
    Create a JWT refresh token (longer expiration).
    
    Usage:
        - Access tokens expire in 24 hours
        - Client can get new access token without re-entering password
        - Refresh tokens expire in 7 days
        - After 7 days, user must log in again
    
    Args:
        user_id: Database user ID
    
    Returns:
        JWT refresh token string
    """
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"user_id": user_id, "exp": expire, "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ============================================================================
# TOKEN VERIFICATION
# ============================================================================

def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify a JWT token and extract payload.
    
    Args:
        token: JWT token string from Authorization header
    
    Returns:
        Token payload (contains user_id)
    
    Raises:
        JWTError: If token is invalid, tampered, or expired
    
    Example:
        >>> token = "eyJhbGc...Z8vF..."
        >>> payload = verify_token(token)
        >>> payload
        {"user_id": 1, "exp": 1715632800}
    
    Verification Checks:
        1. Signature valid (hasn't been tampered)
        2. Expiration valid (not yet expired)
        3. Algorithm matches (HS256)
    
    Security:
        - If any check fails, raises exception
        - No silent failures
        - Requires exact signature match
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise JWTError("Invalid token: missing user_id")
        return payload
    except JWTError as e:
        raise JWTError(f"Could not validate token: {str(e)}")


def get_user_id_from_token(token: str) -> int:
    """
    Extract user_id from token.
    
    Args:
        token: JWT token
    
    Returns:
        User ID
    
    Raises:
        JWTError: If token invalid
    """
    payload = verify_token(token)
    return payload.get("user_id")


# ============================================================================
# PASSWORD VALIDATION
# ============================================================================

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Check if password meets security requirements.
    
    Rules:
        - At least 8 characters
        - At least 1 uppercase
        - At least 1 lowercase
        - At least 1 digit
        - At least 1 special character
    
    Returns:
        (is_valid, error_message)
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters")
    if not any(c.isupper() for c in password):
        errors.append("Must contain uppercase letter (A-Z)")
    if not any(c.islower() for c in password):
        errors.append("Must contain lowercase letter (a-z)")
    if not any(c.isdigit() for c in password):
        errors.append("Must contain digit (0-9)")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Must contain special character (!@#$%^&*)")
    
    if errors:
        return False, "; ".join(errors)
    return True, ""
