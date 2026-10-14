"""
JWT Authentication Schemas and Models

These Pydantic models validate incoming requests and define response formats.

Pydantic = data validation library
  - Validates input shape/types automatically
  - Converts raw JSON to Python objects
  - Raises 422 Unprocessable Entity if invalid

Example:
  Request: POST /login
  Body: {"username": "alice", "password": "MyPass123"}
  
  FastAPI parses with LoginRequest model:
    - Checks: username is string (not number)
    - Checks: password is string (not empty)
    - Returns 422 if missing or wrong type
    - Returns LoginRequest object if valid
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    """User registration payload"""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: str = Field(..., min_length=5, max_length=120, description="Email address")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "new_user",
                "email": "new_user@satellite.gov",
                "password": "MySecure@Pass123"
            }
        }


class RegisterResponse(BaseModel):
    """Response after successful registration"""
    message: str = Field(..., description="Registration status message")
    user: dict = Field(..., description="Created user info")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "User created successfully",
                "user": {
                    "id": 2,
                    "username": "new_user",
                    "email": "new_user@satellite.gov",
                    "role": "viewer",
                    "is_active": True
                }
            }
        }

# ============================================================================
# LOGIN REQUEST
# ============================================================================

class LoginRequest(BaseModel):
    """User login credentials"""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "alice",
                "password": "MySecure@Pass123"
            }
        }


# ============================================================================
# LOGIN RESPONSE
# ============================================================================

class LoginResponse(BaseModel):
    """Response after successful login"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token (optional)")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: dict = Field(..., description="User info")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
                "user": {
                    "id": 1,
                    "username": "alice",
                    "email": "alice@satellite.gov",
                    "role": "admin"
                }
            }
        }


# ============================================================================
# TOKEN REFRESH REQUEST
# ============================================================================

class RefreshTokenRequest(BaseModel):
    """Request to get new access token using refresh token"""
    refresh_token: str = Field(..., description="Refresh token from login")
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


# ============================================================================
# USER RESPONSE
# ============================================================================

class UserResponse(BaseModel):
    """User information (safe to return to client)"""
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True  # SQLAlchemy model → dict conversion
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "alice",
                "email": "alice@satellite.gov",
                "role": "admin",
                "is_active": True,
                "created_at": "2026-05-12T10:00:00"
            }
        }


# ============================================================================
# ERROR RESPONSE
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Invalid credentials",
                "code": "INVALID_CREDENTIALS"
            }
        }
