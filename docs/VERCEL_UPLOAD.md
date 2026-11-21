# Fit Track: Vercel deployment

The app uses Vercel for the static frontend and Flask Python function, Supabase PostgreSQL for persistent application data, and a private Supabase Storage bucket for uploads and generated certificates. SQLite is for local development only; the backend now rejects it in hosted environments.

## Deploy

Connect the Git repository to Vercel and set the project root to this repository. Vercel reads `vercel.json`, installs `requirements.txt`, serves `frontend1`, and rewrites `/api/*` requests to the `/api/index` Python function. Python 3.12 is selected by `.python-version` and is supported by Vercel's Python runtime. Alternatively, build the source archive with `python scripts/package_vercel.py` and upload `artifacts/fitness-tracker-vercel.zip` to [Vercel Drop](https://vercel.com/drop).

The Supabase database pooler hostname in this project resolves to `ap-northeast-2` (Seoul), so `api/index.py` is pinned to Vercel's `icn1` function region in `vercel.json` to keep database calls nearby. Static pages and assets continue to use Vercel's global CDN. If the database project or pooler region changes, update the function region to match it.

## Required Vercel environment variables

Add these in **Vercel → Project → Settings → Environment Variables** for the environment you deployed (usually Production; add Preview too if testing preview links). Vercel does not read a `.env` file committed to the repository or uploaded with the source archive. Enter/import the variables in the Vercel settings, then create a **new deployment** so the function receives the updated values. Keep secrets server-side; never put the service role key or database URI in frontend configuration. Set `FRONTEND_URL` separately for each environment to that environment's exact site origin.

| Variable | Value |
| --- | --- |
| `APP_ENV` | `production` |
| `DATABASE_BACKEND` | `postgres` |
| `SUPABASE_DB_URL` | Supabase Transaction pooler connection string with SSL (port `6543`) for Vercel serverless functions. |
| `DB_POOL_MIN` | `0` for Vercel serverless functions |
| `DB_POOL_MAX` | `1` per warm function instance |
| `SECRET_KEY` | Unique random value with at least 32 random bytes |
| `SUPABASE_URL` | Project URL, e.g. `https://<project-ref>.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only service role key; never expose it in the browser |
| `FIT_TRACK_STORAGE_BUCKET` | `fit-track-uploads` |
| `FRONTEND_URL` | Exact deployed origin, e.g. `https://your-project.vercel.app` |
| `FITNESS_TEST_MODE` | `false` |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_SECURITY` | SMTP host, port, and `starttls` (if email OTPs are used; Gmail defaults are `smtp.gmail.com`, `587`, `starttls`) |
| `MAIL_USERNAME`, `MAIL_PASSWORD` | **Both are required** for OTP email delivery. Use the SMTP account username and its SMTP password (for Gmail, an App Password when required). The app also accepts `SMTP_USERNAME`/`SMTP_PASSWORD` or `SMTP_USER`/`SMTP_PASS` if those are already configured. |
| `MAIL_FROM` | Verified sender address; defaults to `MAIL_USERNAME` if omitted. |
| `MAIL_TIMEOUT` | SMTP timeout in seconds; defaults to `10` |

Use [`.env.example`](../.env.example) as the variable-name template. In Vercel, add the variables individually (or paste them into the Environment Variables form); do not upload or commit a local `.env` containing secrets. After adding or editing variables, redeploy. The admin diagnostics page reports email as `not_configured` until the running deployment has both non-empty `MAIL_USERNAME` and `MAIL_PASSWORD` values. Check spelling and ensure the variables are enabled for the same environment as the deployed URL.

OTP email delivery is awaited inside the Vercel request so the function cannot return success and then be frozen before sending. SMTP errors return a failed response and are logged with the SMTP error type/code. For Gmail SMTP, use a Google App Password when required by the account's sign-in settings; Google requires 2-Step Verification for App Passwords. [Google's App Password guidance](https://support.google.com/mail/answer/185833?hl=en)

Create the `fit-track-uploads` bucket in Supabase Storage before deploying. Keep it **private**; the API streams files through authenticated routes. Do not create public policies for the service role key. Upload files are limited by `FIT_TRACK_MAX_UPLOAD_MB` (default 16 MB). In Vercel, use Supabase's Transaction pooler URL on port `6543`; this app disables persistent prepared statements for compatibility and defaults to zero idle and one maximum connection per warm function instance. Set `DB_POOL_MIN=0` and `DB_POOL_MAX=1` in Vercel too, or remove existing overrides so the serverless defaults apply. Keep the Vercel function and Supabase database in nearby regions when the project settings allow it.

## Database and first administrator

Do not assume the target Supabase project has the required schema. First create or select a dedicated non-production project and verify its connection string. Review the ordered migrations, then apply the base schema and migrations once against that staging database from a trusted local environment. For example, set `DATABASE_BACKEND=postgres` and `SUPABASE_DB_URL` to the staging URL in the current shell, then run `python backend/setup_and_run.py --init-only`. The initializer applies the base schema followed by migrations 005–014 and the sport-assessment schema migration. Migration 014 requires the Supabase pg_cron extension and installs one named hourly auth-cleanup job. Check the setup output and confirm the destination before proceeding. Never run this initializer against production as part of a routine deploy.

Only create an initial admin if the staging database has none. Configure `INITIAL_ADMIN_NAME`, `INITIAL_ADMIN_EMAIL`, and `INITIAL_ADMIN_PASSWORD` only for that setup, then remove them from the environment.

Migration 005 adds the `late` and `excused` attendance statuses to existing PostgreSQL deployments. Coaches and admins can record all four statuses. A late session counts as attended; an excused session is excluded from the attendance-rate denominator. Students can see status counts, weekly status, and their recent attendance history after the migration is applied.

## Go-live checks

Before production, deploy a Preview and verify `/api/health` reports `status: ok` and `database: ok`; then check static page/assets, student and coach/admin sign-in, OTP email, attendance including all four statuses, uploads, and authenticated downloads with staging accounts/data. Run `python scripts/verify_vercel.py` and the safe local test suite before the Preview. Vercel project variables, the Supabase schema/migrations, Storage bucket, SMTP delivery, and deployed cookies/routes still require checks in the connected accounts; a passing source audit alone does not complete those checks.
