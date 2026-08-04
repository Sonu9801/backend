"""
Server-side session store backed by Redis.

Sessions survive container restarts, hot-reloads, and deployments.
Falls back to in-memory storage if Redis is unavailable (dev mode).

Each session stores:
  - session_id (UUID)
  - user_id
  - role
  - created_at
  - expires_at
  - metadata (device info, IP, etc.)
"""
import uuid
import json
import threading
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("uvicorn.error")


def _get_redis_client():
    """Try to connect to Redis. Returns None if unavailable."""
    try:
        import redis
        from app.config import settings
        try:
            client = redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=True,
            )
            client.ping()
            logger.info(f"[SessionStore] Connected to Redis at {settings.REDIS_URL} successfully.")
            return client
        except (redis.ConnectionError, redis.TimeoutError) as e:
            if "redis:6379" in settings.REDIS_URL:
                fallback_url = settings.REDIS_URL.replace("redis:6379", "localhost:6379")
                logger.info(f"[SessionStore] Failed to connect to {settings.REDIS_URL}, trying fallback {fallback_url}...")
                client = redis.Redis.from_url(
                    fallback_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                    retry_on_timeout=True,
                )
                client.ping()
                logger.info(f"[SessionStore] Connected to Redis fallback {fallback_url} successfully.")
                return client
            raise e
    except Exception as e:
        logger.warning(f"[SessionStore] Redis unavailable ({e}). Falling back to in-memory sessions.")
        return None


class RedisSessionStore:
    """Redis-backed session store with TTL. Enterprise-grade persistence."""

    def __init__(self, redis_client):
        self._redis = redis_client

    def create_session(
        self,
        user_id: int,
        role: str,
        ttl_days: int = 30,
        metadata: Optional[dict] = None,
    ) -> str:
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        ttl_seconds = ttl_days * 86400
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "role": role,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(days=ttl_days)).isoformat(),
            "metadata": metadata or {},
        }
        pipe = self._redis.pipeline()
        pipe.setex(f"session:{session_id}", ttl_seconds, json.dumps(session_data))
        pipe.sadd(f"user_sessions:{user_id}", session_id)
        pipe.expire(f"user_sessions:{user_id}", ttl_seconds)
        pipe.execute()
        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        data = self._redis.get(f"session:{session_id}")
        if data is None:
            return None
        try:
            session = json.loads(data)
            expires_at = datetime.fromisoformat(session["expires_at"])
            if datetime.utcnow() > expires_at:
                self.invalidate_session(session_id)
                return None
            return session
        except (json.JSONDecodeError, KeyError):
            return None

    def invalidate_session(self, session_id: str) -> bool:
        data = self._redis.get(f"session:{session_id}")
        if data:
            try:
                session = json.loads(data)
                user_id = session.get("user_id")
                if user_id:
                    self._redis.srem(f"user_sessions:{user_id}", session_id)
            except (json.JSONDecodeError, KeyError):
                pass
        return bool(self._redis.delete(f"session:{session_id}"))

    def invalidate_all_user_sessions(self, user_id: int) -> int:
        session_ids = self._redis.smembers(f"user_sessions:{user_id}")
        count = 0
        if session_ids:
            pipe = self._redis.pipeline()
            for sid in session_ids:
                pipe.delete(f"session:{sid}")
                count += 1
            pipe.delete(f"user_sessions:{user_id}")
            pipe.execute()
        return count

    def get_active_session_count(self, user_id: int) -> int:
        session_ids = self._redis.smembers(f"user_sessions:{user_id}")
        count = 0
        for sid in session_ids:
            if self._redis.exists(f"session:{sid}"):
                count += 1
        return count

    def cleanup_expired(self) -> int:
        return 0  # Redis TTL handles this automatically


class InMemorySessionStore:
    """Fallback in-memory session store (original implementation)."""

    def __init__(self):
        self._sessions: dict[str, dict] = {}
        self._user_sessions: dict[int, set[str]] = {}
        self._lock = threading.Lock()

    def create_session(
        self,
        user_id: int,
        role: str,
        ttl_days: int = 30,
        metadata: Optional[dict] = None,
    ) -> str:
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
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            expires_at = datetime.fromisoformat(session["expires_at"])
            if datetime.utcnow() > expires_at:
                self._remove_session_unlocked(session_id)
                return None
            return session.copy()

    def invalidate_session(self, session_id: str) -> bool:
        with self._lock:
            return self._remove_session_unlocked(session_id)

    def invalidate_all_user_sessions(self, user_id: int) -> int:
        with self._lock:
            session_ids = self._user_sessions.pop(user_id, set())
            count = 0
            for sid in session_ids:
                if sid in self._sessions:
                    del self._sessions[sid]
                    count += 1
            return count

    def get_active_session_count(self, user_id: int) -> int:
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

    def cleanup_expired(self) -> int:
        now = datetime.utcnow()
        expired = []
        with self._lock:
            for sid, session in self._sessions.items():
                if datetime.fromisoformat(session["expires_at"]) < now:
                    expired.append(sid)
            for sid in expired:
                self._remove_session_unlocked(sid)
        return len(expired)

    def _remove_session_unlocked(self, session_id: str) -> bool:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return False
        user_id = session["user_id"]
        if user_id in self._user_sessions:
            self._user_sessions[user_id].discard(session_id)
            if not self._user_sessions[user_id]:
                del self._user_sessions[user_id]
        return True


def _create_session_store():
    """Factory: Redis if available, else in-memory fallback."""
    redis_client = _get_redis_client()
    if redis_client:
        return RedisSessionStore(redis_client)
    return InMemorySessionStore()


# Global singleton
session_store = _create_session_store()
