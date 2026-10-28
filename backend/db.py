"""Database connections for local development and PostgreSQL deployments.

Local development deliberately defaults to SQLite so the application can be
run without a Supabase project.  PostgreSQL remains available by setting
``DATABASE_BACKEND=postgres`` (or by running in a production environment).
"""

import os
import re
import sqlite3
import threading
import weakref
from pathlib import Path
from time import monotonic

import psycopg
try:
    from psycopg_pool import ConnectionPool
except ImportError:  # Local installs can continue using the direct connection.
    ConnectionPool = None
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Load the repository-root .env during local development. Environment values
# configured by a deployment platform take precedence over this optional file.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_SCHEMA_PATH = Path(__file__).resolve().parent / "local_schema.sql"
_local_schema_lock = threading.Lock()
_local_schema_ready: set[str] = set()
_postgres_pool = None
_postgres_pool_lock = threading.Lock()
_postgres_check_times = weakref.WeakKeyDictionary()
_postgres_check_lock = threading.Lock()


def _check_postgres_connection(connection):
    """Check pooled connections periodically instead of adding a DB roundtrip to every request."""
    now = monotonic()
    interval = max(1.0, float(os.getenv("DB_CONNECTION_CHECK_INTERVAL", "30")))
    with _postgres_check_lock:
        checked_at = _postgres_check_times.get(connection)
        if checked_at is None:
            # A newly created pool connection is already known to be live.
            _postgres_check_times[connection] = now
            return
        if now - checked_at < interval:
            return

    try:
        ConnectionPool.check_connection(connection)
    except Exception:
        with _postgres_check_lock:
            _postgres_check_times.pop(connection, None)
        raise
    with _postgres_check_lock:
        _postgres_check_times[connection] = now


class PooledConnection:
    """Return a serverless request's connection to the warm process pool."""

    def __init__(self, pool, connection):
        self._pool = pool
        self._connection = connection
        self._returned = False

    def __getattr__(self, name):
        return getattr(self._connection, name)

    def close(self):
        if not self._returned:
            self._returned = True
            self._pool.putconn(self._connection)


class DatabaseConnectionError(RuntimeError):
    """Safe database connection error that never includes the connection URL."""


class SQLiteCursor:
    """Small psycopg-shaped cursor wrapper used by the existing route code."""

    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False

    @staticmethod
    def _translate(query):
        query = query.replace("%s", "?")
        query = re.sub(
            r"NOW\(\)\s*-\s*INTERVAL\s+'1 hour'",
            "datetime('now', '-1 hour')",
            query,
            flags=re.IGNORECASE,
        )
        return re.sub(r"NOW\(\)", "CURRENT_TIMESTAMP", query, flags=re.IGNORECASE)

    def execute(self, query, params=()):
        return self._cursor.execute(self._translate(query), tuple(params or ()))

    def executemany(self, query, params):
        return self._cursor.executemany(
            self._translate(query), [tuple(values) for values in params]
        )

    def fetchone(self):
        row = self._cursor.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self):
        return [dict(row) for row in self._cursor.fetchall()]

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    def close(self):
        self._cursor.close()


class SQLiteConnection:
    """Connection wrapper exposing the subset of the psycopg API used here."""

    def __init__(self, path):
        self._connection = sqlite3.connect(
            path,
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")

    def cursor(self):
        return SQLiteCursor(self._connection.cursor())

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()


def database_backend():
    """Return ``sqlite`` for local development or ``postgres`` explicitly."""
    configured = os.getenv("DATABASE_BACKEND", "").strip().lower()
    if configured in {"postgres", "postgresql", "supabase"}:
        return "postgres"
    if configured in {"sqlite", "local"}:
        return "sqlite"
    # Vercel Preview deployments also need the configured Supabase database.
    # Without this branch, Preview falls through to the local SQLite default,
    # which is not persistent and is not the deployed application's database.
    if os.getenv("VERCEL_ENV", "").lower() in {"preview", "production"} and os.getenv("SUPABASE_DB_URL"):
        return "postgres"
    if os.getenv("APP_ENV", "development").lower() == "production":
        return "postgres"
    return "sqlite"


def local_database_path():
    configured = os.getenv("LOCAL_DB_PATH", "").strip()
    path = Path(configured) if configured else PROJECT_ROOT / "backend" / "fitness_tracker.sqlite3"
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def initialize_local_database():
    """Create/update the local SQLite schema without deleting existing data."""
    path = local_database_path()
    key = str(path.resolve())
    with _local_schema_lock:
        if key not in _local_schema_ready:
            connection = sqlite3.connect(path)
            try:
                connection.execute("PRAGMA foreign_keys = ON")
                connection.executescript(LOCAL_SCHEMA_PATH.read_text(encoding="utf-8"))
                admin_columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(admins)").fetchall()
                }
                if "is_active" not in admin_columns:
                    connection.execute(
                        "ALTER TABLE admins ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
                    )
                _migrate_legacy_local_accounts(connection, path)
                connection.commit()
                _local_schema_ready.add(key)
            finally:
                connection.close()
    return path


