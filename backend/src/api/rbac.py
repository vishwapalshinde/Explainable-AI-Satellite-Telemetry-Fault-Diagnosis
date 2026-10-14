"""
Role-Based Access Control (RBAC) Middleware

This module implements endpoint protection using roles and permissions.

How RBAC Works:

  1. User logs in → gets JWT token containing user_id
  2. User calls endpoint → sends token in Authorization header
  3. Middleware:
     a. Verify token (signature + expiration)
     b. Get user_id from token
     c. Load user from database
     d. Get user's role
     e. Get role's permissions
     f. Check if role has required permission
     g. If yes: allow endpoint; If no: return 403 Forbidden

  2. Endpoint Protection Levels:

     Public:      No auth needed (e.g., /health)
     Authenticated: Any logged-in user can call (e.g., /api/telemetry)
     Permission:   Only users with specific permission (e.g., /api/diagnose)

  Example:

     @app.get("/api/telemetry")
     async def get_telemetry(current_user: User = Depends(require_auth)):
         # Only logged-in users
     
     @app.post("/api/diagnose")
     async def diagnose(
         data: dict,
         current_user: User = Depends(require_permission("diagnose_faults"))
     ):
         # Only users with "diagnose_faults" permission
         # Admin + Engineer, NOT Viewer

  Permission Names:
  - view_telemetry: Can see satellite data
  - diagnose_faults: Can run fault detection
  - chat: Can chat with AI
  - download_data: Can export data
  - manage_users: Can create/delete users
  - manage_roles: Can modify permissions
"""

from fastapi import HTTPException, Depends, status, Header
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db, User
from ..utils.security import verify_token, get_user_id_from_token
from ..utils.logger import get_logger

logger = get_logger()

# ============================================================================
# DEPENDENCY: EXTRACT TOKEN FROM HEADER
# ============================================================================

def extract_token_from_header(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract JWT token from Authorization header.
    
    Format: Authorization: Bearer <token>
    
    Args:
        authorization: Authorization header value
    
    Returns:
        JWT token string
    
    Raises:
        HTTPException 401: If header missing or invalid format
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid scheme")
        return token
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header. Format: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"}
        )


# ============================================================================
# DEPENDENCY: REQUIRE AUTHENTICATION
# ============================================================================

