"""JSON logging: one line per record, one record per pipeline stage with the trace id."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import IO, Any

_STANDARD = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=repr)


def configure_logging(level: str = "INFO", stream: IO[str] | None = None) -> None:
    """Send ``finsight.*`` logs to ``stream`` (default stderr) as JSON. Safe to call twice."""
    root = logging.getLogger("finsight")
    root.setLevel(level)
    root.propagate = False
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_stage(
    logger: logging.Logger,
    trace_id: str,
    stage: str,
    ms: int | None = None,
    **fields: Any,
) -> None:
    """One log line per pipeline stage: ``{"trace_id", "stage", "ms", ...}``."""
    extra: dict[str, Any] = {"trace_id": trace_id, "stage": stage, **fields}
    if ms is not None:
        extra["ms"] = ms
    logger.info("stage %s", stage, extra=extra)
