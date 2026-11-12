"""``DocTypeAdapter`` for SEBI offer documents (RHP and final Prospectus share one layout)."""

from __future__ import annotations

from vidura.core import registry
from vidura.core.schemas import ParsedDoc, Section
from vidura.parse.sections import find_sections


class RhpAdapter:
    doc_type = "rhp"

    def sections(self, doc: ParsedDoc) -> list[Section]:
        return find_sections(doc)


def register() -> None:
    """Register under ("doc_adapter", "rhp"); safe to call more than once."""
    if "rhp" not in registry.available("doc_adapter"):
        registry.register("doc_adapter", "rhp")(RhpAdapter)


register()
