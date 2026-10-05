"""Retro manifests for the Phase 1 artefacts (C1.4), so the leakage test covers them too.

The Phase 1 extractor (QA, 3 seeds) and the BiLSTM-CRF were trained on the weak labels built
from the corpus only (2009–2023, demo and gold IPOs excluded), so they pass by construction; the
manifests make that checkable. The MuRIL advice guard was trained on questions, not on offer
documents, so its manifest lists no IPO.
"""

from __future__ import annotations

import json
from pathlib import Path

from finsight.splits.manifest import Manifest, file_sha256

WEAKLABEL_FILES = ("train.jsonl", "dev.jsonl")
GUARD_SET = Path("data/gold/advice_guard_set.csv")


def _weaklabel_ids(folder: Path) -> list[str] | None:
    files = [folder / name for name in WEAKLABEL_FILES]
    if not all(f.is_file() for f in files):
        return None
    ids: set[str] = set()
    for f in files:
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    ids.add(json.loads(line)["ipo_id"])
    return sorted(ids)


def retro_manifests(processed_dir: Path, root: Path) -> tuple[list[Manifest], list[str]]:
    """Manifests that can be built from local files, and a note for each one that cannot."""
    made: list[Manifest] = []
    missing: list[str] = []
    ids = _weaklabel_ids(processed_dir / "weaklabel")
    if ids is None:
        missing.append(f"weak labels not found in {processed_dir / 'weaklabel'}: "
                       "weaklabel_v1, extractor_qa_v1, bilstm_crf_v1 not written")  # fmt: skip
    else:
        made.append(Manifest(
            artefact="weaklabel_v1", kind="train", ipo_ids=ids,
            written_by="finsight.weaklabel (Phase 1; retro manifest by finsight.splits)",
            note="SQuAD weak labels from corpus cover pages, train.jsonl + dev.jsonl (ADR-038)",
        ))  # fmt: skip
        for name, what in (("extractor_qa_v1", "DeBERTa QA extractor, 3 seeds (P2.6)"),
                           ("bilstm_crf_v1", "BiLSTM-CRF rung, 3 seeds (P5.3)")):  # fmt: skip
            made.append(Manifest(
                artefact=name, kind="train", ipo_ids=ids, inputs=["weaklabel_v1"],
                written_by="Kaggle notebook (Phase 1; retro manifest by finsight.splits)",
                note=f"{what}; trained on weaklabel_v1",
            ))  # fmt: skip
    guard = root / GUARD_SET
    made.append(Manifest(
        artefact="guard_muril_v1", kind="train", ipo_ids=[],
        sha256=file_sha256(guard) if guard.is_file() else None,
        written_by="finsight.guard.clf_data (Phase 1; retro manifest by finsight.splits)",
        note="MuRIL advice guard (P5.4): trained on questions (data/gold/advice_guard_set.csv), "
             "no offer documents",
    ))  # fmt: skip
    return made, missing
