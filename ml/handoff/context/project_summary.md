# FinSight in one page (for ARGON)

**What it is.** IPO X-Ray for Indian retail investors. Upload an offer document (RHP/Prospectus) and get cited facts, red flags,
a plain-English risk report, a Low/Medium/High risk level with reasons, a comparison with past IPOs, and a chat that checks every
number it says (OK / not found / different). Everything is cited to a page. Open-weight models only. It never gives advice
(no buy / sell / apply / avoid, no predictions).

**Pipeline (all local, laptop).** PDF -> parse (PyMuPDF words + boxes, sections, tables) -> `summary` (restated financials,
litigation, promoter holding, WACA, objects, auditor, peers) + `extract` (key facts) -> `risks` (segment the Risk Factors,
classify category + seriousness band, novelty vs past IPOs, plain-English rewrite) -> `redflags` (13 rule checks + five
"severe" sentence rules) -> `risklevel` -> `reports` (overview, "Five things to know" = top 5 risks by importance) ->
`chat` (hybrid retrieval, rerank, student answers with `[n]` citations, number verifier, advice guard).

**Where each of your models plugs in.**
| Model | Replaces / feeds | Interface (frozen) |
|---|---|---|
| M1 student v2 | `finsight-student:q4` (Ollama): chat answers (primary) and risk rewrites | GGUF q4_K_M + Modelfile, tag `finsight-student:v2-q4`, the two frozen prompt templates |
| M2 salience ranker | the "Five things"/Top 7 selection (`reports`) | `rank_risks` |
| M3 event classifier | the negation/hedge regex in `redflags/severe.py` before a "serious finding" can force High | `classify_events` |
| M4 severity v2 | the seriousness band head of the risk classifier | `predict_severity` (band 1-4 + label + probs) |

**Rules that bind you.** Splits are by IPO (`data/splits_by_ipo.json`); `data/excluded_ipos.json` never enters training (all test-slice
IPOs, demo, Bench v1, Platform Bench). Every label row carries `ipo_id` and `label_source` (`human`, `human_verified_ai`, `ai`, `rule`,
`model`). Numbers in `metrics.json` come only from committed scripts. CPU limits matter: the runtime is a 16 GB laptop and a CPU/GPU VM later.

**Key terms.** RHP = Red Herring Prospectus. SOD = Summary of the Offer Document (a section near the front). WACA = weighted average
cost of acquisition. Bench v1 = the frozen FinSight Bench (7 test-slice showcase IPOs; Tasks A facts, B red flags, C chat questions,
D rewrites, G advice probes). Platform Bench (Phase 4) = Groww / Zerodha / AngelOne pages vs RHP gold, 30 IPOs.
