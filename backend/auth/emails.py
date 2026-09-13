"""Email-sending helpers for authentication flows.

This module contains the email helpers extracted from ``backend.app``.
It has no dependency on the Flask application instance or module
(``backend.app``), and uses ``flask.current_app`` only for logging.
"""

import os
import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app

# Match the semantics used by backend.app (no import from it).
TEST_MODE = os.getenv("FITNESS_TEST_MODE", "true").lower() == "true"
OTP_MINUTES = 10


def display_role(role):
    """Return a human-readable role label."""
    return "Student" if role == "player" else str(role or "").capitalize()


def send_email(recipient, subject, body):
    username = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")
    if not username or not password:
        current_app.logger.warning("Email not configured: set MAIL_USERNAME and MAIL_PASSWORD")
        return False
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = os.getenv("MAIL_FROM", username)
    message["To"] = recipient
    message.set_content(body)
    try:
        with smtplib.SMTP(
            os.getenv("MAIL_SERVER", "smtp.gmail.com"),
            int(os.getenv("MAIL_PORT", "587")),
            timeout=15,
        ) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(username, password)
            server.send_message(message)
        return True
    except (OSError, smtplib.SMTPException, ValueError) as error:
        current_app.logger.error("Email delivery failed: %s", error)
        return False


def send_otp_email(email, name, purpose, otp):
    action = "password reset" if purpose == "password_reset" else "account verification"
    if TEST_MODE:
        print(f"\n[TEST MODE] OTP for {email} ({purpose}): {otp}\n")
        return True
    return send_email(
        email,
        f"Athlete Tracker – {action.title()} OTP",
        f"Hello {name},\n\nYour Athlete Tracker {action} OTP is:\n\n{otp}\n\nThis OTP expires in {OTP_MINUTES} minutes.\n\nThank you,\nAthlete Tracker Team",
    )


def send_account_created_email(email, name, role):
    if TEST_MODE:
        print(f"[TEST MODE] Account created for {email} as {role}")
        return True
    return send_email(
        email,
        "Athlete Tracker Account Created Successfully",
        f"Hello {name},\n\nCongratulations!\n\nYour Athlete Tracker account has been created.\nAccount Type: {display_role(role)}\n\nYou can now log in.\n\nThank you,\nAthlete Tracker Team",
    )


def send_password_reset_success_email(email, name):
    if TEST_MODE:
        print(f"[TEST MODE] Password reset successful for {email}")
        return True
    return send_email(
        email,
        "Password Reset Successful",
        f"Hello {name},\n\nYour password has been reset successfully.\nIf you did not perform this action, contact the administrator.\n\nThank you,\nAthlete Tracker Team",
    )


def send_signup_confirmation_email(email, name, user_code):
    if TEST_MODE:
        print(f"[TEST MODE] Signup confirmation sent to {email}")
        return True
    return send_email(
        email,
        "Welcome to Athlete Tracker — Account Created Successfully",
        f"Hello {name},\n\nWelcome to Athlete Tracker! Your account has been successfully created.\n\nYour Athlete Code: {user_code}\nEmail: {email}\n\nYou can now log in to your dashboard and start tracking your fitness performance.\n\nThank you,\nAthlete Tracker Team",
    )


def send_password_reset_confirmation_email(email, name):
    if TEST_MODE:
        print(f"[TEST MODE] Password reset confirmation sent to {email}")
        return True
    return send_email(
        email,
        "Password Reset Confirmation",
        f"Hello {name},\n\nYour Athlete Tracker password has been successfully reset.\n\nIf you did not perform this action, please contact the administrator immediately.\n\nThank you,\nAthlete Tracker Team",
    )