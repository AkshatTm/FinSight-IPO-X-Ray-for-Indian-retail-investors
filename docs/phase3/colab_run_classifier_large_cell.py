# One Colab cell (G4 runtime, Colab secret HF_TOKEN on): DeBERTa-v3-large, 3 seeds x (category + band).
# Inputs come from the private job repo (`gpu_jobs.py push classifier_large`); outputs (metrics,
# predictions and the best seed's weights per task) go back to `classifier_large/out/` there.
# A disconnect is safe: finished tasks/seeds are skipped when the cell is run again.
import json
import os
import subprocess
from pathlib import Path

subprocess.run(["pip", "install", "-q", "huggingface_hub"], check=False)
from google.colab import userdata
from huggingface_hub import HfApi, hf_hub_download

REPO, JOB = "AkshatTm/finsight-gpu-jobs", "classifier_large"
TOKEN = userdata.get("HF_TOKEN")
DATA = Path("data/processed/kaggle/risk-classifier")
DATA.mkdir(parents=True, exist_ok=True)
for name in ("train.jsonl", "dev.jsonl", "test.jsonl", "labels.json"):
    src = hf_hub_download(REPO, f"{JOB}/in/{name}", repo_type="dataset", token=TOKEN)
    (DATA / name).write_bytes(Path(src).read_bytes())
nb = hf_hub_download(REPO, f"{JOB}/in/notebook.ipynb", repo_type="dataset", token=TOKEN)
cells = ["".join(c["source"]) for c in json.load(open(nb))["cells"] if c["cell_type"] == "code"]

ns = {"__name__": "__main__"}
for src in cells:
    src = src.replace("SEEDS = [42]", "SEEDS = [13, 42, 2026]")
    src = src.replace("BATCH_SIZE = 4", "BATCH_SIZE = 16").replace("GRAD_ACCUM = 4", "GRAD_ACCUM = 1")
    exec(compile(src, "<cell>", "exec"), ns)

# ---- send results home: metrics + predictions, and the best seed's weights per task ------------
out = Path("classifier_out")
api = HfApi(token=TOKEN)
api.upload_folder(folder_path=str(out), repo_id=REPO, repo_type="dataset", path_in_repo=f"{JOB}/out",
                  allow_patterns=["metrics-*.json", "dev-predictions-*.json", "test-predictions-*.json"])
for prefix, folder in (("metrics-", "seed-{s}"), ("metrics-band-", "seed-{s}-band")):
    best = None
    for p in out.glob(f"{prefix}*.json"):
        s = p.stem.removeprefix(prefix)
        if not s.isdigit():
            continue
        f1 = json.loads(p.read_text())["dev"]["macro_f1"]
        if best is None or f1 > best[0]:
            best = (f1, s)
    if best:
        fin = out / folder.format(s=best[1]) / "final"
        api.upload_folder(folder_path=str(fin), repo_id=REPO, repo_type="dataset",
                          path_in_repo=f"{JOB}/out/{folder.format(s=best[1])}/final")
        print("uploaded", fin, "dev macro-F1", round(best[0], 4))
print("CLASSIFIER LARGE DONE", os.listdir(out))
