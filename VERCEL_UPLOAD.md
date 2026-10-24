# Fit Track: Vercel deployment

The app is configured as a Vercel static frontend plus a Python Flask function, using Supabase PostgreSQL for persistent application data and a private Supabase Storage bucket for uploads and generated certificates.

## Deploy

Connect the Git repository to Vercel and set the project root to this repository. Vercel reads `vercel.json`, installs `requirements.txt`, serves `frontend1`, and routes `/api/*` to `api/index.py`. Alternatively, build the source archive with `python scripts/package_vercel.py` and upload the generated `artifacts/fitness-tracker-vercel.zip` to [Vercel Drop](https://vercel.com/drop).

## Required Vercel environment variables

Set these for Production and Preview environments. Keep secrets server-side; never put the service role key or database URI in frontend configuration.

| Variable | Value |
| --- | --- |
| `APP_ENV` | `production` |
| `DATABASE_BACKEND` | `postgres` |
| `SUPABASE_DB_URL` | Supabase PostgreSQL connection string with SSL. For serverless use the Supabase pooler connection string. |
| `DB_POOL_MAX` | `2` |
| `SECRET_KEY` | Unique random value with at least 32 random bytes |
| `SUPABASE_URL` | Project URL, e.g. `https://<project-ref>.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only service role key; never expose it in the browser |
| `FIT_TRACK_STORAGE_BUCKET` | `fit-track-uploads` |
| `FRONTEND_URL` | Exact deployed origin, e.g. `https://your-project.vercel.app` |
| `FITNESS_TEST_MODE` | `false` |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_SECURITY` | SMTP host, port, and `starttls` (if email OTPs are used) |
| `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM` | SMTP credentials and verified sender (if email OTPs are used) |

Create the `fit-track-uploads` bucket in Supabase Storage before deploying. Keep it **private**; the API streams files through authenticated routes. Do not create public policies for the service role key. Upload files are limited by `FIT_TRACK_MAX_UPLOAD_MB` (default 16 MB). Set Vercel's database URL to Supabase's pooler URI, preferably in transaction mode, to avoid using a new direct database connection for every serverless instance. Keep the Vercel function and Supabase database in nearby regions when the project settings allow it.

## Database and first administrator

This project’s current Supabase schema is already initialized. If deploying to a different or empty Supabase project, apply the repository schema and migrations once from a trusted local environment. Only create an initial admin if the target database has none; configure `INITIAL_ADMIN_NAME`, `INITIAL_ADMIN_EMAIL`, and `INITIAL_ADMIN_PASSWORD` only in that trusted setup process, then remove them.

## Go-live checks

After setting variables and redeploying, open `/api/health` and confirm the JSON reports `status: ok` and `database: ok`. Then verify sign-in/OTP email, an upload, and a file download in the deployed app. Vercel project variables, the Storage bucket, SMTP delivery, and the actual hosted deployment must be checked in the user's Vercel/Supabase accounts; they cannot be provisioned by this source archive alone.
