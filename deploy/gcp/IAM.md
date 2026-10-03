# IAM for FinSight on Cloud Run (B3.3a)

Least privilege, two runtime service accounts and one deploy account. Nothing here is created
until Akshat says "go" (B3.3b). `${GCP_PROJECT}` is the project ID and `${FINSIGHT_BUCKET}` the
bucket.

| Account | Used by | Roles (and where) |
|---|---|---|
| `finsight-api@` | the API service | Storage Object Admin **on the bucket**; Service Account Token Creator **on itself** (V4 signed upload URLs call `signBlob`); Secret Manager Secret Accessor on `finsight-db-url` and `finsight-admin-emails`; Cloud Run Developer **on the jobs `finsight-worker` and `finsight-gpu-worker` only** (running a job with env overrides needs it) |
| `finsight-worker@` | the CPU, GPU and sweep jobs | Storage Object Admin on the bucket; Secret Manager Secret Accessor on `finsight-db-url` |
| `finsight-deployer@` | GitHub Actions (`images.yml`) through Workload Identity Federation | Artifact Registry Writer on the `finsight` repository. Nothing else: deploys are run by hand from the runbook |

Notes:
- No service-account keys are created. GitHub signs in with Workload Identity Federation, limited
  to this repository (`attribute.repository == "AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors"`).
- The provider name and deployer e-mail are repository **variables** (`GCP_WIF_PROVIDER`,
  `GCP_DEPLOY_SA`, `GCP_PROJECT`, `GCP_REGION`), not secrets: they identify, they do not grant.
- Supabase holds users and the database. Its service-role key is never given to Cloud Run: the API
  verifies user JWTs with the project's public JWKS.
