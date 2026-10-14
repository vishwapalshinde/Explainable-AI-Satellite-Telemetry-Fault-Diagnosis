"""
Change an existing user's role.

Usage examples:
  python backend/scripts/change_user_role.py --username alice --role engineer
  python backend/scripts/change_user_role.py --username bob --role admin
"""

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
SRC_DIR = os.path.join(BACKEND_DIR, "src")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from src.database import SessionLocal, User, Role


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Change user role")
    parser.add_argument("--username", required=True, help="Username to update")
    parser.add_argument(
        "--role",
        required=True,
        choices=["admin", "engineer", "viewer"],
        help="Target role",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.username == args.username.strip()).first()
        if not user:
            print(f"[ERROR] User not found: {args.username}")
            return 1

        role = db.query(Role).filter(Role.name == args.role).first()
        if not role:
            print(f"[ERROR] Role not found: {args.role}")
            return 1

        user.role_id = role.id
        db.commit()
        db.refresh(user)

        print("[OK] User role updated successfully")
        print(f"      username: {user.username}")
        print(f"      role: {user.role.name}")
        print(f"      email: {user.email}")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Failed to change role: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
