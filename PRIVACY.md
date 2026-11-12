# Privacy

FinSight explains public IPO offer documents, and it runs entirely on your own computer. This page says what it keeps, where, and how to delete it.

## What FinSight stores, and where

Everything is in the `data/` folder of your copy of the repository. Nothing is sent to a server, and no paid or hosted AI service is called.

| What | Where | How long |
| --- | --- | --- |
| Documents you upload, and every result made from them | `data/store/docs/<doc_id>/` (the PDF and one JSON file per stage) | until you delete them; `start.bat` sets retention to 3,650 days |
| Page images and the chat search index | `data/processed/<doc_id>/` | until the document is deleted |
| One row per document and per job, upload counts | `data/finsight.db` (SQLite) | until deleted |
| Chat traces: the question, the passages used, the answer and timings | `data/traces.sqlite` | until you delete the file |
| Logs | the *FinSight API* window (not written to disk unless you redirect them) | until the window closes |

There are no accounts on the laptop: every upload belongs to one local user. The code still contains an optional Supabase sign-in, which is off; with it off no email or account id is stored.

## What FinSight never does

- Send your documents, questions or results anywhere. Models run locally (Ollama, ONNX Runtime, PyTorch); they are downloaded once from Hugging Face.
- Use uploaded documents to train models.
- Set tracking or advertising cookies.

## Personal details inside documents

Offer documents print the names of promoters and directors and business contact details. FinSight shows them as printed. The chat refuses questions asking for a private person's home address, personal phone or email, or identity numbers.

## How to delete

- One document: **Delete** on its report, `DELETE /api/docs/{doc_id}`, or `uv run python -m finsight.jobs forget <doc_id>`. This removes the PDF, the results, the page images, the search index and its rows.
- Everything: stop the app (`stop.bat`) and delete `data/finsight.db`, `data/traces.sqlite`, `data/store/` and the `data/processed/doc_*` folders.

## Changes

Changes to this page are recorded in the [changelog](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/CHANGELOG.md).
