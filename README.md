# SCRYBE API

SCRYBE API is a Python-first ingestion service that converts web URLs into clean Markdown and structured JSON for LLM workflows. It uses deterministic parsing first, optionally enriches content with OpenAI, and can fall back to a Node-based LiteParse CLI adapter for OCR-heavy documents.

## Features

- FastAPI service with sync parse endpoints and async jobs
- Static fetch via `httpx` with Playwright escalation for dynamic pages
- HTML, PDF, JSON, XML, RSS, image, and office-document parsing hooks
- SQLite job persistence and disk-backed cache/artifacts
- Optional OpenAI captions and summaries
- OCR/document fallback through a Python-owned LiteParse subprocess adapter

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
uvicorn scrybe_api.main:app --reload
```

## Environment

Configure `.env` with any values you need:

```env
OPENAI_BASE_URL=
OPENAI_API_KEY=
SCRYBE_DATA_DIR=.scrybe_data
SCRYBE_SQLITE_PATH=.scrybe_data/scrybe.db
SCRYBE_LITEPARSE_CMD=lit
SCRYBE_ENABLE_AUTH=false
```

## API

- `GET /v1/health`
- `GET /v1/capabilities`
- `GET /v1/parse/{format}?url=https://example.com`
- `POST /v1/parse/{format}`
- `POST /v1/jobs`
- `GET /v1/jobs/{job_id}`

## Notes

- `format` is `markdown` or `json`
- heavy or browser/OCR-oriented requests are automatically redirected to async jobs
- Node remains an internal implementation detail behind the OCR adapter

