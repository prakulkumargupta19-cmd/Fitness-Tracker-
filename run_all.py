"""Convenience launcher.

This script starts the two independent services that make up the
``fitness-tracker`` stack:

1.  The **Flask API** – the existing :py:mod:`backend.setup_and_run` module
    which runs on :py:data:`localhost:5000`.
2.  The **static front‑end** – ``dev_server.py`` serving the ``frontend1``
    directory on :py:data:`localhost:8080` and proxying API requests to Flask.

Executing ``python run_all.py`` will launch both programs in parallel and
forward their console output to the terminal.  Pressing **Ctrl‑C** stops both
processes cleanly.

The proxy keeps frontend API requests on the same origin, including session
cookies and CSRF requests.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


HOST = "127.0.0.1"
FRONTEND_PORT = int(os.getenv("FITNESS_FRONTEND_PORT", "8080"))
PREFERRED_BACKEND_PORT = int(os.getenv("FITNESS_BACKEND_PORT", os.getenv("PORT", "5000")))


def _port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def _start(command: list[str], cwd: Path, name: str, environment: dict[str, str]) -> subprocess.Popen:
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=environment,
        stdout=None,
        stderr=None,
    )
    print(f"[*] {name} started (pid={process.pid})", flush=True)
    return process


def _find_available_backend_port(preferred: int) -> int:
    for candidate in range(preferred, preferred + 20):
        if _port_is_available(HOST, candidate):
            return candidate
    raise RuntimeError("No available local backend port was found.")


def _stop(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    deadline = time.monotonic() + 5
    for process in processes:
        if process.poll() is None:
            try:
                process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                process.kill()


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    backend_script = base_dir / "backend" / "app.py"
    frontend_script = base_dir / "dev_server.py"
    frontend_dir = base_dir / "frontend1"

    if not frontend_dir.is_dir():  # pragma: no cover – defensive
        raise FileNotFoundError(f"static directory '{frontend_dir}' does not exist")
    if not backend_script.is_file():  # pragma: no cover – defensive
        raise FileNotFoundError(f"backend script '{backend_script}' not found")
    if not frontend_script.is_file():  # pragma: no cover – defensive
        raise FileNotFoundError(f"static server '{frontend_script}' not found")

    backend_port = _find_available_backend_port(PREFERRED_BACKEND_PORT)
    environment = os.environ.copy()
    environment["PORT"] = str(backend_port)
    processes: list[subprocess.Popen] = []
    try:
        backend_process = _start(
            [sys.executable, str(backend_script)], base_dir, "Flask API", environment
        )
        processes.append(backend_process)
        frontend_process = _start(
            [sys.executable, str(frontend_script)], base_dir, "Frontend API proxy", environment
        )
        processes.append(frontend_process)
        print(
            f"\n[+] Front-end available at http://localhost:{FRONTEND_PORT}"
            f" (API proxy -> http://{HOST}:{backend_port})",
            flush=True,
        )
        webbrowser.open(f"http://localhost:{FRONTEND_PORT}")
        while True:
            for process in processes:
                exit_code = process.poll()
                if exit_code is not None:
                    print(
                        f"[!] A service stopped with exit code {exit_code}.",
                        file=sys.stderr,
                    )
                    return exit_code or 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[!] Shutting down services...", flush=True)
        return 0
    except Exception:
        _stop(processes)
        raise
    finally:
        _stop(processes)


if __name__ == "__main__":
    raise SystemExit(main())
