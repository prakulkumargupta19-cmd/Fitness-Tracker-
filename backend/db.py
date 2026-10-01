"""Database configuration and connection helper.

This module provides a single source of truth for the database
configuration used by the application.  It is intentionally
minimal to avoid circular imports – it only imports :mod:`pymysql`
and exposes :data:`DB_CONFIG` and :func:`get_db`.

The values are copied verbatim from :mod:`backend.app` to preserve
exact behaviour.
"""

import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "password@1234"),
    "database": os.getenv("DB_NAME", "fitness_tracker_auth"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False,
}


def get_db():
    """Return a new :class:`pymysql.connections.Connection`.

    If FITNESS_TEST_MODE is set, uses the isolated test database selected by
    FITNESS_TEST_DB_NAME.
    """
    config = DB_CONFIG.copy()
    if os.getenv("FITNESS_TEST_MODE") == "true":
        config["database"] = os.getenv("FITNESS_TEST_DB_NAME", "fitness_tracker_test")
    return pymysql.connect(**config)
