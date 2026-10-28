"""Safe structured logging for the Flask application."""

import json
import logging
import os
import re
from datetime import datetime, timezone


ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


class JSONFormatter(logging.Formatter):
    """Format application log records as JSON without serializing request data."""

    def format(self, record):
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        event_data = getattr(record, "event_data", {})
        if isinstance(event_data, dict):
            for key in (
                "request_id",
                "route",
                "method",
                "status",
                "duration_ms",
                "user_id",
                "error_type",
            ):
                if key in event_data:
                    payload[key] = event_data[key]
        return json.dumps(payload, default=str)


class ReadableFormatter(logging.Formatter):
    """Format local logs as one readable line per event."""

    def format(self, record):
        message = ANSI_ESCAPE.sub("", record.getMessage())
        event_data = getattr(record, "event_data", {})

        if message == "API request" and isinstance(event_data, dict):
            route = event_data.get("route", "-")
            method = event_data.get("method", "-")
            status = event_data.get("status", "-")
            duration = event_data.get("duration_ms")
            timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
            duration_text = f" | {duration} ms" if duration is not None else ""
            return (
                f"{timestamp} | {record.levelname} | {record.name} | "
                f"{route} | {method} | {status}{duration_text}"
            )

        details = []
        if isinstance(event_data, dict):
            labels = (
                ("request_id", "request"),
                ("route", "route"),
                ("method", "method"),
                ("status", "status"),
                ("duration_ms", "duration"),
                ("success", "success"),
                ("user_id", "user"),
                ("error_type", "error"),
            )
            for key, label in labels:
                if key in event_data:
                    value = event_data[key]
                    if key == "user_id" and value is None:
                        value = "anonymous"
                    elif value is None:
                        continue
                    details.append(f"{label}={value}")

        timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        suffix = f" | {' | '.join(details)}" if details else ""
        return f"{timestamp} | {record.levelname:<7} | {record.name} | {message}{suffix}"


def configure_logging(app):
    """Configure readable local logs and structured production logs."""
    handler = logging.StreamHandler()
    formatter = (
        JSONFormatter()
        if os.getenv("APP_ENV", "development").lower() == "production"
        else ReadableFormatter()
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if not any(getattr(item, "_fitness_json_handler", False) for item in root_logger.handlers):
        handler._fitness_json_handler = True
        root_logger.addHandler(handler)

    # Flask/Werkzeug may install a colored handler of its own. Route those
    # records through the same formatter so local output has one consistent
    # style and no raw ANSI escape sequences.
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.handlers.clear()
    werkzeug_logger.propagate = True

    app.logger.handlers.clear()
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = True
