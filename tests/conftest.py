import os

import pytest

from backend.db import get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Use only an explicitly separate PostgreSQL test database."""
    if os.getenv("RUN_POSTGRES_TESTS", "false").lower() != "true":
        yield
        return

    test_database_url = os.getenv("SUPABASE_TEST_DB_URL", "").strip()
    configured_database_url = os.getenv("SUPABASE_DB_URL", "").strip()
    if not test_database_url:
        pytest.fail("RUN_POSTGRES_TESTS requires SUPABASE_TEST_DB_URL.")
    if test_database_url == configured_database_url:
        pytest.fail("Refusing to run database integration tests against SUPABASE_DB_URL.")

    previous_url = os.environ.get("SUPABASE_DB_URL")
    os.environ["SUPABASE_DB_URL"] = test_database_url
    os.environ["FITNESS_TEST_MODE"] = "true"
    from backend.setup_and_run import init_db

    if not init_db():
        pytest.fail("Could not initialize the dedicated PostgreSQL test database.")

    yield

    if previous_url is None:
        os.environ.pop("SUPABASE_DB_URL", None)
    else:
        os.environ["SUPABASE_DB_URL"] = previous_url


@pytest.fixture
def db_conn():
    if os.getenv("RUN_POSTGRES_TESTS", "false").lower() != "true":
        pytest.skip("Set RUN_POSTGRES_TESTS=true with a dedicated test database URL.")
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()
