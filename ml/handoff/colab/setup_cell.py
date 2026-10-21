# First cell of every ARGON notebook (paste it, or `%run` it after downloading the pack).
# What it does: mounts Google Drive, pulls the handoff pack from the private HF dataset repo,
# installs the pinned deps, fixes the seeds and defines the checkpoint convention.
# Needs a Colab secret named HF_TOKEN (read access to the private dataset repo; Akshat adds it).
import json
import os
import pathlib
import random
import subprocess
import sys

HF_REPO = "AkshatTm/finsight-gpu-jobs"  # private dataset repo (C-ADR-13)
HF_PREFIX = "phase4/handoff"  # folder in that repo; revision pinned in ml/handoff/README.md
HF_REVISION = None  # set to the commit sha printed in ml/handoff/README.md
JOB = "CHANGE_ME"  # e.g. "m3_event_clf"
DEBUG = True  # True = tiny slice for the T4 debug run; False only after DEBUG passes
SEEDS = [13, 42, 2026]
RESUME = True  # continue from the newest checkpoint on Drive if one exists

ROOT = pathlib.Path("/content")
PACK = ROOT / "handoff"  # downloaded pack lands here
DRIVE = pathlib.Path("/content/drive/MyDrive/finsight_p4")
CKPT_DIR = DRIVE / JOB  # checkpoint every epoch here; resume reads from here


def mount_drive() -> None:
    try:
        from google.colab import drive  # type: ignore

        drive.mount("/content/drive")
    except Exception as exc:  # not on Colab (local smoke run)
        print("Drive not mounted:", exc)
    CKPT_DIR.mkdir(parents=True, exist_ok=True)


def hf_token() -> str:
    try:
        from google.colab import userdata  # type: ignore

        return userdata.get("HF_TOKEN")
    except Exception:
        return os.environ["HF_TOKEN"]


def fetch_pack() -> pathlib.Path:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "huggingface_hub"], check=True)
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=HF_REPO,
        repo_type="dataset",
        revision=HF_REVISION,
        token=hf_token(),
        allow_patterns=[f"{HF_PREFIX}/*"],
        local_dir=str(ROOT / "_hf"),
    )
    src = ROOT / "_hf" / HF_PREFIX
    if PACK.exists():
        subprocess.run(["rm", "-rf", str(PACK)], check=True)
    subprocess.run(["cp", "-r", str(src), str(PACK)], check=True)
    return PACK


def verify_manifest() -> None:
    """Every file must match MANIFEST.json (sha256); a mismatch stops the notebook."""
    import hashlib

    manifest = json.loads((PACK / "data" / "MANIFEST.json").read_text(encoding="utf-8"))
    for f in manifest["files"]:
        h = hashlib.sha256((PACK / "data" / f["path"]).read_bytes()).hexdigest()
        assert h == f["sha256"], f"checksum mismatch: {f['path']}"


def install_deps() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "-r",
            str(PACK / "colab" / "requirements_colab.txt"),
        ],
        check=True,
    )


def set_seed(seed: int) -> None:
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import numpy as np

        np.random.seed(seed)
        import torch

        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def latest_checkpoint() -> pathlib.Path | None:
    """Newest `epoch-*` folder in CKPT_DIR (checkpoint every epoch; use it when RESUME is True)."""
    ckpts = sorted(CKPT_DIR.glob("epoch-*"), key=lambda p: int(p.name.split("-")[1]))
    return ckpts[-1] if RESUME and ckpts else None


if __name__ == "__main__":
    mount_drive()
    fetch_pack()
    verify_manifest()
    install_deps()
    sys.path.insert(0, str(PACK / "eval" / "vendor"))  # finsight_lite: number normaliser + metrics
    print("pack ready:", PACK, "| DEBUG =", DEBUG, "| resume from:", latest_checkpoint())
