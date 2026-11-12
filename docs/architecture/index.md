# System overview

Vidura is one Python process (FastAPI API plus an in-process job runner), a Next.js web app and
Ollama, all on one laptop. Documents and results are local files and a SQLite database. This page shows
the system at three levels (context, containers, components) and the two main flows. Each stage is
detailed on [Pipeline stages](pipeline.md); the reasons are in the [decision records](../adr/index.md).

## Context

```mermaid
flowchart LR
  R([Retail investor]) -->|uploads an offer document, reads the report, asks questions| FS[Vidura on a laptop]
  FS -. offline, never at runtime .-> SEBI[(Public RHPs and prospectuses: SEBI, NSE, BSE)]
  FS -. training only .-> HF[(Ghosh et al. Indian IPO corpus, CC BY-NC-SA 4.0)]
  FS -. training only .-> GPU[Kaggle and Colab GPU notebooks]
```

No hosted LLM API is called at runtime (ADR-002, B-ADR-06); every model is open-weight. Nothing is
hosted: the Google Cloud design was removed (B-ADR-16) and deployment was cut with Phase 4.

## Containers

```mermaid
flowchart LR
  B[Browser] --> FE["Next.js web app :3000"]
  FE -->|"REST + SSE /api/*"| API["FastAPI :8000 (profile local)"]
  API --> DB[("SQLite data/finsight.db")]
  API --> FS[("Files data/store/docs/&lt;doc_id&gt;/")]
  API -->|background thread| W[Job runner: 14 stages]
  W --> FS
  W --> DB
  W -->|plain-English rewrites| OL["Ollama :11434 finsight-student:q4"]
  API -->|chat answers| OL
  W --> ONNX[ONNX risk classifier, CPU]
  W --> EMB["bge-m3 embeddings (novelty)"]
  API --> RR["bge-reranker-v2-m3 (chat retrieval)"]
```

| Container | Code | How it starts |
| --- | --- | --- |
| Web app | `frontend/` (Next.js App Router) | `pnpm dev --port 3000` from `start.bat` |
| API + job runner | `vidura.api`, `vidura.jobs` | `uvicorn vidura.api.app:app --port 8000` from `start.bat` |
| Model server | Ollama | `ollama serve` from `start.bat` |
| Jobs by hand | `python -m vidura.jobs run \| simplify \| forget \| sweep` | command line, same stages without the API |

Supabase sign-in and Postgres still exist in code (`vidura.auth`, `VIDURA_DB__URL`) but are off:
without Supabase settings every request is one local user ([Settings](../reference/config.md)).

## Components

```mermaid
flowchart TB
  subgraph api [vidura.api]
    R1[routes: IPOs, X-Ray, chat, lab, glossary]
    R2[routes_uploads, routes_docs, routes_risks]
  end
  subgraph read [Reading the document]
    ingest --> parse --> sections[parse: sections and tables]
    sections --> extract
    sections --> summary["summary: financials and SOD engine"]
    normalize --> extract
    normalize --> verify
  end
  subgraph judge [Judging what it says]
    redflags
    risks
    risklevel
    compare
  end
  subgraph ask [Chat]
    guard --> chat
    retrieve --> chat
    generate --> chat
    verify --> chat
  end
  R1 --> chat
  R1 --> extract
  R2 --> jobs
  jobs --> read
  jobs --> judge
  jobs --> reports
  jobs --> storage
  jobs --> db
  summary --> redflags
  risks --> risklevel
  redflags --> risklevel
  summary --> compare
  risks --> generate
```

Each package lives in `src/vidura/<package>/` and is imported only through its `__init__.py`; its
docstring states its job ([Python packages](../reference/python.md)). The packages by job:

