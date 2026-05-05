# SCRYBE
### Universal Content Ingestion & Markdown Extraction Engine

> Read anything. Return clean, structured Markdown. Always.

---

## Overview

SCRYBE is a Python-native, format-agnostic content extraction engine. It accepts virtually any input — a URL, a file path, or raw bytes — and returns a clean, structured, semantically-rich Markdown document. Under the hood, SCRYBE handles browser automation for dynamic pages, OCR for scanned documents, VLM-powered image captioning, table normalization, metadata harvesting, and much more — all transparently, behind a single unified interface.

---

## Core Design Philosophy

- **One interface, every format.** Callers shouldn't care whether they're reading a tweet or a 300-page PDF.
- **Clean output, not raw dumps.** SCRYBE strips noise (ads, nav, footers, scripts, iframes, forms) and preserves signal (text, images, tables, code blocks, metadata).
- **Python-first, zero compromise.** No Node.js, no Java, no external runtimes beyond what pip can handle.
- **Respect images.** Images are not discarded. They are retained by URL/path and enriched with a VLM-generated description inline.
- **Structured is better than flat.** Headings, tables, lists, and code blocks are normalized into proper Markdown syntax — not collapsed into undifferentiated prose.
- **Fail gracefully.** If a parser fails, SCRYBE falls back to a lower-fidelity extractor rather than throwing.

---

## Architecture

```
Input (URL / File Path / Raw Bytes)
            │
            ▼
    ┌───────────────┐
    │  InputRouter  │  ← Detects type (URL, file ext, MIME, magic bytes)
    └───────┬───────┘
            │
    ┌───────▼────────────────────────────┐
    │           Fetcher Layer            │
    │  • StaticFetcher  (httpx)          │
    │  • DynamicFetcher (Playwright)     │
    │  • LocalFetcher   (disk I/O)       │
    └───────┬────────────────────────────┘
            │
    ┌───────▼────────────────────────────┐
    │           Parser Layer             │
    │  • HTMLParser     (BS4 + lxml)     │
    │  • PDFParser      (PyMuPDF)        │
    │  • DocxParser     (python-docx)    │
    │  • PptxParser     (python-pptx)    │
    │  • XlsxParser     (openpyxl)       │
    │  • EpubParser     (ebooklib)       │
    │  • ImageParser    (Pillow + VLM)   │
    │  • AudioParser    (faster-whisper) │
    │  • MarkdownParser (passthrough)    │
    │  • RSSParser      (feedparser)     │
    │  • YouTubeParser  (yt-dlp + api)   │
    └───────┬────────────────────────────┘
            │
    ┌───────▼────────────────────────────┐
    │        Post-Processing Layer       │
    │  • NoiseScrubber  (remove clutter) │
    │  • ImageEnricher  (VLM captions)   │
    │  • TableNormalizer                 │
    │  • CodeBlockDetector               │
    │  • MetadataExtractor               │
    │  • ChunkEngine    (optional)       │
    └───────┬────────────────────────────┘
            │
            ▼
    Structured ScrybedDocument (Markdown + metadata dict)
```

---

## Supported Input Types

### Web & Network

| Type | Description | Fetcher | Parser |
|---|---|---|---|
| Static webpage | Standard HTML pages | `StaticFetcher` (httpx) | `HTMLParser` |
| Dynamic webpage | JS-rendered SPAs, React, Next.js, etc. | `DynamicFetcher` (Playwright) | `HTMLParser` |
| RSS / Atom feed | Blog feeds, news aggregators | `StaticFetcher` | `RSSParser` |
| YouTube video | Extracts transcript + metadata | `YouTubeFetcher` | `YouTubeParser` |
| Raw HTML (URL) | Direct `.html` served over HTTP | `StaticFetcher` | `HTMLParser` |
| GitHub file / gist | Code files via GitHub raw URLs | `StaticFetcher` | `HTMLParser` / `MarkdownParser` |

### Documents

