"""Build the Phase 4 handoff pack ``ml/handoff/`` for ARGON (CC-02).

    uv run python scripts/export_handoff.py --data-root <checkout with data/processed and models>
    uv run python scripts/export_handoff.py --only selection,templates     # a subset of steps
    uv run python scripts/export_handoff.py --upload   # push files > 4.5 MB and the pack (HF_TOKEN from env or .env)

Reads saved artefacts only (never a PDF into text for reading; the serious-finding step runs the
product's own sentence rules over already-parsed documents). Export, don't move: product code and
data are unchanged. ``--data-root`` is the checkout that holds the git-ignored ``data/processed``,
``data/raw`` and ``models`` (a worktree has none); it defaults to this repo. Output files over 4.5 MB
are listed in ``ml/handoff/data/.gitignore`` and go to the private HF dataset repo (C-ADR-13).
The step ``READY`` is separate: ``touch ml/handoff/READY`` only after the checks pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tomllib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finsight.bench import read_ipo_ids  # noqa: E402
from finsight.core.ids import make_doc_id  # noqa: E402
from finsight.handoff import (  # noqa: E402
    build_baselines,
    build_lite,
    build_manifest,
    chat_template,
    excluded_ipos,
    five_things,
    rewrite_template,
    risk_bank_rows,
    sha256_file,
    splits_by_ipo,
    with_ipo,
    write_jsonl_gz,
    write_manifest,
    write_parquet,
)
from finsight.handoff.templates import versions  # noqa: E402

STEPS = (
    "selection",
    "bank",
    "classifier",
    "student",
    "templates",
    "hits",
    "five",
    "bench",
    "gold",
    "eval",
    "colab",
    "context",
    "manifest",
    "readme",
)
HF_REPO = "AkshatTm/finsight-gpu-jobs"
HF_PREFIX = "phase4/handoff"
GOLD_FILES = (
    "gold150.jsonl",
    "simplify_gold50_sheet.csv",
    "simplify_gold50_ratings.csv",
    "gold_v3_summary.jsonl",
    "gold_v3_1_summary.jsonl",
    "redflag_status_gold.jsonl",
)
BENCH_COPY = ("manifest.yaml", "scoring.yaml", "items", "keys", "prompts", "inputs")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


class Pack:
    """Paths and shared state of one export run."""

    def __init__(self, data_root: Path, out: Path) -> None:
        self.root = ROOT
        self.dr = data_root
        self.out = out
        self.data = out / "data"
        self.stats: dict[str, Any] = {}
        self.splits = yaml.safe_load((ROOT / "configs" / "splits.yaml").read_text("utf-8"))

    def excluded(self) -> dict[str, Any]:
        path = self.data / "excluded_ipos.json"
        if path.exists():
            return load_json(path)
        return self.step_selection()

    def excluded_set(self) -> set[str]:
        return set(self.excluded()["ipos"])

    def step_selection(self) -> dict[str, Any]:
        demo = yaml.safe_load((ROOT / "configs" / "demo_ipos.yaml").read_text("utf-8"))
        demo_ids = [str(i["ipo_id"]) for i in demo["ipos"]]
        bench = yaml.safe_load((ROOT / "bench" / "v1" / "manifest.yaml").read_text("utf-8"))
        platform = read_ipo_ids(
            self.dr / "data" / "platform_bench" / "FinSight_Platform_Bench.xlsx"
        )
        ex = excluded_ipos(self.splits, demo_ids, [str(i) for i in bench["ipos"]], sorted(platform))
        ex["platform_bench_sheet_ids"] = platform  # normalised id -> id as written in the sheet
        write_json(self.data / "excluded_ipos.json", ex)
        write_json(self.data / "splits_by_ipo.json", splits_by_ipo(self.splits, ex))
        self.stats["selection"] = {"excluded": ex["n"], "platform_ids": len(platform)}
        return ex

    def step_bank(self) -> None:
        import pyarrow.parquet as pq

        proc = self.dr / "data" / "processed"
        bank = pq.read_table(
            proc / "bank" / "risk_bank.parquet",
            columns=["risk_id", "company", "year", "title", "ipo_id", "doc_date", "split"],
        ).to_pylist()
        scored = {
            p.stem: load_json(p)
            for p in sorted((proc / "risk_bank" / "scored").glob("*.json"))
            if not p.name.endswith(".flags.json")
        }
        teacher = {r["risk_id"]: r for r in read_jsonl(proc / "teacher" / "labels.clean.jsonl")}
        cats = load_json(proc / "risk_bank" / "categories.json")
        rows, st = risk_bank_rows(bank, scored, teacher, cats, self.excluded_set())
        write_parquet(self.data / "risk_bank.parquet", rows)
        self.stats["bank"] = {"rows": len(rows), **st, "scored_ipos": len(scored)}

    def step_classifier(self) -> None:
        d = self.dr / "data" / "processed" / "kaggle" / "risk-classifier"
        ex = self.excluded_set()
        st: dict[str, Any] = {}
        for name, src, kw in (
            ("train", "train", {}),
            ("dev", "dev", {}),
            ("test", "test", {"keep": True}),
        ):
            label_source = "human_verified_ai" if name == "test" else "ai"
            rows, dropped = with_ipo(read_jsonl(d / f"{src}.jsonl"), label_source, ex, **kw)
            n = write_jsonl_gz(self.data / f"classifier_{name}.jsonl.gz", rows)
            st[name] = {"rows": n, "dropped_excluded": dropped, "label_source": label_source}
        (self.data / "classifier_labels.json").write_text(
            (d / "labels.json").read_text("utf-8"), encoding="utf-8", newline="\n"
        )
        self.stats["classifier"] = st

    def step_student(self) -> None:
        d = self.dr / "data" / "processed" / "kaggle" / "simplify"
        ex = self.excluded_set()
        st: dict[str, Any] = {}
        for name in ("train", "dev"):
            rows, dropped = with_ipo(read_jsonl(d / f"{name}.jsonl"), "ai", ex)
            n = write_jsonl_gz(self.data / f"student_v1_{name}.jsonl.gz", rows)
            st[name] = {"rows": n, "dropped_excluded": dropped}
        self.stats["student"] = st

    def step_templates(self) -> None:
        self.data.mkdir(parents=True, exist_ok=True)
        for name, text in (
            ("student_prompt_template.txt", rewrite_template()),
            ("student_chat_template.txt", chat_template("en")),
            ("student_chat_template_hi.txt", chat_template("hi")),
        ):
            (self.data / name).write_text(text + "\n", encoding="utf-8", newline="\n")
        self.stats["templates"] = versions()

    def step_hits(self) -> None:
        from finsight.core.schemas import ParsedDoc, Section
        from finsight.parse import find_sections
        from finsight.redflags.severe import matches

        proc = self.dr / "data" / "processed"
        cache = proc / "handoff_cache"
        cache.mkdir(parents=True, exist_ok=True)
        ex = self.excluded()["ipos"]
        rows_out: list[dict[str, Any]] = []
        read = skipped = 0
        for row in self.splits["ipos"]:
            ipo_id = str(row["ipo_id"])
            if row.get("source") == "corpus":
                continue  # 2009-2023 corpus IPOs are page text only (no parsed word boxes)
            part = cache / f"{ipo_id}.json"
            if not part.exists():
                pdf = next(
                    (
                        p
                        for p in (
                            self.dr / "data" / "raw" / "offer_docs" / f"{ipo_id}.pdf",
                            self.dr / "data" / "raw" / "rhp" / f"{ipo_id}.pdf",
                        )
                        if p.exists()
                    ),
                    None,
                )
                sha = hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf else None
                base = proc / "batch" / "store" / "docs" / make_doc_id(sha) if sha else None
                if base is None or not (base / "parsed.json").exists():
                    base = proc / ipo_id
                if not (base / "parsed.json").exists():
                    skipped += 1
                    continue
                doc = ParsedDoc.model_validate_json((base / "parsed.json").read_bytes())
                sections: list[Section] = find_sections(doc)
                hits = [
                    {
                        "ipo_id": ipo_id,
                        "slice": row.get("slice"),
                        "excluded": ipo_id in ex,
                        "check_id": m.kind,
                        "page": m.page,
                        "sentence": m.sentence,
                        "context_before": " ".join(m.before),
                        "context_after": " ".join(m.after),
                        "rules_decision": m.decision,
                        "label_source": "rule",
                    }
                    for m in matches(doc, sections)
                ]
                part.write_text(
                    json.dumps(hits, ensure_ascii=False), encoding="utf-8", newline="\n"
                )
            rows_out.extend(load_json(part))
            read += 1
        for i, r in enumerate(rows_out):
            r["id"] = f"hit{i:06d}"
        n = write_jsonl_gz(self.data / "serious_finding_hits.jsonl.gz", rows_out)
        by = {}
        for r in rows_out:
            by[r["rules_decision"]] = by.get(r["rules_decision"], 0) + 1
        self.stats["hits"] = {
            "rows": n,
            "docs_read": read,
            "docs_without_parse": skipped,
            "by_decision": by,
        }

    def step_five(self) -> None:
        proc = self.dr / "data" / "processed" / "risk_bank" / "scored"
        ex = self.excluded_set()
        scored = {
            p.stem: load_json(p)
            for p in sorted(proc.glob("*.json"))
            if not p.name.endswith(".flags.json") and p.stem not in ex
        }
        rows = five_things(scored)
        n = write_jsonl_gz(self.data / "five_things_selection.jsonl.gz", rows)
        self.stats["five"] = {"rows": n, "ipos": len(scored)}

    def step_bench(self) -> None:
        import shutil

        dst = self.data / "bench_v1"
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True)
        for name in BENCH_COPY:
            src = ROOT / "bench" / "v1" / name
            if src.is_dir():
                shutil.copytree(src, dst / name)
            else:
                shutil.copy2(src, dst / name)
        (dst / "README.md").write_text(
            "Bench v1 is FROZEN and for evaluation only (7 test-slice IPOs). Never train on it.\n"
            "Scoring needs the product repo: see eval/run_bench.py.\n",
            encoding="utf-8",
            newline="\n",
        )
        self.stats["bench"] = {"files": sum(1 for p in dst.rglob("*") if p.is_file())}

    def step_gold(self) -> None:
        import shutil

        dst = self.data / "gold"
        dst.mkdir(parents=True, exist_ok=True)
        got = []
        for name in GOLD_FILES:
            src = ROOT / "data" / "gold" / name
            if src.exists():
                shutil.copy2(src, dst / name)
                got.append(name)
        (dst / "README.md").write_text(
            "Evaluation gold. gold150 = risk categories + bands (test-slice IPOs, human-verified); "
            "simplify_gold50 = rewrite sheet + Akshat's blind ratings; gold_v3 = 10 showcase IPOs' "
            "red-flag inputs (v3.1 = four convention fixes, some rows await Akshat's check).\n"
            "None of these IPOs may enter training data.\n",
            encoding="utf-8",
            newline="\n",
        )
        self.stats["gold"] = {"files": got}

    def step_eval(self) -> None:
        ev = self.out / "eval"
        build_lite(ROOT / "src" / "finsight", ev / "vendor")
        er = ROOT / "eval_results"
        mr = self.dr / "models" / "risk_classifier"
        sources: dict[str, dict[str, str]] = {}

        def src(name: str, path: Path) -> Any:
            base_dir = ROOT if path.is_relative_to(ROOT) else self.dr
            sources[name] = {
                "path": path.relative_to(base_dir).as_posix(),
                "sha256": sha256_file(path),
            }
            return load_json(path)

        base = build_baselines(
            classifier=src("classifier_base", er / "b" / "classifier_base.json"),
            band_seed_metrics=src("metrics_band_42", mr / "metrics-band-42.json"),
            bench=src("bench_summary", er / "c4" / "bench_summary.json"),
            gold50_rating=src("simplify_gold50", er / "c" / "simplify_gold50.json"),
            gold50_checks=src("student_vs_base_gold50", er / "c" / "student_vs_base_gold50.json"),
            student_eval=src("student_eval", er / "c" / "student_eval.json"),
            sources=sources,
        )
        write_json(ev / "baselines.json", base)
        self.stats["eval"] = {"severe_recall": base["m4_severity"]["severe_recall_mean"]}

    def step_colab(self) -> None:
        lock = tomllib.loads((ROOT / "uv.lock").read_text("utf-8"))
        ver = {p["name"]: p["version"] for p in lock["package"]}
        want = [
            "transformers",
            "datasets",
            "peft",
            "accelerate",
            "onnx",
            "onnxruntime",
            "optimum",
            "pyarrow",
            "pandas",
            "scikit-learn",
            "sentencepiece",
            "pydantic",
            "numpy",
            "pyyaml",
        ]
        lines = [f"{n}=={ver[n]}" for n in want if n in ver]
        (self.out / "colab").mkdir(parents=True, exist_ok=True)
        (self.out / "colab" / "requirements_colab.txt").write_text(
            "# pins from the product's uv.lock; torch and CUDA come from the Colab image\n"
            + "\n".join(lines)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        self.stats["colab"] = {"pins": len(lines)}

    def step_context(self) -> None:
        text = (ROOT / "docs" / "phase4" / "P4_HANDOFF_CONTRACT.md").read_text("utf-8")
        body = (
            "# Interfaces and metrics.json schema (frozen after CC-02; change only via Akshat)\n\n"
            "Copied from `docs/phase4/P4_HANDOFF_CONTRACT.md` sections C and D by the exporter.\n\n"
            + text[text.index("## C. Interfaces") :]
        )
        (self.out / "context").mkdir(parents=True, exist_ok=True)
        (self.out / "context" / "interfaces.md").write_text(body, encoding="utf-8", newline="\n")

    def step_manifest(self, revision: str | None = None) -> None:
        manifest = build_manifest(self.data, HF_REPO, f"{HF_PREFIX}/data", revision)
        write_manifest(manifest, self.data / "MANIFEST.json")
        big = [f for f in manifest["files"] if f["where"] == "hf"]
        self.stats["manifest"] = {
            "files": len(manifest["files"]),
            "hf_files": [f["path"] for f in big],
            "hf_revision": revision,
        }

    def step_readme(self) -> None:
        stats = {**load_json(self.out / "export_stats.json"), **self.stats}
        manifest = load_json(self.data / "MANIFEST.json")
        (self.out / "README.md").write_text(
            readme_text(stats, manifest), encoding="utf-8", newline="\n"
        )

    def hf_token(self) -> str:
        """HF_TOKEN from the environment or the data root's .env (value never printed)."""
        tok = os.environ.get("HF_TOKEN", "")
        env = self.dr / ".env"
        if not tok and env.exists():
            for line in env.read_text("utf-8").splitlines():
                if line.startswith("HF_TOKEN="):
                    tok = line.split("=", 1)[1].split("#", 1)[0].strip().strip("\"'")
        if not tok:
            raise SystemExit("HF_TOKEN not set (env or .env)")
        return tok

    def upload_large(self) -> str:
        """Commit the files over 5 MB to the private HF dataset repo; return the commit sha."""
        from huggingface_hub import CommitOperationAdd, HfApi

        api = HfApi(token=self.hf_token())
        api.create_repo(HF_REPO, repo_type="dataset", private=True, exist_ok=True)
        manifest = load_json(self.data / "MANIFEST.json")
        ops = [
            CommitOperationAdd(
                path_in_repo=f["hf"]["path"], path_or_fileobj=str(self.data / f["path"])
            )
            for f in manifest["files"]
            if f["where"] == "hf"
        ]
        info = api.create_commit(
            repo_id=HF_REPO,
            repo_type="dataset",
            operations=ops,
            commit_message="phase4 handoff: large data files (CC-02)",
        )
        self.stats["upload_large"] = {"revision": info.oid, "files": [o.path_in_repo for o in ops]}
        return str(info.oid)

    def upload_pack(self) -> str:
        """Upload the whole pack folder (Colab fetches it from here); return the commit sha."""
        from huggingface_hub import HfApi

        api = HfApi(token=self.hf_token())
        info = api.upload_folder(
            repo_id=HF_REPO,
            repo_type="dataset",
            folder_path=str(self.out),
            path_in_repo=HF_PREFIX,
            ignore_patterns=["**/__pycache__/**", "*.pyc"],
            commit_message="phase4 handoff pack (CC-02)",
        )
        self.stats["upload_pack"] = {"commit": str(info.oid)}
        return str(info.oid)


