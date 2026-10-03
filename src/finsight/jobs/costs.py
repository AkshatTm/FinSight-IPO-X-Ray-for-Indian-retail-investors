"""Cost estimate of one job and the admin cost summary (B02 §12, B06 §6).

Cloud Run bills a job for its configured vCPUs and memory for as long as it runs, so the
estimate is wall-clock seconds × resources × rates from ``settings.costs``. It is an estimate:
the billing export is the truth, and the rates stay ``provisional`` until checked for the region.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from finsight.core.config import CostConfig
from finsight.core.schemas import Job
from finsight.jobs.quotas import IST


def estimate(wall_s: float, cfg: CostConfig, gpu: bool = False) -> dict[str, Any]:
    """vCPU-, GiB- and GPU-seconds of a job that ran ``wall_s`` seconds, and its USD estimate.

    ``usd`` is ``None`` when a needed rate is unknown (the GPU rate until it is checked).
    """
    vcpu = cfg.gpu_vcpu if gpu else cfg.cpu_vcpu
    memory = cfg.gpu_memory_gib if gpu else cfg.cpu_memory_gib
    seconds = max(wall_s, 0.0)
    out: dict[str, Any] = {
        "wall_s": round(seconds, 3),
        "vcpu_s": round(seconds * vcpu, 3),
        "gib_s": round(seconds * memory, 3),
        "gpu_s": round(seconds, 3) if gpu else 0.0,
    }
    rates = cfg.rates_usd
    usd = out["vcpu_s"] * rates.vcpu_s + out["gib_s"] * rates.gib_s
    if gpu:
        usd = None if rates.gpu_s is None else usd + out["gpu_s"] * rates.gpu_s
    out["usd"] = None if usd is None else round(usd, 6)
    return out


def _day(job: Job, created_at: datetime | None) -> str:
    when = job.started_at or created_at
    return when.astimezone(IST).date().isoformat() if when else "unknown"


def summarise(
    rows: Iterable[tuple[Job, datetime | None]], uploads_by_day: dict[str, int], cfg: CostConfig
) -> dict[str, Any]:
    """Per-day totals (IST) and the share of the monthly free grant, for ``/api/admin/costs``."""
    days: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"jobs": 0, "failed": 0, "vcpu_s": 0.0, "gib_s": 0.0, "gpu_s": 0.0, "usd": 0.0}
    )
    unknown_cost = False
    for job, created_at in rows:
        day = days[_day(job, created_at)]
        day["jobs"] += 1
        day["failed"] += job.status == "failed"
        cost = job.progress.get("cost_estimate") or {}
        for key in ("vcpu_s", "gib_s", "gpu_s"):
            day[key] += float(cost.get(key) or 0.0)
        if cost and cost.get("usd") is None:
            unknown_cost = True
        day["usd"] += float(cost.get("usd") or 0.0)
    for name in uploads_by_day:
        _ = days[name]  # every upload day appears, even without a finished job
    table: list[dict[str, Any]] = [
        {
            "date": name,
            "uploads": uploads_by_day.get(name, 0),
            **{k: round(v, 6) if isinstance(v, float) else v for k, v in values.items()},
        }
        for name, values in sorted(days.items(), reverse=True)
    ]
    total_vcpu = sum(d["vcpu_s"] for d in table)
    total_gib = sum(d["gib_s"] for d in table)
    return {
        "days": table,
        "total": {
            "uploads": sum(d["uploads"] for d in table),
            "jobs": sum(d["jobs"] for d in table),
            "vcpu_s": round(total_vcpu, 3),
            "gib_s": round(total_gib, 3),
            "usd": round(sum(d["usd"] for d in table), 6),
            "free_vcpu_share": round(total_vcpu / cfg.free_vcpu_s_per_month, 6),
            "free_gib_share": round(total_gib / cfg.free_gib_s_per_month, 6),
        },
        "usd_incomplete": unknown_cost,
        "provisional": cfg.provisional,
    }
