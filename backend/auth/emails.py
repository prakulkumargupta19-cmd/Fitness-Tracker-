"""Email-sending helpers for authentication flows.

This module contains the email helpers extracted from ``backend.app``.
It has no dependency on the Flask application instance or module
(``backend.app``), and uses ``flask.current_app`` only for logging.
"""

import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from flask import current_app
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# Match the semantics used by backend.app (no import from it).
TEST_MODE = os.getenv("FITNESS_TEST_MODE", "false").lower() == "true"
OTP_MINUTES = 3


def _test_mode():
    return TEST_MODE or os.getenv("FITNESS_TEST_MODE", "false").lower() == "true"


def smtp_settings():
    """Return validated SMTP settings without exposing the password."""
    username = os.getenv("MAIL_USERNAME", "").strip()
    password = os.getenv("MAIL_PASSWORD", "")
    host = os.getenv("MAIL_SERVER", "smtp.gmail.com").strip()
    security = os.getenv("MAIL_SECURITY", "starttls").strip().lower()
    try:
        port = int(os.getenv("MAIL_PORT", "587"))
        timeout = float(os.getenv("MAIL_TIMEOUT", "20"))
    except ValueError as error:
        raise ValueError("MAIL_PORT and MAIL_TIMEOUT must be numeric.") from error
    if not host or not 1 <= port <= 65535:
        raise ValueError("MAIL_SERVER and MAIL_PORT must be configured correctly.")
    if security not in {"starttls", "tls", "ssl", "smtps", "none"}:
        raise ValueError("MAIL_SECURITY must be starttls, ssl, or none.")
    return {
        "username": username,
        "password": password,
        "host": host,
        "port": port,
        "timeout": timeout,
        "security": security,
        "from": os.getenv("MAIL_FROM", "").strip() or username,
    }


def check_smtp_connection():
    """Connect and authenticate without sending an email."""
    settings = smtp_settings()
    if not settings["username"] or not settings["password"]:
        raise ValueError("MAIL_USERNAME and MAIL_PASSWORD are required.")
    server = None
    try:
        if settings["security"] in ("ssl", "smtps") or settings["port"] == 465:
            server = smtplib.SMTP_SSL(
                settings["host"], settings["port"], timeout=settings["timeout"],
                context=ssl.create_default_context(),
            )
        else:
            server = smtplib.SMTP(
                settings["host"], settings["port"], timeout=settings["timeout"]
            )
            server.ehlo()
            if settings["security"] in ("starttls", "tls"):
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
        server.login(settings["username"], settings["password"])
    finally:
        if server is not None:
            server.quit()


def display_role(role):
    """Return a human-readable role label."""
    return "Student" if role == "player" else str(role or "").capitalize()


def send_email(recipient, subject, body):
    try:
        settings = smtp_settings()
    except ValueError as error:
        current_app.logger.error("Email configuration is invalid (%s)", type(error).__name__)
        return False
    if not settings["username"] or not settings["password"]:
        current_app.logger.warning(
            "Email not configured: set MAIL_USERNAME and MAIL_PASSWORD"
        )
        return False
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings["from"]
    message["To"] = recipient
    message.set_content(body)
    try:
        if settings["security"] in ("ssl", "smtps") or settings["port"] == 465:
            server = smtplib.SMTP_SSL(
                settings["host"],
                settings["port"],
                timeout=settings["timeout"],
                context=ssl.create_default_context(),
            )
        else:
            server = smtplib.SMTP(
                settings["host"], settings["port"], timeout=settings["timeout"]
            )

        with server:
            server.ehlo()
            if settings["security"] in ("starttls", "tls"):
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            server.login(settings["username"], settings["password"])
            server.send_message(message)
        return True
    except (OSError, smtplib.SMTPException, ValueError) as error:
        current_app.logger.error(
            "Email delivery failed (%s)",
            type(error).__name__,
        )
        return False


def send_otp_email(email, name, purpose, otp):
    action = {
        "password_reset": "password reset",
        "login": "login verification",
    }.get(purpose, "account verification")
    if _test_mode():
        return True
    return send_email(
        email,
        f"Athlete Tracker – {action.title()} OTP",
        f"Hello {name},\n\nYour Athlete Tracker {action} OTP is:\n\n{otp}\n\nThis OTP expires in {OTP_MINUTES} minutes.\n\nThank you,\nAthlete Tracker Team",
    )


def send_account_created_email(email, name, role):
    if _test_mode():
        return True
    return send_email(
        email,
        "Athlete Tracker Account Created Successfully",
        f"Hello {name},\n\nCongratulations!\n\nYour Athlete Tracker account has been created.\nAccount Type: {display_role(role)}\n\nYou can now log in.\n\nThank you,\nAthlete Tracker Team",
    )


def send_coach_approval_email(email, name, status):
    approved = status == "approved"
    subject = "Coach application approved" if approved else "Coach application rejected"
    body = (
        f"Hello {name},\n\nYour coach application has been approved by the administrator. "
        "You can now log in to your coach dashboard.\n\nFitness Performance Tracker"
        if approved
        else f"Hello {name},\n\nYour coach application was not approved by the administrator. "
        "Please contact the administrator for more information.\n\nFitness Performance Tracker"
    )
    if _test_mode():
        return True
    return send_email(email, subject, body)


def send_password_reset_success_email(email, name):
    if _test_mode():
        return True
    return send_email(
        email,
        "Password Reset Successful",
        f"Hello {name},\n\nYour password has been reset successfully.\nIf you did not perform this action, contact the administrator.\n\nThank you,\nAthlete Tracker Team",
    )


def send_signup_confirmation_email(email, name, user_code):
    if _test_mode():
        return True
    return send_email(
        email,
        "Welcome to Athlete Tracker — Account Created Successfully",
        f"Hello {name},\n\nWelcome to Athlete Tracker! Your account has been successfully created.\n\nYour Athlete Code: {user_code}\nEmail: {email}\n\nYou can now log in to your dashboard and start tracking your fitness performance.\n\nThank you,\nAthlete Tracker Team",
    )


def send_password_reset_confirmation_email(email, name):
    if _test_mode():
        return True
    return send_email(
        email,
        "Password Reset Confirmation",
        f"Hello {name},\n\nYour Athlete Tracker password has been successfully reset.\n\nIf you did not perform this action, please contact the administrator immediately.\n\nThank you,\nAthlete Tracker Team",
    )
