"""
Database Initialization Script

This script:
  1. Creates all tables in PostgreSQL
  2. Inserts default roles (admin, engineer, viewer)
  3. Inserts default permissions
  4. Assigns permissions to roles

Run once after setting up PostgreSQL:
  python backend/scripts/init_db.py

This creates the initial database schema with:
  - 3 Roles: admin (full access), engineer (diagnose+chat), viewer (read-only)
  - 6 Permissions: view_telemetry, diagnose_faults, chat, download_data, manage_users, manage_roles
  - Role-Permission assignments
"""

import sys
import os

# Add backend and backend/src to path so imports work from the repo root
SCRIPT_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
SRC_DIR = os.path.join(BACKEND_DIR, 'src')
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, SRC_DIR)

from sqlalchemy.orm import Session
from src.database import (
    create_all_tables, 
    SessionLocal, 
    Role, 
    Permission,
    engine
)

# ============================================================================
# PERMISSIONS DEFINITION
# ============================================================================
# 
# Define all permissions available in the system
# Each permission represents an action a user can perform
# 
# ============================================================================

PERMISSIONS_LIST = [
    {
        "name": "view_telemetry",
        "description": "Can view satellite telemetry data and dashboard"
    },
    {
        "name": "diagnose_faults",
        "description": "Can run fault detection and get diagnosis"
    },
    {
        "name": "chat",
        "description": "Can chat with AI diagnosis assistant"
    },
    {
        "name": "download_data",
        "description": "Can download/export telemetry and analysis results"
    },
    {
        "name": "manage_users",
        "description": "Can create/edit/delete users (admin only)"
    },
    {
        "name": "manage_roles",
        "description": "Can modify role permissions (admin only)"
    },
]

# ============================================================================
# ROLES DEFINITION
# ============================================================================
# 
# Define roles and their permissions
# 
# RBAC Matrix:
#   Permission          | Admin | Engineer | Viewer
#   -------------------|-------|----------|--------
#   view_telemetry      |   ✓   |    ✓     |   ✓
#   diagnose_faults     |   ✓   |    ✓     |   ✗
#   chat                |   ✓   |    ✓     |   ✗
#   download_data       |   ✓   |    ✓     |   ✗
#   manage_users        |   ✓   |    ✗     |   ✗
#   manage_roles        |   ✓   |    ✗     |   ✗
#
# Admin: Full access (all 6 permissions)
#   - Created first system admin user
#   - Full system management
#   - Can create other admins
#
# Engineer: Can diagnose and chat (4 permissions)
#   - Created by admin
#   - Can view telemetry, diagnose, chat, download
#   - Cannot manage users or roles
#   - Most satellite operations team members have this role
#
# Viewer: Read-only (1 permission)
#   - Can only view dashboard
#   - Good for stakeholders, managers, external teams
#   - Cannot modify anything
# 
# ============================================================================

ROLES_LIST = [
    {
        "name": "admin",
        "description": "Full system access with user management",
        "permissions": [
            "view_telemetry",
            "diagnose_faults",
            "chat",
            "download_data",
            "manage_users",
            "manage_roles"
        ]
    },
    {
        "name": "engineer",
        "description": "Can diagnose faults and chat with AI",
        "permissions": [
            "view_telemetry",
            "diagnose_faults",
            "chat",
            "download_data"
        ]
    },
    {
        "name": "viewer",
        "description": "Read-only access to dashboard",
        "permissions": [
            "view_telemetry"
        ]
    },
]


# ============================================================================
# INITIALIZATION FUNCTION
# ============================================================================

def init_database():
    """
    Initialize database with default roles and permissions.
    
    Steps:
      1. Create all tables
      2. Check if already initialized (to prevent duplicates)
      3. Insert permissions
      4. Insert roles
      5. Link permissions to roles
    """
    
    print("=" * 70)
    print("DATABASE INITIALIZATION")
    print("=" * 70)
    
    # Step 1: Create tables
    print("\n[1/5] Creating database tables...")
    try:
        create_all_tables()
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        return False
    
    db = SessionLocal()
    
    try:
        # Step 2: Check if already initialized
        existing_roles = db.query(Role).count()
        if existing_roles > 0:
            print("⚠ Database already initialized (roles exist)")
            response = input("Do you want to reinitialize? (yes/no): ")
            if response.lower() != 'yes':
                print("Cancelling initialization")
                return True
            else:
                print("Reinitializing...")
        
        # Step 3: Insert permissions
        print("\n[2/5] Creating permissions...")
        permission_objects = {}
        for perm_data in PERMISSIONS_LIST:
            # Check if permission already exists
            existing_perm = db.query(Permission).filter(
                Permission.name == perm_data["name"]
            ).first()
            
            if existing_perm:
                permission_objects[perm_data["name"]] = existing_perm
                print(f"  ✓ Permission '{perm_data['name']}' already exists")
            else:
                perm = Permission(
                    name=perm_data["name"],
                    description=perm_data["description"]
                )
                db.add(perm)
                permission_objects[perm_data["name"]] = perm
                print(f"  ✓ Created permission '{perm_data['name']}'")
        
        db.commit()
        
        # Step 4: Insert roles
        print("\n[3/5] Creating roles...")
        role_objects = {}
        for role_data in ROLES_LIST:
            # Check if role already exists
            existing_role = db.query(Role).filter(
                Role.name == role_data["name"]
            ).first()
            
            if existing_role:
                role_objects[role_data["name"]] = existing_role
                print(f"  ✓ Role '{role_data['name']}' already exists")
            else:
                role = Role(
                    name=role_data["name"],
                    description=role_data["description"]
                )
                db.add(role)
                role_objects[role_data["name"]] = role
                print(f"  ✓ Created role '{role_data['name']}'")
        
        db.commit()
        
        # Step 5: Link permissions to roles
        print("\n[4/5] Assigning permissions to roles...")
        for role_data in ROLES_LIST:
            role = role_objects[role_data["name"]]
            for perm_name in role_data["permissions"]:
                perm = permission_objects[perm_name]
                
                # Check if already linked
                if perm not in role.permissions:
                    role.permissions.append(perm)
                    print(f"  ✓ Assigned '{perm_name}' to '{role_data['name']}'")
                else:
                    print(f"  ✓ '{perm_name}' already assigned to '{role_data['name']}'")
        
        db.commit()
        
        # Step 6: Summary
        print("\n[5/5] Database initialization complete!")
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Roles created:       {len(ROLES_LIST)}")
        print(f"Permissions created: {len(PERMISSIONS_LIST)}")
        print("\nRole-Permission Matrix:")
        for role_data in ROLES_LIST:
            perms = ", ".join(role_data["permissions"])
            print(f"  {role_data['name']:15} → {perms}")
        print("\n" + "=" * 70)
        print("Next Steps:")
        print("  1. Start PostgreSQL: docker-compose up -d postgres")
        print("  2. Run this script: python backend/scripts/init_db.py")
        print("  3. Create first admin user (next step)")
        print("=" * 70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during initialization: {e}")
        db.rollback()
        return False
    finally:
        db.close()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