| Type | Extension(s) | Parser |
|---|---|---|
| PDF (text-native) | `.pdf` | `PDFParser` (PyMuPDF) |
| PDF (scanned / image-based) | `.pdf` | `PDFParser` + Tesseract OCR |
| Word document | `.docx`, `.doc` | `DocxParser` (python-docx) |
| PowerPoint | `.pptx`, `.ppt` | `PptxParser` (python-pptx) |
| Excel / Spreadsheet | `.xlsx`, `.xls`, `.csv`, `.tsv` | `XlsxParser` (openpyxl / pandas) |
| Markdown | `.md`, `.mdx` | `MarkdownParser` (passthrough + lint) |
| Plain text | `.txt`, `.log`, `.env` | `TextParser` |
| HTML file (local) | `.html`, `.htm` | `HTMLParser` |
| EPUB / ebook | `.epub` | `EpubParser` (ebooklib) |
| JSON | `.json` | `JSONParser` (pretty-prints, optionally summarizes via LLM) |
| XML | `.xml` | `XMLParser` (converts to Markdown tree) |

### Media

| Type | Extension(s) | Parser |
|---|---|---|
| Image | `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif` | `ImageParser` (VLM description) |
| Audio | `.mp3`, `.mp4`, `.wav`, `.m4a`, `.ogg` | `AudioParser` (faster-whisper) |
| Video (audio track) | `.mp4`, `.mkv`, `.webm` | `AudioParser` (extracts audio → transcribes) |

---

## Phase 1 Features (Core MVP)

### 1. Dual-Mode Web Fetching
SCRYBE auto-detects whether a page requires JavaScript execution. If a static fetch returns a near-empty `<body>`, SCRYBE escalates automatically to Playwright.

```python
result = await scrybe.read("https://some-spa-react-app.com")
# → Playwright fires automatically, page is fully rendered before parsing
```

### 2. Noise Scrubbing
The `NoiseScrubber` strips the following from HTML before conversion:

- `<nav>`, `<header>`, `<footer>`, `<aside>` elements
- Cookie banners, GDPR notices (heuristic class/id matching)
- `<script>`, `<style>`, `<iframe>`, `<noscript>` tags
- Ad containers (`div[id*="ad"]`, `div[class*="banner"]`, etc.)
- Social share buttons, comment sections
- Form elements: `<form>`, `<input>`, `<button>`, `<select>`
- Audio/video players (but retains `<img>`)

### 3. Image Enrichment
Every image encountered is:
1. Retained with its original URL or relative path preserved in Markdown
2. Passed through a configured VLM (local or API) for a brief, contextual caption
3. Rendered as: `![{vlm_caption}]({original_url})`

### 4. Table Normalization
Tables are extracted and converted into proper GitHub-Flavored Markdown tables. Multi-row headers, colspan/rowspan, and nested tables are handled with best-effort flattening.

### 5. Code Block Detection
Inline `<code>` and block `<pre>` elements are converted with language detection using the `pygments` lexer guessing API.

### 6. Metadata Extraction
Every `ScrybedDocument` includes a `metadata` dict:

```python
{
  "title": str,
  "description": str,        # og:description or meta description
  "author": str,
  "published_date": str,     # ISO 8601 if found
  "source_url": str,
  "content_type": str,       # "webpage" | "pdf" | "docx" | ...
  "language": str,           # detected via langdetect
  "word_count": int,
  "image_count": int,
  "reading_time_minutes": float,
  "scrybe_version": str,
  "scraped_at": str,         # ISO 8601 timestamp
}
```

---

## Phase 2 Features (Planned)

### 7. Chunking Engine
For RAG pipelines and LLM context windows. Supports:

- **Fixed-size chunking** with configurable overlap
- **Semantic chunking** by heading hierarchy (H1 → H2 → H3)
- **Paragraph-aware chunking** (no mid-sentence splits)

```python
result = await scrybe.read(url, chunk=True, chunk_strategy="semantic", max_chunk_tokens=512)
# → result.chunks: list[str]
```

### 8. Caching Layer
Content-addressed cache (MD5 of URL/path) with configurable TTL. Backed by local filesystem or Redis.

```python
scrybe = Scrybe(cache=True, cache_ttl=3600)  # 1-hour TTL
```

### 9. Batch Processing
Process multiple sources concurrently via `asyncio`.

```python
results = await scrybe.read_many(["url1", "url2", "path/to/file.pdf"], concurrency=5)
```

### 10. Output Formats
Beyond Markdown, SCRYBE supports:

