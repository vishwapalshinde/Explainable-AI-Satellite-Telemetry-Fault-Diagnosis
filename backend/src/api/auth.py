"""
Authentication Endpoints

This module implements:
  1. POST /api/v1/auth/login - Exchange credentials for JWT token
  2. POST /api/v1/auth/logout - Invalidate token (client removes it)
  3. POST /api/v1/auth/refresh - Get new access token using refresh token
  4. GET /api/v1/auth/me - Get current logged-in user info

Security Flow:

  LOGIN:
  1. User enters username + password
  2. We hash password and compare with stored hash
  3. If match: Create JWT token with user_id + expiration
  4. Send token back to client
  5. Client stores token in secure storage
  
  REQUEST:
  1. Client sends: Authorization: Bearer <token>
  2. We verify: signature valid? Not expired?
  3. If valid: Process request with user_id from token
  4. If invalid: Return 401 Unauthorized
  
  TOKEN EXPIRATION:
  Access token: 24 hours (balance security vs UX)
  Refresh token: 7 days (user re-login every week)
  
  Use case:
  - Day 1: User logs in, gets 24-hour access token
  - Day 1, 8pm: Token still valid, works
  - Day 2: Token still valid, works
  - Day 3: Token expired (24h passed)
  - Client uses refresh token to get new access token
  - No re-login needed (smooth UX)
  - Day 8: Refresh token expired, must re-login (security)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from ..database import get_db, User, Role
from ..utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_user_id_from_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)
from .schemas import LoginRequest, LoginResponse, RefreshTokenRequest, UserResponse, ErrorResponse
from .schemas import RegisterRequest, RegisterResponse
from ..utils.logger import get_logger

logger = get_logger()
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user with default viewer role."""
    normalized_username = request.username.strip()
    normalized_email = request.email.strip().lower()

    if not normalized_username:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username cannot be empty"
        )

    if "@" not in normalized_email or "." not in normalized_email.split("@")[-1]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email address"
        )

    existing_user = db.query(User).filter(User.username == normalized_username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )

    existing_email = db.query(User).filter(User.email == normalized_email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists"
        )

    viewer_role = db.query(Role).filter(Role.name == "viewer").first()
    if not viewer_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default role 'viewer' not found. Run init_db.py first."
        )

    new_user = User(
        username=normalized_username,
        email=normalized_email,
        password_hash=hash_password(request.password),
        role_id=viewer_role.id,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"User registered successfully: {new_user.username}")

    return RegisterResponse(
        message="User created successfully",
        user=user_to_response(new_user)
    )

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_user_from_token(token: str, db: Session) -> User:
    """
    Extract user from JWT token.
    
    Args:
        token: JWT token from Authorization header
        db: Database session
    
    Returns:
        User object
    
    Raises:
        HTTPException 401: If token invalid or user doesn't exist
    """
    try:
        payload = verify_token(token)
        user_id = payload.get("user_id")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account inactive"
            )
        
        return user
        
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


def user_to_response(user: User) -> dict:
    """Convert User model to response dict (safe - no password hash)"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role.name,
        "is_active": user.is_active
    }


# ============================================================================
# ENDPOINT: LOGIN
# ============================================================================

@router.post("/login", response_model=LoginResponse, status_code=200)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    User login endpoint.
    
    Flow:
    1. Check if user exists with this username
    2. Verify password matches stored hash
    3. Generate JWT access token (24 hours)
    4. Generate JWT refresh token (7 days)
    5. Return tokens + user info
    
    Request:
        username: str (3-50 chars)
        password: str (8+ chars)
    
    Response:
        access_token: JWT token (use in Authorization header)
        refresh_token: JWT token (use to get new access token)
        expires_in: Seconds until access token expires
        user: User info (id, username, email, role)
    
    Errors:
        401: Invalid username or password
        422: Invalid request format
    
    Examples:
        POST /api/v1/auth/login
        {
            "username": "alice",
            "password": "MySecure@Pass123"
        }
        
        Response 200:
        {
            "access_token": "eyJhbGc...",
            "refresh_token": "eyJhbGc...",
            "token_type": "bearer",
            "expires_in": 86400,
            "user": {
                "id": 1,
                "username": "alice",
                "email": "alice@satellite.gov",
                "role": "admin",
                "is_active": true
            }
        }
    """
    
    normalized_username = request.username.strip()

    # Step 1: Find user by username (case-insensitive)
    user = db.query(User).filter(
        User.username == normalized_username
    ).first()
    
    if not user:
        logger.warning(f"Login attempt for non-existent user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"  # Don't reveal which is wrong (security)
        )
    
    # Step 2: Check if user is active
    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive. Contact administrator."
        )
    
    # Step 3: Verify password
    # verify_password() is SLOW (0.1 sec) - intentional to stop brute force
    if not verify_password(request.password, user.password_hash):
        logger.warning(f"Invalid password for user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Step 4: Update last login time
    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Step 5: Generate tokens
    access_token = create_access_token(user_id=user.id)
    refresh_token = create_refresh_token(user_id=user.id)
    
    logger.info(f"User logged in successfully: {user.username}")
    
    # Step 6: Return response
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        user=user_to_response(user)
    )


