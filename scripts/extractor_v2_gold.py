"""C2.7: run the v2 extractor seeds (``models/extractor_v2``) over the gold ladder as rung ``qa_finetuned_v2``.

    FINSIGHT_PATHS__PROCESSED_DIR=<main>/data/processed \
        uv run --group ml python scripts/extractor_v2_gold.py [--seed 13]
    # -> eval_results/ladder/qa_finetuned_v2_seed<n>.json

Same extraction code, gold rows and scoring as ``finsight.evaluate.run_gold --rung qa_finetuned``; only the
weights differ. This is a **reporting** row: v2 is chosen (or not) on the v3 dev rows, never on gold
(C-ADR-02; the gold IPOs are not in the v3 training data). The ``test`` IPOs are scored but not used to decide.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finsight.evaluate import run_gold  # noqa: E402
from finsight.extract.qa_finetuned import SEEDS, FineTunedExtractor  # noqa: E402

NAME = "qa_finetuned_v2"
MODELS = ROOT / "models" / "extractor_v2"


def main() -> None:
    """Score each requested seed and write its ladder file."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, choices=SEEDS)
    ap.add_argument("--out", type=Path, default=ROOT / "eval_results" / "ladder")
    a = ap.parse_args()
    run_gold.make_extractor = lambda rung, seed, answerer=None: FineTunedExtractor(  # type: ignore[assignment]
        seed, answerer=answerer, models_dir=MODELS
    )
    for seed in [a.seed] if a.seed else SEEDS:
        result = run_gold.run_rung("qa_finetuned", seed)
        result["name"] = f"{NAME}_seed{seed}"
        result["rung"] = NAME
        result["notes"] += (
            " Weights: models/extractor_v2 (weak labels v3, C2.7); reporting row, not a selection."
        )
        print("wrote", run_gold.write_result(result, a.out))


if __name__ == "__main__":
    main()
