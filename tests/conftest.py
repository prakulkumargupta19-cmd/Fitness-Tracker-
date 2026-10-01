import os
import re
import pytest
import pymysql
from uuid import uuid4
from backend.db import get_db
from pathlib import Path

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    if os.getenv("RUN_MYSQL_TESTS", "false").lower() != "true":
        yield
        return

    # Use an isolated database name so test setup never touches a developer DB.
    os.environ["FITNESS_TEST_MODE"] = "true"
    database_name = f"fitness_tracker_test_{uuid4().hex}"
    os.environ["FITNESS_TEST_DB_NAME"] = database_name
    connection_config = {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "charset": "utf8mb4",
    }
    
    conn = pymysql.connect(**connection_config)
    with conn.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE `{database_name}`")
        
        # Read and execute schema.sql
        schema_path = Path(__file__).parent.parent / "backend" / "schema.sql"
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = re.sub(r"(?m)^\s*--[^\r\n]*", "", f.read())
            for stmt in [s.strip() for s in schema_sql.split(";") if s.strip()]:
                if not stmt or stmt.upper().startswith(("CREATE DATABASE", "USE ")):
                    continue
                cursor.execute(stmt)
        
    conn.commit()
    conn.close()

    yield

    # Cleanup
    conn = pymysql.connect(**connection_config)
    with conn.cursor() as cursor:
        cursor.execute(f"DROP DATABASE `{database_name}`")
    conn.commit()
    conn.close()

@pytest.fixture
def db_conn():
    if os.getenv("RUN_MYSQL_TESTS", "false").lower() != "true":
        pytest.skip("Set RUN_MYSQL_TESTS=true to run MySQL integration tests.")
    conn = get_db()
    yield conn
    conn.close()
