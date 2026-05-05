# SCRYBE

## Overview

SCRYBE is a Python-first content ingestion API built to convert messy web URLs and documents into structured, LLM-readable data.

Its job is simple:

- take a URL
- fetch the real content
- remove noise
- preserve semantic structure
- return clean Markdown or structured JSON

SCRYBE exists because most webpages are designed for humans, not language models. Raw HTML is noisy, layout-heavy, repetitive, and often structurally misleading. SCRYBE reconstructs a document that is much closer to something an LLM can actually reason over.

---

## What SCRYBE Does

At a high level, SCRYBE turns:

- landing pages
- articles
- documentation pages
- JS-heavy web apps
- PDFs
- OCR-heavy documents

into:

- semantic Markdown
- structured JSON
- optional chunks
- optional summaries
- optional image captions

The output is designed for:

- RAG pipelines
- agents
- long-context workflows
- enterprise knowledge systems
- downstream summarization and reasoning

---

## Core Product Idea

The key idea behind SCRYBE is not scraping.

The key idea is document reconstruction.

SCRYBE does not just dump visible text from a page. It attempts to recover a more meaningful document by:

- identifying the real content root
- removing navigation, banners, boilerplate, and clutter
- preserving headings, sections, lists, links, tables, and code blocks
- detecting when static HTML is insufficient
- escalating to browser rendering only when needed
- falling back to OCR/document parsing when native extraction is weak

The result is a calmer, cleaner, more semantically useful representation of content.

---

## Product Shape

SCRYBE is implemented as an API service.

Primary endpoints:

- `GET /v1/parse/json?url=...`
- `GET /v1/parse/markdown?url=...`
- `POST /v1/parse/{format}`
- `POST /v1/jobs`
- `GET /v1/jobs/{job_id}`
- `GET /v1/health`
- `GET /v1/capabilities`

SCRYBE supports both:

- synchronous parsing for lighter pages
- async job-based parsing for heavier or more expensive workloads

---

## How It Works

### 1. Fetch

SCRYBE starts with a static HTTP fetch.

If the page appears too thin, too shell-like, or explicitly requires it, SCRYBE escalates to browser rendering using Playwright.

### 2. Parse

SCRYBE routes content by type:

- HTML pages through a semantic DOM-to-Markdown parser
- PDFs through native extraction first
- OCR-heavy or difficult docs through LiteParse fallback
- structured files like JSON, XML, RSS, and CSV through dedicated format handlers

### 3. Normalize

SCRYBE then normalizes output into a consistent internal document shape containing:

- source
- content type
- markdown
- raw text
- metadata
- images
- warnings
- timings

### 4. Enrich

Optional enrichments include:

- chunking
- OpenAI summaries
- image captions

These are opt-in so cost and latency stay under control.

---

## Output Philosophy

SCRYBE output is designed to be directly usable by an LLM.

Markdown output includes a metadata preamble such as:

- title
- meta description
- author
- published date
- content type
- language
- URL source

followed by the normalized content body.

JSON output exposes the same document in a more structured envelope for applications that want stable fields and machine-side processing.

---

## Technical Positioning

SCRYBE is:

- Python-first
- API-first
- LLM-oriented
- deterministic by default
- extensible through optional enrichment

Although OCR/document fallback can depend on Node-based tooling, that dependency is hidden behind Python adapters. The public product remains a Python-owned service surface.

---

## Why It Matters

Most “web to text” systems fail in one of two ways:

- they return raw, noisy, low-trust dumps
- they overcomplicate the pipeline with unnecessary model calls

SCRYBE is meant to sit in the middle:

- structured enough to be useful
- deterministic enough to be reliable
- extensible enough to handle real-world documents

That makes it a strong fit for enterprise AI systems where provenance, cleanliness, and predictable output shape matter.

---

## Ideal Use Cases

- ingesting company websites into internal knowledge systems
- turning documentation into clean RAG-ready corpora
- normalizing competitor, market, or research pages for agents
- extracting readable content from JS-heavy modern websites
- converting PDFs and scanned docs into structured context
- building enterprise ingestion pipelines behind a single API

---

## BRAHMAI Positioning

SCRYBE should be positioned as:

**An experimental intelligence infrastructure product from BRAHMAI.**

More specifically, it fits naturally into BRAHMAI’s stack as the ingestion and document reconstruction layer that prepares external knowledge for downstream reasoning systems, memory systems, and agentic workflows.

It is not just a parser.

It is a context preparation engine.

---

## Suggested Product Taglines

- URLs in. Structured context out.
- Read anything. Return what an LLM can actually use.
- Document reconstruction for machine reasoning.
- From messy pages to calm context.
- The ingestion layer for intelligent systems.

---

## Current State

SCRYBE currently includes:

- FastAPI service surface
- semantic HTML extraction
- markdown and JSON responses
- async jobs
- metadata preamble generation
- browser escalation via Playwright
- OCR/document fallback via LiteParse adapter
- optional OpenAI enrichment hooks
- dedicated landing page

Future improvements can include:

- richer landing-page and feature-grid extraction heuristics
- stronger PDF/document structural recovery
- cache backends beyond local disk
- auth and multi-tenant controls
- more advanced chunking and summarization policies

---

## One-Line Summary

SCRYBE is a URL-to-structured-context API that converts noisy web content and documents into clean, semantically useful Markdown and JSON for LLMs, agents, and enterprise knowledge systems.
