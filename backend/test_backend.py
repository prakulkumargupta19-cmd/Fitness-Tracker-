import os
import sys
import unittest
import uuid

os.environ.setdefault("SECRET_KEY", "dev-secret-key-32-chars-long")

sys.path.insert(0, os.path.dirname(__file__))

import app



class BackendSmokeTests(unittest.TestCase):
    def test_root_serves_frontend_index(self):
        client = app.app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Role Selection", response.data)

    def test_seed_initial_users(self):
        app.ensure_demo_seed()
        self.assertGreater(app.count_users(), 0)

    def test_student_login_works_with_demo_account(self):
        app.ensure_demo_seed()
        client = app.app.test_client()
        response = client.post(
            "/api/login",
            json={"email": "arjun@college.edu", "password": "1234", "role": "student"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])

    def test_authenticated_write_requires_csrf_token(self):
        client = app.app.test_client()
        login = client.post(
            "/api/login",
            json={"email": "arjun@college.edu", "password": "1234", "role": "student"},
        )
        self.assertEqual(login.status_code, 200)
        blocked = client.post("/api/logout")
        self.assertEqual(blocked.status_code, 403)

        token_response = client.get("/api/csrf-token")
        self.assertEqual(token_response.status_code, 200)
        original_generate_otp = app.generate_otp
        # Patch in both locations: app.py and auth.helpers (for signup flow)
        app.generate_otp = lambda: "123456"
        auth_helpers.generate_otp = lambda: "123456"
        self.assertEqual(logout.status_code, 200)

    def test_admin_login_requires_password_and_otp(self):
        client = app.app.test_client()
        invalid = client.post(
            "/api/admin-login",
            json={"email": "admin@college.edu", "password": "wrong-password"},
        )
        self.assertEqual(invalid.status_code, 401)
        original_generate_otp = auth_helpers.generate_otp
        try:
            password_step = client.post(
                "/api/admin-login",
                json={"email": "admin@college.edu", "password": "1234"},
            )
            app.generate_otp = original_generate_otp
            auth_helpers.generate_otp = original_generate_otp
            bad_otp = client.post(
                "/api/admin-login/verify-otp",
                json={"email": "admin@college.edu", "otp": "000000"},
            )
            self.assertEqual(bad_otp.status_code, 400)
            valid_otp = client.post(
                "/api/admin-login/verify-otp",
                json={"email": "admin@college.edu", "otp": "123456"},
            )
            self.assertEqual(valid_otp.status_code, 200)
        finally:
            app.generate_otp = original_generate_otp
            auth_helpers.generate_otp = original_generate_otp

    def test_coach_account_requires_admin_approval_before_login(self):
        app.ensure_demo_seed()
        client = app.app.test_client()
        email = f"newcoach.workflow.{uuid.uuid4().hex[:8]}@test.com"
        password = "StrongPass123"

        original_generate_otp = auth_helpers.generate_otp
        app.generate_otp = lambda: "123456"
        auth_helpers.generate_otp = lambda: "123456"
        try:
            register = client.post(
                "/api/register",
                json={
                    "name": "New Workflow Coach",
                    "email": email,
                    "password": password,
                    "role": "coach",
                    "sport": "Cricket",
                    "contact_number": "9991234567",
                    "gender": "Male",
                    "date_of_birth": "1990-01-01",
                },
            )
            self.assertEqual(register.status_code, 201)

            verify = client.post(
                "/api/account-verification/verify",
                json={"email": email, "otp": "123456"},
            )
            self.assertEqual(verify.status_code, 200)

            pending_login = client.post(
                "/api/login",
                json={"email": email, "password": password, "role": "coach"},
            )
            self.assertEqual(pending_login.status_code, 403)

            admin_login = client.post(
                "/api/admin-login",
                json={"email": "admin@college.edu", "password": "1234"},
            )
            self.assertEqual(admin_login.status_code, 200)
            admin_verify = client.post(
                "/api/admin-login/verify-otp",
                json={"email": "admin@college.edu", "otp": "123456"},
            )
            self.assertEqual(admin_verify.status_code, 200)

            approve = client.post(
                "/api/admin/coach-approve",
                json={"email": email},
            )
            self.assertEqual(approve.status_code, 200)

            final_login = client.post(
                "/api/login",
                json={"email": email, "password": password, "role": "coach"},
            )
            self.assertEqual(final_login.status_code, 200)

            blocked_signup = client.post(
                "/api/admin-signup",
                json={
                    "name": "Blocked Admin",
                    "email": "blocked.admin@test.com",
                    "password": "StrongPass123",
                },
            )
            self.assertEqual(blocked_signup.status_code, 403)
        finally:
            app.generate_otp = original_generate_otp
            auth_helpers.generate_otp = original_generate_otp

    def test_coach_signup_resend_otp_route_is_available(self):
        client = app.app.test_client()
        email = f"coach-resend-workflow.{uuid.uuid4().hex[:8]}@test.com"
        password = "StrongPass123"

        original_generate_otp = auth_helpers.generate_otp
        app.generate_otp = lambda: "123456"
        auth_helpers.generate_otp = lambda: "123456"
        try:
            register = client.post(
                "/api/register",
                json={
                    "name": "Coach Resend",
                    "email": email,
                    "password": password,
                    "role": "coach",
                    "sport": "Cricket",
                    "contact_number": "9999876543",
                    "gender": "Female",
                    "date_of_birth": "1992-05-11",
                },
            )
            self.assertEqual(register.status_code, 201)

            resend = client.post(
                "/api/verify-otp/resend",
                json={"email": email},
            )
            self.assertEqual(resend.status_code, 200)
            payload = resend.get_json()
            self.assertTrue(payload["success"])
        finally:
            app.generate_otp = original_generate_otp
            auth_helpers.generate_otp = original_generate_otp

    def test_signup_route_alias_verifies_signup_otp(self):
        client = app.app.test_client()
        email = f"coach-signup-alias.{uuid.uuid4().hex[:8]}@test.com"
        password = "StrongPass123"

        original_generate_otp = auth_helpers.generate_otp
        app.generate_otp = lambda: "123456"
        try:
            register = client.post(
                "/api/register",
                json={
                    "name": "Coach Alias",
                    "email": email,
                    "password": password,
                    "role": "coach",
                    "sport": "Cricket",
                    "contact_number": "9991234321",
                    "gender": "Male",
                    "date_of_birth": "1991-02-02",
                },
            )
            self.assertEqual(register.status_code, 201)

            verify = client.post(
                "/api/verify-otp",
                json={"email": email, "otp": "123456"},
            )
            self.assertEqual(verify.status_code, 200)
            payload = verify.get_json()
            self.assertTrue(payload["success"])
        finally:
            app.generate_otp = original_generate_otp


if __name__ == "__main__":
    unittest.main()
