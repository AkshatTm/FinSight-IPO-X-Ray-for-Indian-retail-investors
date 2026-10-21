# Gold v3.1 changelog (test-informed convention fixes, C-ADR-20)

11 rows changed out of 280. Gold v3 is untouched.

## ather-energy-2025 / waca_selling_shareholders / final
- change: complete list of selling shareholders (was the two promoter sellers only)
- old: `found` 'Promoter selling shareholders: Tarun Sanjay Mehta 21.09; Swapnil Babanlal Jain 21.09' (page 1)
- new: `found` 'Promoter selling shareholders: Tarun Sanjay Mehta 21.09; Swapnil Babanlal Jain 21.09. Other selling shareholders: Caladium Investment Pte Ltd 204.24; National Investment and Infrastructure Fund II 183.71; Internet Fund III Pte. Ltd. 38.58; IITM Incubation Cell Nil; IITMS Rural Technology and Business Incubator 8.31; Amit Bhatia 184.82' (page 44)
- label_source: `claude_chat_prefill+akshat_verified+claude_code_fix`, needs_akshat_verify: true

## ather-energy-2025 / auditor_remarks / latest
- change: notes only: Emphasis of Matter recorded, value kept
- old: `found` 'No qualifications' (page 31)
- new: `found` 'No qualifications' (page 31)
- label_source: `claude_chat_prefill+akshat_verified`, needs_akshat_verify: true

## groww-2025 / waca_selling_shareholders / final
- change: complete list of selling shareholders (was the top 10)
- old: `found` 'Top-10 selling shareholders (all investors, no promoter sells): Peak XV 1.91; YC Holdings II 3.45; Ribbit Capital V 2.30; GW-E Ribbit Opportunity V 37.87; Internet Fund VI 21.97; Kauffman Fellows 0.51; Alkeon Innovation Master Fund II 37.83; Alkeon (Private Series) 37.83; Propel Venture Partners 5.39; Sequoia Global Growth III 37.94' (page 1)
- new: `found` 'All 15 selling shareholders (all investors, no promoter sells): Peak XV Partners Investments VI-1 1.91; YC Holdings II 3.45; Ribbit Capital V 2.30; GW-E Ribbit Opportunity V 37.87; Internet Fund VI 21.97; Propel Venture Partners 5.39; Sequoia Capital Global Growth 37.94; Kauffman Fellows Fund 0.51; Friale Fund IV 0.29; Alkeon Innovation Master Fund II 37.83; Alkeon Innovation Master Fund II Private Series 37.83; Alkeon Innovation Master Fund 37.83; Alkeon Innovation Opportunity 37.83; Nirman Investments 0.79; Nirman Holdings 0.79' (page 40)
- label_source: `claude_chat_prefill+akshat_verified+claude_code_fix`, needs_akshat_verify: true

## hdb-financial-services-2025 / promoter_holding_post_pct / final
- change: was not_found; value, page and quote from the Prospectus
- old: `not_found` '' (page None)
- new: `found` '73.98' (page 21)
- label_source: `claude_code_fix`, needs_akshat_verify: true

## hexaware-technologies-2025 / issuer_pe / final
- change: flagged computed=true, value kept
- old: `found` '43.04 (computed: ₹708 / basic EPS ₹16.45)' (page 257)
- new: `found` '43.04 (computed: ₹708 / basic EPS ₹16.45)' (page 257)
- label_source: `claude_chat_prefill+akshat_verified`, needs_akshat_verify: true

## lg-electronics-india-2025 / auditor_remarks / latest
- change: notes only: Emphasis of Matter recorded, value kept
- old: `found` 'No qualifications' (page 24)
- new: `found` 'No qualifications' (page 24)
- label_source: `claude_chat_prefill+akshat_verified`, needs_akshat_verify: true

## physicswallah-2025 / promoter_holding_post_pct / final
- change: was not_found; value, page and quote from the Prospectus
- old: `not_found` '' (page None)
- new: `found` '71.48' (page 149)
- label_source: `claude_code_fix`, needs_akshat_verify: true

## physicswallah-2025 / auditor_remarks / latest
- change: value is qualifications only; Emphasis of Matter moved to notes
- old: `found` 'Qualifications in the audit reports and CARO 2020 annexures for Fiscals 2025, 2024 and 2023 (no restatement effect needed); disclaimer on internal financial controls for Fiscal 2023; emphasis of matter on the FY2023 special-purpose statements' (page 35)
- new: `found` 'Qualifications in the audit reports and CARO 2020 annexures for Fiscals 2025, 2024 and 2023 (no restatement effect needed); disclaimer on internal financial controls for Fiscal 2023' (page 35)
- label_source: `claude_chat_prefill+akshat_verified+claude_code_fix`, needs_akshat_verify: true

## tata-capital-2025 / auditor_remarks / latest
- change: notes only: Emphasis of Matter recorded, value kept
- old: `found` 'No qualifications' (page 27)
- new: `found` 'No qualifications' (page 27)
- label_source: `claude_chat_prefill+akshat_verified`, needs_akshat_verify: true

## urban-company-2025 / promoter_holding_post_pct / final
- change: was not_found; value, page and quote from the Prospectus
- old: `not_found` '' (page None)
- new: `found` '19.35 (computed: 3 promoters x 6.45)' (page 27)
- label_source: `claude_code_fix`, needs_akshat_verify: true

## urban-company-2025 / auditor_remarks / latest
- change: notes only: Emphasis of Matter recorded, value kept
- old: `found` 'No qualifications' (page 30)
- new: `found` 'No qualifications' (page 30)
- label_source: `claude_chat_prefill+akshat_verified`, needs_akshat_verify: true

## Left unchanged on purpose

- promoter_holding_post_pct: other not_found rows may also be printed in the Prospectus (Groww p30: Lalit Keshre 8.97 per row; Lenskart p34: Total (A) 17.51); Ather, Hexaware, Meesho and Tata Capital were not checked. Only the three rows Akshat named were filled. Filling the rest would turn Ather / Groww into pipeline misses (it reads not_found there); Lenskart (it reads 85.61) and Tata Capital (6.6) are wrong reads whatever the gold says.
- waca_selling_shareholders: Lenskart and Meesho list only some investors ('others on the cover'); the pipeline reads no WACA table there, so the score cannot change, but the rows are incomplete and need the cover read.
- auditor_remarks Lenskart: gold is not_found although the RHP summary (p36) prints a statement; unchanged.
