"""Static deployment checks for Vercel and Supabase readiness."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".playwright-mcp",
    "artifacts",
    "Fit-Track",
}
SOURCE_SUFFIXES = {".py", ".js", ".html", ".sql"}


def source_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        if any(part in IGNORED_PARTS for part in path.relative_to(ROOT).parts):
            continue
        yield path


def check_source_patterns(paths, patterns):
    matches = []
    for path in paths:
        try:
            content = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            continue
        for label, pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                matches.append((label, path.relative_to(ROOT).as_posix()))
    return matches


def print_check(label, passed, detail=None):
    state = "PASS" if passed else "FAIL"
    print(f"[{state}] {label}" + (f" — {detail}" if detail else ""))
    return passed


def main():
    results = []
    failures = []
    src = list(source_files())

    requirements_path = ROOT / "requirements.txt"
    requirements = (
        requirements_path.read_text(encoding="utf-8-sig").lower()
        if requirements_path.exists()
        else ""
    )
    for package in ("flask", "psycopg", "python-dotenv"):
        results.append(
            print_check(
                f"Production dependency: {package}",
                package in requirements,
            )
        )

    for module, label in (("flask", "Flask import"), ("psycopg", "psycopg installed")):
        try:
            available = importlib.util.find_spec(module) is not None
        except (ImportError, ValueError):
            available = False
        results.append(print_check(label, available))

    try:
        config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
        vercel_config_ok = (
            any(build.get("src") == "api/index.py" for build in config.get("builds", []))
            and (ROOT / "api" / "index.py").is_file()
            and any(route.get("src") == "/api/(.*)" for route in config.get("routes", []))
        )
    except (OSError, json.JSONDecodeError):
        vercel_config_ok = False
    results.append(print_check("Vercel configuration and API entry point", vercel_config_ok))

    example_env = (ROOT / ".env.example").read_text(encoding="utf-8-sig")
    backend_config_source = "\n".join(
        path.read_text(encoding="utf-8-sig")
        for path in (ROOT / "backend").glob("*.py")
    )
    env_names_ok = all(
        name in backend_config_source and name in example_env
        for name in ("SUPABASE_DB_URL", "SECRET_KEY", "FRONTEND_URL")
    )
    results.append(print_check("Server-side environment variable names", env_names_ok))

    frontend_config = (ROOT / "frontend1" / "js" / "config.js").read_text(
        encoding="utf-8-sig"
    )
    relative_api = bool(re.search(r"API_BASE\s*:\s*apiBase", frontend_config)) and (
        'const apiBase = configuredApiBase.replace(/\\/+$/, "");' in frontend_config
    )
    results.append(print_check("Same-origin / configurable frontend API base", relative_api))

    patterns = [
        ("MySQL/PyMySQL", r"\bpymysql\b|\bmysql(?:\.connector)?\b|AUTO_INCREMENT|ON DUPLICATE KEY|GROUP_CONCAT|INSERT IGNORE|lastrowid"),
        ("SQLite", r"\bsqlite3?\b"),
    ]
    forbidden_matches = check_source_patterns(
        (path for path in src if path.resolve() != Path(__file__).resolve()),
        patterns,
    )
    for label, file_name in forbidden_matches:
        failures.append(f"{label} compatibility construct in {file_name}")
    results.append(
        print_check(
            "No MySQL or SQLite production-source constructs",
            not forbidden_matches,
            ", ".join(f"{label}: {name}" for label, name in forbidden_matches[:8]) or None,
        )
    )

    localhost_matches = check_source_patterns(
        (ROOT / "frontend1" / "js").glob("*.js"),
        [("local API origin", r"https?://(?:localhost|127\.0\.0\.1)(?::\d+)?")],
    )
    for _, file_name in localhost_matches:
        failures.append(f"Hardcoded local API URL in {file_name}")
    results.append(
        print_check(
            "No hardcoded localhost API URL in frontend JavaScript",
            not localhost_matches,
            ", ".join(name for _, name in localhost_matches) or None,
        )
    )

    tracked_env_files = []
    try:
        tracked = subprocess.run(
            ["git", "ls-files", "--cached"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        tracked_env_files = [
            name for name in tracked
            if Path(name).name.startswith(".env")
            and Path(name).name != ".env.example"
        ]
    except (OSError, subprocess.CalledProcessError):
        pass
    results.append(
        print_check(
            "No tracked secret environment files",
            not tracked_env_files,
            ", ".join(tracked_env_files) or None,
        )
    )
    if tracked_env_files:
        failures.append("Secret environment file is tracked by Git")

    secret_pattern = re.compile(
        r"""(?im)^\s*(?:SECRET_KEY|SUPABASE_DB_URL|MAIL_PASSWORD|INITIAL_ADMIN_PASSWORD)\s*=\s*['"][^'"]+['"]"""
    )
    hardcoded_secrets = []
    for path in src:
        try:
            contents = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            continue
        if secret_pattern.search(contents):
            hardcoded_secrets.append(path.relative_to(ROOT).as_posix())
    results.append(
        print_check(
            "No obvious hardcoded deployment secrets in source",
            not hardcoded_secrets,
            ", ".join(hardcoded_secrets) or None,
        )
    )
    if hardcoded_secrets:
        failures.append("Possible hardcoded deployment secret found in source")

    backend_source = "\n".join(
        path.read_text(encoding="utf-8-sig", errors="ignore")
        for path in (ROOT / "backend").glob("*.py")
    )
    results.append(
        print_check(
            "Health endpoint",
            '"/api/health"' in backend_source,
        )
    )
    results.append(
        print_check(
            "Protected admin diagnostics endpoint",
            '"/api/admin/diagnostics"' in backend_source
            and "@role_required(\"admin\")" in backend_source,
        )
    )

    if not all(results):
        failures.append("One or more required static checks failed.")

    print("\nFITNESS TRACKER VERCEL DIAGNOSTIC")
    print("==================================")
    print("FINAL RESULT:")
    if failures:
        print("NOT READY FOR VERCEL")
        for failure in dict.fromkeys(failures):
            print(f"- {failure}")
        return 1
    print("STATIC CHECKS PASS — hosted Supabase, SMTP, and Vercel runtime checks remain necessary.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
