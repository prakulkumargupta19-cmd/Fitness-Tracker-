import os
import pytest
import pymysql
from backend.db import get_db
from pathlib import Path

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Set test mode
    os.environ["FITNESS_TEST_MODE"] = "true"
    
    # Create test database
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="password@1234"
    )
    with conn.cursor() as cursor:
        cursor.execute("DROP DATABASE IF EXISTS fitness_tracker_test")
        cursor.execute("CREATE DATABASE fitness_tracker_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("USE fitness_tracker_test")
        
        # Read and execute schema.sql
        schema_path = Path(__file__).parent.parent / "backend" / "schema.sql"
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
            for stmt in [s.strip() for s in schema_sql.split(";") if s.strip()]:
                # Skip database creation and usage statements
                if stmt.upper().startswith("CREATE DATABASE") or stmt.upper().startswith("USE"):
                    continue
                cursor.execute(stmt)
        
    conn.commit()
    conn.close()

    yield

    # Cleanup
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="password@1234"
    )
    with conn.cursor() as cursor:
        cursor.execute("DROP DATABASE IF EXISTS fitness_tracker_test")
    conn.commit()
    conn.close()

@pytest.fixture
def db_conn():
    conn = get_db()
    yield conn
    conn.close()
