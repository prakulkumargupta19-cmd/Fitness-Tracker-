# Security Policy

Security reporting guidance for the Fitness Performance Tracker repository (`Inspiria-InSeed/fitness-tracker`). Do not include secrets, OTPs, session cookies, personal records, or production database contents in a report.

## Supported versions

The repository currently declares application version `1.0.0` in `pyproject.toml`, but it does not publish a release/support lifecycle or identify maintained branches. Until maintainers publish one, assume only the latest code on `main` is considered for fixes; no older release is guaranteed security support. This is a provisional expectation, not a formal support commitment.

## Report a vulnerability

**Do not open a public GitHub issue or pull request for an unpatched vulnerability.** Use GitHub's private vulnerability reporting for this repository if the feature is enabled: open the repository's **Security** tab and select **Report a vulnerability**. If private reporting is unavailable, contact a repository owner/maintainer privately through an independently verified organizational contact channel and ask for a secure reporting route. No dedicated security email address is published in this repository; do not guess one or send sensitive details to an unverified address.

Include, where safe:

- A concise description and potential impact.
- Affected version/commit and component/endpoint.
- Reproduction steps or a minimal proof of concept using synthetic data.
- Any mitigations already identified.

Give maintainers a reasonable opportunity to investigate and fix the issue before public disclosure. Coordinate disclosure timing directly with maintainers; this repository has not published a fixed response or disclosure deadline. Avoid accessing, changing, or downloading other users' data, and stop testing if you encounter real personal information.

## Response expectations

No formal service-level response time or disclosure timeline is established. Maintainers should acknowledge reports, assess impact, coordinate a fix and release, and agree on disclosure with the reporter. Do not interpret this guidance as a guaranteed response time.

## Security-sensitive areas

Examples include authentication/OTP/password reset, session and CSRF handling, role checks/data scoping, database migrations and credentials, SMTP, uploads/downloads, and deployment configuration. Report suspected exposure promptly through the private route above.