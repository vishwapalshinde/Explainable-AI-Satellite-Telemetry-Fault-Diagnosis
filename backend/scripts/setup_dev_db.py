"""
Development Database Setup - SQLite Version

Creates a local SQLite database for development when PostgreSQL is not available.
This allows testing authentication without Docker.

Run:
  cd backend
  python scripts/setup_dev_db.py
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, Permission, Role, User
from src.utils.security import hash_password

# SQLite database file
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'dev.db')

def setup_dev_database():
    """Setup SQLite database for development"""
    print(f"\n📦 Setting up development database at {DB_PATH}")
    
    # Remove old database if exists
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("✓ Removed old database")
    
    # Create engine and tables
    engine = create_engine(f'sqlite:///{DB_PATH}')
    Base.metadata.create_all(engine)
    print("✓ Created all tables")
    
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 1. Create Permissions
        permissions = [
            Permission(name="view_telemetry", description="View telemetry data"),
            Permission(name="diagnose_faults", description="Run diagnosis"),
            Permission(name="chat", description="Chat with diagnosis engine"),
            Permission(name="download_data", description="Download data exports"),
            Permission(name="manage_users", description="Manage system users"),
            Permission(name="manage_roles", description="Manage roles and permissions"),
        ]
        session.add_all(permissions)
        session.commit()
        print(f"✓ Created {len(permissions)} permissions")
        
        # 2. Create Roles
        admin_role = Role(
            name="admin",
            description="Administrator with full access"
        )
        engineer_role = Role(
            name="engineer",
            description="Engineer with analysis and chat access"
        )
        viewer_role = Role(
            name="viewer",
            description="Viewer with read-only access"
        )
        
        session.add_all([admin_role, engineer_role, viewer_role])
        session.commit()
        print(f"✓ Created 3 roles: admin, engineer, viewer")
        
        # 3. Assign Permissions to Roles
        perms = {p.name: p for p in session.query(Permission).all()}
        
        # Admin: all permissions
        admin_role.permissions = list(perms.values())
        
        # Engineer: everything except user/role management
        engineer_role.permissions = [
            perms["view_telemetry"],
            perms["diagnose_faults"],
            perms["chat"],
            perms["download_data"],
        ]
        
        # Viewer: read-only
        viewer_role.permissions = [perms["view_telemetry"]]
        
        session.commit()
        print("✓ Assigned permissions to roles")
        
        # 4. Create Admin User
        admin_user = User(
            username="admin",
            email="admin@satellite.gov",
            password_hash=hash_password("Admin@123456"),
            role_id=admin_role.id,
            is_active=True
        )
        
        session.add(admin_user)
        session.commit()
        print(f"\n✅ Created admin user:")
        print(f"   Username: admin")
        print(f"   Password: Admin@123456")
        print(f"   Email: admin@satellite.gov")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        session.close()
    
    print(f"\n✅ Database ready: {DB_PATH}")
    print(f"   Use: SQLALCHEMY_DATABASE_URL=sqlite:///{DB_PATH}")
    return DB_PATH


if __name__ == "__main__":
    setup_dev_database()
