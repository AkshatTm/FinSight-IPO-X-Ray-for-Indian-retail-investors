"""Fill quality_sheet.csv with the reviewed ratings.

Every row gets faithful=1 and category_correct=1, then the rows listed in
quality_ratings.csv get their values and notes. The original is kept as
quality_sheet.orig.csv. Run from anywhere:  python apply_quality_ratings.py
"""
from pathlib import Path
import shutil
import pandas as pd

here = Path(__file__).resolve().parent
sheet = here / "quality_sheet.csv"
ratings = here / "quality_ratings.csv"
backup = here / "quality_sheet.orig.csv"

if not backup.exists():
    shutil.copy2(sheet, backup)

d = pd.read_csv(backup, encoding="utf-8")
r = pd.read_csv(ratings, encoding="utf-8")

assert len(d) == 100, f"expected 100 rows, got {len(d)}"
missing = set(r.risk_id) - set(d.risk_id)
assert not missing, f"risk_ids not in sheet: {missing}"

d["faithful"] = 1
d["category_correct"] = 1
d["notes"] = ""
d = d.set_index("risk_id")
r = r.set_index("risk_id")
d.loc[r.index, ["faithful", "category_correct", "notes"]] = r[["faithful", "category_correct", "notes"]]
d = d.reset_index()[pd.read_csv(backup, nrows=0).columns]

d.to_csv(sheet, index=False, encoding="utf-8")
print(f"faithful {d.faithful.mean():.0%} | category_correct {d.category_correct.mean():.0%} | notes {int((d.notes != '').sum())}")
print(f"wrote {sheet}")
