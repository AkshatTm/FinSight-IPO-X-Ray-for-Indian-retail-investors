"""The extractor ladder table from the E2/E3 result files (05 section 5, ADR-031, ADR-018).

    uv run python -m finsight.evaluate.ladder

Reads ``eval_results/ladder/{rules,qa_pretrained,qa_finetuned_seed<n>}.json`` (written by
``evaluate.run_gold``) and writes ``ladder_table.{json,csv,tex}``. The Model Lab and the report
read only these.

Headline: overall NVM on the **test** IPOs, per setting, with a 95 % bootstrap interval that
resamples IPOs, and paired per-IPO differences between rungs (the same resampled IPOs for both).
Fine-tuned scores are the mean over the three seeds (per row), with the seed std beside them.
Per-field numbers are descriptive: one IPO moves a field by 10+ points. Dev scores are used only
to choose an extractor per field (``choose_extractors``), never quoted as results.
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from finsight.core.config import get_settings
from finsight.evaluate.metrics import bootstrap_ci, paired_bootstrap
from finsight.evaluate.run_gold import SETTINGS, SPLITS
from finsight.extract import SEEDS

RUNG_LABELS = {
    "rules": "Rung 1: rules",
    "qa_pretrained": "Rung 2: pretrained QA",
    "qa_finetuned": "Rung 3: fine-tuned QA",
}
RUNGS = tuple(RUNG_LABELS)
TIE_ORDER = ("rules", "qa_finetuned", "qa_pretrained")  # the simplest rung wins a tie
HEADLINE_SPLIT = "test"


def load_results(ladder_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Result files grouped by rung; the fine-tuned rung has one file per seed."""
    out: dict[str, list[dict[str, Any]]] = {}
    for rung in RUNGS:
        names = [f"qa_finetuned_seed{s}" for s in SEEDS] if rung == "qa_finetuned" else [rung]
        files = [ladder_dir / f"{n}.json" for n in names]
        missing = [f.name for f in files if not f.exists()]
        if missing:
            raise FileNotFoundError(f"missing result files: {', '.join(missing)}")
        out[rung] = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    return out


def _rows(result: dict[str, Any], split: str, setting: str) -> list[dict[str, Any]]:
    splits = {i: s for s, ids in result["data"]["splits"].items() for i in ids}
    rows = [p for p in result["predictions"] if splits[p["ipo_id"]] == split]
    if setting == "body_only":
        rows = [p for p in rows if p["in_body"]]
    return rows


def _key(row: dict[str, Any]) -> tuple[str, str]:
    return row["ipo_id"], row["field_id"]


def per_row_scores(
    results: list[dict[str, Any]], split: str, setting: str, metric: str = "nvm"
) -> dict[tuple[str, str], float]:
    """One score per (IPO, field): the mean over the files of the rung (seeds)."""
    scores: dict[tuple[str, str], list[float]] = defaultdict(list)
    for result in results:
        for row in _rows(result, split, setting):
            scores[_key(row)].append(float(row[setting][metric]))
    return {k: sum(v) / len(v) for k, v in scores.items()}


def per_ipo(scores: dict[tuple[str, str], float]) -> dict[str, list[float]]:
    out: dict[str, list[float]] = defaultdict(list)
    for (ipo, _), value in scores.items():
        out[ipo].append(value)
    return dict(out)


def _r(x: float) -> float:
    return round(x, 4)


def rung_summary(results: list[dict[str, Any]], split: str, setting: str) -> dict[str, Any]:
    nvm_scores = per_row_scores(results, split, setting)
    mean, low, high = bootstrap_ci(per_ipo(nvm_scores))
    seed_nvm = [
        sum(r[setting]["nvm"] for r in _rows(res, split, setting))
        / max(1, len(_rows(res, split, setting)))
        for res in results
    ]
    return {
        "n": len(nvm_scores),
        "n_ipos": len(per_ipo(nvm_scores)),
        "nvm": _r(mean),
        "nvm_ci95": [_r(low), _r(high)],
        "em": _r(statistics.fmean(per_row_scores(results, split, setting, "em").values())),
        "f1": _r(statistics.fmean(per_row_scores(results, split, setting, "f1").values())),
        "nvm_seed_std": _r(statistics.stdev(seed_nvm)) if len(seed_nvm) > 1 else None,
        "n_files": len(results),
    }


def per_field_nvm(results: list[dict[str, Any]], split: str, setting: str) -> dict[str, Any]:
    by_field: dict[str, list[float]] = defaultdict(list)
    for (_, field_id), value in per_row_scores(results, split, setting).items():
        by_field[field_id].append(value)
    return {f: {"n": len(v), "nvm": _r(sum(v) / len(v))} for f, v in sorted(by_field.items())}


def paired(
    a: list[dict[str, Any]], b: list[dict[str, Any]], split: str, setting: str
) -> dict[str, Any]:
    diff, low, high = paired_bootstrap(
        per_ipo(per_row_scores(a, split, setting)), per_ipo(per_row_scores(b, split, setting))
    )
    return {"diff": _r(diff), "ci95": [_r(low), _r(high)], "excludes_zero": low > 0 or high < 0}


