"""
Google OAuth2 integration using authlib.

Provides the OAuth client setup and a helper to find/create
a user from a Google profile.
"""
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session
from app.config import settings
from app.models.user import User
from app.security import hash_password

oauth = OAuth()

# Register Google OAuth provider (only if credentials are configured)
if settings.GOOGLE_CLIENT_ID:
    oauth.register(
        name="google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def get_or_create_user_from_google(db: Session, google_user: dict) -> User | None:
    """
    Find an existing user by google_id or email, or create a new one.
    
    Args:
        db: Database session
        google_user: Dict from Google with keys like 'sub', 'email', 'name', 'picture'
    
    Returns:
        User instance (existing or newly created) or None if signup is restricted
    """
    google_id = google_user.get("sub")
    email = google_user.get("email")
    name = google_user.get("name", email)

    # 1. Try to find by google_id (already linked)
    user = db.query(User).filter(User.google_id == google_id).first()
    if user:
        return user

    # 2. Try to find by email (link existing account/invited account)
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.google_id = google_id
        if google_user.get("picture") and not user.profile_photo_url:
            user.profile_photo_url = google_user["picture"]
        db.commit()
        db.refresh(user)
        return user

    # 3. Create new user — ONLY if no users exist in the system (first run)
    user_count = db.query(User).count()
    if user_count == 0:
        user = User(
            email=email,
            name=name,
            role="admin",  # First user gets Admin role
            google_id=google_id,
            profile_photo_url=google_user.get("picture"),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # Otherwise, new registrations are closed
    return None
