# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| 1.1 (latest `main`) | yes |
| older tags | no (kept for the record) |

Vidura runs on the user's own machine; there is no hosted deployment.

## Reporting a problem

Please do not open a public issue for a security problem. Use GitHub's **Report a vulnerability** button on the repository's Security tab (private vulnerability reporting). Include what you found, how to reproduce it and what an attacker could do with it. You will get a reply within a week; fixes are credited in the changelog if you wish.

## In scope

- The FastAPI service (`src/finsight/api`) and the upload pipeline: PDF validation, path handling in storage, the job runner.
- Anything that lets one document's data leak into another's report, or lets a crafted PDF run code.
- The web app (`frontend/`): script injection from document text, unsafe rendering.
- Anything that would make Vidura show investment advice despite the guard and the forbidden-phrase checks.

## Out of scope

- The API has no authentication on the laptop (one local user, `auth.mode: off`). Do not expose ports 8000 or 3000 to a network. `start.bat` starts uvicorn without `--host`, so it listens on `127.0.0.1` only.
- Wrong model answers that the verifier marks ⚠️ or ❌: that is the verifier working.
- Problems in third-party software (Ollama, PyMuPDF, Next.js, Hugging Face, Kaggle, Colab): report those upstream.

## How secrets are handled

- No secret is ever committed. `.env.example` lists variable **names** only; `scripts/check_env.py` checks names and never prints values.
- The running app needs no secret. The training lanes use a Kaggle token (`~/.kaggle/kaggle.json`) and `HF_TOKEN` (environment or `.env`), both outside git.
- If a token may have leaked: revoke it on Kaggle or Hugging Face, create a new one and update the local file. The old cloud runbooks are kept in `docs/archive/` for the record.
