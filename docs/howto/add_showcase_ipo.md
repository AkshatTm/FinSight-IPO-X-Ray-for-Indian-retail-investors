# Add a showcase IPO

Showcase IPOs are the prebuilt reports in the library. Each has an RHP and its final Prospectus.

1. **Get the documents.** Download the RHP and the Prospectus from SEBI or the exchange. Save them as `data/raw/rhp/<ipo_id>.pdf` and `data/raw/prospectus/<ipo_id>.pdf`; `<ipo_id>` is the company slug and the year, like `meesho-2025`. The PDFs are never committed.
2. **Register them** in `configs/demo_ipos.yaml`: `ipo_id`, `company`, `split` and, for each document, `file`, `pages`, `sha256` and the cover's `dated` line. `doc_id` is `doc_` plus the first 16 hex characters of the hash (B-ADR-14).
   - `split: dev` IPOs may be used to tune rules and thresholds.
   - `split: test` IPOs are only for reported numbers (ADR-026). Do not tune on them.
3. **Add the sector and listing date** to `configs/ipo_meta.yaml` from a public listing record.
4. **Exclude it from training data:** the corpus builder drops every company in `configs/demo_ipos.yaml` and in `data/gold/excluded_ipos.txt` (`finsight.ingest.exclusion`). Rebuild the corpus if it was built before this IPO was added.
5. **Build it** stage by stage (see [Analyse your first IPO document](../tutorials/first_document.md)), then add `--stage qa` on a machine with the extractor weights.
6. **Record the demo answers** ([Record the demo cache](record_demo_cache.md)).
7. **Check:** `uv run poe test`, then open `/ipos/<ipo_id>` and click through every fact's page chip.
