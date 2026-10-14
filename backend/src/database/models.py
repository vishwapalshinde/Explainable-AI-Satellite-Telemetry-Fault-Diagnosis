"""
SQLAlchemy ORM Models for Satellite Telemetry Fault Diagnosis System

This file defines all database tables:
  - Users: System users (who can log in)
  - Roles: User roles (admin, engineer, viewer)
  - Permissions: What actions each role can perform
  - Telemetry Data: Raw satellite sensor readings
  - Anomalies: Detected faults in telemetry
  - Chat Sessions & Messages: User conversations (audit trail)

Each model class represents ONE table in PostgreSQL.
Column definitions ensure data integrity at database level.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    Text, JSON, ForeignKey, Table, UniqueConstraint, Index,
    CheckConstraint, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

# Base class: every model inherits from this
Base = declarative_base()


# ============================================================================
# ASSOCIATION TABLE: Many-to-Many relationship between Roles and Permissions
# ============================================================================
# Why: A role (e.g., "engineer") can have multiple permissions (chat, diagnose)
#      A permission (e.g., "diagnose") can be assigned to multiple roles
# Solution: Junction table that links them
#
# Example: 
#   roles table has: 1 | engineer
#   permissions table has: 1 | diagnose_faults
#   role_permissions table has: 1 | 1 (engineer has diagnose_faults permission)
# ============================================================================

role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    Index('idx_role_permissions', 'role_id', 'permission_id')
)


# ============================================================================
# TABLE 1: PERMISSIONS
# ============================================================================
# Purpose: Define what actions a user can perform (fine-grained access control)
#
# Why separate from roles?
#   - Roles bundle permissions (e.g., "engineer" = diagnose + chat + view)
#   - Permissions are reusable across roles
#   - Easy to add new permissions without creating new roles
#
# Examples:
#   - view_telemetry: Can see satellite data
#   - diagnose_faults: Can run fault detection
#   - download_data: Can export telemetry
#   - manage_users: Can create/delete users (admin only)
#   - manage_roles: Can modify role permissions (admin only)
# ============================================================================

class Permission(Base):
    __tablename__ = 'permissions'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    # Example: "view_telemetry", "diagnose_faults", "download_data"
    
    description = Column(String(255))
    # Example: "User can view satellite telemetry data"
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship: which roles have this permission
    roles = relationship('Role', secondary=role_permissions, back_populates='permissions')
    
    def __repr__(self):
        return f'<Permission {self.name}>'


# ============================================================================
# TABLE 2: ROLES
# ============================================================================
# Purpose: Group permissions into roles for easier management
#
# Why not assign permissions to every user individually?
#   - 100 users × 10 possible permissions = 1000 assignments
#   - If you add a new permission, need to update 100 users
#   - Error-prone and scales poorly
#
# With roles:
#   - Create 3 roles (admin, engineer, viewer)
#   - Assign permissions to roles (done once)
#   - Assign users to roles (easy!)
#   - Adding new user = just pick a role
#
# Built-in Roles:
#   - admin: Full system access (all permissions)
#   - engineer: Can diagnose and chat (subset of permissions)
#   - viewer: Read-only access to dashboard
# ============================================================================

class Role(Base):
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    # Example: "admin", "engineer", "viewer"
    
    description = Column(String(255))
    # Example: "Full system access with user management capabilities"
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship: which permissions does this role have
    permissions = relationship('Permission', secondary=role_permissions, back_populates='roles')
    
    # Relationship: which users have this role
    users = relationship('User', back_populates='role')
    
    def __repr__(self):
        return f'<Role {self.name}>'


# ============================================================================
# TABLE 3: USERS
# ============================================================================
# Purpose: Store system users who can log in
#
# Security Notes:
#   - password_hash: NEVER store plain passwords!
#     Instead, hash password using bcrypt/argon2
#     During login: hash(entered_password) == stored password_hash
#   - is_active: Soft delete (set to False instead of removing row)
#   - created_at/updated_at: Audit trail (when did this user join/last change)
#   - email: Unique constraint so can't have duplicates
#   - role_id: Foreign key enforces user must have valid role
#
# Constraints:
#   - username: 3-50 chars, unique
#   - email: Valid email format (enforced by app logic)
#   - password_hash: Required (never NULL)
# ============================================================================

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    
    username = Column(String(50), unique=True, nullable=False, index=True)
    # Constraint: Must be 3-50 characters, alphanumeric + underscore
    
    email = Column(String(120), unique=True, nullable=False, index=True)
    # Constraint: Must be valid email format
    
    password_hash = Column(String(255), nullable=False)
    # IMPORTANT: This is a HASH, not the plain password
    # Hash function is one-way (can't reverse to get password)
    # During login: bcrypt.verify(entered_password, this_hash) = True/False
    
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='RESTRICT'), nullable=False, index=True)
    # Foreign Key: Ensures role_id points to actual role in roles table
    # ondelete='RESTRICT': Can't delete a role if users still have it
    
    is_active = Column(Boolean, default=True, nullable=False)
    # Soft delete: Set to False to deactivate user instead of deleting row
    # Preserves audit trail (user still exists, just inactive)
    
    last_login = Column(DateTime, nullable=True)
    # Tracks when user last logged in (for session management, abuse detection)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    role = relationship('Role', back_populates='users')
    
    chat_sessions = relationship('ChatSession', back_populates='user', cascade='all, delete-orphan')
    # cascade='all, delete-orphan': If user deleted, also delete their chat sessions
    
    telemetry_uploads = relationship('TelemetryData', back_populates='created_by_user', foreign_keys='TelemetryData.created_by_user_id')
    anomaly_detections = relationship('Anomaly', back_populates='detected_by_user', foreign_keys='Anomaly.detected_by_user_id')
    
    # Index for faster queries
    __table_args__ = (
        Index('idx_user_active_role', 'is_active', 'role_id'),  # Fast lookup: "find all active engineers"
    )
    
    def __repr__(self):
        return f'<User {self.username}>'


# ============================================================================
# TABLE 4: TELEMETRY_DATA
# ============================================================================
# Purpose: Store satellite sensor readings from CSV
#
# Migration Plan:
#   - Read from dataset/dataset.csv
#   - Parse each row into telemetry record
#   - Store with satellite_id, timestamp, channel data
#   - created_by_user_id: Who uploaded/processed this data
#
# Data Model:
#   - satellite_id: Which satellite (OPS-SAT, etc.)
#   - timestamp: When measurement was taken
#   - channel_data: JSON blob of all sensor readings
#     {"channel_1": [value1, value2, ...], "channel_2": [...]}
#   - created_by_user_id: Who uploaded this (audit trail)
#
# Why JSON for channel_data?
#   - Flexible: Can store any number of channels
#   - Easy to query: PostgreSQL has JSON operators
#   - Fast: Stored as single column, not 100 separate columns
# ============================================================================

class TelemetryData(Base):
    __tablename__ = 'telemetry_data'
    
    id = Column(Integer, primary_key=True)
    
    satellite_id = Column(String(50), nullable=False, index=True)
    # Which satellite this data came from
    
    timestamp = Column(DateTime, nullable=False, index=True)
    # When the measurement was taken
    
    channel_data = Column(JSON, nullable=False)
    # All sensor values as JSON: {"channel_1": [v1, v2, ...], ...}
    
    created_by_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    # Who uploaded this (audit trail)
    # ondelete='SET NULL': If user deleted, set to NULL (preserve data)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    created_by_user = relationship('User', back_populates='telemetry_uploads', foreign_keys=[created_by_user_id])
    anomalies = relationship('Anomaly', back_populates='telemetry_data', cascade='all, delete-orphan')
    
    # Index for common queries: "Get all telemetry for satellite between dates"
    __table_args__ = (
        Index('idx_telemetry_satellite_timestamp', 'satellite_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f'<TelemetryData {self.satellite_id} {self.timestamp}>'


# ============================================================================
# TABLE 5: ANOMALIES
# ============================================================================
# Purpose: Store detected faults in telemetry data
#
# Audit Trail:
#   - Which telemetry record had anomaly
#   - Anomaly score (0-1 probability)
#   - Threshold used (0.5, 0.7, etc.)
#   - Root causes (JSON): Top 3 likely faults
#   - Who detected it and when
#
# Why separate table from TelemetryData?
#   - Not every telemetry has anomaly
#   - Can query "all anomalies for satellite" without scanning 1M rows
#   - Easy to update if threshold changes (re-classify without re-ingesting)
# ============================================================================

class Anomaly(Base):
    __tablename__ = 'anomalies'
    
    id = Column(Integer, primary_key=True)
    
    telemetry_id = Column(Integer, ForeignKey('telemetry_data.id', ondelete='CASCADE'), nullable=False, index=True)
    # Which telemetry record this anomaly came from
    # ondelete='CASCADE': If telemetry deleted, also delete this anomaly
    
    anomaly_score = Column(Float, nullable=False)
    # FCNN probability (0-1): 0 = normal, 1 = definitely anomaly
    # Constraint: Must be between 0 and 1
    
    threshold_used = Column(Float, nullable=False, default=0.5)
    # Which threshold was used to classify
    
    is_confirmed = Column(Boolean, default=False, nullable=False)
    # Was this anomaly confirmed by engineer (vs. auto-detected)
    
    root_causes = Column(JSON, nullable=True)
    # Top likely causes from KG: [{"fault": "battery_voltage", "score": 0.8}, ...]
    
    explanation = Column(Text, nullable=True)
    # LLM-generated explanation of what went wrong
    
    detected_by_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    # Which engineer ran the diagnosis
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    confirmed_at = Column(DateTime, nullable=True)
    # When engineer confirmed this anomaly
    
    # Relationships
    telemetry_data = relationship('TelemetryData', back_populates='anomalies')
    detected_by_user = relationship('User', back_populates='anomaly_detections', foreign_keys=[detected_by_user_id])
    
    # Index for quick queries: "Get all anomalies detected by engineer alice"
    __table_args__ = (
        Index('idx_anomaly_telemetry_score', 'telemetry_id', 'anomaly_score'),
        CheckConstraint('anomaly_score >= 0 AND anomaly_score <= 1', name='check_anomaly_score_range'),
    )
    
    def __repr__(self):
        return f'<Anomaly {self.id} score={self.anomaly_score}>'


# ============================================================================
# TABLE 6: CHAT_SESSIONS
# ============================================================================
# Purpose: Track user conversations (audit trail)
#
# Why persist chat?
#   - Audit compliance: Show what was discussed
#   - User continuity: Return to previous conversations
#   - Analysis: See what users ask about most
#
# Session Lifecycle:
#   1. User logs in, creates new chat session
#   2. User sends messages, each stored with timestamp
#   3. If connection drops, session persists
#   4. User can view chat history even after logout
# ============================================================================

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    
    id = Column(Integer, primary_key=True)
    
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    # Which user this session belongs to
    # ondelete='CASCADE': If user deleted, also delete their chats
    
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    # Unique session identifier: "user_123_session_1715529600"
    
    title = Column(String(255), default="Untitled Chat", nullable=False)
    # User can name their chat sessions
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship('User', back_populates='chat_sessions')
    messages = relationship('ChatMessage', back_populates='session', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ChatSession {self.session_id}>'


# ============================================================================
# TABLE 7: CHAT_MESSAGES
# ============================================================================
# Purpose: Store individual messages in a chat session
#
# Structure:
#   - session_id: Which conversation
#   - role: 'user' or 'assistant' (who sent it)
#   - content: The actual message text
#   - created_at: When it was sent
#
# Example conversation:
#   user:      "What's causing the anomaly in channel 5?"
#   assistant: "Based on telemetry patterns, likely causes are..."
#   user:      "Show me the root causes"
#   assistant: [Diagnosis with JSON structure]
# ============================================================================

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    
    id = Column(Integer, primary_key=True)
    
    session_id = Column(Integer, ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    # Which session this message belongs to
    
    role = Column(String(20), nullable=False)
    # Who sent: 'user' or 'assistant'
    # Could use Enum for type safety: role = Column(SQLEnum(MessageRole), nullable=False)
    
    content = Column(Text, nullable=False)
    # The actual message text
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    session = relationship('ChatSession', back_populates='messages')
    
    # Index for efficient sorting: "Get messages for session 123 ordered by time"
    __table_args__ = (
        Index('idx_message_session_timestamp', 'session_id', 'created_at'),
    )
    
    def __repr__(self):
        return f'<ChatMessage session={self.session_id} role={self.role}>'


# ============================================================================
# SUMMARY OF TABLES AND RELATIONSHIPS
# ============================================================================
# 
# User Authentication & Authorization:
#   User → Role → Permissions (many-to-many)
#   Allows: "Does user 'alice' (engineer role) have 'diagnose_faults' permission?"
#
# Data Audit Trail:
#   Telemetry ← created_by_user_id → User
#   Anomaly ← detected_by_user_id → User
#   Allows: "Who uploaded this telemetry? Who detected this anomaly?"
#
# Chat History:
#   ChatSession ← user_id → User
#   ChatMessage ← session_id → ChatSession
#   Allows: "Show all messages in user's chat session 'diagnosis_may12'"
#
# Cascading Deletes:
#   Delete user → deletes their chat sessions → deletes their messages
#   Maintains referential integrity (no orphaned records)
#
# ============================================================================
