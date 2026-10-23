"""Create a clean source archive for deployment with Vercel Drop."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "fitness-tracker-vercel.zip"
SKIP_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".playwright-mcp",
    ".git",
    ".vercel",
    "node_modules",
}


def deployment_files():
    """Yield only files needed by the frontend and Flask function."""
    for name in ("api", "backend", "frontend1"):
        base = ROOT / name
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT)
            if any(part in SKIP_DIRS for part in relative.parts):
                continue
            if name == "backend" and path.suffix.lower() not in {".py", ".sql"}:
                continue
            if path.name.lower().endswith((".sqlite", ".sqlite3", ".db")):
                continue
            yield path

    for name in (
        "vercel.json",
        "requirements.txt",
        ".python-version",
        "pyproject.toml",
        "VERCEL_UPLOAD.md",
    ):
        path = ROOT / name
        if path.is_file():
            yield path


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(set(deployment_files()))
    required = {
        "api/index.py",
        "backend/app.py",
        "backend/schema.sql",
        "frontend1/index.html",
        "vercel.json",
        "requirements.txt",
    }
    included = {path.relative_to(ROOT).as_posix() for path in files}
    missing = required - included
    if missing:
        raise SystemExit(f"Cannot package deployment; missing: {', '.join(sorted(missing))}")

    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
    print(f"Created {OUTPUT} ({len(files)} files, {OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
