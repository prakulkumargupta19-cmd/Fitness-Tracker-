import pytest
import subprocess
import time
import socket
from pathlib import Path

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

@pytest.fixture(scope="session", autouse=True)
def setup_servers():
    """
    Starts the Flask backend and the Frontend dev server.
    """
    # 1. Start Backend (Flask)
    # We assume the environment is set up such that 'python backend/app.py' starts the server on port 5000
    # Use DEVNULL instead of PIPE to prevent the process from hanging when the buffer fills
    backend_proc = subprocess.Popen(
        ["python", "backend/app.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={"FLASK_ENV": "development", "PORT": "5000"}
    )
    
    # Wait for backend to be ready
    timeout = 30
    start_time = time.time()
    while not is_port_open(5000):
        if time.time() - start_time > timeout:
            backend_proc.terminate()
            pytest.fail("Backend failed to start on port 5000")
        time.sleep(0.5)

    # 2. Start Frontend Server (dev_server.py)
    # Serves from port 8080
    frontend_proc = subprocess.Popen(
        ["python", "dev_server.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for frontend to be ready
    start_time = time.time()
    while not is_port_open(8080):
        if time.time() - start_time > timeout:
            frontend_proc.terminate()
            backend_proc.terminate()
            pytest.fail("Frontend failed to start on port 8080")
        time.sleep(0.5)

    yield

    # Cleanup
    frontend_proc.terminate()
    backend_proc.terminate()

@pytest.fixture
def base_url():
    return "http://localhost:8080"
