"""Legacy reset entry point intentionally disabled for data safety."""

def main():
    print("Database reset is disabled to protect existing application data.")
    print("Use `python backend/setup_and_run.py --init-only` for non-destructive setup.")
    raise SystemExit(2)


if __name__ == "__main__":
    main()
