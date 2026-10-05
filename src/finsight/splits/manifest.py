"""Artefact manifests (C02 §4): which IPOs went into each training or reference artefact.

Artefacts live in ``data/processed/`` (git-ignored); their manifests are committed as
``data/manifests/<artefact>.json`` so the leakage test runs in ``poe test`` without any data.
The script that writes an artefact writes its manifest at the same time; Colab/Kaggle outputs
list the exported input's manifest under ``inputs``.

Kinds:

- ``train``: training data, weak labels, teacher input/outputs, the risk bank.
- ``fit``: inputs used to fit thresholds (τ, risk-level ``low_below``/``high_from``,
  ``unusual_below``). Train + dev only.
- ``eval_reference``: "past IPOs" as of each test IPO's date (train + dev only, C-ADR-03).
- ``product_reference``: every collected IPO before today; may hold test IPOs, never an input
  to a ``train`` or ``fit`` artefact.
- ``eval``: test-time artefacts (e.g. ``risk_eval.parquet``, bench answers); may hold test IPOs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

Kind = Literal["train", "fit", "eval_reference", "product_reference", "eval"]
NO_TEST_KINDS: frozenset[str] = frozenset({"train", "fit", "eval_reference"})


class Manifest(BaseModel):
    """What one artefact was built from."""

    artefact: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    kind: Kind
    ipo_ids: list[str]
    inputs: list[str] = Field(default_factory=list)  # other artefacts' names
    sha256: str | None = None  # of the artefact file, when there is one
    written_by: str  # script or module that wrote the artefact
    note: str = ""

    @property
    def n_ipos(self) -> int:
        """Number of distinct IPOs."""
        return len(set(self.ipo_ids))


def file_sha256(path: Path) -> str:
    """sha256 of a file, read in 1 MB blocks."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_manifest(manifest: Manifest, directory: Path) -> Path:
    """Write ``<directory>/<artefact>.json`` (ids sorted and unique, LF endings)."""
    directory.mkdir(parents=True, exist_ok=True)
    data = manifest.model_dump()
    data["ipo_ids"] = sorted(set(manifest.ipo_ids))
    data["n_ipos"] = len(data["ipo_ids"])
    path = directory / f"{manifest.artefact}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
                    newline="\n")  # fmt: skip
    return path


def read_manifests(directory: Path) -> list[Manifest]:
    """Every manifest in ``directory`` (empty when it does not exist yet)."""
    if not directory.is_dir():
        return []
    out = []
    for path in sorted(directory.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw.pop("n_ipos", None)
        m = Manifest.model_validate(raw)
        if m.artefact != path.stem:
            raise ValueError(f"{path.name}: artefact {m.artefact!r} does not match the file name")
        out.append(m)
    return out
