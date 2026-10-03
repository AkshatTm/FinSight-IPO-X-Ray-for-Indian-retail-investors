"""Upload limits: the kill switch, 3 per user per day, 10 per day overall (B01 B-FR-01).

A "day" is the calendar day in India (IST), so limits reset at midnight for the users.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from finsight.core.config import UploadsConfig
from finsight.db import Database, utcnow

IST = timezone(timedelta(hours=5, minutes=30), "IST")


class UploadBlocked(Exception):
    """Why an upload may not start; the API maps ``code`` to its status (B06 §1)."""

    def __init__(self, code: str, limit: int = 0, resets_at: datetime | None = None) -> None:
        super().__init__(code)
        self.code = code  # uploads_disabled | quota_exceeded | global_quota_exceeded
        self.limit = limit
        self.resets_at = resets_at


def day_window(now: datetime) -> tuple[datetime, datetime]:
    """Start and end of ``now``'s calendar day in IST, as aware datetimes."""
    local = now.astimezone(IST)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def check_upload_allowed(
    db: Database, limits: UploadsConfig, user_id: str, now: datetime | None = None
) -> None:
    """Raise ``UploadBlocked`` if this user may not start another upload today."""
    if not limits.enabled:
        raise UploadBlocked("uploads_disabled")
    start, end = day_window(now or utcnow())
    if db.count_uploads(start, user_id) >= limits.per_user_per_day:
        raise UploadBlocked("quota_exceeded", limits.per_user_per_day, end)
    if db.count_uploads(start) >= limits.global_per_day:
        raise UploadBlocked("global_quota_exceeded", limits.global_per_day, end)
