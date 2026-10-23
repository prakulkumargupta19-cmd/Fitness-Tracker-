# Deploy the Fitness Tracker on Vercel

The upload archive is `artifacts/fitness-tracker-vercel.zip`. Create it from the project root with:

```powershell
python scripts/package_vercel.py
```

Then open [Vercel Drop](https://vercel.com/drop), upload that ZIP, choose your team, and deploy. The ZIP contains the static frontend, Flask API, Python dependencies, and Vercel routing configuration. It deliberately excludes `.env`, local database files, caches, tests, and the prototype project.

## Configure the live services

The project needs a hosted PostgreSQL database. Vercel's temporary function filesystem and the local SQLite file are not persistent production databases.

1. Create a Supabase project and copy its PostgreSQL connection URI.
2. In the Vercel project's **Settings → Environment Variables**, add these values for **Production** (and Preview too if you will test Preview deployments):

   | Name | Value |
   | --- | --- |
   | `DATABASE_BACKEND` | `postgres` |
   | `SUPABASE_DB_URL` | Supabase PostgreSQL connection URI, including SSL mode |
   | `SECRET_KEY` | A unique random secret, at least 32 random bytes |
   | `APP_ENV` | `production` |
   | `FITNESS_TEST_MODE` | `false` |
   | `FRONTEND_URL` | The exact deployed origin, such as `https://your-project.vercel.app` |
   | `MAIL_SERVER` | Your SMTP server hostname |
   | `MAIL_PORT` | Your SMTP port, usually `587` |
   | `MAIL_SECURITY` | `starttls` |
   | `MAIL_USERNAME` | Your SMTP username |
   | `MAIL_PASSWORD` | Your SMTP password or provider app password |
   | `MAIL_FROM` | Verified sender address |

   Keep secrets in Vercel settings; do not add them to this ZIP or to frontend files. `SESSION_COOKIE_SECURE` is enabled automatically on Vercel.

3. Apply the database schema and migrations once to the Supabase database using `backend/setup_and_run.py --init-only` from a trusted local checkout with the production database URL configured. To create the first admin at the same time, also set `INITIAL_ADMIN_NAME`, `INITIAL_ADMIN_EMAIL`, and `INITIAL_ADMIN_PASSWORD` in that local process environment. Do not run this against a database containing unrelated data. Clear the initial admin password from the environment after setup.
4. Redeploy after adding environment variables, then check `https://your-project.vercel.app/api/health`.

## Before inviting real users

File uploads currently use local disk storage, which Vercel does not preserve. Uploads and generated certificates therefore need an object-storage integration (such as Supabase Storage) before those features can be relied on. The project also still needs CSRF protection and a live SMTP/database deployment check. The ZIP makes the project deployable; it does not provision these external services or make those application gaps disappear.
