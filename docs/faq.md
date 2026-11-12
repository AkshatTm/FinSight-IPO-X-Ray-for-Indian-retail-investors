# FAQ

## About the product

**Does Vidura tell me whether to apply for an IPO?**
No. It summarises what the offer document discloses, with the page behind every number. It never
recommends applying, buying, selling or avoiding, and does not predict listing gains. Advice questions
in chat are declined and answered with the key facts instead.

**What is the risk level, then?**
A summary of how much risk the document discloses compared with past Indian IPOs: points from red
flags and rare serious risks as a share of the points possible, cut into Low / Medium / High at
thresholds fitted on 165 past IPOs. Details: [Reading the results](user-guide/reading-results.md#risk-level).

**Why did a big, well-known company get "Low" and a small one "High"?**
The level reflects what the document says, not the company's reputation. One serious finding about
the company itself (a going-concern doubt, a regulator order against it, a qualified audit) sets High
on its own. An order against a promoter or director is shown but does not (C-ADR-26).

**Why is the "riskier than X % of past IPOs" line gone?**
It tracked document length: long RHPs always looked riskier. It is hidden with a note (C-ADR-28).

**Why do some red flags say "Not available"?**
The document does not give the numbers the check needs. An RHP leaves the price blank (`[●]`), so the
checks that need it (what insiders paid, founders' stake after the IPO, vague use of money, price versus
peers) wait for the final prospectus. They are never shown as zero.

**Can it read scanned PDFs?**
No. Use the text PDF from SEBI or the exchange; OCR is not built.

**Is there Hindi or voice input?**
Not since v1.1. Both were removed to keep one well-tested English path ([history](history.md#final-session-v11)).
Old clients that still send a `language` field are accepted; the answer is in English.

**How accurate is it?**
On the 10 showcase IPOs, summary facts match the hand-checked gold 0.774 of the time (NVM, 195 rows)
and red-flag statuses 0.769 (130 statuses), both re-measured for v1.1. Every number with its source and
caveats is on [Results and experiments](evaluation.md).

## About running it

**Does anything leave my machine?**
No. The API, the models and the data stay on the laptop; no paid or hosted LLM is called. Models are
downloaded once from Hugging Face. See [PRIVACY](https://github.com/AkshatTm/Vidura-IPO-X-Ray/blob/main/PRIVACY.md).

**Do I need a GPU?**
No, but it helps: the chat reranker takes 0.82 s per question on the RTX 2050 and 42.8 s on the CPU
([reranker card](model_cards/reranker.md#evaluation)). The student runs in Ollama either way.

**Why does the home page mention signing in with Google?**
That line comes from the hosted design, which was never deployed. Locally there is no sign-in: every
upload belongs to one local user.

**How do I start over with a document?**
Click **Delete** on the report and upload it again, or **Re-analyse** to keep the PDF and run the
pipeline again. From the command line: `uv run python -m vidura.jobs forget <doc_id>`.

**The report says it was made with an older version.**
It is re-analysed automatically because its `pipeline_version` differs from 4.2
([cache key](architecture/pipeline.md#cache-key-and-pipeline-version)).

## About the project

**Is it open source? Can I use it commercially?**
The code is MIT. The trained models learned from the Ghosh et al. corpus (CC BY-NC-SA 4.0) and from
Gemma outputs, so they are non-commercial ([NOTICE](https://github.com/AkshatTm/Vidura-IPO-X-Ray/blob/main/NOTICE)).

**What happened to Phase 4, Platform Bench and the cloud deployment?**
They were cut: no Phase 4 model was trained, the Platform Bench data was not ready, and hosting was
not done. The product kept the Phase 3 models ([history](history.md#phase-4-closed)).

**Where are the planning documents?**
On GitHub, unchanged, with a "historical record" banner; [Project history](history.md) links to each.
