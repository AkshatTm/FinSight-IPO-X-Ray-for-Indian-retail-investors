# FinSight — Phase 4 Plan ("Beat the brokers")
### Wed 21 Oct → Sun 25 Oct 2026 · Two agents: Claude Code (CC) + Gemini 4 Argon in Antigravity (ARGON) · Owner: Akshat

> Phase 4 sits on top of V1.0 (phases 1–3, tagged `v1.0`). Phase 3 docs (`docs/phase3/C05_ROADMAP.md`,
> `docs/phase3/C_EXECUTION_PLAN.md`) stay valid for history and ADRs. Where they conflict with this file,
> **this file wins for Phase 4 work**. CC reconciles the two in its execution plan (Kickstart step 3).

---

## 1. Goal

Make FinSight's IPO analysis **better than Groww, Zerodha and AngelOne** on the same IPOs, while keeping what
they don't have: every figure cited to a page, numbers checked by code, Hindi, upload-any-RHP.

Measured by **Platform Bench**: 30 recent IPOs (ids in the repo's hyphen slug format, e.g. `jio-platforms-2026`), each platform's page hand-collected by Akshat, scored against
RHP gold.

### Why (the Jio audit, 18 Oct)
| Gap | Evidence |
|---|---|
| Red flags mostly empty | Jio: 12 of 13 "Not available" on a 591-page RHP |
| False serious findings | "Loan default" (p.40) and "Regulator order" (p.472) forced Risk = High; likely hypothetical/negated wording |
| Risk level length-biased | Big RHP → more risk factors → "riskier than 95%" |
| No financials, strengths, promoter holding | All three brokers show these |
| Risks tab is a wall | 100+ cards; brokers show 5–7 curated |
| Compare bugs | "The Company" label, `₹-3.30`, RoNW blank, "not enough data" vs past IPOs |
| Chat hallucination | Student: 0.333 hallucinated numbers on unanswerable (rules: 0.048) |
| Cache/no delete | A run made with models down stayed cached; no delete / re-analyse |

## 2. Ownership (hard rule)

| Agent | Owns | Never touches |
|---|---|---|
| **CC** (Claude Code) | Everything in the product: parsing/extraction (Summary-of-Offer engine, financials, strengths), red flags v2 rules, risk level v2, cache/jobs, API, frontend, Compare, Platform Bench ingest + deterministic scoring, **integration of every Argon model**, git integration, hosting prep (next week) | `ml/` internals (reads only `ml/deliveries/`) |
| **ARGON** (Gemini 4 Argon, Antigravity) | Models only: M1 student v2, M2 salience ranker, M3 event classifier, M4 severity v2, M5 model evaluation. Plus **labelling from PDFs** (gold v4, SOD fixtures, event labels, top-risk labels) and the blind judge for Platform Bench Product code (`src/finsight/` or wherever the package lives), `frontend/`, `configs/`, `deploy/`, existing tests, `main` branch, git history rewrites |
| **AKSHAT** | Runs Colab notebooks, verifies labels, collects Platform Bench, picks the 30 IPOs, approves contract changes, final review | — |

Why this split: CC has the full project history (493 commits, ADRs, phase 1–3 decisions). Anything that needs
that history stays with CC. Model training is self-contained behind a frozen handoff pack and a delivery contract,
so ARGON can't break the product.

### Exclusions (C-ADR-02 stays in force)
`excluded_ipos.json` = **all 110 test-slice IPOs** (`configs/splits.yaml`) + the SME-excluded IPOs + demo/showcase IPOs + Bench v1 IPOs + every Platform Bench IPO (including Jio). Nothing in it enters any training set, threshold, prompt or parser tuning. The one disclosed exception: Jio is an SOD fixture (parser diagnosis only; flagged test-informed in the report).

## 3. Workstreams

### CC (product) — details in `P4_PRODUCT_SPECS.md`
| ID | Work | Day |
|---|---|---|
| CC-01 | V1.0 freeze: fix 3 red tests, clean gold files, tag `v1.0`, create Phase 4 branches, install these files | Wed |
| CC-02 | **Handoff pack** for ARGON (`ml/handoff/`) — unblocks ARGON | Wed |
| CC-03 | Platform Bench template ingest + bench IPO exclusion list (no training on bench IPOs) | Wed/Thu |
| CC-04 | Cache v2: preflight model check, versioned cache key, degraded status, delete + re-analyse | Thu |
| CC-05 | **Summary-of-Offer (SOD) engine** built against ARGON's SOD fixtures | Thu–Fri |
| CC-06 | Financials table + Our Strengths + promoter holding pre/post | Fri |
| CC-07 | Red flags v2 (rules, rewired on SOD/financials, negation rule baseline, new insight checks) + Risk level v2 (severity-weighted, length-normalized, recalibrated) | Sat |
| CC-08 | Frontend: Risks tab rebuild, Financials tab, Strengths card, red-flag UI v2, Compare fixes, cache UI | Sat |
| CC-09 | Integrate ARGON deliveries (M1–M4) behind existing interfaces, with fallbacks | Sat–Sun |
| CC-10 | Re-run 30 bench IPOs end to end + Platform Bench deterministic scorecard | Sun |

### ARGON (models + labels) — details in `P4_MODEL_SPECS.md`
| ID | Work | Day |
|---|---|---|
| AR-01 | Read docs, write own execution plan | Wed |
| AR-02 | **SOD fixtures**: SOD page text + gold values for 10 RHPs → unblocks CC-05 | Wed–Thu |
| AR-03 | Event labels (~800 sentences) + M3 event classifier notebook | Thu–Fri |
| AR-04 | M1 teacher data-generation notebook (G4) + student v2 notebook | Thu–Fri |
| AR-05 | Gold v4 for the 30 bench IPOs (facts, financials, strengths, top risks) | Fri–Sat |
| AR-06 | M2 salience ranker + M4 severity v2 notebooks | Sat |
| AR-07 | M5: evaluate every delivered model vs baseline; Platform Bench blind judge for risk quality | Sun |

## 4. Gates

| Gate | When | Must be true | If it fails |
|---|---|---|---|
| **P4-G0** | Wed night | `v1.0` tagged; tests green; handoff pack pushed; ARGON plan written | Nothing else starts until green |
| **P4-G1** | Fri night | SOD engine passes ARGON fixtures on ≥8/10 RHPs; M1 teacher data generated | Financials/strengths slip to Sat; SOD scope cut to financials + litigation + promoter holding |
| **P4-G2** | Sat night | Jio red flags ≥10/13 with 0 false serious findings; new tabs render on Jio | Ship rules-only red flags; M3 integration moves to Sun |
| **P4-G3** | Sun night | Platform Bench scorecard exists; each model is either adopted (beats baseline) or rejected (old stays) | Report what we have; carry to hosting week |

## 5. Sunday targets

| Metric | Now | Target |
|---|---|---|
| Jio red flags found | 1/13 | ≥10/13 |
| False serious findings on 30 bench IPOs | unknown (Jio: likely 2) | 0 confirmed false |
| Student hallucinated numbers on unanswerable chat questions (Bench v1 Task C) | 0.333 | ≤0.10 |
| Student faithful (gold-50) | 0.92 | ≥0.92 (no regression) |
| Severe-band recall (seriousness band 4, dev, 3-seed mean, see `baselines.json`) | 0.56 | ≥0.70; category macro-F1 (0.892) must not regress by more than 0.01 (guardrail, not the target) |
| Top-7 risk overlap with broker risk lists | n/a | ≥ best single broker's overlap with the other two |
| Fact coverage vs AngelOne (field count) | ~40% | ≥100% of RHP-derivable fields |
| Fact accuracy on gold v4 | n/a | ≥ every broker |

## 6. Compute budget (Colab, 140 units; G4 = 8.71 units/hr ≈ 16 G4 hours total)

| Job | Units | Hardware |
|---|---|---|
| Debug runs (tiny slices) | ~8 | T4 |
| M1 teacher data generation (Gemma-4-31B) | ~35 (≈4 h) | G4 |
| M1 student v2 LoRA (4B) | ~35 (≈4 h) | G4 |
| M2 ranker, M3 event classifier, M4 severity (3 seeds each) | ~25 | G4 short runs or T4 |
| Reserve (second iteration of whichever misses target) | ~35 | — |

Rule: every notebook runs end to end on a tiny slice on T4 before any G4 run. Checkpoint to Drive every epoch.

## 7. Out of scope this week
Supabase auth/users, deployment to GCP (both are hosting week, 26 Oct–1 Nov). Risk level keeps Low/Medium/High.
No paid LLM APIs at runtime. No training on Platform Bench IPOs. No scraping of broker sites.
