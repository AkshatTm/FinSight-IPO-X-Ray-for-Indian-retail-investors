"""Protocols every swappable component implements (02_ARCHITECTURE.md section 7)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Literal, Protocol

from finsight.core.schemas import (
    Candidate,
    CheckResult,
    Claim,
    FieldSpec,
    ParsedDoc,
    Passage,
    Section,
    Table,
)


class Extractor(Protocol):
    name: str

    def extract(
        self,
        doc: ParsedDoc,
        sections: list[Section],
        tables: list[Table],
        field: FieldSpec,
    ) -> list[Candidate]: ...


class VerifierCheck(Protocol):
    name: str

    def check(self, claim: Claim, evidence: list[Passage]) -> list[CheckResult]: ...


class LLMBackend(Protocol):
    name: str

    def stream(
        self,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
        language: Literal["en", "hi"],
    ) -> Iterator[str]: ...


class ASRBackend(Protocol):
    name: str

    def transcribe(self, audio_path: Path, language: str = "hi") -> str: ...


class Reranker(Protocol):
    def score(self, query: str, passages: list[Passage]) -> list[float]: ...


class DocTypeAdapter(Protocol):
    doc_type: str  # "rhp" now; "concall", "annual_report" later

    def sections(self, doc: ParsedDoc) -> list[Section]: ...
