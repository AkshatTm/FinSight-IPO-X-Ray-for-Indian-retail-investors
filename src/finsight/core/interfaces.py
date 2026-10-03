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
    """Proposes candidate values for one X-Ray field from a parsed document."""

    name: str

    def extract(
        self,
        doc: ParsedDoc,
        sections: list[Section],
        tables: list[Table],
        field: FieldSpec,
    ) -> list[Candidate]:
        """Candidates for ``field``, each with its page, box and score."""


class VerifierCheck(Protocol):
    """One deterministic check of the numbers in a claim against the cited passages."""

    name: str

    def check(self, claim: Claim, evidence: list[Passage]) -> list[CheckResult]:
        """One result per number in the claim."""


class LLMBackend(Protocol):
    """A local text generator (Ollama, llama.cpp or vLLM) that streams its output."""

    name: str

    def stream(
        self,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
        language: Literal["en", "hi"],
    ) -> Iterator[str]:
        """Yield the generated text piece by piece."""


class ASRBackend(Protocol):
    """Speech recognition for short spoken questions."""

    name: str

    def transcribe(self, audio_path: Path, language: str = "hi") -> str:
        """The transcript of the audio file."""


class Reranker(Protocol):
    """Scores query-passage pairs together (a cross-encoder)."""

    def score(self, query: str, passages: list[Passage]) -> list[float]:
        """One relevance score per passage, in the given order."""


class DocTypeAdapter(Protocol):
    """Document-type specific logic, such as how sections are found."""

    doc_type: str  # "rhp" now; "concall", "annual_report" later

    def sections(self, doc: ParsedDoc) -> list[Section]:
        """The document's sections with their page spans."""
