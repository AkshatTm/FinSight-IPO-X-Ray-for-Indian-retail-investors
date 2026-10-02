"""The MuRIL advice classifier as a guard backend (P5.4, E8 classifier row).

``guard.backend: muril`` in the config swaps the keyword rules for a fine-tuned
``google/muril-base-cased`` that says how likely a question is to ask for advice, a forecast or a
rating. Privacy stays rule-based in both modes (it is a hard refusal with its own categories).
Weights come from Kaggle (``python -m finsight.guard.kaggle_clf fetch full``) into
``models/guard_clf/`` and are never committed; without them the guard says so instead of
silently falling back to the keywords.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from finsight.core.config import get_settings

Scorer = Callable[[str], float]  # question -> probability that it asks for advice


def weights_dir(models_dir: Path | None = None) -> Path:
    return (models_dir or Path(get_settings().paths.models_dir)) / "guard_clf"


def load_scorer(directory: Path | None = None) -> Scorer:
    """The fine-tuned model on the CPU: roughly 0.2 s per question, loaded once."""
    directory = directory or weights_dir()
    if not (directory / "config.json").exists():
        raise FileNotFoundError(
            f"{directory} not found; fetch the classifier with "
            "`python -m finsight.guard.kaggle_clf fetch full`"
        )
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(directory)
    net = AutoModelForSequenceClassification.from_pretrained(directory).eval()

    def score(question: str) -> float:
        enc = tok(question, truncation=True, max_length=64, return_tensors="pt")
        with torch.no_grad():
            logits = net(**enc).logits.float()
        return float(logits.softmax(-1)[0, 1])  # label 1 = advice

    return score
