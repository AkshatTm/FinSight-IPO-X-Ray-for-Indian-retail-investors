# Phase 4 — Handoff contract between CC and ARGON

Two directions: **CC → ARGON** (the handoff pack: data + baselines + interfaces) and **ARGON → CC** (deliveries:
models + labels). Both are files in git. Chat between agents does not exist; files are the only channel.

---

## A. CC → ARGON: the handoff pack (`ml/handoff/`, built in CC-02)

ARGON must not explore the product repo to understand history. Everything it needs is here.

```
ml/handoff/
├── README.md                 # what each file is, how it was made, row counts, label_source of every set
├── READY                     # empty marker file; ARGON starts training work only when this exists
├── context/
│   ├── project_summary.md    # 1 page: what FinSight is, pipeline, where each model plugs in
│   ├── phase3_models.md      # what exists today per model: architecture, data, hyper-params, scores, ADR refs
│   └── interfaces.md         # exact Python signatures + pydantic schemas the deliveries must satisfy (copy of section C)
├── data/                     # frozen exports: gzip files ≤ 4.5 MB are committed; larger ones live in the private HF dataset repo (README: repo id, revision, SHA256 per file; Akshat puts an HF read token in Colab secrets)
│   ├── splits_by_ipo.json    # train/dev/test IPO ids used in phase 3 — ARGON must reuse them
│   ├── excluded_ipos.json    # ALL 110 test-slice IPOs + SME-excluded + demo + Bench v1 + Platform Bench (incl. Jio): NEVER in any training set
│   ├── risk_bank.parquet     # 29,677 risk factors, train+dev only (ipo_id, title, text, page, category, severity_band, label_source; section is empty, see README gaps)
│   ├── classifier_train.jsonl.gz / classifier_dev.jsonl.gz / classifier_test.jsonl.gz   # test = gold-150, EVAL ONLY
│   ├── student_v1_train.jsonl.gz / student_v1_dev.jsonl.gz  # existing teacher-generated SFT data (10,891 clean pairs → 10,362 train / 529 dev)
│   ├── student_prompt_template.txt  # EXACT risk-rewrite template the app uses — must not change
│   ├── student_chat_template.txt (+ _hi.txt)  # EXACT chat-answer template (build_prompt) — M1's primary target — must not change
│   ├── serious_finding_hits.jsonl.gz  # every sentence a severe pattern matched on the parsed 2024+ documents, with rules_decision (fired / blocked_soft / blocked_no_debt), page, 2 sentences of context each side
│   ├── five_things_selection.jsonl.gz # what the current "Five things to know" picked per IPO + the method used (baseline for M2)
│   ├── bench_v1/             # FinSight Bench v1 items, keys, prompts, stored retrieval (EVAL ONLY)
│   ├── MANIFEST.json         # size, sha256 and location (git / HF) of every file in data/
│   └── gold/                 # gold-50 (simplification), gold-150 (risk categories), gold v3 (10 IPOs)
├── eval/
│   ├── run_bench.py          # thin wrapper (laptop, product repo): evaluate a student candidate on Bench v1 Tasks A and C
│   ├── run_classifier_eval.py # macro-F1 / severe-band recall, 3-seed aggregation, verdict vs baselines.json
│   ├── numkeep.py            # M1 number-keeping filter
│   ├── vendor/finsight_lite/ # stand-alone copy of the product normaliser + metrics (no product import)
│   └── baselines.json        # every current number ARGON must beat (see section D)
└── colab/
    ├── setup_cell.py         # mount Drive, install pinned deps, set seeds, checkpoint dir convention
    └── requirements_colab.txt
```

Rules for CC when building the pack:
- Export, don't move. Product code keeps working unchanged.
- Every dataset row carries `ipo_id` and `label_source` (`human`, `human_verified_ai`, `ai`, `rule`, `model` = predicted by a shipped classifier).
- SOD fixture word boxes for the 10 IPOs ARGON proposes (`## REQUEST sod_fixture_ids`) are exported by CC into `tests/fixtures/real/` after the request.
- `excluded_ipos.json` is enforced by a test (`tests/ml/test_no_leakage.py`, owned by CC) that fails if any excluded
  IPO appears in any `ml/` training file.
