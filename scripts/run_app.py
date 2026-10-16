"""Start the whole app on this laptop: `uv run poe app`.

Checks that Ollama runs and has `finsight-student:q4` (creates it from
`models/student/simplifier-q4_k_m.gguf` when the file is there), installs the frontend packages
when they are missing, starts the API on :8000 (profile `local`) and the frontend on :3000, waits
until both answer and prints the address. Ctrl+C stops both.

    uv run poe app            # or: uv run python scripts/run_app.py [--no-frontend] [--port 8000]

Nothing else is loaded at start: the classifier, bge-m3 (novelty) and the reranker are loaded
by the stage or question that needs them and released again.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLLAMA = "http://127.0.0.1:11434"
MODEL = "finsight-student:q4"
GGUF = ROOT / "models" / "student" / "simplifier-q4_k_m.gguf"
MODELFILE = ROOT / "deploy" / "ollama" / "Modelfile.student"


def say(text: str) -> None:
    """Print one line now."""
    print(text, flush=True)


def fail(text: str) -> int:
    """Print the problem and give the exit status."""
    say(f"\nCannot start: {text}")
    return 1


def fetch(url: str, payload: dict[str, object] | None = None, timeout: float = 3) -> dict | None:
    """GET (or POST) JSON; ``None`` when nothing answers."""
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return json.loads(body) if body else {}
    except (OSError, ValueError):
        return None


def ensure_ollama() -> str | None:
    """Make sure Ollama runs and has the student model; the problem as text, or ``None``."""
    # A busy Ollama can be slow to answer; only start another one when it stays silent.
    if not any(fetch(f"{OLLAMA}/api/tags", timeout=5) is not None for _ in range(3)):
        exe = shutil.which("ollama")
        if exe is None:
            return "Ollama is not installed. Get it from https://ollama.com/download, then retry."
        say("Starting Ollama ...")
        flags = 0x00000008 | 0x00000200 if os.name == "nt" else 0  # detached: outlives this script
        subprocess.Popen(
            [exe, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        for _ in range(30):
            if fetch(f"{OLLAMA}/api/tags") is not None:
                break
            time.sleep(1)
        else:
            return "Ollama did not start. Open the Ollama app, then retry."
    tags = fetch(f"{OLLAMA}/api/tags") or {}
    names = {m.get("name") for m in tags.get("models", [])}
    if MODEL in names:
        return None
    if not GGUF.exists():
        return f"{MODEL} is not in Ollama and {GGUF.relative_to(ROOT)} is missing."
    say(f"Creating {MODEL} in Ollama from {GGUF.name} ...")
    text = MODELFILE.read_text(encoding="utf-8").replace("{{GGUF}}", str(GGUF))
    with tempfile.NamedTemporaryFile("w", suffix=".Modelfile", delete=False, encoding="utf-8") as f:
        f.write(text)
    done = subprocess.run(["ollama", "create", MODEL, "-f", f.name], check=False)
    Path(f.name).unlink(missing_ok=True)
    return None if done.returncode == 0 else f"`ollama create {MODEL}` failed."


def wait_for(url: str, name: str, seconds: int) -> bool:
    """Poll ``url`` until it answers or the time is up."""
    for _ in range(seconds):
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except urllib.error.HTTPError:
            return True  # the server is up even if this path says no
        except OSError:
            time.sleep(1)
    say(f"{name} did not answer within {seconds} s.")
    return False


def stop(proc: subprocess.Popen[bytes]) -> None:
    """Stop a child and everything it started (Windows keeps grandchildren alive otherwise)."""
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.terminate()


def main() -> int:
    """Run the app until Ctrl+C."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-frontend", action="store_true")
    a = ap.parse_args()

    problem = ensure_ollama()
    if problem:
        return fail(problem)
    say(f"Ollama is running with {MODEL}.")
    # Load the student into memory now (kept for 30 minutes) so the first answer is not slow.
    fetch(f"{OLLAMA}/api/generate", {"model": MODEL, "keep_alive": "30m"}, timeout=120)

    for needed, label in (("onnx", "risk classifier"), ("bge", "bge-m3 (novelty)")):
        if needed == "onnx" and not (ROOT / "models" / "risk_classifier" / "onnx").exists():
            say(f"Note: models/risk_classifier/onnx is missing, so the {label} stage will fail.")
        if (
            needed == "bge"
            and not (ROOT / "data" / "processed" / "bank" / "risk_bank.parquet").exists()
        ):
            say(f"Note: the risk bank is missing, so {label} is skipped (no 'unusual' badges).")

    env = {
        **os.environ,
        "FINSIGHT_PROFILE": "local",
        "FINSIGHT_UPLOADS__PER_USER_PER_DAY": "1000",
        "FINSIGHT_UPLOADS__GLOBAL_PER_DAY": "1000",
        "FINSIGHT_UPLOADS__RETENTION_DAYS": "3650",
        "PYTHONUTF8": "1",
    }
    procs: list[subprocess.Popen[bytes]] = []
    try:
        say(f"Starting the API on :{a.port} ...")
        procs.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "finsight.api.app:app",
                    "--port",
                    str(a.port),
                    "--timeout-keep-alive",
                    "30",
                ],
                cwd=ROOT,
                env=env,
            )
        )
        if not wait_for(f"http://127.0.0.1:{a.port}/api/health", "The API", 90):
            return fail("the API did not start (see the messages above).")
        if not a.no_frontend:
            front = ROOT / "frontend"
            pnpm = shutil.which("pnpm")
            if pnpm is None:
                return fail("pnpm is not installed (https://pnpm.io/installation).")
            if not (front / "node_modules").exists():
                say("Installing the frontend packages (first run only) ...")
                if subprocess.run([pnpm, "install", "--frozen-lockfile"], cwd=front).returncode:
                    return fail("`pnpm install` failed.")
            say("Starting the frontend on :3000 ...")
            fenv = {**env, "FINSIGHT_API_ORIGIN": f"http://127.0.0.1:{a.port}"}
            fenv.pop("NEXT_PUBLIC_USE_MOCKS", None)
            procs.append(subprocess.Popen([pnpm, "dev", "--port", "3000"], cwd=front, env=fenv))
            if not wait_for("http://127.0.0.1:3000/", "The frontend", 120):
                return fail("the frontend did not start (see the messages above).")
        say("\n" + "=" * 60)
        say("FinSight is running.")
        say("  Open:   http://localhost:3000/upload   (upload your own RHP / prospectus PDF)")
        say(f"  API:    http://127.0.0.1:{a.port}/docs")
        say("  Stop:   Ctrl+C")
        say("=" * 60)
        while all(p.poll() is None for p in procs):
            time.sleep(1)
        return 1
    except KeyboardInterrupt:
        say("\nStopping ...")
        return 0
    finally:
        for p in procs:
            stop(p)


if __name__ == "__main__":
    sys.exit(main())
