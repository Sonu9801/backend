"""
One-time migration script to hash all existing plaintext passwords.

Safe to run multiple times — detects already-hashed passwords and skips them.

Usage:
    python migrate_passwords.py
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User
from app.security import hash_password, needs_rehash


def migrate_passwords():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        migrated = 0
        skipped = 0
        no_password = 0

        for user in users:
            if not user.password:
                no_password += 1
                print(f"  SKIP (no password): {user.email or user.mobile_number or f'id={user.id}'}")
                continue

            if needs_rehash(user.password):
                plain = user.password
                user.password = hash_password(plain)
                migrated += 1
                print(f"  HASHED: {user.email or user.mobile_number or f'id={user.id}'}")
            else:
                skipped += 1
                print(f"  SKIP (already hashed): {user.email or user.mobile_number or f'id={user.id}'}")

        db.commit()
        print(f"\n{'='*50}")
        print(f"  Migration Complete")
        print(f"  Hashed: {migrated}")
        print(f"  Already hashed (skipped): {skipped}")
        print(f"  No password (skipped): {no_password}")
        print(f"  Total users: {len(users)}")
        print(f"{'='*50}")

    except Exception as e:
        db.rollback()
        print(f"ERROR: Migration failed — {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("="*50)
    print("  Password Migration: Plaintext -> bcrypt")
    print("="*50)
    migrate_passwords()