- Run `run_bench.py` and `run_classifier_eval.py` once on the current models and write the results into
  `baselines.json`, so ARGON's comparisons are apples to apples. For severity it records severe-band recall/precision, band MAE, split, seeds, and the category macro-F1 guardrail separately.

## B. ARGON → CC: deliveries (`ml/deliveries/<model_id>/<version>/`)

```
ml/deliveries/m3_event_clf/v1/
├── MODEL_CARD.md      # data, label_source mix, hyper-params, seeds, compute used, known failure cases
├── metrics.json       # schema in section D
├── predict.py         # implements the interface in section C; no imports from the product package
├── requirements.txt   # pinned; must be a subset of the product's deps or explicitly listed as new
├── SHA256SUMS         # of weight files
└── WEIGHTS.md         # where the weights are (Drive path / private HF repo), size, format, and where Akshat must put them: models/<model_id>/<version>/
```

A delivery is **ready** only when ARGON appends to `docs/phase4/comms/to_cc.md`:
```
## DELIVERY m3_event_clf v1 — <date>
- commit: <sha on p4/argon>
- verdict vs baseline: BEATS / TIES / LOSES  (numbers)
- weights placed by Akshat: yes/no
- integration notes: ...
```
CC integrates only BEATS deliveries (or TIES with a stated reason). LOSES → stays in `ml/deliveries` as an ablation for the report.

Label deliveries (no model) follow the same format with `data/gold/<set>/` and a `LABELS_CARD.md`
(count, method, how many Akshat verified, label_source per row).

## C. Interfaces (frozen after CC-02; change only via Akshat)

```python
# All inputs/outputs are plain dicts/dataclasses so predict.py never imports product code.

# M1 student v2 — no Python interface. Delivered as GGUF q4_K_M + Ollama Modelfile.
#   Ollama tag: finsight-student:v2-q4
#   Must use ml/handoff/data/student_prompt_template.txt unchanged.

# M2 salience ranker
def rank_risks(risks: list[dict], doc_meta: dict) -> list[float]:
    """risks: [{"risk_id","text","section","page","category","severity"}]; doc_meta: {"ipo_id","company","sector"}.
    Returns one score per risk (higher = show first). Deterministic. CPU, <= 2 s for 300 risks."""

# M3 event classifier
LABELS = ["actual_event", "hypothetical", "negated", "not_relevant"]
def classify_events(items: list[dict]) -> list[dict]:
    """items: [{"id","sentence","context_before","context_after","check_id"}]  # check_id: a severe kind of redflags/severe.py
    Returns [{"id","label","probs": {label: float}}]. CPU, <= 50 ms/item."""

# M4 severity v2 — the seriousness band head of the current classifier (bands 1-4, 4 = severe)
def predict_severity(texts: list[str]) -> list[dict]:
    """Returns [{"band": 1..4, "label": "low"|"medium"|"high"|"severe", "probs": {"1": float, ...}}].
    label maps band 1->low, 2->medium, 3->high, 4->severe. ONNX fp32. CPU."""
```
CPU limits matter: runtime is a 16 GB laptop now and a CPU/GPU GCP VM next week.

## D. `metrics.json` schema (every model delivery)
```json
{
  "model_id": "m3_event_clf", "version": "v1",
  "task": "event classification", "split": "test (by IPO, excluded IPOs removed)",
  "n_test": 0, "seeds": [13, 42, 2026],
  "primary_metric": {"name": "macro_f1", "mean": 0.0, "std": 0.0},
  "secondary": {"precision_actual_event": 0.0, "recall_actual_event": 0.0},
  "baseline": {"name": "rules_v1", "primary": 0.0, "source": "ml/handoff/eval/baselines.json"},
  "verdict": "BEATS|TIES|LOSES",
  "label_source_mix": {"human": 0, "human_verified_ai": 0, "ai": 0, "rule": 0},
  "compute": {"hardware": "G4", "units_used": 0.0, "wall_minutes": 0},
  "date": "2026-10-23"
}
```
Rule: no number goes in `metrics.json` that wasn't produced by a script committed in `ml/`.
