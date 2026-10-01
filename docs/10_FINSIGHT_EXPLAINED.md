# 10 — FinSight Explained (learning doc + viva prep)

Written for someone starting NLP from zero. Read Part A and B now; Part C grows as each module is built (Claude Code appends a section per module); Part D is the viva drill. If a paragraph doesn't make sense, ask Claude to explain it with a different example — that's what this doc is for.

---

## Part A — The finance you need

**IPO (Initial Public Offering).** A private company sells shares to the public for the first time and lists on NSE/BSE.

**DRHP vs RHP.** The *Draft* Red Herring Prospectus is filed with SEBI first; key numbers like the price are left blank as `[●]`. The *Red Herring Prospectus* is the updated version filed just before the issue opens; most numbers are filled in. We use RHPs.

**Fresh issue vs Offer for Sale (OFS).** Fresh issue = the company creates new shares; the money goes to the company. OFS = existing shareholders (often promoters or investors) sell their shares; the money goes to them, not the company. Total issue = fresh + OFS. A retail investor cares because "how much actually goes into the business" is the fresh part.

**Price band.** The range (e.g. ₹440–₹463) within which investors bid. **Face value** is a nominal accounting value (e.g. ₹2), not the price.

**Promoters.** The people/entities who control the company. **Book Running Lead Managers (BRLMs)** are the investment banks managing the issue. **Registrar** handles applications and allotment.

**Objects of the Offer.** What the company will do with the fresh-issue money (repay debt, build a plant, etc.), usually a table.

**Lakh and crore.** 1 lakh = 1,00,000 = 10⁵. 1 crore = 1,00,00,000 = 10⁷ = 100 lakh. 1 million = 10⁶ = 10 lakh. 1 billion = 10⁹ = 100 crore. So ₹1,250 crore = ₹12,500 million = ₹12.5 billion. Indian grouping puts commas after the first three digits, then every two: 12,50,00,00,000.

**Why SEBI matters to us.** Recommending whether to buy a security requires SEBI registration. FinSight only explains the document.

---

## Part B — NLP and ML concepts (in pipeline order)

### B1. Text extraction from PDFs
A PDF stores characters with positions, not paragraphs. PyMuPDF gives us every word with its bounding box (x0, y0, x1, y1). Keeping boxes is what lets us draw a highlight on the page image later. Scanned PDFs are just pictures of text; without OCR we can't read them, so we detect and skip them.

### B2. Tokens and tokenization
Models don't read words; they read *tokens* — pieces of words from a fixed vocabulary. "crore" might be one token; "₹1,250.00" might be five. Every model has its own tokenizer, and length limits (e.g. 384 tokens for our QA model) are counted in tokens.

### B3. Embeddings
An embedding turns a piece of text into a list of numbers (a vector) so that similar meanings land close together. "offer for sale" and "OFS" end up near each other. We use embeddings to find passages related to a question (B11).

### B4. Transformers and attention (just enough)
A transformer reads all tokens at once and, for each token, computes *attention*: how much to look at every other token. That's how "it" in a sentence can be linked to the right noun. Stacking many attention layers gives rich, context-aware token representations.

### B5. Encoder models: BERT → DeBERTa
Encoder models (BERT family) read text and produce a vector per token; they're great for understanding tasks. **DeBERTa-v3** improves BERT by separating *what* a token is from *where* it is (disentangled attention) and a better pre-training task. We use `deberta-v3-base` (~184 M parameters) — small enough for a T4 and our laptop.

### B6. Extractive question answering
Give the model a question and a passage; it outputs the *span* of the passage that answers it. Technically it predicts, for every token, a score for "answer starts here" and "answer ends here"; the best valid (start, end) pair is the answer. **SQuAD 2.0** adds unanswerable questions: the model can point at a special "no answer" token. This matters because most passages in an RHP don't contain the fresh-issue size.

Why extractive rather than generative for the X-Ray? An extractive model can only copy text that exists in the document — it cannot invent a number.

