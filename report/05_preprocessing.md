# 5 Preprocessing

> **DRAFT — Akshat to rewrite in his voice.** Sources: ADR-025, ADR-027, ADR-028, ADR-034,
> ADR-017, `eval_results/parse_timing.json`, `sections.json`, `tables.json`.

## 5.1 PDF parsing and page addressing

PyMuPDF reads each page's words with their boxes; a page is flagged scanned when it has almost no
text (Groww has 2, HDB 1; Ather none). Parsing a 586-page document takes about 10
seconds; rendering the page images takes about 90 seconds per document (`parse_timing.json`). Page
numbers are PDF pages (1-based), with the printed page number kept as a secondary field (ADR-025):
581 of 586 Ather pages carry a printed number. Every fact the product shows carries a document, a PDF
page and, where found, a box on that page.

## 5.2 Sections and tables

Section boundaries come from the table of contents where there is one and from heading patterns
otherwise (method and confidence stored). The four key sections (cover, the offer, capital
structure, objects of the offer) are found in 10 of 10 RHPs and 10 of 10 Prospectuses. Tables are read
with Docling (PyMuPDF as fallback, ADR-017); the objects-of-the-offer table with its fresh-issue rows
is read for 8 of 8 IPOs that have a fresh issue. Two IPOs (Hexaware, LG) are pure offers for sale and
the document has no such table (`tables.json`).

## 5.3 Indian numeral normalisation

Amounts in these documents are written as `₹ 4,720.00 million`, `Rs. 1,50,000 lakh`, `₹ 26.26 crore`,
`10,00,00,000` (lakh-crore grouping), `₹ [●]` placeholders, and in Hindi as `₹ 800 करोड़`, `रु. 50 लाख`,
`800 करोड़ रुपये`, sometimes with Devanagari digits (`₹ ८०० करोड़`). The normaliser turns each into a typed value:
amount in rupees, the scale word that was printed, the number of printed decimals, the currency, the
unit (shares, per cent, basis points), the period and the source span. The conventions that change
what the verifier accepts are fixed in ADR-034:

1. An amount needs a signal (currency, scale word, per cent, bps or a share unit); a bare number is
   read only when a whole table cell is the number, with the table's unit header.
2. A scale word without a currency is rupees ("4,720 million").
3. Two values are equal when they agree at the coarser printed granularity (printed decimals ×
   scale): "₹ 5 crore" equals "₹ 4.6 crore", but a ten-fold gap never rounds away.
4. A `-` cell is not zero; serial numbers ("1.") are not amounts; `[●]` is a placeholder, never a number.
5. `scale_mismatch` is raised only when the ratio is 10^k (k = 1 to 3) and the scale words differ or
   the printed digits are identical (ADR-027), so a face value of ₹10 against ₹1 is a wrong value,
   not a scale slip.
6. Hindi: scale words, रुपये and Devanagari digits are parsed; generated answers use Western digits
   (ADR-028).

The module has hypothesis property tests (`tests/normalize/test_properties.py`) and a table of Hindi and
English cases (`test_cases_table.py`); it is the only code the verifier trusts to read a number.

## 5.4 Privacy at indexing

Personal data in the filings (residential addresses, phone numbers, e-mail addresses of individuals) is
redacted when passages are indexed, and an output filter backs it up (ADR-048); business contact
details stay.
