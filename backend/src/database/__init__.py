"""
Database Module

Exports:
  - Models: User, Role, Permission, TelemetryData, Anomaly, ChatSession, ChatMessage
  - Functions: get_db, create_all_tables, health_check
"""

from .models import (
    Base,
    User,
    Role,
    Permission,
    TelemetryData,
    Anomaly,
    ChatSession,
    ChatMessage,
    role_permissions
)

from .database import (
    engine,
    SessionLocal,
    get_db,
    create_all_tables,
    drop_all_tables,
    health_check,
    DATABASE_URL,
    SQLALCHEMY_DATABASE_URL
)

__all__ = [
    # Models
    'Base',
    'User',
    'Role',
    'Permission',
    'TelemetryData',
    'Anomaly',
    'ChatSession',
    'ChatMessage',
    'role_permissions',
    # Database
    'engine',
    'SessionLocal',
    'get_db',
    'create_all_tables',
    'drop_all_tables',
    'health_check',
    'SQLALCHEMY_DATABASE_URL',
]
