"""Verify SMTP connectivity and authentication without sending a message."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from auth.emails import check_smtp_connection  # noqa: E402


def main():
    try:
        check_smtp_connection()
    except Exception as error:
        print(f"SMTP check failed: {type(error).__name__}: {error}")
        return 1
    print("SMTP connection and authentication succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
