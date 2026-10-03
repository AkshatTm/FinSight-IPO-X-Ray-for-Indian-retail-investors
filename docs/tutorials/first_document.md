# Analyse your first IPO document

This tutorial follows one offer document through FinSight on your laptop: first a showcase IPO built with the offline pipeline, then the same kind of file uploaded through the website. It assumes you finished [Run FinSight locally](run_locally.md).

## Part 1: build a showcase IPO

Showcase IPOs are listed in `configs/demo_ipos.yaml`. Each has an RHP and a final Prospectus whose hashes are recorded there. The PDFs are public filings but are not in the repository.

1. Download the RHP and the Prospectus of one listed IPO (for example `ather-energy-2025`) from SEBI or the exchange, and save them at the paths in `configs/demo_ipos.yaml` (`data/raw/rhp/…` and `data/raw/prospectus/…`).
2. Run the stages in order:

   ```bash
   uv run python -m finsight.pipeline build --ipo ather-energy-2025 --stage parse
   uv run python -m finsight.pipeline build --ipo ather-energy-2025 --stage sections
   uv run python -m finsight.pipeline build --ipo ather-energy-2025 --stage tables
   uv run python -m finsight.pipeline build --ipo ather-energy-2025 --stage rules
   uv run python -m finsight.pipeline build --ipo ather-energy-2025 --stage xray
   uv run python -m finsight.pipeline build --ipo ather-energy-2025 --stage index
   ```

   `parse` reads every page (words and their boxes), renders page images and records each file's SHA-256; `inspect --stats` prints it so you can compare it with the config. `xray` builds the fact sheet. `index` builds the BM25 index for chat. The `qa` stage (the fine-tuned extractor as a cross-check) needs the model weights and the `ml` group, so leave it out on a first run.
3. Look at what was read, without opening the PDF:

   ```bash
   uv run python -m finsight.pipeline inspect --ipo ather-energy-2025 --stats
   uv run python -m finsight.pipeline inspect --ipo ather-energy-2025 --grep "fresh issue"
   ```

4. Open <http://localhost:3000/ipos/ather-energy-2025>. Every fact has a page chip. Click it and the document viewer jumps to the box the value was read from. In the inspector you can see each extractor's candidate and the verifier's checks.

## Part 2: upload a document

1. Open <http://localhost:3000/upload> and choose an offer document (a text PDF up to 50 MB and 1,500 pages).
2. The browser hashes the file first. If the same file was analysed before, you go straight to its report.
3. Otherwise the file is uploaded and the processing screen follows each stage as it happens (the `GET /api/docs/{doc_id}/events` stream).

!!! note "What the upload pipeline does today"
    The worker currently validates the file (text PDF, size, pages, no password, an offer
    document) and detects its type and page count. The later stages (sections, facts, red
    flags, risks, risk level, rewrites, compare, chat index) are added part by part, and the
    report page shows each part as soon as it exists. To see the finished report layout now,
    run the site with `NEXT_PUBLIC_USE_MOCKS=1` and open any report.

## What to read next

- [Architecture](../architecture/index.md): the upload and chat sequences.
- [Risk level](../reference/risklevel.md): how the level is worked out.
- [FinSight explained](../10_FINSIGHT_EXPLAINED.md): every module in plain English, with viva questions.
