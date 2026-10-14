"""Shared helpers for every FinSight Colab notebook (C03 §2).

Checkpoints are written to the runtime's local disk (fast) and synced to Google Drive (IO mode
``"drive"``) or a private Hugging Face dataset repo (IO mode ``"hf"``, the default; resumes from
there too) every N items or steps. A disconnect loses at most one sync interval.
Standard library only (``huggingface_hub`` is imported lazily in ``HubBackend``), so it also runs
in tests on the laptop.

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
import os
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
OBSERVED_UNITS_PER_HOUR = {"T4": 1.07, "L4": 1.54, "A100": 6.77}  # H100: not measured yet


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


class DirBackend:
    """A local folder standing in for the Hub (tests, dry runs): same three calls as HubBackend."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, pairs: list[tuple[Path, str]]) -> None:
        """Copy ``(local, remote)`` pairs in."""
        for src, remote in pairs:
            dst = self.root / remote
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    def get(self, remote: str, dst: Path) -> bool:
        """Copy one remote file to ``dst``; False if it does not exist."""
        src = self.root / remote
        if not src.is_file():
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return True

    def ls(self, prefix: str = "") -> list[str]:
        """Remote file paths under ``prefix``."""
        base = self.root / prefix
        if not base.exists():
            return []
        return sorted(p.relative_to(self.root).as_posix() for p in base.rglob("*") if p.is_file())


class HubBackend:
    """A private Hugging Face *dataset* repo as the job store (one commit per ``put``)."""

    def __init__(self, repo: str, token: str, repo_type: str = "dataset") -> None:
        from huggingface_hub import HfApi

        self.repo, self.repo_type = repo, repo_type
        self._token = token  # never printed
        self.api = HfApi(token=token)

    def put(self, pairs: list[tuple[Path, str]]) -> None:
        """Upload all pairs in a single commit (HF rate-limits commits, not bytes)."""
        from huggingface_hub import CommitOperationAdd

        if not pairs:
            return
        ops = [CommitOperationAdd(path_in_repo=r, path_or_fileobj=str(p)) for p, r in pairs]
        self.api.create_commit(
            repo_id=self.repo, repo_type=self.repo_type, operations=ops,
            commit_message=f"job files ({len(ops)})",
        )  # fmt: skip

    def get(self, remote: str, dst: Path) -> bool:
        """Download one file to ``dst``; False if it is not in the repo."""
        from huggingface_hub import hf_hub_download
        from huggingface_hub.errors import EntryNotFoundError

        try:
            src = hf_hub_download(
                self.repo, remote, repo_type=self.repo_type, token=self._token,
                force_download=True,
            )  # fmt: skip
        except EntryNotFoundError:
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return True

    def ls(self, prefix: str = "") -> list[str]:
        """Repo file paths under ``prefix``."""
        files = self.api.list_repo_files(self.repo, repo_type=self.repo_type)
        return sorted(f for f in files if f.startswith(prefix))


class Checkpointer:
    """Local-disk checkpoints synced to Drive and/or a Hub store; resumes from either side.

    Args:
        local_dir: checkpoint folder on the runtime's disk.
        drive_dir: Drive folder to mirror (``None`` in IO mode ``"hf"``).
        every: appends between syncs.
        store: a ``HubBackend`` / ``DirBackend`` to mirror to and restore from.
        remote_prefix: folder inside the store, e.g. ``"teacher_full/out"``.
    """

    def __init__(
        self,
        local_dir: str | Path,
        drive_dir: str | Path | None = None,
        every: int = 100,
        store: Any = None,
        remote_prefix: str = "",
    ) -> None:
        self.local = Path(local_dir)
        self.drive = Path(drive_dir) if drive_dir is not None else None
        self.every = max(1, every)
        self.store = store
        self.prefix = remote_prefix.strip("/")
        self.local.mkdir(parents=True, exist_ok=True)
        if self.drive is not None:
            self.drive.mkdir(parents=True, exist_ok=True)
        self._since_sync = 0
        self._uploaded: dict[str, tuple[int, int]] = {}
        self._restore()

    def _remote(self, rel: str) -> str:
        return f"{self.prefix}/{rel}" if self.prefix else rel

    def _restore(self) -> None:
        """Copy newer Drive / Hub files back to local disk (after a runtime restart)."""
        if self.drive is not None:
            for src in self.drive.rglob("*"):
                if not src.is_file():
                    continue
                dst = self.local / src.relative_to(self.drive)
                if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
        if self.store is not None:
            lead = self.prefix + "/" if self.prefix else ""
            for remote in self.store.ls(lead):
                rel = remote[len(lead) :]
                dst = self.local / rel
                if not dst.exists():  # a fresh runtime: the Hub copy is the only one
                    self.store.get(remote, dst)
                    st = dst.stat() if dst.exists() else None
                    if st is not None:
                        self._uploaded[rel] = (st.st_size, st.st_mtime_ns)

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
        """Copy every local checkpoint file to Drive / the Hub (only if pending, or forced)."""
        if not force and self._since_sync == 0:
            return
        pairs: list[tuple[Path, str]] = []
        for src in self.local.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(self.local).as_posix()
            if self.drive is not None:
                dst = self.drive / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            st = src.stat()
            if self._uploaded.get(rel) != (st.st_size, st.st_mtime_ns):
                pairs.append((src, self._remote(rel)))
                self._uploaded[rel] = (st.st_size, st.st_mtime_ns)
        if self.store is not None and pairs:
            self.store.put(pairs)
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
    """Map an nvidia-smi name to ``T4`` / ``L4`` / ``A100`` / ``H100`` / ``other``."""
    for k in ("H100", "A100", "L4", "T4"):
        if k in name:
            return k
    return "other"


