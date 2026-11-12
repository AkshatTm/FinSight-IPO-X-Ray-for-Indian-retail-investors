# Reading the results

## Risk level

The risk level says how much risk **the document discloses** compared with past Indian IPOs. It is not
a rating, a prediction or advice, and the card always shows that disclaimer.

How it is worked out ([configs/risklevel.yaml](../reference/risklevel.md), B-ADR-11, C-ADR-25):

1. Each red flag at **Concern** adds 2 points, each **Watch** adds 1.
2. Each risk factor that is highly serious *and* unusual (found in fewer than 10 % of past IPOs) adds
   1 point, up to 4.
3. Checks that could not be decided are left out, so the total is a **share of the points possible**:
   2 per decided check plus the 4 risk points.
4. A share below **0.2857** is **Low**, from **0.4167** up is **High**, in between is **Medium**. These
   thresholds are the terciles of the same score over 165 past train and dev IPOs with full documents
   (fitted, `provisional: false`).
5. A **serious finding about the company itself** (going-concern doubt, regulator order against the
   company, qualified audit, wilful-defaulter listing …) sets the level to High whatever the points say.
   The same kind of event about a promoter, a director or a group company is shown under Serious
   findings but does not force High (C-ADR-26).

Example from the screenshot: Jio Platforms decided 7 of 13 checks, so 7 × 2 + 4 = 18 points were
possible; it scored 5 (5 / 18 = 0.278), which is Low. Before C-ADR-26 the SEBI order on its promoter
(page 472) forced High.

The old line "more disclosed risk than X % of past IPOs" is hidden: it tracked document length, so long
RHPs always looked riskier (C-ADR-28).

## Red-flag statuses

| Status | Meaning |
| --- | --- |
| **OK** | The rule ran and the number is inside the safe range. |
| **Watch** | Worth a look; adds 1 point. |
| **Concern** | Outside the range the rule sets; adds 2 points. |
| **Not available** | The document does not give the numbers the check needs. An RHP prints `[●]` for the price, so the checks that need the price (RF05 what insiders paid, RF06 founders' stake after the IPO, RF07 vague use of money, RF11 price versus peers) are often Not available until the final prospectus. Never shown as zero. |
| **Not applicable** | The check does not apply, for example debt to equity for a lender. |

The Overview groups them as **Decided** (OK, Watch or Concern), **Not available**, and **Pending** (not
calculated yet, while the analysis is still running). Each check's thresholds and "How this check
works" text are on [Red-flag checks](../reference/redflags.md).

## Page citations

Every number Vidura reads carries the page it came from (the "page 76" chips). Clicking one opens
the page in **Facts, pages and Ask** and highlights the words. The number checker compares numbers
with code, not with a model: lakh, crore and million are converted before comparing.

In chat, every number in an answer is marked:

- ✅ **verified**: the number is on the cited page.
- ⚠️ **unverifiable**: the checker could not find it to compare (the answer may still be right).
- ❌ **contradicted**: the cited page says something else.

The checker marks numbers, not reasoning; a sentence can still be wrong with every number ✅.

## Plain-English rewrites

Each rewrite is checked before it is shown: every number must be kept as written, the certainty must
not change ("may" stays "may"), it must be at most 60 words and it must not contain advice phrases
(`configs/forbidden_phrases.yaml`). If a check fails, the original text is shown instead. The original
is always one click away.

## Unusual and common risks

"Unusual: in 4 % of past IPOs" means risks similar to this one (cosine similarity at least 0.71 with
`bge-m3` embeddings, C-ADR-14) appeared in that share of past IPOs in the reference window. Recent kinds
of risk can look more unusual than they are because the window looks back four years.

## Incomplete reports

A report is **degraded** when a stage did not finish or ran without one of its models (for example
"analysed without the risk classifier"). The banner names what is missing, the affected parts say
"This part isn't ready yet", and the report is not cached as complete: start the missing model and
click **Re-analyse**.

## What Vidura does not do

- Recommend applying, buying, selling or avoiding, or predict listing gains.
- Read scanned PDFs.
- Check the company's claims about itself (its strengths are shown in its own words, marked unchecked).
