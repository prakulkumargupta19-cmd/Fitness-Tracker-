"""Database configuration and connection helper.

This module provides a single source of truth for the database
configuration used by the application.  It is intentionally
minimal to avoid circular imports – it only imports :mod:`pymysql`
and exposes :data:`DB_CONFIG` and :func:`get_db`.

The values are copied verbatim from :mod:`backend.app` to preserve
exact behaviour.
"""

import os
import pymysql

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "password@1234"),
    "database": os.getenv("DB_NAME", "fitness_tracker_auth"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False,
}


def get_db():
    """Return a new :class:`pymysql.connections.Connection`.

    If FITNESS_TEST_MODE is set, uses 'fitness_tracker_test' as the database.
    """
    config = DB_CONFIG.copy()
    if os.getenv("FITNESS_TEST_MODE") == "true":
        config["database"] = "fitness_tracker_test"
    return pymysql.connect(**config)