| Package | Job |
| --- | --- |
| `core` | Schemas, settings, logging and IDs shared by every package |
| `ingest` | Showcase registry, corpus builder, upload checks (`validate_pdf`) |
| `parse` | PDF to words, boxes and page images (PyMuPDF), sections and tables |
| `normalize` | Indian number formats: lakh, crore, million, `[●]` placeholders, periods |
| `extract` | Field extractors (rules first, fine-tuned QA as cross-check) and the X-Ray fact sheet |
| `summary` | Financial summary and the Summary of the Offer Document (SOD) engine |
| `redflags` | 13 rule-based checks and serious findings with their subject |
| `risks` | Risk factors: split, classify (ONNX), novelty (bge-m3), hedging, seriousness |
| `risklevel` | Points, share of points possible, Low / Medium / High, overrides |
| `compare` | Listed peers from the document and the past-IPO reference |
| `reports` | Assemble `report.json` from the stage outputs |
| `retrieve`, `generate`, `guard`, `verify`, `chat` | Chat: BM25 + reranker, the student, the advice guard, the number checker |
| `jobs`, `storage`, `db`, `auth` | Job runner and cache, files, database, the local user |
| `evaluate`, `bench`, `weaklabel`, `splits`, `handoff` | Evaluation, Vidura Bench, weak labels, time split, Phase 4 hand-off pack |

## Upload sequence

```mermaid
sequenceDiagram
  participant U as Browser
  participant A as API
  participant S as data/store
  participant D as SQLite
  participant W as Job runner
  U->>U: SHA-256 of the file
  U->>A: POST /api/uploads/init {filename, size_bytes, sha256}
  A->>D: doc_id = "doc_" + first 16 hex of the hash
  alt same file, current pipeline version
    A-->>U: {status: "exists", doc_id}
  else new or stale
    A->>D: size and daily-quota checks
    A-->>U: {status: "upload", doc_id, upload_url}
    U->>A: POST /api/uploads/{doc_id}/file (the PDF)
    A->>S: source.pdf
    U->>A: POST /api/uploads/{doc_id}/complete {analyse_without?}
    A->>A: model preflight (503 models_unavailable unless skipped)
    A->>S: re-hash (422 hash_mismatch if it differs)
    A->>W: start the job on a background thread
    A-->>U: {doc_id, job_id, status: "queued"}
    U->>A: GET /api/docs/{doc_id}/events (SSE, resumable)
    loop each stage
      W->>S: stage output (parsed.json, redflags.json, ...)
      W->>D: stage, progress and ready events
      A-->>U: events
    end
    W->>D: done; analysis_status complete / degraded / failed
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
  participant L as Student (Ollama)
  participant V as Number checker
  U->>A: POST /api/chat {ipo_id, question}
  A->>G: advice, forecast or private data?
  alt declined
    G-->>U: guard event with the key facts
  else allowed
    A->>R: BM25, then the cross-encoder reranker
    alt top score below the abstain threshold
      R-->>U: abstain event with the closest passage
    else
      A->>L: prompt with passages [1]..[n]
      L-->>U: token events
      A->>V: every number against its cited passage
      V-->>U: verdicts (verified, unverifiable, contradicted)
      A-->>U: final event (trace id, timings)
    end
  end
```

## Training data flow

```mermaid
flowchart LR
  C[(Ghosh corpus: 389 IPOs 2009–2023)] --> WL[Weak labels: cover-page seeds propagated]
  N[(Recent RHPs 2024–2026: 275 parsed)] --> WL
  WL --> QA["Field extractor: DeBERTa-v3 QA (Kaggle)"]
  C --> RS[Train-slice risk factors]
  N --> RS
  RS --> T["Teacher: Gemma-4-31B-it (Colab G4)"]
  T --> F[Filters: numbers, phrases, length, certainty, category remap]
  F --> CL["Risk classifier: DeBERTa-v3-base, ONNX fp32 (Kaggle)"]
  F --> ST["Student: Qwen3-4B LoRA, GGUF Q4_K_M (Colab G4)"]
  RS --> BANK[("Risk bank: 29,677 risks, 440 IPOs")]
```

Training never runs on the laptop ([training lanes](../operations/training-lanes.md)). Labels written by
a model carry `label_source`; test-slice and bench IPOs never enter training (C-ADR-02,
[Data](../data/index.md)).