### B7. Fine-tuning
Start from a model that already knows English and general QA (`deberta-v3-base-squad2`), then keep training it on our own examples so it learns RHP wording. Key knobs: learning rate (3e-5: small steps so we don't destroy what it knows), epochs (2–3 passes over data), batch size, warm-up. We run 3 random seeds because results vary a bit run to run; we report mean ± std.

### B8. Distant supervision (weak labelling) — our key idea
We have no labelled training data. But the cover page states the issue sizes in a very standard sentence that simple rules can read with high precision. So:
1. Rules read the true value from the cover page (the "seed").
2. We search the rest of the RHP for passages containing the *same normalized value* (₹800 crore == ₹8,000 million).
3. Those passages become training examples: question "What is the fresh issue size?", answer = that span.
4. Passages without the value become "no answer" examples.
The model then learns to find the value in wordings the rules never saw. Labels are "weak" (some are wrong), so we audit 50 and report precision. This idea comes from relation extraction (Mintz et al., 2009).

### B9. The extractor ladder
Rung 1 rules → Rung 2 pretrained QA → Rung 3 our fine-tuned QA → (Rung 4 BiLSTM-CRF). Comparing rungs on the same gold set shows *what each step buys you*. That comparison is the core experimental result.

### B10. BiLSTM-CRF (sequence labelling)
A different way to extract: label every token with a tag — `B-FRESH` (beginning), `I-FRESH` (inside), `O` (outside). An LSTM reads tokens left-to-right and right-to-left (bidirectional) to build context; a CRF layer on top makes the tag sequence consistent (it won't allow `O` followed by `I-FRESH`). Older than transformers, smaller, and a good syllabus comparison.

### B11. Retrieval: BM25, dense, fusion, reranking
To answer a chat question we first find the 5 most relevant passages out of thousands.
- **BM25** scores passages by matching words, weighting rare words more. Great for exact terms and numbers.
- **Dense retrieval** compares embeddings (B3); finds matches even with different wording, and with **bge-m3** even across languages (Hindi question → English passage).
- **Reciprocal Rank Fusion** combines both rankings: each passage gets Σ 1/(60 + rank). Simple and robust.
- **Reranker (cross-encoder)** reads question and passage *together* and scores relevance precisely. Too slow for thousands, perfect for re-ordering the top 20.
If even the best passage scores low, we **abstain** instead of guessing.

### B12. RAG (retrieval-augmented generation)
Put the retrieved passages into the LLM's prompt and instruct it to answer only from them, citing `[n]`. The model's knowledge is replaced by the document's facts.

### B13. LLMs, decoding, quantization
A decoder LLM predicts the next token repeatedly. **Temperature** controls randomness (we use 0.2: near-deterministic). **Quantization** stores weights in 4 bits instead of 16, shrinking a 2–4 B model to ~1.5–3.3 GB so it fits our 4 GB GPU, with a small quality loss. **GGUF** is the file format llama.cpp/Ollama use for quantized models. Small models sometimes have a "thinking" mode that writes hidden reasoning first — we disable it for speed.

### B14. Hallucination and faithfulness
A *hallucination* is output not supported by the source. *Faithfulness* = every claim is supported by the retrieved evidence. Small LLMs especially slip on numbers: they may write "lakh" where the document says "crore".

### B15. Deterministic verification — our second key idea
Instead of asking another model "is this right?", we parse every number in the answer and in the evidence into a canonical rupee value and compare them in code. If they differ by exactly 100× and the units are lakh vs crore, that's a scale mismatch → ❌. Code can't be talked out of the truth, and every verdict has a reason we can show.

### B16. NLI (natural language inference)
A model that decides if a *premise* entails, contradicts, or is neutral to a *hypothesis*. We can use it for non-numeric claims ("the registrar is X") where number-matching doesn't apply.

### B17. Speech recognition (ASR)
Whisper-family models turn audio into text; they were trained on huge amounts of weakly labelled audio. We run a quantized version on CPU for Hindi. We measure **CER** (character error rate) because Hindi word boundaries make WER harsher.

### B18. Evaluation metrics
- **EM:** predicted string exactly equals gold. **Token F1:** partial-overlap credit.
- **NVM (normalized value match):** our primary metric — `₹800 crore` and `₹8,000 million` count as the same.
- **Precision / recall / F1:** of the errors the verifier flagged, how many were real (precision); of the real errors, how many it caught (recall).
- **Recall@5:** was the right passage in the top 5?
- **Mean ± std over seeds; bootstrap CIs:** our test set is small, so we show uncertainty honestly.

### B19. Train/test leakage
If a company's passages appear in both training and test, scores look better than reality. We split by IPO and exclude every demo/gold IPO from training, with a test that checks it.

---

## Part C — How each FinSight module works

*(Claude Code appends one section per module when its PR merges: what it does, the key algorithm in plain words, one worked example, known limitations, and 2 likely viva questions.)*

### C0. Core and the API skeleton (built in P0.3)

**What it does.** `finsight.core` is the shared vocabulary: the data shapes every other package passes around (schemas), the interfaces they implement, a registry that picks an implementation by name from config, profile-based settings, IDs and JSON logging. `finsight.api` is the *contract* of the web server, written before any feature exists.

**Key ideas in plain words.**
- *Typed values with a `kind` label.* An extracted value is a `Money`, `Count`, `Percent`, `Placeholder` (`[●]`), `Range`, text, list or table. Each carries `kind`, so when JSON is read back the program knows exactly which one it is. A `[●]` is its own type, so it can never be mistaken for zero.
- *Money as strings.* Amounts travel as `"8000000000.00"`, never as floating-point numbers, so no rounding error can change a rupee figure.
- *Registry and profiles.* Code asks for "the LLM" by name and config decides which one (`dev_light` uses a tiny model while coding, `full` the demo model). Swapping a model is a config change, not a rewrite.
- *Contract first.* The API routes exist from day one and answer "not implemented" in a fixed error format. The frontend team (you, later) can generate TypeScript types from `openapi.json` before the real backend is ready. Streaming events are described by one model each, because OpenAPI cannot describe a stream by itself.

**Worked example.** `₹ 800.00 crore` becomes `Money(kind="money", value_inr="8000000000.00", scale_word="crore", precision=2)`. Written to JSON and read back it is identical; a `[●]` becomes `Placeholder(raw="[●]")`.

**Limits.** Every endpoint still answers 501. The schemas are a sketch that later sub-phases may refine (with a matching change to `06`).

**Likely viva questions.** (1) *Why store money as strings, not floats?* (2) *What does "contract first" buy you when one person builds both sides?*

### C1. Parsing PDFs into words, clean text and page images (built in P1.1)

**What it does.** `finsight.parse` turns each RHP and Prospectus PDF into a `ParsedDoc`: for every page, every word with its exact box (x0, y0, x1, y1 in PDF points), font size and bold flag, the page's clean text, its printed page number and a scanned-page flag. It also renders every page to a WebP image for the document viewer. `finsight.pipeline build` runs this for the demo set; `pipeline inspect` shows a capped summary (at most 40 lines), which is how Claude Code looks at a document without reading the PDF.

**Key ideas in plain words.**
- *Words from characters.* PyMuPDF gives every character with its box. We join characters into words and take the union of their boxes, so a highlight later lands exactly on "₹ 800.00 crore".
- *Headers and footers.* A line near the top or bottom of the page that repeats (digits ignored) on more than half the pages is boilerplate ("ACME LIMITED", "Page # of #"). It is removed from the page text, so it doesn't pollute search or extraction, but its words stay available for highlighting.
- *Two page numbers.* The PDF page (1, 2, 3, ...) is what the viewer and citations use; the number printed in the footer ("1" on PDF page 7, roman numerals in the front matter) is kept for the popover (ADR-025).
- *Scanned pages.* A page with images but almost no text is a picture of text. Without OCR we can't read it, so it is flagged and skipped.

**Worked example.** Meesho's RHP: 689 PDF pages, printed page 1 is PDF page 7, 683 pages have a printed number, 6 image-only pages (charts and photos), median 2,923 characters per page. Parsing takes about 10 s; images about 0.15 s and 115 KB per page.

**Limits.** Multi-column layouts are read in PyMuPDF's sorted order, which can interleave columns. Tables come out as lines of text here; P1.3 extracts them as cells. Rupee signs rendered as images or custom glyphs would be lost (not seen in the demo set so far).

**Likely viva questions.** (1) *Why render page images instead of using a PDF viewer?* (2) *How do you tell a header from a real sentence that happens to repeat?*

### C2. Finding the sections (built in P1.2)

**What it does.** `finsight.parse.sections` splits each RHP or Prospectus into its SEBI-standard sections ("The Offer", "Capital Structure", "Objects of the Offer", "Risk Factors", ...), each with a PDF page range, the method that found it and a confidence. Later stages use this to look only in the right pages: the offer size lives in "The Offer", the use of money in "Objects of the Offer". `pipeline build --stage sections` writes `sections.json` per document; `build-all --stage sections` also writes the found/not-found matrix to `eval_results/sections.json`.

**Key ideas in plain words.**
- *The table of contents is a map with the wrong page numbers.* The TOC says "CAPITAL STRUCTURE .... 96", but 96 is the *printed* number. P1.1 read the printed number in every footer, so we look up which PDF page carries "96"; if that footer is unreadable we use the typical gap between the two numbers (the median offset).
- *Three signals vote.* (1) the TOC entry, (2) the title appearing as a whole line in the first 8 lines of that page, (3) the title's words being bold or ≥ 1.2× the page's usual font size. All three agree → confidence 1.0; TOC + heading → 0.9; TOC alone → 0.7. If the heading is found a few pages away instead, the heading wins (0.5–0.6).
- *Canonical ids.* Different companies write "OBJECTS OF THE OFFER" or "OBJECTS OF THE ISSUE"; both become `objects_of_the_offer`, so later code has one name to ask for.
- *Ranges.* A section runs until the next one starts; the cover is everything before the TOC.

**Worked example.** Hexaware's RHP TOC lists "CAPITAL STRUCTURE .... 92"; the PDF page whose footer reads "92" is page 96, whose first line is the bold heading "CAPITAL STRUCTURE" → start page 96, method `toc`, confidence 1.0. On the 20 demo documents all 4 key sections were found in 10/10 RHPs and 10/10 Prospectuses; of 688 non-cover sections, 648 scored 1.0, 38 scored 0.9 and 2 scored 0.7.

**Limits.** A section that the TOC doesn't list and whose heading doesn't sit in the top lines of a page is missed. Very long sections (Hexaware's capital structure runs to page 251 because its TOC nests many sub-parts under it) are correct by the TOC but broad, so retrieval still has to rank passages inside them. Scanned TOC pages would disable the TOC signal.

**Likely viva questions.** (1) *Why not trust the TOC page numbers directly?* (2) *What happens when the TOC and the heading disagree?*
### C2b. Tables (built in P1.3)

**What it does.** `finsight.parse.tables` pulls the tables out of the three sections the X-Ray needs (The Offer, Capital Structure, Objects of the Offer), cell by cell, each cell with its text, row, column and exact box on the page. It also records the table's unit ("₹ in million"), because "4,720" means nothing without it. `pipeline build --stage tables` writes `tables.json` per document and updates `eval_results/tables.json`.

**Key ideas in plain words.**
- *Two ways to find a table.* PyMuPDF finds tables from the lines drawn around cells: fast and exact when every cell is boxed. But many RHPs box only the header row and print the body as plain text, so line-finding sees a two-row table with no numbers. Docling runs a small vision model that looks at the page layout and rebuilds the grid even without lines. We use Docling when it is installed and fall back to PyMuPDF (ADR-017).
- *Only where it matters.* Docling is slower (about 1.5 s a page on the laptop GPU), so it runs only on the three key sections, at most 40 pages each: about 7 % of all pages.
- *The unit header.* We look for phrases like "(in ₹ million)", "(₹ in crore)" or "(Rs. in lakhs)" in the table's first two rows or in the inch of text above it, and store one canonical form such as "₹ in million". A phrase with digits, like "(₹ 800 crore)", is an amount, not a unit, and is ignored.
- *Offer for Sale only.* When the whole IPO is existing shareholders selling (no fresh issue), the company gets no money and there is no "use of proceeds" table. The Objects section then says "will not receive any proceeds from the Offer", and we report `not_in_document` instead of "missing".

**Worked example.** Urban Company RHP, PDF page 163: PyMuPDF found only "Particulars | Estimated Amount | (in ₹ million)". Docling found the rows "Gross Proceeds of the Fresh Issue | 4,720", "Less: Offer expenses … | [●]", "Total Net Proceeds | [●]", with unit "₹ in million". Over the demo set: Objects rows were found in 8/8 fresh-issue RHPs and 8/8 Prospectuses; Hexaware and LG Electronics (pure OFS) were reported as `not_in_document`. 1,000 pages took 25 minutes.

**Limits.** A table that continues onto the next page is stored as two tables (joining them is left to extraction). Docling occasionally drops a few cells that fit no row or column (it logs a warning). Docling needs the optional `tables` group and preferably the GPU; without it the ruled-table fallback misses unruled bodies.

**Likely viva questions.** (1) *Why not run the table model on the whole 700-page document?* (2) *How do you know "4,720" is ₹ 4,720 million and not ₹ 4,720?*

**Update (1 Oct): the AI-prefilled gold.** Gold v1 was pre-filled by an AI and checked by a human instead of labelled blind. To make the validator accept real filings it now ignores capitals and footnote marks, treats `[•]` as `[●]`, lets a name wrap across table lines, and lets list items sit between contact details (words must still appear in order). Numbers still need an exact match. Every row is tagged `ai_assisted_verified`, so any score against gold v1 must say so (ADR-035).

### C3. Normalizing numbers, units and periods (built in P1.4)

**What it does.** `finsight.normalize` turns the ways an RHP or a Hindi answer can write a number into one exact value. `parse_amounts(text)` finds every amount in a sentence with its character span; `parse_amount(cell, header_scale)` reads one table cell; `equal(a, b)` says whether two amounts are the same number; `to_unit` / `format_money` give UI equivalents ("₹ 1,249.98 crore = ₹ 12,499.8 million"); `find_periods` reads FY24, FY2024-25, Q3FY25 and "six months ended September 30, 2024".

**Key ideas in plain words.**
- *One exact value.* "₹ 1,250.5 crore", "Rs. 12,505 mn" and "₹ १,२५०.५ करोड़" all become 12,505,000,000 rupees, stored as a `Decimal` (never a float), plus the scale word and how many decimals were printed.
- *Only amounts, not every digit.* A number counts only with a signal: ₹/Rs./INR/रुपये, a scale word (lakh, crore, million, करोड़ …), %, bps or "equity shares". So years, page numbers and "FY24" are skipped. A table cell may be a bare number because its column header ("₹ in million") supplies the unit.
- *Indian and Western grouping.* 1,23,45,678 and 12,345,678 both read as 12345678. Devanagari digits are converted; output always uses Western digits (ADR-028).
- *[●] is a blank, not zero.* It becomes a `Placeholder` that is never equal to anything.
- *Equality at the stated precision.* "₹ 1,250 crore" is only precise to ₹ 1 crore, so "₹ 12,499.8 million" (= ₹ 1,249.98 crore) counts as the same. "₹ 800 crore" vs "₹ 800 million" can never round together: that 10× gap is exactly the scale error the verifier must catch.
- *Fiscal years.* India's year runs April–March and is named by the year it ends: FY2024-25 = FY25 = Fiscal 2025; Q3 ends 31 December.

**Worked example.** "a Fresh Issue of ₹ 4,720 million and an Offer for Sale of ₹ 14,280 million" → two `Money` values, 4,720,000,000 and 14,280,000,000 rupees, spans pointing at "₹ 4,720 million" and "₹ 14,280 million". In the demo tables, every number-like Objects cell parses; the misses are "-" (nil), serial numbers and decimals in tables without a unit.

**Limits.** Words for numbers ("five crore") are not read. A bare cell under a unit header is taken as money even in a serial-number column, so extraction must pick value columns. Other currencies (€, £) are not recognised. Periods in Hindi are not parsed yet.

**Likely viva questions.** (1) *Why is "₹ 5 crore" equal to "₹ 4.6 crore" but "₹ 800 crore" not equal to "₹ 800 million"?* (2) *How do property-based tests differ from your table of examples, and what did they check?*



### C2c. The training corpus (built in P1.5)

**What it does.** `finsight.ingest.corpus` turns the public IPO dataset (2009-2023 RHPs and final Prospectuses, already extracted to text page by page) into a clean training corpus: one file per IPO with the page texts, the document kind and the sections found by the P1.2 detector. `finsight.ingest.exclusion` guarantees that no demo IPO and no gold-v2 IPO is in it. Weak labelling (P2) and the BiLSTM-CRF/QA training use this corpus, never the demo PDFs.

**Key ideas in plain words.**
- *Kind by cover, not by file name.* About 170 files named `_RHP` are really final Prospectuses. The first title phrase on the cover ("RED HERRING PROSPECTUS" vs "PROSPECTUS") decides, and draft (DRHP) or unreadable texts are dropped (ADR-016).
- *One text per IPO.* The Excel sheet links each IPO to exactly one text file, so an IPO can never be in both training and dev/test data through two documents.
- *Reuse the section detector.* The dataset gives no boxes or fonts, so we wrap each page's text in the same `ParsedDoc` shape and run `find_sections`. The heading and table-of-contents signals still work; the font signal does not, so confidence tops out at 0.9.
- *Fuzzy exclusion.* Company names are normalised (lowercase, no "Limited", "IPO", punctuation) and compared three ways: equal, equal without spaces (Urbancompany = Urban Company), or one distinctive word opening the other (Groww = Groww Innovations). "Tata Capital" and "Tata Motors" stay different. The demo companies come from `configs/demo_ipos.yaml`; the ten gold-v2 companies go in `data/gold/excluded_ipos.txt`.

**Worked example.** `Edserv Softsystems Limited IPO`, closed 2009 becomes `edserv-softsystems-2009`: cover says Prospectus, so `doc_kind = prospectus`; its TOC gives The Offer, Capital Structure and Objects of the Offer page ranges. Result on the full dataset: 389 IPOs (110 RHP-derived, 279 Prospectus-derived), 331 with all four key sections found; 5 DRHP, 15 unreadable and 9 too-short texts were skipped; nothing needed excluding because the dataset ends in 2023 and the demo IPOs are all from 2025.

**Limits.** The text is whatever the dataset's PDF extractor produced: no boxes, so no highlight source. Tables come as text rows. 16 % of texts miss a key section (mostly older scans with irregular TOCs), which the weak-label step simply skips. The corpus is 470 MB and lives in `data/processed/` (not committed).

**Likely viva questions.** (1) *Why must the demo IPOs be excluded from training?* (2) *Why classify the document kind from the cover text instead of the file name?*

### C2d. Gold values: schema, validator, template (built in P1.7)

**What it does.** The *gold* file is the answer key: for each demo IPO and each of the 11 X-Ray fields, the value a human read from the PDF, the PDF page and the exact quote. Every later score (rules baseline, pretrained QA, fine-tuned model, the X-Ray itself) is measured against it. `finsight.evaluate.gold` does not create answers; it checks that the file Akshat fills in is well formed, and writes an empty template to fill.

**Key ideas in plain words.**
- *Blind labelling.* Values are written from the PDF before any extractor exists, so the model cannot look better by having "seen" the labels' source.
- *One line per (IPO, field, document).* Most fields are read from the RHP; `offer_price` and `total_issue_size` from the final Prospectus, where the RHP shows `[●]` (ADR-023). A field the document does not contain is `not_in_document`; a blank the document leaves open is `placeholder`; both are valid answers a system must reproduce.
- *The validator catches typos, not judgement.* It checks the IPO and field exist, the page is inside the document (using the page count in `demo_ipos.yaml`), the value parses with the P1.4 normalizer as the right type (money, count, range), the value really appears in the quote, and lists and tables have the right shape. `[●]` under `status=present` is rejected.
- *Self-consistency.* Re-label 10 values a week later; `gold consistency a.jsonl b.jsonl` compares by value ("₹ 4,720 million" = "₹ 472 crore"), not by string, and lists the disagreements.

- *An Excel sheet instead of raw JSON.* `gold export-xlsx` writes `data/gold/gold_labelling.xlsx` (git-ignored): one row per value with a status dropdown and a HOW TO sheet. Lists are typed as `name | name`, objects rows as `purpose :: amount | purpose :: amount`. `gold import-xlsx` converts the filled sheet to `gold_values.jsonl`, runs the validator and reports mistakes as "Row 14 (...): what is wrong, how to fix it"; `--partial` checks only the rows filled so far, and nothing is written unless every checked row is valid.

**Worked example.** Row: `{"ipo_id": "urban-company-2025", "field_id": "fresh_issue_size", "doc": "rhp", "value_raw": "₹ 4,720 million", "page": 163, "quote": "...aggregating up to ₹ 4,720 million by our Company...", "status": "present", "labelled_at": "2026-10-08"}` passes; the same row with `"page": 900` fails with "page 900 is beyond the document (577 pages)". The empty template has 110 rows (11 fields × 10 IPOs) and fails validation until filled, by design.

**Limits.** The validator cannot tell that a value is the *right* occurrence, only that it is in the quote on a real page. Companion labels (the other document's value for the same field) are accepted but not required.

**Likely viva questions.** (1) *Why label the gold set before building any extractor?* (2) *Why is `not_in_document` a label rather than an empty cell?*

<!-- C4 extract.rules -->
<!-- C5 extract.qa -->
<!-- C6 weaklabel -->
<!-- C7 retrieve -->
<!-- C8 generate -->
<!-- C9 verify -->
<!-- C10 guard -->
<!-- C11 voice -->
<!-- C12 chat + api -->
<!-- C13 frontend -->

### C4. Rules extractor: Rung 1 of the ladder (built in P2.1)
**What it is:** a few regular expressions ("regexes": text patterns) that read the cover page of an RHP or Prospectus. SEBI forces nearly every company to use the same sentences, for example "Fresh Issue of [●] Equity Shares aggregating up to ₹ 4,720 million", so a pattern can pick out the number. It needs no training, runs in milliseconds, and always says which page the value came from.
**Why start here:** the project compares three rungs: rules, a pretrained question-answering model, and our fine-tuned model. Rules are the baseline. If rules already get a field right, a bigger model adds nothing for that field, and saying so honestly is part of the result.
**Details a beginner trips on:** `[●]` means "the company has not filled this in yet", so the code returns a Placeholder, never zero. Names in the BRLM and registrar tables wrap across lines and sit between phone numbers, so the rules look for a short list of known firms and write them out in full legal form. The Objects table is chosen by what its rows say (a "general corporate purposes" row, "Net Proceeds" in the header), not by size.
**How it was tuned:** on three dev IPOs only (Ather, Hexaware, Urban Company), where all 33 gold values match. The other seven IPOs are scored for the first time in P2.6, so the demo numbers are not inflated by tuning on them. `scripts/rules_dev_check.py` is the dev-only check. Caveat: gold v1 was AI-prefilled then human-checked (ADR-035).


### C5. Pretrained QA, choosing a value, and the X-Ray (built in P2.2)
**Pretrained QA (Rung 2):** a question-answering model reads a passage and points at the words that answer a question ("What is the size of the fresh issue?" -> "₹ 4,720 million"). We use a public model that was never trained on IPO documents, so it shows what you get for free. For each token it scores "the answer starts here" and "the answer ends here"; the best pair wins unless the "no answer" score is higher. A new library version removed the ready-made helper for this, so `qa_pretrained.py` does those few lines itself.
**Choosing a value:** rules and QA each give candidates. The field's main extractor decides; the other one can confirm it or, if it read a different number from the *same page*, cast doubt. Two readers quoting different pages are not in conflict. A `[●]` stays a `[●]` and is labelled "placeholder", never replaced by a number from elsewhere.
**Consistency check:** a fresh issue plus an offer for sale must equal the total. The code adds them and compares within the precision printed ("₹ 19,000 million" is not a mismatch with 18,999.6). If a number is still blank or missing the check says "unverifiable", not "wrong".
**The X-Ray:** one JSON per IPO with the chosen value, its page and extractor, a verdict with a plain reason, every candidate from both documents, and the derived shares. "Verified" means read from the page and not contradicted; it does not mean a second independent source agreed.
**Honest limits:** the QA model is weak on names and tables, so rules win those fields; scores against gold come in P2.6.


### C6. Weak labelling: making training data without a human (built in P2.3)
**The idea (see B8):** the cover page states the key numbers in a fixed sentence the rules read reliably. That value is the *seed*. We then look through the rest of the same document for other sentences that contain the same value, written differently ("Rs. 300 crore" is the same as "₹ 3,000 million"), next to a word naming the metric ("fresh issue"). Each such sentence becomes a training question with its answer marked; sentences without the value become "no answer" examples.
**Why be strict with seeds:** a wrong seed spreads its mistake into every sentence it matches. So a seed is kept only if the cover never gives two different values, the three issue amounts add up, and the dataset's own spreadsheet agrees when it has the number. About one total-issue seed in three disagreed with the spreadsheet and was thrown away.
**Old documents:** the corpus goes back to 2009, when covers said "public issue" and "Rs. 38.96 crores", and PDF text turned ₹ into a backtick. The rules and a small clean-up step handle these.
**No leakage:** training and dev sets are split by company, and no demo or gold company is ever included (checked twice). Otherwise the model could memorise the answers it is later tested on.
**How good are the labels?** Unknown until checked, so 50 examples, spread over the fields, go to Akshat to mark correct or wrong (P2.4). That gives a precision number with an error bar, which the report quotes.

### C7. Metrics, the fine-tuning notebook and the Kaggle hand-off (built in P2.4)
**Metrics (`evaluate/metrics.py`):** *Exact match* asks whether the predicted text equals the gold text after lower-casing and dropping punctuation and "a/an/the". *Token F1* gives partial credit for overlapping words. For FinSight the main score is *NVM* (normalized value match): ₹ 4,720 million equals ₹ 472 crore because both normalise to the same number, but ₹ 10 million never equals ₹ 10 crore; names ignore case; a list matches as a set; "no answer" matches only "no answer".
**Error bars:** with only 7 test IPOs a single accuracy number is shaky. We resample whole IPOs 1,000 times (bootstrap) to get a 95 % interval, because the thing that varies from case to case is the company, not the field. Rung comparisons use the same resamples for both rungs (paired bootstrap). The weak-label audit uses a Wilson interval, which behaves sensibly for small counts near 0 or 100 %.
**The notebook (`notebooks/01_finetune_extractor.ipynb`):** it takes the model that already answers SQuAD 2.0 questions and trains it a little more on our weak labels. Long pages are cut into overlapping 384-token windows; a window that does not hold the answer is taught to say "no answer". After each epoch it saves a checkpoint, so a dropped Kaggle session resumes. Three seeds give a mean and a spread, so one lucky run is not reported as the result.
**Packager (`weaklabel/package.py`):** copies the training files, adds 200-example slices and a Kaggle metadata file. Slices keep the answerable and unanswerable mix, so the smoke run exercises both paths.
**Run it (Akshat):** `uv run python -m finsight.weaklabel.package --username <kaggle-username>`, then `kaggle datasets create -p data/processed/kaggle/finsight-weaklabel` (private), open the notebook on Kaggle with GPU and the dataset attached; run with `SLICE = 200`, `SEEDS = [13]`, `EPOCHS = 1` until it prints `SMOKE OK`; then `SLICE = None` and all three seeds. Download `extractor/seed-*/final` to `models/extractor/` and the `metrics*.json` files to `eval_results/` (P2.5).

---

## Part D — Viva drill (answer aloud without notes)

1. **What problem does FinSight solve, for whom?** Retail IPO applicants can't read 500-page RHPs; chatbots mis-scale Indian numbers and don't cite pages.
2. **Why not just use ChatGPT/Claude?** No page-level traceability, lakh/crore slips, cost, can't run offline; our E9 results show where they fail and where they win.
3. **What's DRHP vs RHP, and why RHPs?** DRHPs have `[●]` placeholders for key numbers.
4. **Fresh issue vs OFS?** New shares, money to company vs existing holders selling, money to them.
5. **What is extractive QA? How does the model choose an answer?** Start/end token scores; best valid span; "no answer" option.
6. **Why DeBERTa-v3-base?** Strong QA encoder that fits a free T4 and our laptop; disentangled attention.
7. **Where did your training labels come from?** Distant supervision from cover-page rules + value propagation.
8. **How noisy are they? How do you know?** 50-sample audit → precision with CI.
9. **Why exclude the cover page from positives (ablation)?** Otherwise the model just learns to copy the rules.
10. **How do you prevent leakage?** Split by IPO; demo/gold excluded; overlap test.
11. **What does the ladder show?** What each rung adds per field; where fine-tuning helped and where rules are enough.
12. **Why three seeds?** Fine-tuning variance; report mean ± std.
13. **Explain BM25 in one sentence.** Word-match scoring that rewards rare terms and normalizes for passage length.
14. **Why hybrid retrieval?** BM25 for exact names/numbers, dense for paraphrase and cross-lingual.
15. **What is RRF?** Sum of 1/(60+rank) across rankers.
16. **Bi-encoder vs cross-encoder?** Separate embeddings (fast, used for search) vs reading pair together (accurate, used for reranking).
17. **When does FinSight abstain?** Top rerank score below a threshold tuned on dev questions.
18. **Why a small local LLM? What did you lose?** Offline, free, private; weaker fluency — compensated by retrieval + verifier.
19. **What is quantization?** Fewer bits per weight → smaller, faster, slight quality loss.
20. **How does the verifier decide ❌ vs ⚠️?** Same metric with different value/scale → ❌; number absent → ⚠️.
21. **Why is scale mismatch always ❌?** An exact 10ⁿ ratio with a unit swap is a unit error, not missing info.
22. **Why deterministic instead of an LLM judge?** Explainable, testable, and model judges are weak on bare numbers.
23. **How did you test the verifier?** Seeded errors by type + correct answers incl. allowed rounding → P/R/F1.
24. **How does Hindi work without translation?** bge-m3 cross-lingual retrieval; LLM answers in Hindi; numbers verified the same way.
25. **How is prompt injection handled?** Passages delimited as data, system rule to ignore embedded instructions, adversarial test.
26. **Why can't FinSight say "apply"?** SEBI registration rules; guard refuses and shows facts.
27. **What are your biggest limitations?** Small gold set, weak-label noise, scanned PDFs unsupported, small LLM fluency, 9 fields only.
28. **What would you do with one more month?** More fields, QLoRA generator, concall adapter, larger gold set, user study.
29. **How is the demo mode honest?** It replays recorded real outputs only; never edited.
30. **Walk me through one chat answer end to end.** Guard → BM25 + dense → RRF → rerank → prompt with [1]–[5] → stream → claims → numbers normalized → matched → marks → trace.
