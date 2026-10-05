"""Shared helpers for every FinSight Colab notebook (C03 §2).

Checkpoints are written to the runtime's local disk (fast) and synced to Google Drive every N
items or steps (Drive-mounted writes are slow). A disconnect loses at most one sync interval.
Plain standard library only, so it also runs in tests on the laptop.

Typical use in a notebook::

    from _common import mount_drive, Checkpointer, run_summary
    root = mount_drive("teacher_bakeoff")
    ck = Checkpointer(local_dir="/content/ck", drive_dir=root / "ck", every=100)
    done = ck.done_ids("raw.jsonl")
    ...
    ck.append("raw.jsonl", row)       # syncs to Drive every `every` rows
    ck.sync(force=True)
    run_summary(root, job="teacher_bakeoff", units_before=199.97, units_after=190.2, items_done=600)
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DRIVE_MOUNT = Path("/content/drive")
DRIVE_ROOT = DRIVE_MOUNT / "MyDrive" / "FinSight"

# Observed Colab Pro rates (C0.2, units per hour). Used only to estimate cost in run_summary.
OBSERVED_UNITS_PER_HOUR = {"T4": 1.07, "L4": 1.54, "A100": 6.77}


def mount_drive(job: str, root: Path | None = None) -> Path:
    """Mount Google Drive (Colab only) and return ``MyDrive/FinSight/<job>/``, created if needed.

    Args:
        job: Job folder name, e.g. ``"teacher_bakeoff"``.
        root: Override for the Drive root (tests / non-Colab runs).
    """
    if root is None:
        try:
            from google.colab import drive  # type: ignore[import-not-found]

            drive.mount(str(DRIVE_MOUNT))
        except ImportError:  # not on Colab: fall back to a local folder
            pass
        root = DRIVE_ROOT if DRIVE_MOUNT.exists() else Path.cwd() / "FinSight_local"
    job_dir = Path(root) / job
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


class Checkpointer:
    """Local-disk checkpoints synced to Drive every ``every`` appends; resumes from either side."""

    def __init__(self, local_dir: str | Path, drive_dir: str | Path, every: int = 100) -> None:
        self.local = Path(local_dir)
        self.drive = Path(drive_dir)
        self.every = max(1, every)
        self.local.mkdir(parents=True, exist_ok=True)
        self.drive.mkdir(parents=True, exist_ok=True)
        self._since_sync = 0
        self._restore()

    def _restore(self) -> None:
        """Copy newer Drive files back to local disk (after a runtime restart)."""
        for src in self.drive.rglob("*"):
            if not src.is_file():
                continue
            dst = self.local / src.relative_to(self.drive)
            if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

    def path(self, name: str) -> Path:
        """Local path of a checkpoint file."""
        return self.local / name

    def done_ids(self, name: str, key: str = "id") -> set[str]:
        """Ids already present in a JSONL checkpoint (skip them on restart)."""
        p = self.path(name)
        out: set[str] = set()
        if not p.exists():
            return out
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                out.add(str(json.loads(line)[key]))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue  # a torn last line after a disconnect
        return out

    def append(self, name: str, row: dict[str, Any]) -> None:
        """Append one JSON row; sync to Drive every ``every`` rows."""
        p = self.path(name)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._since_sync += 1
        if self._since_sync >= self.every:
            self.sync()

    def sync(self, force: bool = True) -> None:
        """Copy every local checkpoint file to Drive (only when something is pending, or forced)."""
        if not force and self._since_sync == 0:
            return
        for src in self.local.rglob("*"):
            if src.is_file():
                dst = self.drive / src.relative_to(self.local)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        self._since_sync = 0

    def latest_trainer_checkpoint(self, subdir: str = "trainer") -> str | None:
        """Newest ``checkpoint-N`` folder under ``subdir`` for ``Trainer.train(resume_from_checkpoint=...)``."""
        base = self.local / subdir
        if not base.exists():
            return None
        found = [p for p in base.glob("checkpoint-*") if p.is_dir() and p.name.split("-")[-1].isdigit()]
        if not found:
            return None
        return str(max(found, key=lambda p: int(p.name.split("-")[-1])))


def gpu_info() -> dict[str, Any]:
    """GPU name, memory and driver from ``nvidia-smi`` (empty dict without a GPU)."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=20, check=True,
        ).stdout.strip().splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return {}
    name, mem, driver = [s.strip() for s in out.split(",")]
    return {"gpu": name, "memory": mem, "driver": driver}


def gpu_class(name: str) -> str:
    """Map an nvidia-smi name to ``T4`` / ``L4`` / ``A100`` / ``other``."""
    for k in ("A100", "L4", "T4"):
        if k in name:
            return k
    return "other"


def run_summary(
    out_dir: str | Path,
    job: str,
    started: float | None = None,
    units_before: float | None = None,
    units_after: float | None = None,
    items_done: int = 0,
    pins: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write ``run_summary.json`` (GPU, wall time, items, compute units, library pins).

    ``units_before`` / ``units_after`` are typed in by Akshat from the Colab Resources panel.
    ``scripts/log_compute.py`` appends this file to ``eval_results/c/compute_log.jsonl``.
    """
    info = gpu_info()
    wall = round(time.time() - started, 1) if started is not None else None
    used = round(units_before - units_after, 2) if units_before is not None and units_after is not None else None
    cls = gpu_class(info.get("gpu", ""))
    summary: dict[str, Any] = {
        "job": job,
        "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "gpu": info.get("gpu"),
        "gpu_class": cls,
        "driver": info.get("driver"),
        "python": platform.python_version(),
        "wall_seconds": wall,
        "items_done": items_done,
        "units_before": units_before,
        "units_after": units_after,
        "units_used": used,
        "units_per_hour_observed": round(used / (wall / 3600), 2) if used is not None and wall else None,
        "units_per_hour_reference": OBSERVED_UNITS_PER_HOUR.get(cls),
        "pins": pins or {},
    }
    if extra:
        summary.update(extra)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def unassign_runtime(enabled: bool) -> None:
    """Disconnect the Colab runtime when a job ends (``enabled`` is the notebook's flag)."""
    if not enabled:
        return
    try:
        from google.colab import runtime  # type: ignore[import-not-found]

        runtime.unassign()
    except ImportError:
        pass
