"""Write the reviewed ratings into simplify_gold50_sheet.csv (faithful, plain_english_1to5, notes).

Keeps the original once as simplify_gold50_sheet.orig.csv. Run:
    python data/gold/apply_gold50_ratings.py
"""
import csv
import shutil
from pathlib import Path

here = Path(__file__).resolve().parent
sheet = here / "simplify_gold50_sheet.csv"
orig = here / "simplify_gold50_sheet.orig.csv"
if not orig.exists():
    shutil.copy2(sheet, orig)

with open(here / "simplify_gold50_ratings.csv", encoding="utf-8", newline="") as fh:
    upd = {r["sheet_id"]: r for r in csv.DictReader(fh)}
with open(orig, encoding="utf-8-sig", newline="") as fh:
    rd = csv.DictReader(fh)
    cols, rows = rd.fieldnames, list(rd)

assert len(rows) == len(upd) == 150, f"rows {len(rows)} ratings {len(upd)}"
for r in rows:
    u = upd[r["sheet_id"]]
    r["faithful"], r["plain_english_1to5"], r["notes"] = u["faithful"], u["plain_english_1to5"], u["notes"]

with open(sheet, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
yes = sum(r["faithful"] == "yes" for r in rows)
print(f"rated {len(rows)} rows: faithful yes {yes}, partly {len(rows) - yes}")