- `json` — structured JSON with sections, metadata, images
- `html` — cleaned HTML (without noise)
- `plaintext` — raw extracted text, no formatting
- `llm_context` — Markdown optimized for LLM context windows (compresses redundant whitespace, removes decorative elements)

```python
result = await scrybe.read(url, output_format="json")
```

### 11. LLM Summarization Mode
Optionally pass extracted Markdown through an LLM (local via Ollama, or API) for a structured summary alongside the full content.

```python
result = await scrybe.read(url, summarize=True, summarize_model="ollama/mistral")
# → result.summary: str
# → result.full_markdown: str
```

### 12. API Server Mode
SCRYBE ships with a FastAPI wrapper exposable as a microservice.

```bash
scrybe serve --host 0.0.0.0 --port 8420
```

```http
POST /read
Content-Type: application/json

{
  "source": "https://example.com/article",
  "output_format": "markdown",
  "chunk": false
}
```

---

## Python Stack

| Responsibility | Library |
|---|---|
| HTTP client | `httpx` (async) |
| Browser automation | `playwright` |
| HTML parsing | `beautifulsoup4`, `lxml` |
| HTML → Markdown | `markdownify` |
| PDF extraction | `PyMuPDF` (fitz) |
| OCR (scanned PDFs) | `pytesseract` + `Pillow` |
| Word documents | `python-docx` |
| PowerPoint | `python-pptx` |
| Excel / CSV | `openpyxl`, `pandas` |
| EPUB | `ebooklib` |
| RSS feeds | `feedparser` |
| YouTube | `yt-dlp`, `youtube-transcript-api` |
| Audio transcription | `faster-whisper` |
| Image VLM captions | `transformers` (LLaVA / InternVL / configurable) |
| Language detection | `langdetect` |
| Code language detection | `pygments` |
| API server | `fastapi`, `uvicorn` |
| Caching | `diskcache` (local) / `redis` (optional) |
| Config management | `pydantic-settings` |
| CLI | `typer` |

---

## Interface

### Python SDK

```python
from scrybe import Scrybe

scrybe = Scrybe(
    vlm_model="llava",         # VLM for image captioning
    vlm_backend="ollama",      # "ollama" | "openai" | "huggingface"
    dynamic_threshold=500,     # chars; below this → escalate to Playwright
    cache=True,
    cache_ttl=1800,
)

# Single source
doc = await scrybe.read("https://news.ycombinator.com")
print(doc.markdown)
print(doc.metadata)

# From file
doc = await scrybe.read("/path/to/report.pdf")

# From raw bytes
doc = await scrybe.read(pdf_bytes, mime_type="application/pdf")

# Batch
docs = await scrybe.read_many(["url1", "url2", "file.docx"], concurrency=4)
```

### CLI

```bash
# Read a URL
scrybe read https://example.com

# Read a file
scrybe read ./report.pdf

# Output as JSON
scrybe read https://example.com --format json

# Enable chunking
scrybe read ./big-doc.pdf --chunk --chunk-strategy semantic --max-tokens 512

# Start API server
scrybe serve --port 8420
```

---

## Output: `ScrybedDocument`

```python
@dataclass
class ScrybedDocument:
    markdown: str               # The primary output
    metadata: dict              # Structured metadata
    images: list[ImageRecord]   # All images with URLs + captions
    chunks: list[str] | None    # Populated if chunking was requested
    summary: str | None         # Populated if summarization was requested
    raw_text: str               # Plain text, no formatting
    source: str                 # Original input (URL or path)
    content_type: str           # Detected format
    success: bool
    errors: list[str]           # Non-fatal warnings / fallback notices
```

---

## Roadmap

| Phase | Status | Scope |
|---|---|---|
| Phase 1 | `In Progress` | HTML, PDF, DOCX, PPTX, XLSX, images, audio, dynamic pages, VLM image captioning, metadata |
| Phase 2 | `Planned` | Chunking engine, caching, batch processing, output formats, API server mode |
| Phase 3 | `Planned` | LLM summarization, EPUB, RSS, YouTube, JSON/XML, code repository ingestion |
| Phase 4 | `Future` | Browser extension integration, webhook support, live content monitoring |

---

*SCRYBE — part of the BRAHMAI ecosystem.*