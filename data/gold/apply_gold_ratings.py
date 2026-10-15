"""Write the reviewed ratings into gold150_sheet.csv and novelty_pairs.csv.

gold150: rows listed in gold150_ratings.csv get their category and a note; every other row
keeps its prefilled category (confirmed correct). novelty: same_risk filled for all 60 pairs.
Originals are kept once as *.orig.csv. Run:  python data/gold/apply_gold_ratings.py
"""
import csv
import shutil
from pathlib import Path

here = Path(__file__).resolve().parent


def backup(p: Path) -> Path:
    b = p.with_name(p.stem + ".orig.csv")
    if not b.exists():
        shutil.copy2(p, b)
    return b


def rewrite(sheet: str, ratings: str, key: str, fields: list[str], enc: str) -> tuple[int, int]:
    p = here / sheet
    src = backup(p)
    with open(here / ratings, encoding="utf-8", newline="") as fh:
        upd = {r[key]: r for r in csv.DictReader(fh)}
    with open(src, encoding=enc, newline="") as fh:
        rd = csv.DictReader(fh)
        cols, rows = rd.fieldnames, list(rd)
    seen = 0
    for r in rows:
        if r[key] in upd:
            seen += 1
            for f in fields:
                r[f] = upd[r[key]][f]
    missing = set(upd) - {r[key] for r in rows}
    assert not missing, f"{sheet}: ids not found: {missing}"
    with open(p, "w", encoding=enc, newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return len(rows), seen


n, k = rewrite("gold150_sheet.csv", "gold150_ratings.csv", "risk_id", ["category", "notes"], "utf-8-sig")
print(f"gold150: {n} rows, {k} with a note ({k - 1} category changes, 1 kept-with-note)")
n, k = rewrite("novelty_pairs.csv", "novelty_ratings.csv", "pair_id", ["same_risk"], "utf-8")
print(f"novelty: {n} pairs, {k} rated")
