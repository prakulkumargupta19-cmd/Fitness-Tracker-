import pytest
from backend.app import app

def test_signup_domain_restriction():
    with app.test_client() as client:
        # Test invalid email
        response = client.post("/api/signup", json={
            "role": "student",
            "full_name": "Test User",
            "email": "test@gmail.com",
            "password": "Password123"
        })
        assert response.status_code == 400
        assert "Only @inspiria.edu.in emails are allowed." in response.get_json()["message"]

        # Test valid email
        # This will fail with 400 or other because it's not a full registration flow,
        # but it shouldn't be the domain error.
        response = client.post("/api/signup", json={
            "role": "student",
            "full_name": "Test User",
            "email": "test@inspiria.edu.in",
            "password": "Password123"
        })
        assert response.status_code != 400 or "Only @inspiria.edu.in emails are allowed." not in response.get_json().get("message", "")
