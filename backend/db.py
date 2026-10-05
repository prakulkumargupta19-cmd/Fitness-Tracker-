"""Supabase PostgreSQL database connection."""

import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Load the repository-root .env during local development. Environment values
# configured by a deployment platform take precedence over this optional file.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class DatabaseConnectionError(RuntimeError):
    """Safe database connection error that never includes the connection URL."""


def get_db():
    """
    Create and return a PostgreSQL connection to Supabase.

    Uses SUPABASE_DB_URL from the environment.
    """

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