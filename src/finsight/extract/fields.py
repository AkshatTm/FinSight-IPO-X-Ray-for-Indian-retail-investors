"""The field registry: which fields exist and how each is extracted (``configs/fields.yaml``)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from finsight.core.config import project_root
from finsight.core.schemas import FieldSpec


def _path() -> Path:
    return project_root() / "configs" / "fields.yaml"


def load_fields(path: Path | None = None) -> list[FieldSpec]:
    """Every field in file order; duplicate ids and unknown documents are errors."""
    raw = yaml.safe_load((path or _path()).read_text(encoding="utf-8"))
    fields = [FieldSpec.model_validate(entry) for entry in raw["fields"]]
    seen: set[str] = set()
    for f in fields:
        if f.id in seen:
            raise ValueError(f"duplicate field id {f.id!r} in fields.yaml")
        seen.add(f.id)
    return fields


@lru_cache(maxsize=1)
def _default() -> dict[str, FieldSpec]:
    return {f.id: f for f in load_fields()}


def get_field(field_id: str) -> FieldSpec:
    try:
        return _default()[field_id]
    except KeyError:
        raise KeyError(f"unknown field {field_id!r}") from None


def field_ids() -> list[str]:
    return list(_default())
