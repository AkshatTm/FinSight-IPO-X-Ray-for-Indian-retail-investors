# Deploy to Google Cloud Run

Deploying costs money once billing is on, so it happens only after Akshat's explicit "go".

- First-time setup (accounts, project, budget alert, bucket, service accounts): [Hosting setup](../phase2/HOSTING_SETUP_STEPS.md).
- The deploy itself, step by step: [Deploy runbook](../runbooks/DEPLOY_RUNBOOK.md).
- If something goes wrong: [Rollback](../runbooks/ROLLBACK.md) and [Costs spiking / GPU stuck](../runbooks/COST_INCIDENT.md).
- After a deploy: [Monitoring and logs](../runbooks/MONITORING.md).

The container images are built in CI on every pull request (`deploy.yml`) and smoke-tested against the API container, so a deploy starts from images that are known to boot.
