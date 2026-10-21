# Interfaces and metrics.json schema (frozen after CC-02; change only via Akshat)

Copied from `docs/phase4/P4_HANDOFF_CONTRACT.md` sections C and D by the exporter.

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
