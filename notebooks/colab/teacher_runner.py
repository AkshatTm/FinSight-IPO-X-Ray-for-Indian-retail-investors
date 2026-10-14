# FinSight teacher runner (C2.2 / C2.3): paste as two cells in a Colab notebook (split at "# ---- cell 2").
# It downloads the pushed notebooks/c2_teacher.ipynb from the HF job repo and runs it as a plain
# python process, so vLLM's engine child gets a real stdout (in-kernel runs crashed with
# "io.UnsupportedOperation: fileno"). The kernel, not the job, releases the GPU when UNASSIGN.
# The HF token is read from Colab secrets and passed in the environment; it is never printed.
PRESET = "teacher_full"    # bakeoff_smoke | bakeoff | teacher_smoke | teacher_full | gold_eval
UNITS_BEFORE = None        # Resources panel reading before the session
UNASSIGN = True            # True on the last job of the session (releases the GPU at the end or on a crash)
TEACHER_PICK = "google/gemma-4-31B-it"   # C-ADR-05 winner
JOBS_REPO = "AkshatTm/finsight-gpu-jobs"

# ---- cell 2
import json, os, re, subprocess, sys  # noqa: E401, E402
from huggingface_hub import hf_hub_download  # noqa: E402
from google.colab import userdata  # noqa: E402

_tok = userdata.get("HF_TOKEN")
_nb = hf_hub_download(JOBS_REPO, "notebooks/c2_teacher.ipynb", repo_type="dataset",
                      token=_tok, local_dir="/content/_boot", force_download=True)
_cells = ["".join(c["source"]) for c in json.load(open(_nb))["cells"] if c["cell_type"] == "code"]
_params = _cells[0]
for _k, _v in {"PRESET": repr(PRESET), "UNITS_BEFORE": repr(UNITS_BEFORE),
               "UNASSIGN": "False", "TEACHER_PICK": repr(TEACHER_PICK)}.items():
    _params, _n = re.subn(rf"^{_k} = .*$", f"{_k} = {_v}", _params, count=1, flags=re.M)
    assert _n == 1, _k
_body = "\n\n".join([_params] + _cells[1:]).replace('userdata.get("HF_TOKEN")', 'os.environ["HF_TOKEN"]')
_body = re.sub(r"^from __future__ import .*$", "", _body, flags=re.M)
_script = "import os, sys\nif __name__ == '__main__':\n" + "".join(
    "    " + line if line.strip() else line for line in _body.splitlines(keepends=True))
compile(_script, "teacher_job.py", "exec")
open("/content/teacher_job.py", "w").write(_script)
print(f"running teacher_job.py | PRESET={PRESET} UNASSIGN(kernel)={UNASSIGN} TEACHER_PICK={TEACHER_PICK}", flush=True)
_env = dict(os.environ, HF_TOKEN=_tok, PYTHONUNBUFFERED="1")
_rc = None
try:
    _p = subprocess.Popen([sys.executable, "/content/teacher_job.py"], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, env=_env, cwd="/content")
    _tail: list[str] = []
    for _line in _p.stdout:
        _tail = (_tail + [_line])[-40:]
        if any(k in _line for k in ("PROGRESS", "TEACHER", "checkpoint", "risks;", "PRESET", "skipping")):
            print(_line, end="", flush=True)
    _rc = _p.wait()
    print("job exit code", _rc, flush=True)
    if _rc:
        print("".join(_tail), flush=True)
finally:
    if UNASSIGN:
        from google.colab import runtime
        runtime.unassign()
