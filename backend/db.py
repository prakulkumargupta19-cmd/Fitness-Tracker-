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
            try:
                # Clear read-only/failed transactions before returning this
                # connection. Otherwise psycopg_pool performs the same
                # rollback and emits a warning on every normal SELECT request.
                if self._connection.info.transaction_status.name in {"INTRANS", "INERROR"}:
                    self._connection.rollback()
            except Exception:
                # Let the pool discard or reset a connection it cannot clean.
                pass
            finally:
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
    """Use PostgreSQL for hosted deployments and SQLite only for local development."""
    configured = os.getenv("DATABASE_BACKEND", "").strip().lower()
    vercel_environment = os.getenv("VERCEL_ENV", "").strip().lower()
    is_hosted = (
        os.getenv("VERCEL", "").strip() == "1"
        or vercel_environment in {"preview", "production"}
        or os.getenv("APP_ENV", "development").strip().lower() == "production"
    )
    if configured in {"postgres", "postgresql", "supabase"}:
        return "postgres"
    if configured in {"sqlite", "local"}:
        if is_hosted:
            raise RuntimeError("SQLite is only supported for local development; configure PostgreSQL for hosted deployments.")
        return "sqlite"
    if is_hosted:
        return "postgres"
    return "sqlite"


def local_database_path():
    configured = os.getenv("LOCAL_DB_PATH", "").strip()
    path = Path(configured) if configured else PROJECT_ROOT / "backend" / "fitness_tracker.sqlite3"
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _migrate_legacy_coaching_sessions(connection):
    """Drop or recreate legacy coaching_sessions without sport_id before applying schema."""
    try:
        columns = {
            row[1]: row
            for row in connection.execute("PRAGMA table_info(coaching_sessions)").fetchall()
        }
        if columns and "sport_id" not in columns:
            connection.execute("DROP TABLE IF EXISTS coaching_sessions")
    except Exception:
        pass


def initialize_local_database():
    """Create/update the local SQLite schema and remove retired performance tables."""
    path = local_database_path()
    key = str(path.resolve())
    with _local_schema_lock:
        if key not in _local_schema_ready:
            connection = sqlite3.connect(path)
            try:
                connection.execute("PRAGMA foreign_keys = ON")
                _migrate_legacy_coaching_sessions(connection)
                connection.executescript(LOCAL_SCHEMA_PATH.read_text(encoding="utf-8"))
                profile_columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(student_profiles)").fetchall()
                }
                if "gender" not in profile_columns:
                    connection.execute("ALTER TABLE student_profiles ADD COLUMN gender TEXT")
                tournament_columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(tournaments)").fetchall()
                }
                if "registration_url" not in tournament_columns:
                    connection.execute("ALTER TABLE tournaments ADD COLUMN registration_url TEXT")
                admin_columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(admins)").fetchall()
                }
                if "is_active" not in admin_columns:
                    connection.execute(
                        "ALTER TABLE admins ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
                    )
                user_columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(users)").fetchall()
                }
                for column, declaration in (
                    ("account_status", "TEXT NOT NULL DEFAULT 'active'"),
                    ("deactivated_at", "TIMESTAMP"),
                    ("deactivated_by", "INTEGER"),
                    ("reactivated_at", "TIMESTAMP"),
                ):
                    if column not in user_columns:
                        connection.execute(f"ALTER TABLE users ADD COLUMN {column} {declaration}")
                for table in ("users", "pending_registrations"):
                    table_columns = {
                        row[1]
                        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
                    }
                    for column in ("qualification", "specialization", "experience_years"):
                        if column in table_columns:
                            connection.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
                connection.execute("UPDATE users SET account_status = CASE WHEN is_active THEN 'active' ELSE 'deactivated' END WHERE account_status IS NULL OR (account_status = 'active' AND is_active = 0)")
                _migrate_local_tournament_sport(connection)
                _migrate_legacy_local_accounts(connection, path)
                connection.commit()
                _local_schema_ready.add(key)
            finally:
                connection.close()
    return path


