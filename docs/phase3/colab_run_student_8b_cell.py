# Paste this whole cell into ONE code cell of a Colab notebook on a G4 runtime and run it.
# Needs the Colab secret HF_TOKEN (notebook access on). It pulls notebooks/c2_student.ipynb from the
# private job repo, runs the 8B smoke, then the real 8B run (checkpoints every 200 steps synced to the
# job repo; a disconnect is safe: re-run the cell with MODE = "resume").
MODE = "smoke_then_full"   # "smoke_then_full" | "resume" (continue the full run after a disconnect)
UNITS_BEFORE = None         # optional: units shown in the Resources panel before you start

import json, subprocess
print(subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv"],
                     capture_output=True, text=True).stdout)
subprocess.run(["pip", "install", "-q", "huggingface_hub"], check=False)
from google.colab import userdata
from huggingface_hub import hf_hub_download

NB = hf_hub_download("AkshatTm/finsight-gpu-jobs", "notebooks/c2_student.ipynb",
                     token=userdata.get("HF_TOKEN"))
CELLS = ["".join(c["source"]) for c in json.load(open(NB))["cells"] if c["cell_type"] == "code"]


def run_notebook(overrides):
    ns = {"__name__": "__main__"}
    for src in CELLS:
        for old, new in overrides.items():
            src = src.replace(old, new)
        exec(compile(src, "<cell>", "exec"), ns)
    return ns


units = f"UNITS_BEFORE = {UNITS_BEFORE}"
if MODE == "smoke_then_full":
    run_notebook({'PRESET = "student_smoke"': 'PRESET = "student_8b_smoke"',
                  "UNASSIGN = True": "UNASSIGN = False"})
    run_notebook({'PRESET = "student_smoke"': 'PRESET = "student_8b"', "RESUME = True": "RESUME = False",
                  "UNITS_BEFORE = None": units})
else:
    run_notebook({'PRESET = "student_smoke"': 'PRESET = "student_8b"', "RESUME = True": "RESUME = True",
                  "UNITS_BEFORE = None": units})