def choose_extractors(results: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Per field, the rung with the best dev NVM (mean of the full and body-only settings that
    have rows); ties go to the simplest rung. Only dev rows are read."""
    fields = sorted({r["field_id"] for p in results["rules"][0]["predictions"] for r in [p]})
    choice: dict[str, Any] = {}
    for field_id in fields:
        board: dict[str, dict[str, Any]] = {}
        for rung in RUNGS:
            by_setting = {}
            for setting in SETTINGS:
                scores = [
                    v
                    for (_, f), v in per_row_scores(results[rung], "dev", setting).items()
                    if f == field_id
                ]
                if scores:
                    by_setting[setting] = _r(sum(scores) / len(scores))
            if by_setting:
                board[rung] = {
                    "score": _r(statistics.fmean(by_setting.values())),
                    **by_setting,
                }
        best = max(board, key=lambda r: (board[r]["score"], -TIE_ORDER.index(r)))
        choice[field_id] = {"extractor": best, "dev": board}
    return choice


def build(results: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    ladder: dict[str, Any] = {}
    for rung in RUNGS:
        ladder[rung] = {
            "label": RUNG_LABELS[rung],
            **{
                split: {s: rung_summary(results[rung], split, s) for s in SETTINGS}
                for split in SPLITS
            },
        }
    comparisons = {
        f"{a}_minus_{b}": {s: paired(results[a], results[b], HEADLINE_SPLIT, s) for s in SETTINGS}
        for a, b in (
            ("qa_finetuned", "qa_pretrained"),
            ("qa_finetuned", "rules"),
            ("qa_pretrained", "rules"),
        )
    }
    return {
        "experiment": "E2+E3",
        "name": "ladder_table",
        "headline_split": HEADLINE_SPLIT,
        "gold_version": results["rules"][0]["data"]["gold_version"],
        "git_sha": results["rules"][0]["git_sha"],
        "seeds": list(SEEDS),
        "ladder": ladder,
        "paired_test": comparisons,
        "per_field_test": {
            rung: {s: per_field_nvm(results[rung], HEADLINE_SPLIT, s) for s in SETTINGS}
            for rung in RUNGS
        },
        "choice_on_dev": choose_extractors(results),
        "notes": (
            "NVM on gold v1. Headline = test IPOs, bootstrap over IPOs (1,000 resamples), "
            "paired differences with the same IPOs drawn for both rungs. Fine-tuned = mean over "
            "3 seeds per row. body_only blanks pages 1-15 and is scored on rows whose value is "
            "still stated in the searched pages (registrar, managers and promoters are read "
            "from the cover only, so they have no body-only rows). Per-field numbers are "
            "descriptive. Dev is used only to choose the extractor per field (ADR-018)."
        ),
    }


def write_csv(table: dict[str, Any], path: Path) -> None:
    columns = ["rung", "split", "setting", "n", "n_ipos", "nvm", "ci_low", "ci_high", "em", "f1",
               "nvm_seed_std"]  # fmt: skip
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(columns)
        for rung, entry in table["ladder"].items():
            for split in SPLITS:
                for setting in SETTINGS:
                    m = entry[split][setting]
                    low, high = m["nvm_ci95"]
                    std = m["nvm_seed_std"] if m["nvm_seed_std"] is not None else ""
                    writer.writerow([rung, split, setting, m["n"], m["n_ipos"], m["nvm"],
                                     low, high, m["em"], m["f1"], std])  # fmt: skip


def _pct(x: float) -> str:
    return f"{100 * x:.1f}"


def write_tex(table: dict[str, Any], path: Path) -> None:
    lines = [
        "\\begin{tabular}{lrcccc}",
        "\\hline",
        "Rung & $n$ & NVM full (\\%) & 95\\% CI & NVM body-only (\\%) & 95\\% CI \\\\",
        "\\hline",
    ]
    for entry in table["ladder"].values():
        full, body = entry[HEADLINE_SPLIT]["full"], entry[HEADLINE_SPLIT]["body_only"]
        n = f"{full['n']} / {body['n']}"
        ci = lambda m: f"{_pct(m['nvm_ci95'][0])}--{_pct(m['nvm_ci95'][1])}"  # noqa: E731
        lines.append(
            f"{entry['label']} & {n} & {_pct(full['nvm'])} & {ci(full)} & "
            f"{_pct(body['nvm'])} & {ci(body)} \\\\"
        )
    lines += ["\\hline", "\\end{tabular}"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_all(table: dict[str, Any], out_dir: Path) -> list[Path]:
    paths = [
        out_dir / "ladder_table.json",
        out_dir / "ladder_table.csv",
        out_dir / "ladder_table.tex",
    ]
    paths[0].write_text(json.dumps(table, indent=1, ensure_ascii=False) + "\n", encoding="utf-8",
                        newline="\n")  # fmt: skip
    write_csv(table, paths[1])
    write_tex(table, paths[2])
    return paths


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    eval_dir = Path(get_settings().paths.eval_dir)
    table = build(load_results(eval_dir / "ladder"))
    for entry in table["ladder"].values():
        for setting in SETTINGS:
            m = entry[HEADLINE_SPLIT][setting]
            std = f" +-{m['nvm_seed_std']}" if m["nvm_seed_std"] is not None else ""
            print(f"{entry['label']:24} {setting:10} n={m['n']:3} NVM={m['nvm']}{std} "
                  f"CI={m['nvm_ci95']} EM={m['em']} F1={m['f1']}")  # fmt: skip
    for name, by_setting in table["paired_test"].items():
        for setting, d in by_setting.items():
            print(f"  {name:32} {setting:10} diff={d['diff']:+} CI={d['ci95']}")
    for field_id, c in table["choice_on_dev"].items():
        print(f"  dev choice {field_id:28} -> {c['extractor']}")
    for p in write_all(table, eval_dir):
        print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
