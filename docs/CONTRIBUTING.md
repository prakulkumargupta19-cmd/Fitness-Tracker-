# Contributing

Thank you for considering a contribution to the Fitness Performance Tracker repository. These instructions apply to the repository root (not a separate `FIT-TRACK` project).

## Before you start

1. Check existing issues and pull requests to avoid duplicate work.
2. For a significant feature, behavior change, schema change, or security-sensitive change, open an issue or discussion first. The project has no checked-in issue templates or published contribution agreement at this time.
3. Never include real user data, credentials, session cookies, OTP values, database URLs, or production logs in an issue, commit, test fixture, or screenshot.

## Report a bug

Use the repository's GitHub Issues page. Include:

- A concise title and the affected page/API workflow.
- Steps to reproduce, expected result, and actual result.
- Relevant sanitized error output and request/response status (remove secrets and personal data).
- Environment: OS, Python version, selected database mode, and whether local, test, or Preview.
- Whether the issue reproduces on the current `main` branch and the smallest safe reproduction you can provide.

Do not report exploitable vulnerabilities in a public issue; follow [SECURITY.md](SECURITY.md).

## Branching and commits

- The repository's default branch is `main`. Create a short-lived branch from the latest `main` (for example, `fix/csrf-test-setup` or `feat/attendance-export`).
- There is no documented `develop` branch or release branching model; target pull requests at `main` unless maintainers state otherwise.
- Use clear, imperative commit messages and keep each commit focused. Do not rewrite shared branch history.

## Coding guidelines

- Follow established patterns: Flask/Python backend, pytest tests, and plain HTML/CSS/JavaScript frontend. Avoid introducing a new framework or runtime dependency without explaining the need.
- Keep authorization, validation, and data scoping server-side. Preserve CSRF protections and role checks.
- Add focused tests for behavior changes, including denied/unauthorized cases where relevant.
- For database changes, update the appropriate PostgreSQL and/or local SQLite schema, add an ordered migration as needed, and test against a disposable non-production database. Never use production for development tests.
- Keep credentials out of code and logs; `.env` is local-only. Do not log OTPs.
- No formatter, linter, or static type checker is configured as a required project tool. Avoid reformatting unrelated files; match surrounding style.

## Verify locally

From the repository root, install the development dependencies and run:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/verify_vercel.py
```

The PostgreSQL workflow tests are opt-in; use only a dedicated test database as described in [DEVELOPER_SETUP.md](DEVELOPER_SETUP.md). Current test and audit failures are documented in [PROJECT_READINESS.md](PROJECT_READINESS.md). If a check fails, report whether the failure is pre-existing and include its sanitized output; do not claim checks passed when they did not.

## Pull requests

1. Rebase or merge the latest `main` into your branch as appropriate.
2. Keep the PR focused. Explain the problem, the implementation, any schema/environment implications, and any security/privacy impact.
3. Link related issues and include screenshots for visible UI changes (with synthetic data only).
4. List exact verification commands and their actual results. Note any tests requiring external services that were not run.
5. Update relevant docs (`README.md`, setup, project docs, or readiness notes) when behavior or setup changes.
6. Request review from repository maintainers. A maintainer must approve and resolve requested changes before merge; no automated CI/review policy is currently documented in this repository.

## License and contributions

No `LICENSE` file or contribution license terms were found. Do not assume contributions are licensed under MIT or another open-source license. The project owner should publish a license and contribution policy before accepting external contributions broadly.