# Hosting comparison (B0.3, B-ADR-04)

Checked on 3 Oct 2026 against the provider docs. Prices are approximate; the budget alert (₹2,000/month) is the real guard.

| | **GCP Cloud Run, CPU only** (`cloud`) | **GCP Cloud Run + L4 GPU job** (`cloud_gpu`) | **HF Docker Space** (`deploy_cpu`, fallback) |
|---|---|---|---|
| Status | primary when billing is on | default once billing and the L4 job quota exist | paid, optional |
| Who pays | pay per use; scales to zero | pay per use; the L4 is billed per instance-second while a job runs | HF PRO ~$9/month |
| Upload pipeline | every stage on the CPU job; top 15 risks rewritten by the student GGUF Q4, the rest on click | CPU job + GPU job (vLLM student, bge-m3 dense index) | showcase only; no uploads |
| Rewrite speed (B01 §7) | CPU targets | GPU targets | n/a |
| Chat | qwen3.5:2b Q4 llama.cpp, BM25 | same, plus dense retrieval | qwen3.5:2b Q4 (ADR-022) |
| Storage | GCS, signed URLs | GCS | baked into the image |
| Region | asia-southeast1 | asia-southeast1 (Mumbai L4 is invite-only) | HF-managed |
| Cold start | API 5–15 s, job 30–60 s | GPU job minutes (measured in E23) | Space sleeps; ~1 min wake |
| Risk | CPU rewrite is slow for long lists | quota request may take days; free trial gets no GPU | single container, no auth |

**Decision:** build for `cloud_gpu`, keep `cloud` working as the automatic fallback, and keep the HF Space as a paid emergency fallback. Nothing is deployed until Akshat says "go".
