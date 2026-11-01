# Fit Track: Vercel deployment

The app uses Vercel for the static frontend and Flask Python function, Supabase PostgreSQL for persistent application data, and a private Supabase Storage bucket for uploads and generated certificates. SQLite is for local development only; the backend now rejects it in hosted environments.

## Deploy

Connect the Git repository to Vercel and set the project root to this repository. Vercel reads `vercel.json`, installs `requirements.txt`, serves `frontend1`, and rewrites `/api/*` requests to the `/api/index` Python function. Alternatively, build the source archive with `python scripts/package_vercel.py` and upload `artifacts/fitness-tracker-vercel.zip` to [Vercel Drop](https://vercel.com/drop).

## Required Vercel environment variables

Set these in Vercel Project Settings for Preview and Production. Keep secrets server-side; never put the service role key or database URI in frontend configuration. Set `FRONTEND_URL` separately for each environment to that environment's exact site origin.

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
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_SECURITY` | SMTP host, port, and `starttls` (if email OTPs are used) |
| `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM` | SMTP credentials and verified sender (if email OTPs are used) |

Create the `fit-track-uploads` bucket in Supabase Storage before deploying. Keep it **private**; the API streams files through authenticated routes. Do not create public policies for the service role key. Upload files are limited by `FIT_TRACK_MAX_UPLOAD_MB` (default 16 MB). In Vercel, use Supabase's Transaction pooler URL on port `6543`; this app disables persistent prepared statements for compatibility and defaults to zero idle and one maximum connection per warm function instance. Set `DB_POOL_MIN=0` and `DB_POOL_MAX=1` in Vercel too, or remove existing overrides so the serverless defaults apply. Keep the Vercel function and Supabase database in nearby regions when the project settings allow it.

## Database and first administrator

Do not assume the target Supabase project has the required schema. First create or select a dedicated non-production project and verify its connection string. Review the ordered migrations, then apply the base schema and migrations once against that staging database from a trusted local environment. For example, set `DATABASE_BACKEND=postgres` and `SUPABASE_DB_URL` to the staging URL in the current shell, then run `python backend/setup_and_run.py --init-only`. Check the setup output and confirm the destination before proceeding. Never run this initializer against production as part of a routine deploy.

Only create an initial admin if the staging database has none. Configure `INITIAL_ADMIN_NAME`, `INITIAL_ADMIN_EMAIL`, and `INITIAL_ADMIN_PASSWORD` only for that setup, then remove them from the environment.

Migration 005 adds the `late` and `excused` attendance statuses to existing PostgreSQL deployments. Coaches and admins can record all four statuses. A late session counts as attended; an excused session is excluded from the attendance-rate denominator. Students can see status counts, weekly status, and their recent attendance history after the migration is applied.

## Go-live checks

Before production, deploy a Preview and verify `/api/health` reports `status: ok` and `database: ok`; then check static page/assets, student and coach/admin sign-in, OTP email, attendance including all four statuses, uploads, and authenticated downloads with staging accounts/data. Run `python scripts/verify_vercel.py` and the safe local test suite before the Preview. Vercel project variables, the Supabase schema/migrations, Storage bucket, SMTP delivery, and deployed cookies/routes still require checks in the connected accounts; a passing source audit alone does not complete those checks.