README_TEMPLATE = (Path(__file__).resolve().parent / "handoff_readme.md.tmpl").read_text(
    encoding="utf-8"
)


def readme_text(stats: dict[str, Any], manifest: dict[str, Any]) -> str:
    """The pack README from a template; every number comes from the export stats."""
    g = stats.get
    bank, cl, st = g("bank", {}), g("classifier", {}), g("student", {})
    hits, five, sel = g("hits", {}), g("five", {}), g("selection", {})
    big = [f["path"] for f in manifest["files"] if f["where"] == "hf"]
    values = {
        "HF_REPO": HF_REPO,
        "HF_PREFIX": HF_PREFIX,
        "REV": manifest.get("hf_revision") or "(not uploaded yet)",
        "BIG": ", ".join(big) or "none",
        "N_EXCLUDED": sel.get("excluded"),
        "BANK_ROWS": bank.get("rows"),
        "BANK_TEACHER": bank.get("teacher"),
        "BANK_MODEL": bank.get("model"),
        "BANK_NO_TEXT": bank.get("no_text"),
        "CL_TRAIN": cl.get("train", {}).get("rows"),
        "CL_DEV": cl.get("dev", {}).get("rows"),
        "CL_TEST": cl.get("test", {}).get("rows"),
        "ST_TRAIN": st.get("train", {}).get("rows"),
        "ST_DEV": st.get("dev", {}).get("rows"),
        "HITS_ROWS": hits.get("rows", "not built yet"),
        "HITS_DOCS": hits.get("docs_read", "?"),
        "HITS_BY": hits.get("by_decision", {}),
        "FIVE_ROWS": five.get("rows"),
        "FIVE_IPOS": five.get("ipos"),
    }
    out = README_TEMPLATE
    for key, val in values.items():
        out = out.replace("@@" + key + "@@", str(val))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--data-root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path, default=ROOT / "ml" / "handoff")
    ap.add_argument("--only", default=",".join(STEPS), help=f"comma list of {STEPS}")
    ap.add_argument("--upload", action="store_true", help="push big files + the pack to HF")
    args = ap.parse_args(argv)
    pack = Pack(args.data_root, args.out)
    for step in [s for s in STEPS if s in args.only.split(",")]:
        print(f"== {step}", flush=True)
        getattr(pack, f"step_{step}")()
    if args.upload:
        print("== upload", flush=True)
        rev = pack.upload_large()
        pack.step_manifest(rev)
        pack.step_readme()
        pack.upload_pack()
    stats_path = args.out / "export_stats.json"
    merged = load_json(stats_path) if stats_path.exists() else {}
    merged.update(pack.stats)
    write_json(stats_path, merged)
    print(json.dumps(pack.stats, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
