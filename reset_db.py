import pymysql
from backend.setup_and_run import ROOT_CONFIG, APP_CONFIG, SCHEMA_PATH

def reset_database():
    try:
        # Drop and create database
        conn = pymysql.connect(**ROOT_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("DROP DATABASE IF EXISTS fitness_tracker_auth")
            cursor.execute(
                "CREATE DATABASE fitness_tracker_auth CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        conn.close()
        print("Database dropped and created")

        # Load schema
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        # Execute schema
        conn = pymysql.connect(**APP_CONFIG)
        with conn.cursor() as cursor:
            for stmt in [s.strip() for s in schema_sql.split(";") if s.strip()]:
                try:
                    cursor.execute(stmt)
                except Exception as e:
                    print(f"Warning: Could not execute statement: {e}")
        conn.commit()
        conn.close()
        print("Schema loaded")

        # Seed data
        from backend.seed import main
        main()
        print("Data seeded")

    except Exception as e:
        print(f"Error: {e}")
        return False
    return True

if __name__ == "__main__":
    reset_database()