async def require_auth(
    token: str = Depends(extract_token_from_header),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency that requires valid JWT token.
    
    Usage in endpoint:
        @app.get("/api/telemetry")
        async def get_telemetry(current_user: User = Depends(require_auth)):
            return f"Hello {current_user.username}"
    
    Args:
        token: JWT token from Authorization header
        db: Database session
    
    Returns:
        User object (verified and active)
    
    Raises:
        HTTPException 401: If token invalid/expired or user inactive
    
    Flow:
        1. Verify token signature (hasn't been tampered)
        2. Verify token not expired
        3. Extract user_id from token
        4. Load user from database
        5. Check user is active
        6. Return user object
    """
    
    try:
        # Step 1: Verify token
        payload = verify_token(token)
        user_id = payload.get("user_id")
        
        if not user_id:
            raise ValueError("Missing user_id in token")
        
        # Step 2: Load user from database
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            logger.warning(f"Token references non-existent user: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Step 3: Check if user is active
        if not user.is_active:
            logger.warning(f"Inactive user attempted access: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive"
            )
        
        return user
        
    except HTTPException:
        raise  # Re-raise FastAPI exceptions
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


# ============================================================================
# DEPENDENCY: REQUIRE SPECIFIC PERMISSION
# ============================================================================

def require_permission(required_permission: str):
    """
    FastAPI dependency factory that checks if user has permission.
    
    Usage in endpoint:
        @app.post("/api/diagnose")
        async def run_diagnosis(
            data: dict,
            current_user: User = Depends(require_permission("diagnose_faults"))
        ):
            return f"Running diagnosis for {current_user.username}"
    
    Args:
        required_permission: Permission name (e.g., "diagnose_faults")
    
    Returns:
        Dependency function that returns User
    
    Raises:
        HTTPException 401: If not authenticated
        HTTPException 403: If authenticated but permission denied
    
    Example Permission Check:
        
        User "alice" (admin role) → has all 6 permissions → allow
        User "bob" (engineer role) → has [view, diagnose, chat, download] → allow
        User "charlie" (viewer role) → has [view] → DENY (403 Forbidden)
    
    RBAC Matrix:
        Permission          Admin  Engineer  Viewer
        view_telemetry       ✓       ✓         ✓
        diagnose_faults      ✓       ✓         ✗
        chat                 ✓       ✓         ✗
        download_data        ✓       ✓         ✗
        manage_users         ✓       ✗         ✗
        manage_roles         ✓       ✗         ✗
    """
    
    async def check_permission(
        current_user: User = Depends(require_auth)
    ) -> User:
        """
        Inner dependency function that performs permission check.
        
        Args:
            current_user: Authenticated user (from require_auth)
        
        Returns:
            User if permission granted
        
        Raises:
            HTTPException 403: If permission denied
        """
        
        # Get user's role
        user_role = current_user.role
        
        if not user_role:
            logger.error(f"User {current_user.username} has no role")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no role assigned"
            )
        
        # Get all permission names for this role
        # permissions is SQLAlchemy relationship that returns list of Permission objects
        role_permissions = [p.name for p in user_role.permissions]
        
        logger.debug(f"Checking permission '{required_permission}' for {current_user.username}")
        logger.debug(f"User permissions: {role_permissions}")
        
        # Check if user's role has required permission
        if required_permission not in role_permissions:
            logger.warning(
                f"Permission denied for {current_user.username}: "
                f"required '{required_permission}' but has {role_permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {required_permission}"
            )
        
        logger.debug(f"Permission granted for {current_user.username}: {required_permission}")
        return current_user
    
    return check_permission


# ============================================================================
# DEPENDENCY: REQUIRE ADMIN ROLE
# ============================================================================

async def require_admin(
    current_user: User = Depends(require_auth)
) -> User:
    """
    Convenience dependency for admin-only endpoints.
    
    Usage:
        @app.delete("/api/users/{user_id}")
        async def delete_user(
            user_id: int,
            current_user: User = Depends(require_admin)
        ):
            # Only admin can call
    
    Args:
        current_user: Authenticated user
    
    Returns:
        User if admin role
    
    Raises:
        HTTPException 403: If not admin
    """
    
    if current_user.role.name != "admin":
        logger.warning(f"Non-admin user attempted admin action: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


# ============================================================================
# DEPENDENCY: OPTIONAL AUTH (Get user if token present, return None if not)
# ============================================================================

async def optional_auth(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication - returns user if authenticated, None otherwise.
    
    Useful for endpoints that work with or without login:
    - Public dashboard (no auth needed)
    - But if user logged in, show personalized content
    
    Usage:
        @app.get("/dashboard")
        async def dashboard(current_user: Optional[User] = Depends(optional_auth)):
            if current_user:
                return f"Hello {current_user.username}, welcome back!"
            else:
                return "Welcome! Please log in for personalized content."
    
    Args:
        authorization: Authorization header (optional)
        db: Database session
    
    Returns:
        User object if authenticated, None if not
    """
    
    if not authorization:
        return None
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        
        payload = verify_token(token)
        user_id = payload.get("user_id")
        
        if not user_id:
            return None
        
        user = db.query(User).filter(User.id == user_id).first()
        return user if user and user.is_active else None
        
    except Exception:
        return None


# ============================================================================
# SUMMARY OF RBAC DEPENDENCIES
# ============================================================================

"""
Use in endpoints:

1. PUBLIC endpoint (no auth):
   @app.get("/health")
   async def health():
       return {"status": "ok"}

2. AUTHENTICATED endpoint (any logged-in user):
   @app.get("/api/telemetry")
   async def get_telemetry(current_user: User = Depends(require_auth)):
       return f"Hello {current_user.username}"

3. PERMISSION-BASED endpoint:
   @app.post("/api/diagnose")
   async def diagnose(
       data: dict,
       current_user: User = Depends(require_permission("diagnose_faults"))
   ):
       return "Diagnosis results"

4. ADMIN ONLY endpoint:
   @app.delete("/api/users/{user_id}")
   async def delete_user(
       user_id: int,
       current_user: User = Depends(require_admin)
   ):
       return "User deleted"

5. OPTIONAL AUTH (works with or without login):
   @app.get("/dashboard")
   async def dashboard(current_user: Optional[User] = Depends(optional_auth)):
       if current_user:
           return f"Personalized for {current_user.username}"
       return "Public dashboard"
"""
