"""Write the results table of README.md from ``eval_results/`` (nothing typed by hand).

``render_final`` writes the README's v1.1 headline table (the same files as
``eval_results/final/FINAL_SCORECARD.md``, each row linked to its file); ``render`` writes the
Phase 1 table used by the evaluation page.

    uv run python scripts/readme_results.py          # rewrite the block in README.md
    uv run python scripts/readme_results.py --check  # exit 1 if README.md is out of date

The block sits between ``<!-- results:start -->`` and ``<!-- results:end -->``. A row whose file is
missing is left out, not invented. Numbers are the test-IPO figures; read the intervals in the
files, not only the point scores.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

START, END = "<!-- results:start -->", "<!-- results:end -->"


def load(eval_dir: Path, name: str) -> dict[str, Any] | None:
    path = eval_dir / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def pct(x: float) -> str:
    return f"{x:.2f}"


def ci(pair: list[float]) -> str:
    return f"[{pair[0]:.2f}, {pair[1]:.2f}]"


def ladder_rows(eval_dir: Path) -> list[str]:
    table = load(eval_dir, "ladder_table.json")
    if table is None:
        return []
    rows = []
    for data in table["ladder"].values():
        test = data["test"]
        full, body = test["full"], test["body_only"]
        rows.append(
            f"| Extractor ladder, {data['label']} | NVM, 7 test IPOs | full {pct(full['nvm'])}, "
            f"body-only {pct(body['nvm'])} | `ladder_table.json` |"
        )
    return rows


def simple_rows(eval_dir: Path) -> list[str]:
    rows = []
    verifier = load(eval_dir, "verifier.json")
    if verifier:
        held = verifier["headline"]["scale_mismatch_recall"]["held_out"]
        rows.append(
            f"| Number verifier, seeded errors | scale-mismatch recall, held out | "
            f"{held['hits']}/{held['n']} {ci(held['wilson_95'])} | `verifier.json` |"
        )
    guard = load(eval_dir, "guard.json")
    if guard:
        o = guard["overall"]
        rows.append(
            f"| Advice guard (keyword), in-sample | block / false-block | "
            f"{o['block_rate']['hits']}/{o['block_rate']['n']} / "
            f"{o['false_block_rate']['hits']}/{o['false_block_rate']['n']} | `guard.json` |"
        )
    retrieval = load(eval_dir, "retrieval.json")
    if retrieval:
        for method in ("bm25", "hybrid+rerank"):
            m = retrieval["methods"].get(method)
            if m:
                t = m["test"]["all"]
                rows.append(
                    f"| Retrieval, {method} | recall@1 / recall@5, 56 test questions | "
                    f"{pct(t['recall@1']['mean'])} / {pct(t['recall@5']['mean'])} | `retrieval.json` |"
                )
    e7 = load(eval_dir, "e7.json")
    if e7:
        for split, s in e7.items():
            share = s.get("verified_share")
            if share is not None:
                rows.append(
                    f"| Chat answers (E7, {split}), one run | numbers marked ✅ | "
                    f"{pct(share)} of {s['n_numbers']} | `e7.json` |"
                )
    return rows


def render(eval_dir: Path) -> str:
    rows = [*ladder_rows(eval_dir), *simple_rows(eval_dir)]
    head = ["| Experiment | Metric | Result | File |", "|---|---|---|---|"]
    return "\n".join([*head, *rows])


REPO = "https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/"


def _link(eval_dir: Path, name: str) -> str:
    return f"[`{name}`]({REPO}eval_results/{name})"


def _iv(m: dict[str, Any]) -> str:
    return f"{m['mean']:.3f} [{m['low']:.3f}, {m['high']:.3f}]"


def final_rows(eval_dir: Path) -> list[str]:
    """Headline v1.1 rows; a row whose file is missing is left out."""
    rows = []
    e14 = load(eval_dir, "final/e14_today.json")
    if e14:
        s = e14["summary"]
        rows.append(
            f"| Key facts from the offer document (E14) | value match, 10 showcase IPOs, gold v3 | "
            f"**{s['nvm']:.3f}** ({s['n_valued']} rows) | re-measured, v1.1 | "
            f"{_link(eval_dir, 'final/e14_today.json')} |"
        )
    e15 = load(eval_dir, "final/e15_today.json")
    if e15:
        s = e15["summary"]
        rows.append(
            f"| Red-flag statuses (E15) | accuracy, 13 checks × {s['n_ipos']} IPOs | "
            f"**{s['accuracy']:.3f}** ({s['n_rows']} statuses) | re-measured, v1.1 | "
            f"{_link(eval_dir, 'final/e15_today.json')} |"
        )
    clf = load(eval_dir, "b/classifier_base.json")
    if clf:
        c = clf["category"]
        rows.append(
            f"| Risk category classifier (DeBERTa-v3-base) | dev macro-F1, {c['n_seeds']} seeds "
            f"(TF-IDF {c['tfidf_dev_macro_f1']:.3f}) | **{c['dev_macro_f1_mean']:.3f} ± "
            f"{c['dev_macro_f1_sd']:.3f}**; gold-150 {c['test_macro_f1_mean']:.3f} | carried | "
            f"{_link(eval_dir, 'b/classifier_base.json')} |"
        )
    simp = load(eval_dir, "c/simplify_gold50.json")
    if simp:
        b, st, t = (simp["systems"][k] for k in ("base", "student", "teacher"))
        rows.append(
            f"| Plain-English rewrites, faithful (gold-50, blind human rating) | "
            f"base / student / teacher | {b['faithful_yes_share']:.2f} / "
            f"**{st['faithful_yes_share']:.2f}** / {t['faithful_yes_share']:.2f} | carried, one seed | "
            f"{_link(eval_dir, 'c/simplify_gold50.json')} |"
        )
        rows.append(
            f"| Plain-English rewrites, readability 1–5 (gold-50) | base / student / teacher | "
            f"{b['plain_english_mean']:.2f} / **{st['plain_english_mean']:.2f}** / "
            f"{t['plain_english_mean']:.2f} | carried, one seed | "
            f"{_link(eval_dir, 'c/simplify_gold50.json')} |"
        )
    svb = load(eval_dir, "c/student_vs_base_gold50.json")
    if svb:
        st, b = svb["systems"]["student"], svb["systems"]["base"]
        rows.append(
            f"| Rewrites passing the product post-checks (gold-50) | student vs base | "
            f"**{st['passed']} / {svb['n']}** vs {b['passed']} / {svb['n']} | carried, one seed | "
            f"{_link(eval_dir, 'c/student_vs_base_gold50.json')} |"
        )
    bench = load(eval_dir, "c4/bench_summary.json")
    if bench:
        r = bench["systems"]["rules_v1"]
        n = len(bench["ipos"])
        rows.append(
            f"| FinSight Bench v1, task A key facts (rules) | value match [95 % CI], {n} test IPOs | "
            f"{_iv(r['A']['nvm'])} | carried, single run | {_link(eval_dir, 'c4/bench_summary.json')} |"
        )
        rows.append(
            f"| FinSight Bench v1, task B red flags (rules) | status accuracy [95 % CI] | "
            f"{_iv(r['B']['status_accuracy'])} | carried, single run | "
            f"{_link(eval_dir, 'c4/bench_summary.json')} |"
        )
    return rows


def render_final(eval_dir: Path) -> str:
    """The README results table: metric, value, status and a link to the result file."""
    head = ["| What | Metric | Result | Status | File |", "| --- | --- | --- | --- | --- |"]
    return "\n".join([*head, *final_rows(eval_dir)])


def replace_block(readme: str, body: str) -> str:
    start, end = readme.index(START), readme.index(END)
    return readme[: start + len(START)] + "\n" + body + "\n" + readme[end:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    parser.add_argument("--eval-dir", type=Path, default=Path("eval_results"))
    args = parser.parse_args(argv)
    current = args.readme.read_text(encoding="utf-8")
    updated = replace_block(current, render_final(args.eval_dir))
    if args.check:
        return 0 if updated == current else 1
    args.readme.write_text(updated, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