def gpu_tier(name: str, mem_gb: float) -> str:
    """``H100`` / ``A100-80GB`` / ``A100-40GB`` / ``L4`` / ``T4`` / ``other`` from name and memory."""
    cls = gpu_class(name)
    if cls == "A100":
        return "A100-80GB" if mem_gb > 60 else "A100-40GB"
    return cls


# Per-tier vLLM settings. ``awq_marlin`` needs compute capability 8.0+ (L4, A100, H100); a T4
# (sm75) needs plain ``awq``. H100 can also run FP8 checkpoints (``fp8_ok``).
_TIER_CONFIG: dict[str, dict[str, Any]] = {
    "H100": {"quant": "awq_marlin", "gpu_mem": 0.92, "fp8_ok": True},
    "A100-80GB": {"quant": "awq_marlin", "gpu_mem": 0.92, "fp8_ok": False},
    "A100-40GB": {"quant": "awq_marlin", "gpu_mem": 0.90, "fp8_ok": False},
    "L4": {"quant": "awq_marlin", "gpu_mem": 0.90, "fp8_ok": True},
    "T4": {"quant": "awq", "gpu_mem": 0.88, "fp8_ok": False},
}


def gpu_config(name: str, mem_gb: float, capability: tuple[int, int] | None = None) -> dict[str, Any]:
    """Pick quantisation kernel and ``GPU_MEM`` from the detected GPU (no manual editing).

    Args:
        name: ``nvidia-smi`` / torch device name.
        mem_gb: total GPU memory in GiB (as torch reports it; an A100-40GB shows ~39.5).
        capability: ``torch.cuda.get_device_capability()``; decides the kernel on unknown GPUs.
    """
    tier = gpu_tier(name, mem_gb)
    if tier in _TIER_CONFIG:
        cfg = dict(_TIER_CONFIG[tier])
    else:  # an unlisted GPU: choose the kernel by compute capability
        modern = capability is not None and capability[0] >= 8
        cfg = {"quant": "awq_marlin" if modern else "awq", "gpu_mem": 0.88, "fp8_ok": False}
    return {"tier": tier, "mem_gb": round(mem_gb, 1), **cfg}


class JobIO:
    """Where a Colab job reads its inputs and writes its checkpoints and outputs.

    ``io="hf"`` (default): inputs ``<job>/in/<name>`` and outputs ``<job>/out/...`` live in a
    private Hub dataset repo, so a runtime can start from nothing and a rerun resumes from there.
    ``io="drive"``: the old flow, ``MyDrive/FinSight/<job>/<name>`` and ``.../out/``.
    """

    def __init__(
        self,
        job: str,
        io: str = "hf",
        *,
        hf_repo: str | None = None,
        token: str | None = None,
        store: Any = None,
        drive_root: Path | None = None,
        work: str | Path = "/content/job",
    ) -> None:
        if io not in ("hf", "drive"):
            raise ValueError(f"io must be 'hf' or 'drive', not {io!r}")
        self.job, self.io = job, io
        self.work = Path(work)
        self.work.mkdir(parents=True, exist_ok=True)
        self.drive_dir: Path | None = None
        self.store: Any = None
        if io == "hf":
            if store is None:
                if not (hf_repo and token):
                    raise ValueError("io='hf' needs hf_repo and an HF_TOKEN (Colab secret)")
                store = HubBackend(hf_repo, token)
            self.store = store
        else:
            self.drive_dir = mount_drive(job, root=drive_root)

    def fetch_input(self, name: str) -> Path:
        """Local path of an input file (downloaded from the Hub in ``hf`` mode)."""
        if self.io == "drive":
            assert self.drive_dir is not None
            return self.drive_dir / name
        dst = self.work / "in" / name
        if not self.store.get(f"{self.job}/in/{name}", dst):
            raise FileNotFoundError(f"{self.job}/in/{name} is not in the job repo (gpu_jobs.py push)")
        return dst

    def checkpointer(self, every: int = 1) -> Checkpointer:
        """The job's checkpointer; its ``local`` folder is the ``out/`` folder."""
        if self.io == "drive":
            assert self.drive_dir is not None
            return Checkpointer(self.work / "out", self.drive_dir / "out", every=every)
        return Checkpointer(
            self.work / "out", None, every=every, store=self.store, remote_prefix=f"{self.job}/out"
        )


def hf_secret(name: str = "HF_TOKEN") -> str | None:
    """Colab secret ``name`` (else the environment); the value is never printed."""
    try:
        from google.colab import userdata  # type: ignore[import-not-found]

        return str(userdata.get(name))
    except Exception:  # not on Colab, secret missing or access not granted
        return os.environ.get(name)


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