# ============================================================================
# ENDPOINT: LOGOUT
# ============================================================================

@router.post("/logout", status_code=204)
async def logout(
    authorization: str = None
):
    """
    User logout endpoint.
    
    Note: JWT tokens are stateless, so logout doesn't invalidate server-side.
    Client is responsible for deleting token from storage.
    
    For production security:
    - Token blacklist: Store expired tokens in Redis
    - Check blacklist on every request
    - When logout: Add token to blacklist until expiration
    
    For now: Client just deletes token, token remains valid until expiration
    
    Request:
        Authorization header with token (not required for logout)
    
    Response:
        204 No Content (success, no body)
    
    Examples:
        POST /api/v1/auth/logout
        Authorization: Bearer eyJhbGc...
        
        Response 204: (empty body)
    """
    
    # In this simple implementation, logout just returns 204
    # Client must delete token from localStorage/cookie
    
    logger.info("User logged out")
    return None


# ============================================================================
# ENDPOINT: REFRESH TOKEN
# ============================================================================

@router.post("/refresh", response_model=LoginResponse, status_code=200)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    
    Flow:
    1. Verify refresh token is valid and not expired
    2. Extract user_id from refresh token
    3. Load user from database
    4. Generate NEW access token (24 hour expiration)
    5. Return new access token
    
    Use case:
    - User logged in, got access token (24h expiration)
    - After 24 hours, access token expired
    - Client can use refresh token (valid for 7 days) to get new access token
    - No re-login needed
    - After 7 days, must login again
    
    Request:
        refresh_token: str (from login response)
    
    Response:
        access_token: NEW access token (24h)
        refresh_token: SAME refresh token (7d remaining)
        expires_in: 86400 (seconds = 24 hours)
        user: User info
    
    Errors:
        401: Refresh token invalid or expired
        422: Invalid request format
    
    Examples:
        POST /api/v1/auth/refresh
        {
            "refresh_token": "eyJhbGc..."
        }
        
        Response 200:
        {
            "access_token": "eyJhbGc...",  ← NEW token
            "refresh_token": "eyJhbGc...",  ← Same token
            "token_type": "bearer",
            "expires_in": 86400,
            "user": {...}
        }
    """
    
    try:
        # Step 1: Verify refresh token
        payload = verify_token(request.refresh_token)
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Step 2: Load user
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Step 3: Generate new access token
        access_token = create_access_token(user_id=user.id)
        
        logger.info(f"Token refreshed for user: {user.username}")
        
        # Step 4: Return new access token
        return LoginResponse(
            access_token=access_token,
            refresh_token=request.refresh_token,  # Refresh token unchanged
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_to_response(user)
        )
        
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )


# ============================================================================
# ENDPOINT: GET CURRENT USER
# ============================================================================

@router.get("/me", response_model=UserResponse, status_code=200)
async def get_current_user(
    authorization: str = None,
    db: Session = Depends(get_db)
):
    """
    Get current logged-in user information.
    
    How this works:
    1. Client sends: Authorization: Bearer <token>
    2. We extract token from header
    3. We verify token (signature + expiration)
    4. We get user_id from token
    5. We load user from database
    6. We return user info
    
    Request:
        Authorization: Bearer eyJhbGc...
    
    Response:
        id: User ID
        username: Username
        email: Email
        role: User role (admin, engineer, viewer)
        is_active: Whether account is active
        created_at: When account was created
    
    Errors:
        401: Token missing or invalid
        422: Invalid request format
    
    Examples:
        GET /api/v1/auth/me
        Authorization: Bearer eyJhbGc...
        
        Response 200:
        {
            "id": 1,
            "username": "alice",
            "email": "alice@satellite.gov",
            "role": "admin",
            "is_active": true,
            "created_at": "2026-05-12T10:00:00"
        }
    """
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authorization scheme")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>"
        )
    
    # Verify token and get user
    user = get_user_from_token(token, db)
    
    return UserResponse.model_validate(user)
