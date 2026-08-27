# Fitness Performance Tracker

Flask, SQLite, and static frontend for Admin, Coach, and Student fitness tracking.

## Run locally

Copy `.env.example` to `.env`, fill in your real SMTP details, then start the server. For Gmail, `MAIL_PASSWORD` must be a **Google App Password** (not your normal Gmail password); enable two-step verification first.

Alternatively, configure the values in PowerShell:

```powershell
$env:SECRET_KEY = "replace-with-a-long-random-secret"
$env:MAIL_SERVER = "smtp.gmail.com"
$env:MAIL_PORT = "587"
$env:MAIL_USERNAME = "your-email@example.com"
$env:MAIL_PASSWORD = "your-app-password"
$env:MAIL_FROM = "your-email@example.com"
python backend/app.py
```

Open `http://127.0.0.1:5000`. The app serves `frontend1` directly, so API calls and the secure session cookie remain same-origin.

Never commit `SECRET_KEY` or mail credentials.
