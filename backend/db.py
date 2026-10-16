"""Database connections for local development and PostgreSQL deployments.

Local development deliberately defaults to SQLite so the application can be
run without a Supabase project.  PostgreSQL remains available by setting
``DATABASE_BACKEND=postgres`` (or by running in a production environment).
"""

import os
import re
import sqlite3
import threading
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Load the repository-root .env during local development. Environment values
# configured by a deployment platform take precedence over this optional file.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_SCHEMA_PATH = Path(__file__).resolve().parent / "local_schema.sql"
_local_schema_lock = threading.Lock()
_local_schema_ready: set[str] = set()


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
    if os.getenv("VERCEL_ENV", "").lower() == "production":
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
                connection.commit()
                _local_schema_ready.add(key)
            finally:
                connection.close()
    return path


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

    try:
        return psycopg.connect(
            database_url,
            row_factory=dict_row,
            connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
        )
    except psycopg.Error as error:
        raise DatabaseConnectionError(
            "Could not connect to the configured PostgreSQL database."
        ) from error
