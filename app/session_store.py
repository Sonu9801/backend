"""
Server-side session store backed by Redis with seamless in-memory fallback.

Sessions survive container restarts, hot-reloads, and deployments when Redis is available.
If Redis is down, fails authentication, or times out, it gracefully falls back to in-memory storage
so user authentication/login never crashes with a 500 error.

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
    """Try to connect to Redis. Returns None if unavailable or auth fails."""
    try:
        import redis
        import socket
        from app.config import settings
        try:
            client = redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2.0,
                socket_timeout=2.0,
                retry_on_timeout=False,
                protocol=2,  # Force RESP2 to prevent HELLO handshake NOAUTH issues
            )
            client.ping()
            logger.info(f"[SessionStore] Connected to Redis at {settings.REDIS_URL} successfully.")
            return client
        except Exception as e:
            if "redis:6379" in settings.REDIS_URL:
                fallback_url = settings.REDIS_URL.replace("redis:6379", "localhost:6379")
                try:
                    client = redis.Redis.from_url(
                        fallback_url,
                        decode_responses=True,
                        socket_connect_timeout=1.0,
                        socket_timeout=1.0,
                        retry_on_timeout=False,
                        protocol=2,
                    )
                    client.ping()
                    logger.info(f"[SessionStore] Connected to Redis fallback {fallback_url} successfully.")
                    return client
                except Exception:
                    pass
            logger.warning(f"[SessionStore] Redis unavailable or auth failed ({e}). Falling back to in-memory sessions.")
            return None
    except Exception as exc:
        logger.warning(f"[SessionStore] Redis initialization failed ({exc}). Falling back to in-memory sessions.")
        return None


class InMemorySessionStore:
    """Fallback in-memory session store."""

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


class RedisSessionStore:
    """Redis-backed session store with TTL and automatic in-memory fallback."""

    def __init__(self, redis_client):
        self._redis = redis_client
        self._fallback = InMemorySessionStore()

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
        try:
            pipe = self._redis.pipeline()
            pipe.setex(f"session:{session_id}", ttl_seconds, json.dumps(session_data))
            pipe.sadd(f"user_sessions:{user_id}", session_id)
            pipe.expire(f"user_sessions:{user_id}", ttl_seconds)
            pipe.execute()
        except Exception as e:
            logger.warning(f"[SessionStore] Redis error in create_session ({e}). Storing session in fallback memory.")
            self._fallback._sessions[session_id] = session_data
            if user_id not in self._fallback._user_sessions:
                self._fallback._user_sessions[user_id] = set()
            self._fallback._user_sessions[user_id].add(session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        try:
            data = self._redis.get(f"session:{session_id}")
            if data is not None:
                try:
                    session = json.loads(data)
                    expires_at = datetime.fromisoformat(session["expires_at"])
                    if datetime.utcnow() > expires_at:
                        self.invalidate_session(session_id)
                        return None
                    return session
                except (json.JSONDecodeError, KeyError):
                    return None
        except Exception as e:
            logger.warning(f"[SessionStore] Redis error in get_session ({e}). Checking fallback memory.")
        return self._fallback.get_session(session_id)

    def invalidate_session(self, session_id: str) -> bool:
        fallback_res = self._fallback.invalidate_session(session_id)
        try:
            data = self._redis.get(f"session:{session_id}")
            if data:
                try:
                    session = json.loads(data)
                    user_id = session.get("user_id")
                    if user_id:
                        self._redis.srem(f"user_sessions:{user_id}", session_id)
                except (json.JSONDecodeError, KeyError):
                    pass
            redis_res = bool(self._redis.delete(f"session:{session_id}"))
            return redis_res or fallback_res
        except Exception as e:
            logger.warning(f"[SessionStore] Redis error in invalidate_session ({e}).")
            return fallback_res

    def invalidate_all_user_sessions(self, user_id: int) -> int:
        count = self._fallback.invalidate_all_user_sessions(user_id)
        try:
            session_ids = self._redis.smembers(f"user_sessions:{user_id}")
            if session_ids:
                pipe = self._redis.pipeline()
                for sid in session_ids:
                    pipe.delete(f"session:{sid}")
                    count += 1
                pipe.delete(f"user_sessions:{user_id}")
                pipe.execute()
        except Exception as e:
            logger.warning(f"[SessionStore] Redis error in invalidate_all_user_sessions ({e}).")
        return count

    def get_active_session_count(self, user_id: int) -> int:
        try:
            session_ids = self._redis.smembers(f"user_sessions:{user_id}")
            count = 0
            for sid in session_ids:
                if self._redis.exists(f"session:{sid}"):
                    count += 1
            if count > 0:
                return count
        except Exception as e:
            logger.warning(f"[SessionStore] Redis error in get_active_session_count ({e}).")
        return self._fallback.get_active_session_count(user_id)

    def cleanup_expired(self) -> int:
        count = 0
        try:
            count += self._fallback.cleanup_expired()
        except Exception:
            pass
        return count


def _create_session_store():
    """Factory: Redis if available, else in-memory fallback."""
    redis_client = _get_redis_client()
    if redis_client:
        return RedisSessionStore(redis_client)
    return InMemorySessionStore()


# Global singleton
session_store = _create_session_store()
