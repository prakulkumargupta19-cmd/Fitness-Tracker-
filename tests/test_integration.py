import pytest
import json
from backend.app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_signup_domain_enforcement(client):
    # Invalid domain
    response = client.post("/api/signup", json={
        "role": "student",
        "full_name": "Test User",
        "email": "test@gmail.com",
        "password": "Password123"
    })
    assert response.status_code == 400
    assert "Only @inspiria.edu.in emails are allowed." in response.get_json()["message"]

def test_attendance_flow_stub(client):
    # Just checking if the route exists and returns 401 because no user is logged in
    response = client.get("/api/student/attendance")
    assert response.status_code == 401
