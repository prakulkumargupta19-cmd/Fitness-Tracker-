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
    "password": os.getenv("DB_PASSWORD", "Prakul@2006"),
    "database": os.getenv("DB_NAME", "fitness_tracker_auth"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False,
}

def get_db():
    """Return a new :class:`pymysql.connections.Connection`.

    The function simply forwards the configuration dictionary to
    :func:`pymysql.connect`.  It is kept in a separate module so
    that both :mod:`backend.app` and any future auth modules can
    import it without creating a circular dependency.
    """
    return pymysql.connect(**DB_CONFIG)

