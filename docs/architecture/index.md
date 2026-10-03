# Architecture

This page shows FinSight at three levels of the C4 model (context, containers, components), then the two main flows: upload and chat. The final section shows how the training data is made. The design decisions behind it are in [B02 Architecture](../phase2/B02_ARCHITECTURE.md) and the [ADR index](../adr/index.md).

## Level 1: system context

```mermaid
flowchart LR
  R([Retail investor]) -->|reads reports, asks questions| FS[FinSight]
  A([Akshat, admin]) -->|showcase IPOs, costs| FS
  FS -->|Google sign-in| SB[Supabase Auth]
  FS -. offline, never at runtime .-> SEBI[(Public RHPs and Prospectuses from SEBI and the exchanges)]
  FS -. training only .-> HF[(Ghosh et al. Indian IPO corpus, CC BY-NC-SA)]
  FS -. training only .-> KG[Kaggle GPU notebooks]
```

FinSight explains what an offer document says. It never recommends whether to apply, buy, sell or avoid, and every model is open-weight (no hosted LLM API at runtime, ADR-002).

## Level 2: containers

```mermaid
flowchart LR
  B[Browser] --> FE[Next.js app]
  FE -->|REST + SSE /api| API[FastAPI service on the laptop]
  FE -->|optional Google sign-in| AUTH[Supabase Auth]
  API --> DB[(SQLite, or Supabase Postgres via FINSIGHT_DB__URL)]
  API --> FS[(Local files: data/store)]
  API -->|in-process thread| W[Worker: every stage]
  W --> FS
  W --> DB
  W --> M[Ollama / llama.cpp models]
```

| Container | Code | Profile | Notes |
| --- | --- | --- | --- |
| Web app | `frontend/` | any | MSW mocks with `NEXT_PUBLIC_USE_MOCKS=1` |
| API + worker | `finsight.api`, `finsight.jobs` | `dev_light`, `full` | One process; the upload job runs on a background thread |
| Worker by hand | `python -m finsight.jobs run \| simplify \| sweep` | any | Same stages without the API |

B-ADR-16 removed Google Cloud (Cloud Run, Cloud Storage, the GPU job) because the credit ran out. Nothing is hosted: the product runs on the laptop. Supabase sign-in/Postgres and a Vercel front end remain optional and free.

## Level 3: backend components

```mermaid
flowchart TB
  subgraph api [finsight.api]
    R1[routes: IPOs, X-Ray, chat, lab]
    R2[routes_uploads, routes_docs, routes_risks]
  end
  subgraph phase1 [Phase 1 packages]
    ingest --> parse --> extract
    parse --> retrieve
    extract --> verify
    normalize --> verify
    generate --> chat
    guard --> chat
    retrieve --> chat
    verify --> chat
  end
  subgraph phase2 [Phase 2 packages]
    storage
    db
    auth
    jobs --> risks
    jobs --> risklevel
    jobs --> compare
    jobs --> reports
  end
  R1 --> chat
  R1 --> extract
  R2 --> jobs
  R2 --> db
  R2 --> storage
  R2 --> auth
  risks --> generate
  risks --> guard
```

Each package lives in `src/finsight/<package>/`; other packages import it only through its `__init__.py`. The [Python packages reference](../reference/python.md) is generated from the docstrings.

## Upload sequence

```mermaid
sequenceDiagram
  participant U as Browser
  participant A as API
  participant S as Storage
  participant D as Database
  participant W as Worker job
  U->>U: SHA-256 of the file
  U->>A: POST /api/uploads/init {filename, size, sha256}
  A->>D: duplicate check by hash (doc_id comes from the SHA-256)
  alt same file already processed
    A-->>U: {status: "exists", doc_id}
  else new file
    A->>D: size and quota checks (3 per user, 10 in total per IST day), count the upload
    A->>S: signed upload URL (GCS PUT, or the API's own POST route locally)
    A-->>U: {status: "upload", doc_id, upload_url}
    U->>S: PUT the PDF
    U->>A: POST /api/uploads/{doc_id}/complete
    A->>S: re-hash the file (422 hash_mismatch if it differs)
    A->>D: create the job
    A->>W: launch (503 worker_unavailable if Cloud Run refuses)
    A-->>U: {doc_id, job_id, status: "queued"}
    U->>A: GET /api/docs/{doc_id}/events (SSE, Last-Event-ID to resume)
    loop each stage
      W->>S: stage output (parsed.json, risks.json, ...)
      W->>D: stage / progress / ready events
      A-->>U: events, polled from the database
    end
    W->>D: done {status}
    U->>A: GET /api/docs/{doc_id}/report
  end
```

## Chat sequence

```mermaid
sequenceDiagram
  participant U as Browser
  participant A as API
  participant G as Guard
  participant R as Retriever
  participant L as Local LLM
  participant V as Verifier
  U->>A: POST /api/chat {ipo_id, question, language}
  A->>G: advice, forecast or private data?
  alt blocked
    G-->>U: guard event with key facts and the SEBI note
  else allowed
    A->>R: BM25 (+ dense, RRF, rerank when on)
    alt top score below the threshold
      R-->>U: abstain event with the closest passage
    else
      R-->>U: retrieval event
      A->>L: prompt with passages [1]..[n]
      L-->>U: token events
      A->>V: every number against its cited passage
      V-->>U: verdict events (verified, unverifiable, contradicted)
      A-->>U: final event (trace id, score, timings)
    end
  end
```

## Training data flow

```mermaid
flowchart LR
  C[(Ghosh corpus: older IPO documents)] --> WL[Weak labels: cover-page seeds propagated]
  WL --> QA[Fine-tuned QA extractor, DeBERTa-v3, Kaggle]
  WL --> BL[BiLSTM-CRF baseline, Kaggle]
  C --> RS[Risk factors of 2018-2023 IPOs]
  RS --> T[Teacher: Qwen3-14B-AWQ on vLLM, Kaggle]
  T --> F[8 filters: JSON, schema, numbers, phrases, length, certainty, duplicates]
  F --> CL[Category classifier: DeBERTa-v3, ONNX int8]
  F --> ST[Student: Qwen3-4B QLoRA, GGUF Q4 / AWQ]
  RS --> BANK[(Risk bank for novelty)]
```

Every training run happens on Kaggle (never on the laptop or in a cloud session). Labels written by a model carry `label_source`, and their datasheets say so: see [Teacher outputs](../phase2/datasheets/teacher_outputs.md).
