"""Start the local Flask API and the frontend proxy together."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path


HOST = "127.0.0.1"
FRONTEND_PORT = 8080
BACKEND_PORT = 5000


def _port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def _start(command: list[str], cwd: Path, name: str) -> subprocess.Popen:
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=os.environ.copy(),
        stdout=None,
        stderr=None,
    )
    print(f"[*] {name} started (pid={process.pid})", flush=True)
    return process


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

    if not backend_script.is_file():
        print(f"[!] Backend file not found: {backend_script}", file=sys.stderr)
        return 1
    if not frontend_script.is_file():
        print(f"[!] Frontend server not found: {frontend_script}", file=sys.stderr)
        return 1

    unavailable = [
        f"{HOST}:{port}"
        for port in (FRONTEND_PORT, BACKEND_PORT)
        if not _port_is_available(HOST, port)
    ]
    if unavailable:
        print(
            "[!] These required ports are already in use: "
            + ", ".join(unavailable),
            file=sys.stderr,
        )
        print("Close the old server and run this command again.", file=sys.stderr)
        return 1

    processes: list[subprocess.Popen] = []
    try:
        processes.append(
            _start([sys.executable, str(backend_script)], base_dir / "backend", "Flask API")
        )
        processes.append(
            _start([sys.executable, str(frontend_script)], base_dir, "Frontend proxy")
        )
        print("[+] Open http://localhost:8080", flush=True)

        try:
            import webbrowser

            webbrowser.open("http://localhost:8080")
        except Exception:
            pass

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
    finally:
        _stop(processes)


if __name__ == "__main__":
    raise SystemExit(main())