def _migrate_legacy_local_accounts(connection, current_path):
    """Import accounts from the pre-Supabase local database when present.

    Older checkouts stored administrator accounts in ``users`` in
    ``backend/data/fitness_tracker.db``.  The current schema separates
    administrators into ``admins``; without this compatibility step the new
    database starts empty and password recovery always reports an unknown
    account after an upgrade.

    The migration is intentionally additive: it only inserts emails that do
    not already exist in the current database and never removes or updates
    either database.
    """
    legacy_path = PROJECT_ROOT / "backend" / "data" / "fitness_tracker.db"
    if legacy_path.resolve() == Path(current_path).resolve() or not legacy_path.is_file():
        return

    legacy = sqlite3.connect(str(legacy_path))
    legacy.row_factory = sqlite3.Row
    try:
        tables = {
            row[0]
            for row in legacy.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if "users" not in tables:
            return

        columns = {
            row[1]
            for row in legacy.execute("PRAGMA table_info(users)").fetchall()
        }
        required = {"id", "role", "full_name", "email", "password_hash", "is_verified"}
        if not required.issubset(columns):
            return

        rows = legacy.execute(
            """
            SELECT id, role, full_name, email, password_hash, is_verified,
                   coach_status, qualification, specialization,
                   experience_years, is_active, last_login_at, created_at
            FROM users
            WHERE LOWER(role) IN ('admin', 'student', 'coach')
            """
        ).fetchall()

        for row in rows:
            email = str(row["email"] or "").strip().lower()
            if not email:
                continue
            if row["role"] == "admin":
                connection.execute(
                    """
                    INSERT OR IGNORE INTO admins
                        (id, full_name, email, password_hash, is_verified,
                         last_login_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (row["id"], row["full_name"], email, row["password_hash"],
                     row["is_verified"], row["last_login_at"], row["created_at"]),
                )
            else:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO users
                        (id, role, full_name, email, password_hash,
                         is_verified, coach_status, qualification,
                         specialization, experience_years, is_active,
                         last_login_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (row["id"], row["role"], row["full_name"], email,
                     row["password_hash"], row["is_verified"], row["coach_status"],
                     row["qualification"], row["specialization"],
                     row["experience_years"], row["is_active"], row["last_login_at"],
                     row["created_at"]),
                )
    except (sqlite3.Error, KeyError):
        # A legacy database from an unrelated application must not prevent the
        # current app from starting.
        return
    finally:
        legacy.close()


def get_db():
    """
    Create and return a configured database connection.

    Local development returns SQLite; production PostgreSQL uses
    ``SUPABASE_DB_URL``.
    """

    if database_backend() == "sqlite":
        path = initialize_local_database()
        return SQLiteConnection(str(path))

    database_url = os.getenv("SUPABASE_DB_URL")

    if not database_url:
        raise RuntimeError(
            "SUPABASE_DB_URL environment variable is not configured."
        )

    global _postgres_pool
    try:
        if ConnectionPool is None:
            return psycopg.connect(
                database_url,
                row_factory=dict_row,
                connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
            )
        if _postgres_pool is None:
            with _postgres_pool_lock:
                if _postgres_pool is None:
                    _postgres_pool = ConnectionPool(
                        conninfo=database_url,
                        # Keep a connection ready on warm serverless instances so
                        # requests don't pay PostgreSQL connection setup latency.
                        # Supabase may close idle sessions; validate a pooled
                        # connection before reuse so a warm Vercel instance does
                        # not hand a stale connection to the next request.
                        min_size=max(0, min(2, int(os.getenv("DB_POOL_MIN", "1")))),
                        max_size=max(1, int(os.getenv("DB_POOL_MAX", "5"))),
                        timeout=float(os.getenv("DB_CONNECT_TIMEOUT", "5")),
                        check=_check_postgres_connection,
                        kwargs={"row_factory": dict_row, "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "5"))},
                        open=False,
                    )
                    _postgres_pool.open(wait=False)
        return PooledConnection(_postgres_pool, _postgres_pool.getconn())
    except Exception as error:
        raise DatabaseConnectionError(
            "Could not connect to the configured PostgreSQL database."
        ) from error


def warm_database_pool():
    """Establish the local app's first pooled connection before serving requests."""
    if database_backend() != "postgres" or ConnectionPool is None:
        return False
    connection = get_db()
    connection.close()
    return True
