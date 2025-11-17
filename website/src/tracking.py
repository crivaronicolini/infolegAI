import asyncio
import sqlite3
import threading
from datetime import date
from pathlib import Path

from fastapi import Request


class UsageTracker:
    """Tracks per-IP/User-Agent usage counts per day in SQLite."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()

    def _connect(self) -> None:
        # Ensure parent directory exists
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            self._db_path, check_same_thread=False, isolation_level=None
        )
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")

    def _ensure_schema(self) -> None:
        assert self._conn is not None
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_events (
                  id INTEGER PRIMARY KEY,
                  ip_address TEXT NOT NULL,
                  user_agent TEXT NOT NULL,
                  date_key TEXT NOT NULL,
                  count INTEGER NOT NULL DEFAULT 0,
                  first_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE (ip_address, user_agent, date_key)
                );
                """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_usage_identity_day
                ON usage_events (ip_address, user_agent, date_key);
                """
            )

    async def start(self) -> None:
        await asyncio.to_thread(self._connect)
        await asyncio.to_thread(self._ensure_schema)

    async def close(self) -> None:
        if self._conn is None:
            return
        conn = self._conn
        self._conn = None
        await asyncio.to_thread(conn.close)

    def _today_key(self) -> str:
        return date.today().isoformat()

    async def get_today_count(self, ip_address: str, user_agent: str) -> int:
        assert self._conn is not None
        date_key = self._today_key()

        def _read() -> int:
            with self._lock:
                cur = self._conn.execute(
                    "SELECT count FROM usage_events WHERE ip_address=? AND user_agent=? AND date_key=?",
                    (ip_address, user_agent, date_key),
                )
                row = cur.fetchone()
                return int(row[0]) if row else 0

        return await asyncio.to_thread(_read)

    async def increment(self, ip_address: str, user_agent: str) -> int:
        """Increment today's count and return the new value."""
        assert self._conn is not None
        date_key = self._today_key()

        def _upsert() -> int:
            with self._lock:
                # Try single-step UPSERT with RETURNING (SQLite 3.35+)
                try:
                    cur = self._conn.execute(
                        """
                        INSERT INTO usage_events (ip_address, user_agent, date_key, count)
                        VALUES (?, ?, ?, 1)
                        ON CONFLICT(ip_address, user_agent, date_key)
                        DO UPDATE SET count = count + 1, last_seen = CURRENT_TIMESTAMP
                        RETURNING count
                        """,
                        (ip_address, user_agent, date_key),
                    )
                    row = cur.fetchone()
                    if row and row[0] is not None:
                        return int(row[0])
                except sqlite3.OperationalError:
                    # Fallback for older SQLite versions without RETURNING
                    self._conn.execute(
                        """
                        INSERT INTO usage_events (ip_address, user_agent, date_key, count)
                        VALUES (?, ?, ?, 1)
                        ON CONFLICT(ip_address, user_agent, date_key)
                        DO UPDATE SET count = count + 1, last_seen = CURRENT_TIMESTAMP
                        """,
                        (ip_address, user_agent, date_key),
                    )
                    cur2 = self._conn.execute(
                        "SELECT count FROM usage_events WHERE ip_address=? AND user_agent=? AND date_key=?",
                        (ip_address, user_agent, date_key),
                    )
                    row = cur2.fetchone()
                    return int(row[0]) if row else 1
                # If we got here, RETURNING succeeded but row missing; read explicitly
                cur2 = self._conn.execute(
                    "SELECT count FROM usage_events WHERE ip_address=? AND user_agent=? AND date_key=?",
                    (ip_address, user_agent, date_key),
                )
                row = cur2.fetchone()
                return int(row[0]) if row else 1

        return await asyncio.to_thread(_upsert)


def get_client_identity(request: Request) -> tuple[str, str]:
    """Extract IP address and User-Agent from request for rate limiting."""
    # Prefer X-Forwarded-For (first IP), then X-Real-IP, else client host
    xff = request.headers.get("x-forwarded-for", "")
    ip = (
        (xff.split(",")[0].strip() if xff else "")
        or request.headers.get("x-real-ip")
        or (request.client.host if request.client else "unknown")
    )
    ua = request.headers.get("user-agent", "unknown")
    return ip, ua

