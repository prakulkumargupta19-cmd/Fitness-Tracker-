"""Convenience launcher.

This script starts the two independent services that make up the
``fitness-tracker`` stack:

1.  The **Flask API** – the existing :py:mod:`backend.setup_and_run` module
    which runs on :py:data:`localhost:5000`.
2.  The **static front‑end** – a simple ``http.server`` instance serving the
    ``frontend1`` directory on :py:data:`localhost:8080`.

Executing ``python run_all.py`` will launch both programs in parallel and
forward their console output to the terminal.  Pressing **Ctrl‑C** stops both
processes cleanly.

No changes are made to the project's existing code base – this is a
stand‑alone wrapper.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from threading import Thread

__all__ = ["main"]


def _run_process(cmd: list[str], name: str) -> subprocess.Popen:
    """Start *cmd* as a subprocess.

    The child inherits ``stdout``/``stderr`` so its output appears
    directly in the same terminal.  The function returns the
    :class:`subprocess.Popen` instance so callers can later terminate it.
    """
    try:
        proc = subprocess.Popen(cmd, cwd=os.getcwd(), stdout=None, stderr=None)
        print(f"[*] {name} started (pid={proc.pid})\n")
        return proc
    except Exception as exc:  # pragma: no cover – defensive
        print(f"[!] Failed to start {name}: {exc}")
        raise


def _stream_output(proc: subprocess.Popen, name: str) -> None:
    """Continuously read from *proc*'s stdout and echo to the console.

    The function is intended to run in its own thread.
    """
    try:
        for line in iter(proc.stdout.readline if proc.stdout else b"", b""):  # type: ignore[arg-type]
            if not line:
                break
            sys.stdout.buffer.write(f"[{name}] {line.decode()}".encode())
    finally:
        proc.stdout.close()  # pragma: no cover – defensive


def main() -> None:
    # Resolve paths relative to this script's location.
    base_dir = Path(__file__).resolve().parent
    static_dir = base_dir / "frontend1"
    backend_script = base_dir / "backend" / "setup_and_run.py"

    if not static_dir.is_dir():  # pragma: no cover – defensive
        raise FileNotFoundError(f"static directory '{static_dir}' does not exist")
    if not backend_script.is_file():  # pragma: no cover – defensive
        raise FileNotFoundError(f"backend script '{backend_script}' not found")

    # Commands to start the two services.
    static_cmd = [
        sys.executable,
        "-m",
        "http.server",
        "8080",
        "--directory",
        str(static_dir),
    ]
    backend_cmd = [sys.executable, str(backend_script)]
    # Start them
    global static_proc, backend_proc  # Needed by _shutdown
    static_proc = _run_process(static_cmd, "Static HTTP Server")
    backend_proc = _run_process(backend_cmd, "Flask API")

    # A friendly message – users normally look for this.
    print("\n[+] Static front‑end available at http://localhost:8080")

    # Open the URL in the default browser automatically.
    # (This is optional; if you prefer to keep the terminal clean, comment it out.)
    try:
        import webbrowser
        webbrowser.open("http://localhost:8080")
    except Exception:  # pragma: no cover – defensive
        pass

    # Graceful shutdown helper
    def _shutdown(_: int | None = None, __: object | None = None) -> None:  # pragma: no cover - signal handler
        print("\n[!] Shutting down services…")
        for p in (static_proc, backend_proc):
            if p.poll() is None:
                try:
                    p.terminate()
                except Exception:  # pragma: no cover
                    pass
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Keep the main thread alive while the workers run.
    try:
        while static_proc.poll() is None or backend_proc.poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:  # pragma: no cover – graceful exit
        _shutdown()


if __name__ == "__main__":  # pragma: no cover – command‑line entry point
    main()