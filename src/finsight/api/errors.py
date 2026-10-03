"""Error envelope shared by every non-2xx response (06_API_CONTRACT.md section 1)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ErrorCode = Literal[
    "ipo_not_found",
    "not_available",
    "page_out_of_range",
    "llm_unavailable",
    "models_warming_up",
    "asr_failed",
    "audio_too_long",
    "rate_limited",
    "validation_error",
    "internal_error",
    # Phase 2 (B06 §1-2)
    "unauthorized",
    "quota_exceeded",
    "global_quota_exceeded",
    "uploads_disabled",
    "hash_mismatch",
    "too_large",
    "doc_not_found",
    "upload_not_started",
    "risk_not_found",
    "worker_unavailable",
    "forbidden",
]


class ErrorBody(BaseModel):
    """The error envelope's body: code, message, hint, and quota details if any."""

    code: ErrorCode
    message: str
    hint: str | None = None
    trace_id: str | None = None
    # quota errors only (B06 §1)
    limit: int | None = None
    resets_at: datetime | None = None


class ErrorResponse(BaseModel):
    """Every API error: ``{"error": ErrorBody}`` (B06 §1)."""

    error: ErrorBody


class ApiError(Exception):
    """Raise from a route; the app turns it into the error envelope. No stack traces leak."""

    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        message: str,
        hint: str | None = None,
        trace_id: str | None = None,
        limit: int | None = None,
        resets_at: datetime | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = ErrorBody(
            code=code,
            message=message,
            hint=hint,
            trace_id=trace_id,
            limit=limit,
            resets_at=resets_at,
        )


def not_implemented(what: str) -> ApiError:
    """The contract-first skeleton (ADR-024): every route exists but answers 501 for now."""
    return ApiError(
        501,
        "internal_error",
        f"{what} is not implemented yet.",
        hint="The API skeleton defines the contract; the endpoint arrives in sub-phase P4.1.",
    )
