"""
Password hashing utilities using bcrypt directly.
Centralized so every module uses the same scheme.

Uses the `bcrypt` library directly instead of passlib to avoid
version incompatibility issues (passlib doesn't support bcrypt>=4.1).
"""
import bcrypt


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.
    
    Falls back to plaintext comparison for legacy un-hashed passwords,
    then the caller should auto-upgrade them to bcrypt via needs_rehash().
    """
    # If the stored password doesn't look like a bcrypt hash,
    # do a plaintext comparison (legacy support during migration)
    if not hashed_password.startswith("$2"):
        return plain_password == hashed_password
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Check if a password hash needs to be upgraded (e.g., legacy plaintext)."""
    if not hashed_password or not hashed_password.startswith("$2"):
        return True
    return False
