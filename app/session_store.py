"""
Server-side session store with TTL-based expiration.

Uses an in-memory dictionary for single-server deployments.
The interface is designed so swapping to Redis is a ~5-line change.

Each session stores:
  - session_id (UUID)
  - user_id
  - role
  - created_at
  - expires_at
  - metadata (device info, IP, etc.)
"""
import uuid
import threading
from datetime import datetime, timedelta
from typing import Optional


class SessionStore:
    """Thread-safe in-memory session store with TTL."""

    def __init__(self):
        self._sessions: dict[str, dict] = {}
        self._user_sessions: dict[int, set[str]] = {}  # user_id -> {session_ids}
        self._lock = threading.Lock()

    def create_session(
        self,
        user_id: int,
        role: str,
        ttl_days: int = 30,
        metadata: Optional[dict] = None,
    ) -> str:
        """Create a new session and return the session_id."""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "role": role,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(days=ttl_days)).isoformat(),
            "metadata": metadata or {},
        }
        with self._lock:
            self._sessions[session_id] = session_data
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = set()
            self._user_sessions[user_id].add(session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve a session. Returns None if expired or not found."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            # Check expiration
            expires_at = datetime.fromisoformat(session["expires_at"])
            if datetime.utcnow() > expires_at:
                self._remove_session_unlocked(session_id)
                return None
            return session.copy()

    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate (delete) a single session. Returns True if it existed."""
        with self._lock:
            return self._remove_session_unlocked(session_id)

    def invalidate_all_user_sessions(self, user_id: int) -> int:
        """Invalidate all sessions for a user. Returns count of invalidated sessions."""
        with self._lock:
            session_ids = self._user_sessions.pop(user_id, set())
            count = 0
            for sid in session_ids:
                if sid in self._sessions:
                    del self._sessions[sid]
                    count += 1
            return count

    def cleanup_expired(self) -> int:
        """Remove all expired sessions. Returns count of cleaned sessions."""
        now = datetime.utcnow()
        expired = []
        with self._lock:
            for sid, session in self._sessions.items():
                if datetime.fromisoformat(session["expires_at"]) < now:
                    expired.append(sid)
            for sid in expired:
                self._remove_session_unlocked(sid)
        return len(expired)

    def get_active_session_count(self, user_id: int) -> int:
        """Get number of active sessions for a user."""
        with self._lock:
            session_ids = self._user_sessions.get(user_id, set())
            count = 0
            for sid in session_ids:
                session = self._sessions.get(sid)
                if session:
                    expires_at = datetime.fromisoformat(session["expires_at"])
                    if datetime.utcnow() <= expires_at:
                        count += 1
            return count

    def _remove_session_unlocked(self, session_id: str) -> bool:
        """Remove a session (must hold _lock). Returns True if found."""
        session = self._sessions.pop(session_id, None)
        if session is None:
            return False
        user_id = session["user_id"]
        if user_id in self._user_sessions:
            self._user_sessions[user_id].discard(session_id)
            if not self._user_sessions[user_id]:
                del self._user_sessions[user_id]
        return True


# Global singleton
session_store = SessionStore()
