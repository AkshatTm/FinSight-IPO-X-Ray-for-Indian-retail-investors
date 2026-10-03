# Privacy

FinSight explains public IPO offer documents. It is built to keep as little about you as possible. This page says, in plain English, what it keeps, for how long, and how to have it removed.

## What FinSight stores

| What | Why | How long |
| --- | --- | --- |
| Your account id and email, from Google sign-in through Supabase | To link your uploads to you and enforce the daily limit | Until you ask for deletion |
| Documents you upload, and the reports made from them | To show you the report | 30 days after upload, then deleted automatically (files and records) |
| A record that you uploaded a document today (account id, document id, time) | To keep the daily upload limit fair | Kept after the document is deleted, so the limit cannot be reset by deletion |
| Chat traces: the question, the passages used and the answer, with timings | To find and fix wrong answers | No account id is stored with them |
| Server logs (request, document and job ids, errors) | To keep the service running | Google Cloud's default log retention |

Showcase IPOs (the public examples in the library) are kept permanently; they are public filings.

## What FinSight never stores or does

- No passwords: sign-in is Google's, through Supabase.
- No payment details, phone numbers or addresses of users.
- No tracking or advertising cookies; no data is sold or shared for marketing.
- Uploaded documents are never used to train models.
- Offer documents are public filings, so a report is not treated as secret: anyone with its link (the document id) can open it, and a file someone already uploaded is recognised by its hash and opens the same report. Who uploaded it is never shown.

## Personal details inside documents

Offer documents print names of promoters and directors and business contact details. FinSight shows business contacts (registered office, registrar, lead managers, the compliance officer). The chat refuses questions asking for a private person's home address, personal phone or email, or identity numbers, before it looks anything up.

## Asking for deletion

Open an issue on the GitHub repository titled "Deletion request", **without** your email or any personal detail in it; Akshat will reply with a private way to confirm the account and will delete your account record, uploads and reports within 30 days. Uploads are deleted after 30 days in any case.

## Changes

Changes to this page are recorded in the [changelog](CHANGELOG.md).
