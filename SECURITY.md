# Security policy

## Supported versions

Only the latest code on `main` (and the deployment built from it, once FinSight is live) gets security fixes. Older tags are kept for the record and are not patched.

## Reporting a problem

Please do not open a public issue for a security problem. Report it privately through GitHub's **Report a vulnerability** button on the repository's Security tab (private vulnerability reporting). Include what you found, how to reproduce it and what an attacker could do with it. You will get a reply within a week; fixes are credited in the changelog if you wish.

## In scope

- The FastAPI service (`src/finsight/api`) and the upload pipeline: file validation, signed upload URLs, quotas, authorisation of one user's documents and reports.
- The web app (`frontend/`): authentication with Supabase, anything that could expose another user's uploads or email.
- The deployment definitions in `deploy/` (service accounts, bucket access, secrets wiring).
- Anything that would make FinSight show investment advice despite the guard.

## Out of scope

- Denial of service by volume (uploads are rate-limited and capped per day by design).
- Problems in third-party services (Google Cloud, Supabase, Vercel, Kaggle) — report those to the provider.
- Model answers that are wrong but flagged ⚠️ or ❌ by the verifier: that is the verifier working.

## How secrets are handled

- No secret is ever committed. `.env.example` lists variable **names** only; `scripts/check_env.py` checks names, never prints values.
- In the cloud, secrets live in Google Secret Manager and reach Cloud Run as environment variables at instance start; the browser only ever gets the Supabase URL and anon key, which are public by design.
- Uploaded PDFs are stored privately, reached only through short-lived signed URLs, and deleted after 30 days.
- Rotation steps: [Rotate secrets](docs/runbooks/ROTATE_SECRETS.md).