def _migrate_local_tournament_sport(connection):
    """Allow all-student events on older SQLite schemas that required a sport."""
    columns = {
        row[1]: row
        for row in connection.execute("PRAGMA table_info(tournaments)").fetchall()
    }
    sport_column = columns.get("sport_id")
    if sport_column is None or not sport_column[3]:
        return
    connection.execute("PRAGMA foreign_keys = OFF")
    try:
        connection.executescript("""
            CREATE TABLE tournaments_schedule_upgrade (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, sport_id INTEGER REFERENCES sports(id),
                start_date DATE NOT NULL, end_date DATE, venue TEXT,
                status TEXT NOT NULL DEFAULT 'Upcoming', description TEXT, poster_path TEXT,
                registration_open BOOLEAN NOT NULL DEFAULT 1, registration_url TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO tournaments_schedule_upgrade
            SELECT id,name,sport_id,start_date,end_date,venue,status,description,poster_path,
                   registration_open,registration_url,created_at,updated_at FROM tournaments;
            DROP TABLE tournaments;
            ALTER TABLE tournaments_schedule_upgrade RENAME TO tournaments;
            CREATE TABLE IF NOT EXISTS registrations_schedule_upgrade (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                team_name TEXT, registration_status TEXT NOT NULL DEFAULT 'Registered',
                registered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tournament_id, student_id)
            );
            INSERT INTO registrations_schedule_upgrade
            SELECT id,tournament_id,student_id,team_name,registration_status,registered_at FROM registrations;
            DROP TABLE registrations;
            ALTER TABLE registrations_schedule_upgrade RENAME TO registrations;
            CREATE INDEX IF NOT EXISTS idx_tournaments_start_date ON tournaments(start_date);
        """)
    finally:
        connection.execute("PRAGMA foreign_keys = ON")


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
                   coach_status, is_active, last_login_at, created_at
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
                         is_verified, coach_status, is_active,
                         last_login_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (row["id"], row["role"], row["full_name"], email,
                     row["password_hash"], row["is_verified"], row["coach_status"],
                     row["is_active"], row["last_login_at"], row["created_at"]),
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
        connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
        is_serverless = (
            os.getenv("VERCEL", "").strip() == "1"
            or os.getenv("VERCEL_ENV", "").strip().lower() in {"preview", "production"}
        )
        default_pool_min = "0" if is_serverless else "1"
        default_pool_max = "1" if is_serverless else "4"
        pool_max_size = max(1, int(os.getenv("DB_POOL_MAX", default_pool_max)))
        pool_min_size = max(0, min(pool_max_size, int(os.getenv("DB_POOL_MIN", default_pool_min))))
        if ConnectionPool is None:
            return psycopg.connect(
                database_url,
                row_factory=dict_row,
                connect_timeout=connect_timeout,
            )
        if _postgres_pool is None:
            with _postgres_pool_lock:
                if _postgres_pool is None:
                    _postgres_pool = ConnectionPool(
                        conninfo=database_url,
                        # Keep a connection ready on warm serverless instances so
                        # requests don't pay PostgreSQL connection setup latency.
                        min_size=pool_min_size,
                        max_size=pool_max_size,
                        timeout=float(os.getenv("DB_POOL_TIMEOUT", str(max(15, connect_timeout)))),
                        kwargs={
                            "row_factory": dict_row,
                            "connect_timeout": connect_timeout,
                            # Supabase transaction pooling does not preserve prepared statements.
                            "prepare_threshold": None,
                        },
                        open=False,
                    )
                    _postgres_pool.open(wait=False)
        return PooledConnection(_postgres_pool, _postgres_pool.getconn())
    except Exception as error:
        raise DatabaseConnectionError(
            "Could not connect to the configured PostgreSQL database."
        ) from error
