"""
Create First Admin User

After running init_db.py, run this script to create the first system administrator.

Usage:
  python backend/scripts/create_admin.py

Prompts for:
  - Username (e.g., alice)
  - Email (e.g., alice@satellite.gov)
  - Password (will be hashed with bcrypt)

Security Notes:
  - Passwords NEVER stored in plain text
  - Uses bcrypt: one-way hash function
  - During login: bcrypt.verify(entered_password, stored_hash) = True/False
  - bcrypt is slow on purpose (prevents brute force attacks)
  
Example Flow:
  1. User enters password "MySecurePass123"
  2. bcrypt hashes it to "$2b$12$R9h/cIPz0gi.URNNX3kh2..."
  3. Hash stored in database
  4. On login, bcrypt compares entered password with hash
  5. Takes ~0.1 seconds (intentional - stops attackers from trying 1M passwords/second)
"""

import sys
import os
import re
from getpass import getpass  # Hide password input from terminal
SCRIPT_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
SRC_DIR = os.path.join(BACKEND_DIR, 'src')
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, SRC_DIR)


# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from src.database import SessionLocal, User, Role
from utils.security import hash_password

# ============================================================================
# INPUT VALIDATION
# ============================================================================

def validate_username(username: str) -> bool:
    """
    Validate username format.
    
    Rules:
      - 3-50 characters
      - Only letters, numbers, underscore
      - Cannot start with number
    """
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_]{2,49}$'
    return bool(re.match(pattern, username))


def validate_email(email: str) -> bool:
    """
    Validate email format.
    
    Simple check: contains @ and .
    Production: use email-validator library
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    
    Rules:
      - At least 8 characters
      - At least one uppercase letter
      - At least one lowercase letter
      - At least one digit
      - At least one special character
    
    Returns:
      (is_valid, error_message)
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("Password must contain lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain digit")
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        errors.append("Password must contain special character")
    
    if errors:
        return False, "\n".join(errors)
    return True, ""


# ============================================================================
# USER CREATION
# ============================================================================

def create_admin_user():
    """
    Interactive prompt to create first admin user.
    
    Flow:
      1. Get admin role from database
      2. Prompt for username/email/password with validation
      3. Hash password with bcrypt
      4. Create user in database
      5. Confirm creation
    """
    
    print("=" * 70)
    print("CREATE FIRST ADMIN USER")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        # Check if admin already exists
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            print("✗ Admin role not found. Please run init_db.py first.")
            return False
        
        existing_admin = db.query(User).filter(User.role_id == admin_role.id).first()
        if existing_admin:
            print(f"⚠ Admin user already exists: {existing_admin.username}")
            response = input("Create another admin? (yes/no): ")
            if response.lower() != 'yes':
                return False
        
        # Get username
        print("\n[1/4] Enter username")
        print("  - 3-50 characters")
        print("  - Letters, numbers, underscore only")
        print("  - Must start with letter or underscore")
        while True:
            username = input("Username: ").strip()
            
            # Check if already exists
            existing_user = db.query(User).filter(
                User.username == username
            ).first()
            if existing_user:
                print(f"  ✗ Username '{username}' already taken")
                continue
            
            # Validate format
            if not validate_username(username):
                print("  ✗ Invalid username format")
                continue
            
            print(f"  ✓ Username '{username}' accepted")
            break
        
        # Get email
        print("\n[2/4] Enter email")
        while True:
            email = input("Email: ").strip()
            
            # Check if already exists
            existing_email = db.query(User).filter(
                User.email == email
            ).first()
            if existing_email:
                print(f"  ✗ Email '{email}' already used")
                continue
            
            # Validate format
            if not validate_email(email):
                print("  ✗ Invalid email format")
                continue
            
            print(f"  ✓ Email '{email}' accepted")
            break
        
        # Get password
        print("\n[3/4] Enter password")
        print("  - At least 8 characters")
        print("  - Must include: uppercase, lowercase, digit, special char")
        print("  - Example: MyPass123!")
        while True:
            password = getpass("Password (hidden): ")
            
            # Validate password strength
            is_valid, error_msg = validate_password(password)
            if not is_valid:
                print(f"  ✗ Password too weak:")
                for line in error_msg.split('\n'):
                    print(f"    - {line}")
                continue
            
            # Confirm password
            confirm_password = getpass("Confirm password (hidden): ")
            if password != confirm_password:
                print("  ✗ Passwords do not match")
                continue
            
            print("  ✓ Password accepted")
            break
        
        # Hash password using bcrypt
        print("\n[4/4] Hashing password...")
        password_hash = hash_password(password)
        print("  ✓ Password securely hashed")
        
        # Create user
        print("\nCreating admin user...")
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            role_id=admin_role.id,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print("\n" + "=" * 70)
        print("✓ ADMIN USER CREATED SUCCESSFULLY")
        print("=" * 70)
        print(f"Username:  {user.username}")
        print(f"Email:     {user.email}")
        print(f"Role:      admin")
        print(f"Active:    Yes")
        print(f"Created:   {user.created_at}")
        print("\n" + "=" * 70)
        print("Next Steps:")
        print("  1. Start backend: python backend/app.py")
        print("  2. Login with username and password above")
        print("  3. Create more users from admin panel")
        print("=" * 70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"✗ Error creating admin user: {e}")
        db.rollback()
        return False
    finally:
        db.close()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    success = create_admin_user()
    sys.exit(0 if success else 1)
